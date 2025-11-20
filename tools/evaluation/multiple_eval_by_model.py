#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 평가 시스템 - 통합 버전
O, X 문제를 포함한 객관식 문제 평가 시스템

사용법:
    # OpenRouter API 모드 (기본값)
    python multiple_eval_by_model.py --data_path /path/to/data --sample_size 1000 --api
    
    # vLLM 서버 모드
    python multiple_eval_by_model.py --data_path /path/to/data --sample_size 1000 --server
"""

import os
import pandas as pd
import numpy as np
import re
import time
import logging
import random
import json
import datetime as dt
from typing import List, Dict, Tuple, Iterable, Set, Any
from dataclasses import dataclass
from tqdm import tqdm
import argparse

# -----------------------------
# 로깅 설정
# -----------------------------
# pipeline/config에서 PROJECT_ROOT_PATH, ONEDRIVE_PATH, SFAICENTER_PATH import 시도
try:
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.dirname(current_dir)  # tools
    sys.path.insert(0, project_root_dir)
    from pipeline.config import PROJECT_ROOT_PATH, ONEDRIVE_PATH, SFAICENTER_PATH
    project_root = PROJECT_ROOT_PATH
    onedrive_path = ONEDRIVE_PATH
    sfaicenter_path = SFAICENTER_PATH
except ImportError:
    # fallback: pipeline이 없는 경우 현재 스크립트 기준으로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    import platform
    system = platform.system()
    home_dir = os.path.expanduser("~")
    if system == "Windows":
        onedrive_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
    else:
        onedrive_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
    sfaicenter_path = project_root  # fallback

# 중앙화된 로깅 유틸리티 사용
from core.logger import setup_logger
logger = setup_logger(
    name=__name__,
    log_file='multiple_eval_by_model.log',
    use_console=True,
    use_file=True
)

# -----------------------------
# 유틸: 텍스트 정규화
# -----------------------------
CIRCLED_MAP = {"①":"1","②":"2","③":"3","④":"4","⑤":"5"}

# normalize_option_text는 core.utils.TextProcessor.normalize_option_text를 사용
# 중복 제거를 위해 여기서는 제거하고 core.utils에서 import
from core.utils import TextProcessor
normalize_option_text = TextProcessor.normalize_option_text

# -----------------------------
# O, X 문제 처리 개선
# -----------------------------

def is_ox_question(question: str, options: list) -> bool:
    """O, X 문제인지 판단"""
    if not options or len(options) == 0:
        return False
    # options가 비어있거나 2개 이하이고, O/X 형태인지 확인
    if len(options) <= 2:
        option_text = " ".join(options).upper()
        return "O" in option_text or "X" in option_text
    return False

def parse_answer_set(ans, question: str = "", options: list = None) -> Set[int]:
    """정답 파싱 함수 - O, X 문제도 처리, 리스트 답안도 처리 (변형 시험지용)"""
    if not ans:
        return set()
    
    # 리스트 답안 처리 (변형 시험지의 경우: ["①", "③"] 형식)
    if isinstance(ans, list):
        result_set = set()
        for item in ans:
            if not item:
                continue
            s = str(item).strip()
            # ①~⑤ 를 1~5로 치환
            for k, v in CIRCLED_MAP.items():
                s = s.replace(k, v)
            # 1~5 숫자 추출
            nums = re.findall(r"[1-5]", s)
            result_set.update(int(n) for n in nums)
        return result_set
    
    # 문자열 답안 처리 (기존 로직)
    s = str(ans).strip()
    
    # O, X 문제 처리
    if s.upper() in ['O', 'X']:
        # O, X 문제는 1번(O), 2번(X)으로 변환
        return {1} if s.upper() == 'O' else {2}
    
    # ①~⑤ 를 1~5로 치환
    for k, v in CIRCLED_MAP.items():
        s = s.replace(k, v)
    # 쉼표/슬래시/공백 구분 모두 허용하여 1~5 추출
    nums = re.findall(r"[1-5]", s)
    return set(int(n) for n in nums)

# -----------------------------
# JSON → df_all 변환
# -----------------------------

def json_to_df_all(json_list: List[dict], use_ox_support: bool = False, transformed: bool = False) -> pd.DataFrame:
    """
    JSON → df_all 변환 함수
    컬럼: subject, domain, subdomain, book_id, tag, id, question, opt1..opt5, answer_set [, is_ox_question]
    
    Args:
        json_list: JSON 데이터 리스트
        use_ox_support: O, X 문제 지원 여부 (기본값: False)
        transformed: 변형 시험지 여부 (기본값: False, True면 answer가 리스트일 수 있음)
    
    Note:
        중복 제거는 하지 않습니다. ID만 고유하게 만듭니다.
    """
    rows = []
    for item in json_list:
        book_id = str(item.get("file_id", ""))
        
        # 최상위 구조 (exam 파일 구조)
        tag = item.get("tag", "")
        q = (item.get("question") or "").strip()
        opts = item.get("options", [])
        answer = item.get("answer", "")
        domain = item.get("domain", "")
        subdomain = item.get("subdomain", "")
        
        # 변형 시험지의 경우 answer가 리스트일 수 있음 (parse_answer_set에서 처리)
        ans_set = parse_answer_set(answer, q, opts)
        
        # O, X 문제인지 판단 (ox 모드가 켜진 경우에만)
        is_ox = False
        if use_ox_support:
            is_ox = is_ox_question(q, opts)
            
            if is_ox:
                # O, X 문제는 2개 선지로 고정
                opts = ["O", "X"] + [""] * 3
            else:
                # 5지선다 기준으로 빈칸 보정
                opts = list(opts)[:5] + [""] * max(0, 5 - len(opts))
        else:
            # 5지선다 기준으로 빈칸 보정
            opts = list(opts)[:5] + [""] * max(0, 5 - len(opts))
        
        opts = [normalize_option_text(x) for x in opts]
        
        # subject 정보 추출
        subject = item.get("subject", "")

        # 기본 컬럼 구성
        row_data = {
            "subject": subject,
            "domain": domain,
            "subdomain": subdomain,
            "book_id": book_id,
            "tag": tag,
            "id": f"{book_id}_{tag}",
            "question": q,
            "opt1": opts[0], "opt2": opts[1], "opt3": opts[2], "opt4": opts[3], "opt5": opts[4],
            "answer_set": ans_set
        }
        
        # ox 모드가 켜진 경우에만 is_ox_question 추가
        if use_ox_support:
            row_data["is_ox_question"] = is_ox
        
        rows.append(row_data)
    df = pd.DataFrame(rows)
    
    # 데이터 수 로깅
    original_count = len(df)
    logger.info(f"JSON 변환 완료: {original_count}개 문제")
    
    # 중복 ID 확인 (정보만 출력)
    duplicate_ids = df[df.duplicated(subset=["id"], keep=False)]
    unique_duplicate_ids = set()  # 초기화
    
    if len(duplicate_ids) > 0:
        duplicate_count = len(duplicate_ids)
        unique_duplicate_ids = set(duplicate_ids["id"].unique())
        logger.info(f"중복된 ID 발견: {duplicate_count}개 행, {len(unique_duplicate_ids)}개 고유 ID")
        
        # 중복 상세 정보 (각 ID별 중복 횟수)
        id_counts = df["id"].value_counts()
        duplicated_id_counts = id_counts[id_counts > 1]
        if len(duplicated_id_counts) > 0:
            logger.info(f"ID별 중복 횟수 (최대 10개):")
            for dup_id, count in duplicated_id_counts.head(10).items():
                logger.info(f"  - {dup_id}: {count}회")
    
    # ID 중복이 있으면 인덱스를 추가하여 고유하게 만들기 (pivot 시 문제 방지)
    # 중복 제거는 하지 않고, ID만 고유하게 만듦
    if len(unique_duplicate_ids) > 0:
        logger.info(f"ID 중복 발견 ({len(unique_duplicate_ids)}개 고유 ID) - 인덱스를 추가하여 고유 ID 생성 중...")
        df = df.reset_index(drop=True)
        # 중복된 ID에 대해서만 인덱스 추가
        df['id'] = df.apply(
            lambda row: f"{row['id']}_{row.name}" if row['id'] in unique_duplicate_ids else row['id'],
            axis=1
        )
        logger.info("고유 ID 생성 완료")
    else:
        logger.info(f"ID 중복 없음: 모든 {original_count}개 문제의 ID가 고유합니다")
    
    return df

# -----------------------------
# 배치 사용자 프롬프트 생성
# -----------------------------

SYSTEM_PROMPT = """당신은 금융전문가이자 객관식 문제 풀이 전문가입니다.
여러 금융 객관식 문제에 대해, 각 문제의 정답 "번호만" 하나 선택합니다.

규칙
- 각 문제는 고유 ID와 함께 제시됩니다.
- 출력은 반드시 한 줄당 "ID<TAB>번호" 형식으로만 합니다. (예: SS0000_q_0377_0001<TAB>3)
- 다른 글자, 마크다운, 이유, 기호는 절대 출력하지 않습니다.
- 모든 문제는 보기(1~5) 중 하나만 고릅니다.
- 출력 줄 수는 입력 문제 개수와 동일해야 합니다.
"""

SYSTEM_PROMPT_TRANSFORMED = """당신은 금융전문가이자 객관식 문제 풀이 전문가입니다.
여러 금융 객관식 문제에 대해, 각 문제는 "모두 고르시오" 유형입니다. 정답이 되는 모든 번호를 선택합니다.

규칙
- 각 문제는 고유 ID와 함께 제시됩니다.
- 출력은 반드시 한 줄당 "ID<TAB>번호1,번호2,..." 형식으로만 합니다. (예: SS0000_q_0377_0001<TAB>1,3 또는 SS0000_q_0377_0001<TAB>1 3)
- 여러 정답이 있는 경우 쉼표(,) 또는 공백으로 구분하여 모두 선택합니다. (예: 1,3 또는 1 3)
- 정답이 하나인 경우에도 동일한 형식을 사용합니다. (예: 3 또는 3)
- 다른 글자, 마크다운, 이유, 기호는 절대 출력하지 않습니다.
- 모든 문제는 보기(1~5) 중 하나 이상을 선택합니다.
- 출력 줄 수는 입력 문제 개수와 동일해야 합니다.
"""

def build_user_prompt(batch_df: pd.DataFrame, transformed: bool = False) -> str:
    lines = []
    if transformed:
        lines.append("다음은 금융 객관식 문제들입니다. 각 문제는 '모두 고르시오' 유형입니다. 정답이 되는 모든 번호를 선택하세요.\n")
    else:
        lines.append("다음은 금융 객관식 문제들입니다. 각 문제에 대해 정답 번호만 고르세요.\n")
    lines.append("문제들")
    for _, r in batch_df.iterrows():
        lines.append(f"ID: {r['id']}")
        lines.append(f"Q: {r['question']}")
        lines.append(f"1) {r['opt1']}")
        lines.append(f"2) {r['opt2']}")
        lines.append(f"3) {r['opt3']}")
        lines.append(f"4) {r['opt4']}")
        lines.append(f"5) {r['opt5']}\n")
    lines.append("출력 형식(중요)")
    for _, r in batch_df.iterrows():
        if transformed:
            lines.append(f"{r['id']}\\t{{번호1,번호2,...}}  (예: 1,3 또는 1 3)")
        else:
            lines.append(f"{r['id']}\\t{{번호}}")
    return "\n".join(lines)

# -----------------------------
# LLM 호출 추상화
# -----------------------------

# 모델 캐시를 위한 전역 변수
_model_cache = {}
_config_cache = None
_query_models_module = None

def _find_config_file():
    """Config 파일 경로를 찾습니다 (LLMQuery._find_config_file과 동일한 로직)"""
    # 프로젝트 루트에서 llm_config.ini 찾기
    default_path = os.path.join(project_root, 'llm_config.ini')
    if os.path.exists(default_path):
        return default_path
    
    # 찾지 못한 경우 find 명령어로 검색 (fallback)
    config_path = os.popen(f"find {project_root} -type f -name 'llm_config.ini' 2>/dev/null").read().strip()
    if config_path and os.path.exists(config_path):
        return config_path
    
    # 찾지 못한 경우 기본값 반환
    return default_path

def _load_config():
    """Config 파일을 한 번만 로드하고 캐시"""
    global _config_cache
    if _config_cache is None:
        import configparser
        # LLMQuery와 동일한 방식으로 config 파일 찾기
        config_path = _find_config_file()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config 파일을 찾을 수 없습니다: {config_path}")
        
        _config_cache = configparser.ConfigParser()
        _config_cache.read(config_path, encoding='utf-8')
        logger.info(f"[CACHE] Config 파일 로드 완료: {config_path}")
    
    return _config_cache

def _load_query_models(api_key: str = None):
    """LLMQuery 인스턴스를 한 번만 생성하고 캐시
    
    Args:
        api_key: API 키 (None이면 기본 key 사용, key_evaluate 등 다른 키 사용 가능)
    """
    global _query_models_module
    # api_key가 제공되면 캐시를 무시하고 새 인스턴스 생성
    if _query_models_module is None or api_key is not None:
        import sys
        import os
        # tools/core/llm_query.py에서 LLMQuery 클래스 import
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tools_dir = os.path.dirname(current_dir)  # evaluation -> tools
        sys.path.insert(0, tools_dir)
        
        try:
            from core.llm_query import LLMQuery
            _query_models_module = LLMQuery(api_key=api_key)
            if api_key:
                logger.info(f"[CACHE] LLMQuery 인스턴스 생성 완료 (커스텀 API 키 사용): {tools_dir}")
            else:
                logger.info(f"[CACHE] LLMQuery 인스턴스 생성 완료: {tools_dir}")
        except Exception as e:
            logger.error(f"[CACHE] LLMQuery 인스턴스 생성 실패: {e}")
            raise
    return _query_models_module

def _load_model_cached(model_name: str):
    """모델을 캐시에서 로드하거나 새로 로드"""
    global _model_cache
    
    if model_name not in _model_cache:
        logger.info(f"[CACHE] 모델 로드 중: {model_name}")
        llm_query = _load_query_models()
        
        # LLMQuery.load_vllm_model은 model_path를 받으므로, model_name을 model_path로 사용
        # vLLM 모델 경로는 model_name과 동일하다고 가정
        llm_query.load_vllm_model(model_name)
        
        # LLMQuery 인스턴스에서 llm, tokenizer, sampling_params 가져오기
        llm = llm_query.llm
        tokenizer = llm_query.tokenizer
        sampling_params = llm_query.sampling_params
        
        _model_cache[model_name] = (llm, tokenizer, sampling_params)
        logger.info(f"[CACHE] 모델 로드 완료: {model_name}")
    else:
        logger.debug(f"[CACHE] 캐시된 모델 사용: {model_name}")
    
    return _model_cache[model_name]

def clear_model_cache():
    """모델 캐시를 정리하여 메모리 해제"""
    global _model_cache
    if _model_cache:
        logger.info(f"[CACHE] {len(_model_cache)}개 모델 캐시 정리 중...")
        _model_cache.clear()
        logger.info("[CACHE] 모델 캐시 정리 완료")

def get_cache_info():
    """현재 캐시 상태 정보 반환"""
    global _model_cache, _config_cache, _query_models_module
    return {
        "cached_models": list(_model_cache.keys()),
        "config_loaded": _config_cache is not None,
        "query_models_loaded": _query_models_module is not None
    }

def call_llm(model_name: str, system_prompt: str, user_prompt: str, use_server_mode: bool=False, max_retries: int=3, api_key: str = None) -> Tuple[str, float]:
    """
    - use_server_mode=True면 vLLM 서버 모드로 호출
    - use_server_mode=False면 OpenRouter API로 호출
    - api_key: API 키 (None이면 기본 key 사용, key_evaluate 등 다른 키 사용 가능)
    - 에러 핸들링 및 재시도 로직 포함
    
    Returns:
        Tuple[str, float]: (응답 문자열, 소요 시간(초))
    """
    for attempt in range(max_retries):
            try:
                if use_server_mode:
                    # vLLM 서버 모드 - 캐시된 모델 사용
                    logger.debug(f"[VLLM] 모델 {model_name} 호출 시작 (시도 {attempt + 1}/{max_retries})")
                    start_time = time.time()
                    
                    # 캐시된 모델 로드
                    llm, tokenizer, sampling_params = _load_model_cached(model_name)
                    llm_query = _load_query_models(api_key=api_key)
                    
                    # LLMQuery.query_vllm은 인스턴스 메서드이므로 직접 호출
                    # 하지만 모델이 이미 로드되어 있어야 함
                    ans = llm_query.query_vllm(system_prompt, user_prompt)
                    
                    elapsed_time = time.time() - start_time
                    logger.debug(f"[VLLM] 모델 {model_name} 호출 완료 - 소요시간: {elapsed_time:.2f}초")
                    
                    return ans, elapsed_time
                else:
                    # OpenRouter API 모드
                    logger.debug(f"[API] 모델 {model_name} 호출 시작 (시도 {attempt + 1}/{max_retries})")
                    start_time = time.time()
                    
                    # LLMQuery 인스턴스 사용
                    llm_query = _load_query_models(api_key=api_key)
                    
                    # LLMQuery.query_openrouter 시그니처: (system_prompt, user_prompt, model_name)
                    ans = llm_query.query_openrouter(system_prompt, user_prompt, model_name)
                    
                    elapsed_time = time.time() - start_time
                    logger.debug(f"[API] 모델 {model_name} 호출 완료 - 소요시간: {elapsed_time:.2f}초")
                    time.sleep(1.5)
                    
                    return ans, elapsed_time
                
            except Exception as e:
                mode_str = "[VLLM]" if use_server_mode else "[API]"
                logger.warning(f"{mode_str} 모델 {model_name} 호출 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"{mode_str} 모델 {model_name} 최종 실패 - 모든 재시도 소진")
                    raise e
                else:
                    wait_time = 2 ** attempt  # 지수 백오프
                    logger.info(f"{mode_str} {wait_time}초 후 재시도...")
                    time.sleep(wait_time)

# -----------------------------
# 모델 출력 파싱 
# -----------------------------

def parse_model_output(raw: str, expected_ids: List[str], transformed: bool = False) -> Dict[str, Any]:
    """
    모델 원시 출력(raw)을 파싱.
    - 기본 모드: {id: answer(1~5)} - 단일 답안
    - 변형 모드: {id: Set[int]} - 여러 답안 (모두 고르시오)
    - 'ID\\t번호' 포맷 기준
    - 잘못된 줄/누락 줄은 NaN 처리
    """
    id_set = set(expected_ids)
    if transformed:
        # 변형 모드: Set[int] 반환
        out: Dict[str, Set[int]] = {k: set() for k in expected_ids}
    else:
        # 기본 모드: float 반환 (단일 답안)
        out: Dict[str, float] = {k: np.nan for k in expected_ids}
    
    if not raw or not raw.strip():
        logger.warning("모델 출력이 비어있습니다.")
        return out

    # 탭 구분 포맷 처리
    lines = raw.splitlines()
    logger.debug(f"파싱할 줄 수: {len(lines)}")
    
    for i, ln in enumerate(lines):
        ln = ln.strip()
        logger.debug(f"줄 {i+1}: '{ln}'")
        
        if not ln:
            logger.debug(f"줄 {i+1}: 빈 줄, 스킵")
            continue
        
        # 탭 정규화: <TAB>, 실제 탭, \\t 모두 \t로 변환
        # 1. <TAB> (literal string) -> \t
        ln = ln.replace("<TAB>", "\t")
        # 2. \\t (backslash-t) -> \t
        ln = ln.replace("\\t", "\t")
        # 3. 실제 탭 문자는 이미 \t이므로 추가 처리 불필요
        logger.debug(f"줄 {i+1} (탭 정규화 후): '{ln}'")
            
        if "\t" not in ln:
            logger.debug(f"줄 {i+1}: 탭이 없음, 스킵")
            continue
            
        left, right = ln.split("\t", 1)
        _id = left.strip()
        logger.debug(f"줄 {i+1}: ID='{_id}', 답변='{right}'")
        
        if _id not in id_set:
            logger.debug(f"줄 {i+1}: ID '{_id}'가 예상 목록에 없음, 스킵")
            continue
        
        if transformed:
            # 변형 모드: 여러 답안 파싱 (예: "1,3" 또는 "1 3" 또는 "1, 3")
            # 쉼표 또는 공백으로 구분된 모든 숫자 추출
            # ①~⑤ 를 1~5로 치환
            answer_str = right
            for k, v in CIRCLED_MAP.items():
                answer_str = answer_str.replace(k, v)
            # 쉼표, 공백, 슬래시 등으로 구분된 모든 1~5 숫자 추출
            nums = re.findall(r"[1-5]", answer_str)
            if nums:
                answer_set = set(int(n) for n in nums)
                out[_id] = answer_set
                logger.debug(f"줄 {i+1}: ID '{_id}' -> 답변 {answer_set}")
            else:
                logger.debug(f"줄 {i+1}: ID '{_id}'의 답변에서 1~5 숫자를 찾을 수 없음")
        else:
            # 기본 모드: 첫 번째 1~5 추출 (중괄호 포함: {4}, {5} 등도 인식)
            # 중괄호로 둘러싸인 숫자 또는 일반 숫자 모두 인식
            m = re.search(r"\{?([1-5])\}?", right)
            if m:
                answer = float(m.group(1))
                out[_id] = answer
                logger.debug(f"줄 {i+1}: ID '{_id}' -> 답변 {answer}")
            else:
                logger.debug(f"줄 {i+1}: ID '{_id}'의 답변에서 1~5 숫자를 찾을 수 없음")
    
    return out

# -----------------------------
# 평가 파이프라인
# -----------------------------

def run_eval_pipeline(
    json_list: List[dict],
    models: List[str],
    sample_size: int = 300,
    batch_size: int = 50,
    seed: int = 42,
    use_server_mode: bool = False,
    use_ox_support: bool = True,
    api_key: str = None,
    output_base_dir: str = None,
    transformed: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    평가 파이프라인
    
    Args:
        json_list: 평가할 JSON 데이터 리스트
        models: 평가할 모델 목록
        sample_size: 샘플 크기
        batch_size: 배치 크기
        seed: 랜덤 시드
        use_server_mode: vLLM 서버 모드 사용 여부
        use_ox_support: O, X 문제 지원 여부
        api_key: API 키 (None이면 기본 key 사용, key_evaluate 등 다른 키 사용 가능)
        output_base_dir: 출력 기본 디렉토리 (None이면 기본 경로 사용: 6_exam_evaluation)
        transformed: 변형 시험지 여부 (기본값: False, True면 answer가 리스트일 수 있음)
    
    반환:
      df_all      : 전체 원장 (정규화 선지 + answer_set + is_ox_question)
      pred_long   : (id, model_name, answer) 롱 포맷
      pred_wide   : id 기준 모델별 예측 와이드
      acc_by_model: 모델별 정확도 (복수정답 지원: 예측 ∈ answer_set 이면 정답)
    """
    logger.info(f"평가 파이프라인 시작 - 샘플수: {sample_size}, 배치크기: {batch_size}, 모델수: {len(models)}, O/X 지원: {use_ox_support}, 변형 모드: {transformed}")
    
    # 전체 실행 시간 추적 시작
    overall_start_time = time.time()
    overall_start_datetime = dt.datetime.now()
    
    # (1) JSON → df_all
    logger.info("1단계: JSON 데이터를 DataFrame으로 변환 중...")
    # 중복 제거는 하지 않음 (모든 문제 유지)
    df_all = json_to_df_all(json_list, use_ox_support=use_ox_support, transformed=transformed)
    df_all = df_all.sort_values(by=['book_id', 'tag'], ascending=False).reset_index(drop=True)
    logger.info(f"전체 데이터: {len(df_all)}개 문제")
    
    # 데이터 품질 검사 (중복 문제 확인 포함)
    quality_report = check_data_quality(json_list, df_all)

    # O, X 문제 분석 (use_ox_support가 True일 때만)
    if use_ox_support:
        ox_questions, regular_questions = analyze_ox_questions(df_all)

    # (2) 샘플링
    logger.info(f"2단계: {sample_size}개 샘플 추출 중...")
    # 샘플 크기가 전체 데이터보다 큰 경우, 전체 데이터 크기로 조정
    actual_sample_size = min(sample_size, len(df_all))
    if actual_sample_size < sample_size:
        logger.warning(f"요청한 샘플 크기({sample_size})가 전체 데이터({len(df_all)})보다 큼. {actual_sample_size}개로 조정합니다.")
    df_sample = df_all.sample(n=actual_sample_size, random_state=seed).reset_index(drop=True)
    logger.info(f"샘플 데이터: {len(df_sample)}개 문제")

    # 샘플에서 O, X 문제 비율 확인 (use_ox_support가 True일 때만)
    if use_ox_support:
        sample_ox = df_sample[df_sample['is_ox_question'] == True]
        sample_regular = df_sample[df_sample['is_ox_question'] == False]
        logger.info(f"샘플 내 O, X 문제: {len(sample_ox)}개, 일반 객관식: {len(sample_regular)}개")

    # (3) 배치 분할
    batches = [df_sample.iloc[i:i+batch_size] for i in range(0, len(df_sample), batch_size)]
    logger.info(f"3단계: {len(batches)}개 배치로 분할 완료")

    # (4) 모델 호출/파싱 누적
    logger.info("4단계: 모델 호출 및 예측 시작...")
    rows = []
    invalid_responses = []  # 무효 예측 응답 저장용
    total_calls = len(batches) * len(models)
    
    # 모델별 응답 시간 추적
    model_response_times = {model: [] for model in models}

    # SYSTEM_PROMPT를 transformed에 따라 선택
    local_system_prompt = SYSTEM_PROMPT_TRANSFORMED if transformed else SYSTEM_PROMPT
    
    # 전체 진행상황 표시
    with tqdm(total=total_calls, desc="모델 호출 진행", unit="call") as pbar:
        for bidx, bdf in enumerate(batches, 1):
            user_prompt = build_user_prompt(bdf, transformed=transformed)
            ids = bdf["id"].tolist()
            
            for model in models:
                try:
                    # 배치별 진행상황 표시 (tqdm 진행바에만 표시, 로그는 최소화)
                    pbar.set_description(f"배치 {bidx}/{len(batches)} - {model}")
                    
                    raw, response_time = call_llm(model, local_system_prompt, user_prompt, use_server_mode=use_server_mode, api_key=api_key)
                    # 모델별 응답 시간 기록
                    model_response_times[model].append(response_time)
                    # 모든 모델 응답을 backlog로 저장
                    if output_base_dir:
                        # output_base_dir이 제공된 경우 사용
                        output_dir = os.path.join(output_base_dir, 'model_output')
                    else:
                        # 기본 경로 사용
                        try:
                            from pipeline.config import ONEDRIVE_PATH
                            base_path = ONEDRIVE_PATH
                        except ImportError:
                            import platform
                            system = platform.system()
                            home_dir = os.path.expanduser("~")
                            if system == "Windows":
                                base_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
                            else:
                                base_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
                        output_dir = os.path.join(base_path, 'evaluation', 'eval_data', '6_exam_evaluation', 'model_output')
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"model_output_{model.replace('/', '_')}.txt")
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*80}\n")
                        f.write(f"배치: {bidx}/{len(batches)}, 모델: {model}, 시간: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"ID 목록: {ids}\n")
                        f.write(f"{'='*80}\n")
                        f.write(raw)
                        f.write(f"\n{'='*80}\n\n")
                    parsed = parse_model_output(raw, ids, transformed=transformed)
                    
                    # 파싱 결과 검증
                    if transformed:
                        # 변형 모드: Set[int] 반환, 빈 집합이면 무효
                        valid_predictions = sum(1 for v in parsed.values() if isinstance(v, set) and len(v) > 0)
                    else:
                        # 기본 모드: float 반환, NaN이 아니면 유효
                        valid_predictions = sum(1 for v in parsed.values() if not np.isnan(v))
                    
                    # 무효 예측이 있는 경우에만 로그 출력
                    if valid_predictions < len(ids):
                        logger.warning(f"배치 {bidx} - {model}: {valid_predictions}/{len(ids)}개 유효 예측 (무효 예측 감지)")
                        logger.warning(f"예상 ID: {ids}")
                        logger.warning(f"모델 원시 출력:\n{raw}")
                        logger.warning(f"파싱된 결과: {parsed}")
                        
                        # 무효 예측 응답 저장 (모델명, 문제, 답변 포함)
                        for _id in ids:
                            is_invalid = False
                            if transformed:
                                # 변형 모드: Set[int]가 빈 집합이면 무효
                                is_invalid = not (isinstance(parsed[_id], set) and len(parsed[_id]) > 0)
                            else:
                                # 기본 모드: NaN이면 무효
                                is_invalid = np.isnan(parsed[_id])
                            
                            if is_invalid:
                                # 문제 정보 가져오기
                                question_info = bdf[bdf['id'] == _id].iloc[0] if len(bdf[bdf['id'] == _id]) > 0 else None
                                
                                invalid_response = {
                                    "model_name": model,
                                    "batch_id": bidx,
                                    "question_id": _id,
                                    "question": question_info['question'] if question_info is not None else "정보 없음",
                                    "options": {
                                        "opt1": question_info['opt1'] if question_info is not None else "",
                                        "opt2": question_info['opt2'] if question_info is not None else "",
                                        "opt3": question_info['opt3'] if question_info is not None else "",
                                        "opt4": question_info['opt4'] if question_info is not None else "",
                                        "opt5": question_info['opt5'] if question_info is not None else ""
                                    },
                                    "correct_answer": list(question_info['answer_set']) if question_info is not None else [],
                                    "model_raw_output": raw,
                                    "parsed_result": list(parsed[_id]) if isinstance(parsed[_id], set) else parsed[_id],
                                    "timestamp": dt.datetime.now().isoformat()
                                }
                                invalid_responses.append(invalid_response)
                    
                    for _id in ids:
                        rows.append({"id": _id, "model_name": model, "answer": parsed[_id]})
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"배치 {bidx} - {model} 처리 중 오류: {str(e)}")
                    # 오류 발생 시 기본값으로 채움
                    for _id in ids:
                        if transformed:
                            rows.append({"id": _id, "model_name": model, "answer": set()})
                        else:
                            rows.append({"id": _id, "model_name": model, "answer": np.nan})
                    pbar.update(1)

    logger.info("5단계: 결과 데이터 정리 중...")
    pred_long = pd.DataFrame(rows)
    pred_long = pred_long.sort_values(by=['id'], ascending=True).reset_index(drop=True)
    
    # (5) 와이드 포맷
    pred_wide = pred_long.pivot(index="id", columns="model_name", values="answer").reset_index()
    pred_wide = pred_wide.sort_values(by=['id'], ascending=True).reset_index(drop=True)

    # (6) 정확도 계산
    logger.info("6단계: 정확도 계산 중...")
    key = df_sample[["id", "answer_set"]].copy()
    
    def _is_correct(pred, s: Set[int], is_transformed: bool = False) -> float:
        """정확도 계산 함수
        - 기본 모드: pred가 float이고 s에 포함되면 정답
        - 변형 모드: pred가 Set[int]이고 모든 답안이 s에 포함되고, pred와 s가 동일하면 정답
        """
        if not s:
            return np.nan
        
        if is_transformed:
            # 변형 모드: pred는 Set[int]
            if not isinstance(pred, set) or len(pred) == 0:
                return np.nan
            # 모델이 선택한 모든 답안이 정답 집합에 포함되고, 개수도 일치해야 정답
            return float(pred == s)
        else:
            # 기본 모드: pred는 float
            if np.isnan(pred):
                return np.nan
            return float(int(pred) in s)

    merged = pred_long.merge(key, on="id", how="left")
    merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"], is_transformed=transformed), axis=1)

    acc_by_model = (
        merged.groupby("model_name", dropna=False)["correct"]
        .mean()
        .reset_index()
        .rename(columns={"correct": "accuracy"})
        .sort_values("accuracy", ascending=False)
    )
    
    # O, X 문제와 일반 문제별 정확도 분석
    sample_with_type = df_sample[["id", "is_ox_question"]].copy()
    merged_with_type = merged.merge(sample_with_type, on="id", how="left")
    
    # O, X 문제 정확도
    ox_accuracy = merged_with_type[merged_with_type['is_ox_question'] == True].groupby("model_name")["correct"].mean()
    regular_accuracy = merged_with_type[merged_with_type['is_ox_question'] == False].groupby("model_name")["correct"].mean()
    
    logger.info("평가 완료!")
    logger.info("모델별 전체 정확도:")
    for _, row in acc_by_model.iterrows():
        logger.info(f"  {row['model_name']}: {row['accuracy']:.3f}")
    
    if len(ox_accuracy) > 0:
        logger.info("O, X 문제 정확도:")
        for model, acc in ox_accuracy.items():
            logger.info(f"  {model}: {acc:.3f}")
    
    # 캐시 정보 로깅
    cache_info = get_cache_info()
    logger.info(f"[CACHE] 평가 완료 후 캐시 상태: {len(cache_info['cached_models'])}개 모델 캐시됨")
    
    # 무효 예측 응답 저장
    if 'invalid_responses' in locals() and invalid_responses:
        save_invalid_responses(invalid_responses, "evaluation", output_base_dir=output_base_dir)
    
    # 전체 실행 시간 추적 종료
    overall_end_time = time.time()
    overall_end_datetime = dt.datetime.now()
    overall_elapsed_time = overall_end_time - overall_start_time
    
    # 모델별 평균 응답 시간 계산 및 출력
    logger.info("=" * 80)
    logger.info("⏱️  실행 시간 통계")
    logger.info("=" * 80)
    logger.info(f"전체 실행 시작 시간: {overall_start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"전체 실행 종료 시간: {overall_end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"전체 실행 소요 시간: {overall_elapsed_time:.2f}초 ({overall_elapsed_time/60:.2f}분)")
    logger.info("")
    logger.info("모델별 평균 응답 시간:")
    for model in models:
        if model_response_times[model]:
            avg_time = np.mean(model_response_times[model])
            total_time = np.sum(model_response_times[model])
            call_count = len(model_response_times[model])
            logger.info(f"  {model}:")
            logger.info(f"    - 평균 응답 시간: {avg_time:.2f}초")
            logger.info(f"    - 총 응답 시간: {total_time:.2f}초 ({total_time/60:.2f}분)")
            logger.info(f"    - 호출 횟수: {call_count}회")
        else:
            logger.info(f"  {model}: 호출 기록 없음")
    logger.info("=" * 80)
    
    # 콘솔에도 출력
    print("\n" + "=" * 80)
    print("⏱️  실행 시간 통계")
    print("=" * 80)
    print(f"전체 실행 시작 시간: {overall_start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"전체 실행 종료 시간: {overall_end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"전체 실행 소요 시간: {overall_elapsed_time:.2f}초 ({overall_elapsed_time/60:.2f}분)")
    print("")
    print("모델별 평균 응답 시간:")
    for model in models:
        if model_response_times[model]:
            avg_time = np.mean(model_response_times[model])
            total_time = np.sum(model_response_times[model])
            call_count = len(model_response_times[model])
            print(f"  {model}:")
            print(f"    - 평균 응답 시간: {avg_time:.2f}초")
            print(f"    - 총 응답 시간: {total_time:.2f}초 ({total_time/60:.2f}분)")
            print(f"    - 호출 횟수: {call_count}회")
        else:
            print(f"  {model}: 호출 기록 없음")
    print("=" * 80 + "\n")
    
    # 실행 시간 통계를 별도 로그 파일로 저장 (모델별로 파일 생성)
    try:
        saved_files = save_timing_statistics(
            overall_start_datetime,
            overall_end_datetime,
            overall_elapsed_time,
            model_response_times,
            models,
            "evaluation",
            output_base_dir=output_base_dir
        )
        logger.info(f"실행 시간 통계 파일 저장 완료: 총 {len(saved_files)}개 파일")
        for file_path in saved_files:
            logger.info(f"  - {file_path}")
    except Exception as e:
        logger.error(f"실행 시간 통계 파일 저장 실패: {str(e)}")
    
    return df_all, pred_long, pred_wide, acc_by_model

# -----------------------------
# 유틸리티 함수들
# -----------------------------

def analyze_ox_questions(df: pd.DataFrame):
    """O, X 문제 분석"""
    ox_questions = df[df['is_ox_question'] == True]
    regular_questions = df[df['is_ox_question'] == False]
    
    print(f"📊 문제 유형 분석")
    print(f"   - O, X 문제: {len(ox_questions)}개")
    print(f"   - 일반 객관식: {len(regular_questions)}개")
    print(f"   - 전체: {len(df)}개")
    
    if len(ox_questions) > 0:
        print(f"\n🔍 O, X 문제 정답 분포:")
        ox_answers = ox_questions['answer_set'].apply(lambda x: list(x) if x else [])
        answer_counts = {}
        for answers in ox_answers:
            for ans in answers:
                answer_counts[ans] = answer_counts.get(ans, 0) + 1
        
        for ans, count in sorted(answer_counts.items()):
            answer_text = "O" if ans == 1 else "X" if ans == 2 else str(ans)
            print(f"   - {answer_text}: {count}개")
    
    return ox_questions, regular_questions

def print_evaluation_summary(acc_df: pd.DataFrame, pred_long_df: pd.DataFrame):
    """평가 결과 요약을 보기 좋게 출력"""
    print("\n" + "="*80)
    print("📊 평가 결과 상세 요약")
    print("="*80)
    
    # 기본 통계
    total_predictions = len(pred_long_df)
    valid_predictions = len(pred_long_df.dropna(subset=['answer']))
    invalid_predictions = total_predictions - valid_predictions
    
    print(f"📈 전체 예측 수: {total_predictions:,}")
    print(f"✅ 유효 예측: {valid_predictions:,} ({valid_predictions/total_predictions*100:.1f}%)")
    print(f"❌ 무효 예측: {invalid_predictions:,} ({invalid_predictions/total_predictions*100:.1f}%)")
    
    # 모델별 정확도
    print(f"\n🏆 모델별 정확도 순위:")
    for i, (_, row) in enumerate(acc_df.iterrows(), 1):
        accuracy = row['accuracy']
        if pd.isna(accuracy):
            print(f"  {i}. {row['model_name']}: N/A (데이터 없음)")
        else:
            print(f"  {i}. {row['model_name']}: {accuracy:.3f} ({accuracy*100:.1f}%)")
    
    print("="*80)

def save_timing_statistics(
    overall_start_datetime: dt.datetime,
    overall_end_datetime: dt.datetime,
    overall_elapsed_time: float,
    model_response_times: Dict[str, List[float]],
    models: List[str],
    filename_prefix: str = "evaluation",
    output_base_dir: str = None
):
    """실행 시간 통계를 별도 로그 파일로 저장 (JSON 및 텍스트 형식) - 모델별로 파일 생성"""
    if output_base_dir:
        # output_base_dir이 제공된 경우 사용
        log_dir = os.path.join(output_base_dir, 'timing_stats')
    else:
        # 기본 경로 사용
        try:
            from pipeline.config import ONEDRIVE_PATH
            base_path = ONEDRIVE_PATH
        except ImportError:
            import platform
            system = platform.system()
            home_dir = os.path.expanduser("~")
            if system == "Windows":
                base_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
            else:
                base_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
        log_dir = os.path.join(base_path, 'evaluation',  'eval_data', '6_exam_evaluation', 'timing_stats')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = overall_end_datetime.strftime("%Y-%m-%d_%H%M%S")
    
    saved_files = []
    
    # 각 모델별로 파일 생성
    for model in models:
        model_name_safe = model.replace('/', '_').replace(':', '_')
        
        if model_response_times[model]:
            times = model_response_times[model]
            model_stat = {
                "average_response_time_seconds": float(np.mean(times)),
                "total_response_time_seconds": float(np.sum(times)),
                "total_response_time_minutes": float(np.sum(times) / 60),
                "call_count": len(times),
                "min_response_time_seconds": float(np.min(times)),
                "max_response_time_seconds": float(np.max(times)),
                "std_response_time_seconds": float(np.std(times))
            }
        else:
            model_stat = {
                "average_response_time_seconds": None,
                "total_response_time_seconds": None,
                "total_response_time_minutes": None,
                "call_count": 0,
                "min_response_time_seconds": None,
                "max_response_time_seconds": None,
                "std_response_time_seconds": None
            }
        
        # 모델별 JSON 파일 저장
        json_data = {
            "evaluation_info": {
                "start_time": overall_start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                "end_time": overall_end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                "start_time_iso": overall_start_datetime.isoformat(),
                "end_time_iso": overall_end_datetime.isoformat(),
                "elapsed_time_seconds": float(overall_elapsed_time),
                "elapsed_time_minutes": float(overall_elapsed_time / 60),
                "elapsed_time_hours": float(overall_elapsed_time / 3600),
                "model_name": model
            },
            "model_statistics": model_stat
        }
        
        # 모델별 마크다운 파일 저장
        md_filename = os.path.join(log_dir, f"STATS_{filename_prefix}_timing_{model_name_safe}_{timestamp}.md")
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(f"# ⏱️ 실행 시간 통계 - {model}\n\n")
            f.write("---\n\n")
            f.write(f"**전체 실행 시작 시간**: {overall_start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**전체 실행 종료 시간**: {overall_end_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**전체 실행 소요 시간**: {overall_elapsed_time:.2f}초 ({overall_elapsed_time/60:.2f}분, {overall_elapsed_time/3600:.2f}시간)\n\n")
            f.write(f"**모델**: {model}\n\n")
            f.write("---\n\n")
            
            if model_response_times[model]:
                avg_time = np.mean(model_response_times[model])
                total_time = np.sum(model_response_times[model])
                call_count = len(model_response_times[model])
                min_time = np.min(model_response_times[model])
                max_time = np.max(model_response_times[model])
                std_time = np.std(model_response_times[model])
                
                f.write("## 응답 시간 통계\n\n")
                f.write("| 항목 | 값 |\n")
                f.write("|------|-----|\n")
                f.write(f"| 평균 응답 시간 | {avg_time:.2f}초 |\n")
                f.write(f"| 총 응답 시간 | {total_time:.2f}초 ({total_time/60:.2f}분) |\n")
                f.write(f"| 호출 횟수 | {call_count:,}회 |\n")
                f.write(f"| 최소 응답 시간 | {min_time:.2f}초 |\n")
                f.write(f"| 최대 응답 시간 | {max_time:.2f}초 |\n")
                f.write(f"| 표준 편차 | {std_time:.2f}초 |\n")
            else:
                f.write("## 응답 시간 통계\n\n")
                f.write("호출 기록 없음\n")
        logger.info(f"실행 시간 통계 (마크다운) 저장 [{model}]: {md_filename}")
        saved_files.append(md_filename)
    
    return saved_files

def save_invalid_responses(invalid_responses: List[Dict], filename_prefix: str = "evaluation", output_base_dir: str = None):
    """무효 예측 응답을 별도 파일로 저장 (모델명, 문제, 답변 포함) - 모델별로 파일 생성"""
    if not invalid_responses:
        logger.info("무효 예측이 없어 저장할 파일이 없습니다.")
        return
    
    if output_base_dir:
        # output_base_dir이 제공된 경우 사용
        invalid_dir = os.path.join(output_base_dir, 'invalid_responses')
    else:
        # 기본 경로 사용
        try:
            from pipeline.config import ONEDRIVE_PATH
            base_path = ONEDRIVE_PATH
        except ImportError:
            import platform
            system = platform.system()
            home_dir = os.path.expanduser("~")
            if system == "Windows":
                base_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
            else:
                base_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
        invalid_dir = os.path.join(base_path, 'evaluation', 'eval_data', '6_exam_evaluation', 'invalid_responses')
    os.makedirs(invalid_dir, exist_ok=True)
    
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # 모델별로 무효 예측 분류
    model_invalid_responses = {}
    for resp in invalid_responses:
        model = resp.get('model_name', 'unknown')
        if model not in model_invalid_responses:
            model_invalid_responses[model] = []
        model_invalid_responses[model].append(resp)
    
    saved_files = []
    
    # 각 모델별로 파일 생성
    for model, model_responses in model_invalid_responses.items():
        model_name_safe = model.replace('/', '_').replace(':', '_')
        invalid_filename = os.path.join(invalid_dir, f"{filename_prefix}_invalid_responses_{model_name_safe}_{timestamp}.json")
        
        try:
            with open(invalid_filename, 'w', encoding='utf-8') as f:
                json.dump(model_responses, f, ensure_ascii=False, indent=2)
            logger.info(f"무효 예측 응답 저장 [{model}]: {invalid_filename}")
            logger.info(f"  - 총 {len(model_responses)}개의 무효 예측 응답")
            saved_files.append(invalid_filename)
        except Exception as e:
            logger.error(f"무효 예측 응답 저장 실패 [{model}]: {str(e)}")
    
    # 전체 요약 정보 출력
    logger.info("모델별 무효 예측 수:")
    for model, model_responses in model_invalid_responses.items():
        logger.info(f"  {model}: {len(model_responses)}개")
    
    return saved_files

def save_detailed_logs(pred_long_df: pd.DataFrame, filename_prefix: str = "evaluation"):
    """상세한 로그를 CSV로 저장"""
    # SFAICENTER_PATH 기반 경로 사용
    try:
        from pipeline.config import SFAICENTER_PATH
        log_base_path = SFAICENTER_PATH
    except ImportError:
        # fallback: pipeline이 없는 경우 현재 스크립트 기준으로 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_base_path = os.path.dirname(script_dir)
    
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    log_dir = os.path.join(log_base_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 예측 결과 상세 로그
    pred_log_filename = os.path.join(log_dir, f"{filename_prefix}_predictions_{timestamp}.csv")
    pred_long_df.to_csv(pred_log_filename, index=False, encoding='utf-8-sig')
    logger.info(f"상세 예측 로그 저장: {pred_log_filename}")
    
    # 모델별 통계
    model_stats = pred_long_df.groupby('model_name').agg({
        'answer': [lambda x: x.count(), lambda x: x.notna().sum(), lambda x: x.isna().sum()]
    }).round(3)
    model_stats.columns = ['총_예측수', '유효_예측수', '무효_예측수']
    model_stats['유효율'] = (model_stats['유효_예측수'] / model_stats['총_예측수'] * 100).round(1)
    
    stats_filename = os.path.join(log_dir, f"{filename_prefix}_model_stats_{timestamp}.csv")
    model_stats.to_csv(stats_filename, encoding='utf-8-sig')
    logger.info(f"모델 통계 저장: {stats_filename}")

def check_real_duplicates_in_data(json_list: List[dict]) -> Dict[str, Any]:
    """
    로드된 JSON 데이터에서 진짜 중복 문제를 확인하는 함수
    (문제/정답/선택지가 모두 동일한 경우를 중복으로 판단)
    
    최상위 question/options/answer 구조를 지원합니다.
    
    Args:
        json_list: 검사할 JSON 데이터 리스트
    
    Returns:
        Dict: 중복 검사 결과 (중복 그룹 정보 포함)
    """
    from collections import defaultdict
    
    # 문제/정답/선택지를 조합한 키로 중복 확인
    content_keys = defaultdict(list)
    
    for i, item in enumerate(json_list):
        # 최상위 구조 (exam 파일 구조)
        question = (item.get("question") or "").strip()
        answer_raw = item.get("answer") or ""
        options = item.get("options", [])
        tag = item.get("tag", "")
        
        # answer가 리스트인 경우 처리 (변형된 시험지의 경우)
        if isinstance(answer_raw, list):
            # 리스트를 정렬하여 문자열로 변환 (중복 검사를 위해)
            answer = '|'.join(sorted([str(a).strip() for a in answer_raw if a]))
        else:
            answer = str(answer_raw).strip()
        
        # 빈 문제는 스킵 (데이터 품질 문제)
        if not question:
            continue
        
        # options를 문자열로 변환 (순서가 중요하므로 정렬하지 않음)
        options_str = '|'.join([str(opt).strip() for opt in options]) if options else ''
        
        # 문제/정답/선택지를 조합한 키 생성
        content_key = f"{question}|{answer}|{options_str}"
        content_keys[content_key].append({
            'index': i,
            'id': f"{item.get('file_id', '')}_{tag}",
            'question': question,
            'answer': answer,
            'options': options,
            'file_id': item.get('file_id', ''),
            'tag': tag
        })
    
    # 진짜 중복 찾기 (문제/정답/선택지가 모두 동일한 경우)
    real_duplicates = {key: items for key, items in content_keys.items() if len(items) > 1}
    
    return {
        'total_count': len(json_list),
        'unique_count': len(content_keys),
        'duplicate_groups': len(real_duplicates),
        'duplicates': real_duplicates
    }

def check_data_quality(json_list: List[dict], df_all: pd.DataFrame = None):
    """
    데이터 품질 검사 (중복 문제 확인 포함)
    
    Args:
        json_list: 검사할 JSON 데이터 리스트
        df_all: DataFrame 형태의 데이터 (선택적)
    
    Returns:
        Dict: 품질 검사 결과
    """
    logger.info("데이터 품질 검사 시작...")
    
    issues = []
    quality_report = {
        'total_questions': len(json_list),
        'issues': [],
        'duplicate_info': None
    }
    
    # DataFrame이 제공된 경우 DataFrame 기반 검사
    if df_all is not None:
        # 1. 빈 문제 검사
        empty_questions = df_all[df_all['question'].str.strip() == '']
        if len(empty_questions) > 0:
            issue_msg = f"빈 문제: {len(empty_questions)}개"
            issues.append(issue_msg)
            quality_report['issues'].append({
                'type': 'empty_question',
                'count': len(empty_questions),
                'message': issue_msg
            })
        
        # 2. 빈 선지 검사
        empty_options = df_all[(df_all['opt1'].str.strip() == '') & 
                              (df_all['opt2'].str.strip() == '') & 
                              (df_all['opt3'].str.strip() == '') & 
                              (df_all['opt4'].str.strip() == '') & 
                              (df_all['opt5'].str.strip() == '')]
        if len(empty_options) > 0:
            issue_msg = f"빈 선지 문제: {len(empty_options)}개"
            issues.append(issue_msg)
            quality_report['issues'].append({
                'type': 'empty_options',
                'count': len(empty_options),
                'message': issue_msg
            })
        
        # 3. 정답 없는 문제 검사
        no_answer = df_all[df_all['answer_set'].apply(len) == 0]
        if len(no_answer) > 0:
            issue_msg = f"정답 없는 문제: {len(no_answer)}개"
            issues.append(issue_msg)
            quality_report['issues'].append({
                'type': 'no_answer',
                'count': len(no_answer),
                'message': issue_msg
            })
    
    # 4. 진짜 중복 문제 검사 (문제/정답/선택지가 모두 동일한 경우)
    logger.info("중복 문제 검사 중...")
    duplicate_info = check_real_duplicates_in_data(json_list)
    quality_report['duplicate_info'] = duplicate_info
    
    if duplicate_info['duplicate_groups'] > 0:
        issue_msg = f"중복 문제 그룹: {duplicate_info['duplicate_groups']}개 (총 {duplicate_info['total_count']}개 중 고유: {duplicate_info['unique_count']}개)"
        issues.append(issue_msg)
        quality_report['issues'].append({
            'type': 'duplicates',
            'count': duplicate_info['duplicate_groups'],
            'message': issue_msg
        })
        
        # 중복 상세 정보 로깅 (최대 10개 그룹만)
        logger.warning(f"중복 문제 발견: {duplicate_info['duplicate_groups']}개 그룹")
        for i, (content_key, items) in enumerate(list(duplicate_info['duplicates'].items())[:10], 1):
            logger.warning(f"  중복 그룹 {i}: {len(items)}개 항목")
            for item in items[:3]:  # 각 그룹에서 최대 3개만 표시
                logger.warning(f"    - ID: {item['id']}, 문제: {item['question'][:50]}...")
            if len(items) > 3:
                logger.warning(f"    ... 외 {len(items) - 3}개 항목")
    else:
        logger.info(f"중복 문제 없음: 모든 {duplicate_info['total_count']}개 문제가 고유합니다")
    
    # 결과 요약
    if issues:
        logger.warning("데이터 품질 이슈 발견:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("데이터 품질 검사 통과 ✅")
    
    return quality_report

def calculate_domain_accuracy(pred_long: pd.DataFrame, df_all: pd.DataFrame) -> pd.DataFrame:
    """Domain별 정확도 계산 - 모델별 컬럼 형태로 반환"""
    # pred_long과 df_all을 병합하여 domain 정보 추가
    merged = pred_long.merge(df_all[['id', 'domain', 'subdomain']], on='id', how='left')
    
    # 정답 여부 계산 (기존 로직 사용)
    def _is_correct(pred: float, s: Set[int]) -> float:
        if np.isnan(pred) or not s:
            return np.nan
        return float(int(pred) in s)
    
    # answer_set 정보 추가
    merged = merged.merge(df_all[['id', 'answer_set']], on='id', how='left')
    merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"]), axis=1)
    
    # Domain별 정확도 계산 (모델별 컬럼 형태)
    domain_acc = (
        merged.groupby(["domain", "model_name"], dropna=False)["correct"]
        .mean()
        .reset_index()
        .pivot(index="domain", columns="model_name", values="correct")
        .reset_index()
    )
    
    return domain_acc

def calculate_subdomain_accuracy(pred_long: pd.DataFrame, df_all: pd.DataFrame) -> pd.DataFrame:
    """Subdomain별 정확도 계산 - 모델별 컬럼 형태로 반환"""
    # pred_long과 df_all을 병합하여 subdomain 정보 추가
    merged = pred_long.merge(df_all[['id', 'domain', 'subdomain']], on='id', how='left')
    
    # 정답 여부 계산
    def _is_correct(pred: float, s: Set[int]) -> float:
        if np.isnan(pred) or not s:
            return np.nan
        return float(int(pred) in s)
    
    # answer_set 정보 추가
    merged = merged.merge(df_all[['id', 'answer_set']], on='id', how='left')
    merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"]), axis=1)
    
    # Subdomain별 정확도 계산 (모델별 컬럼 형태)
    subdomain_acc = (
        merged.groupby(["domain", "subdomain", "model_name"], dropna=False)["correct"]
        .mean()
        .reset_index()
        .pivot(index=["domain", "subdomain"], columns="model_name", values="correct")
        .reset_index()
    )
    
    return subdomain_acc

def calculate_subject_accuracy(pred_long: pd.DataFrame, df_all: pd.DataFrame) -> pd.DataFrame:
    """Subject별 정확도 계산 - 모델별 컬럼 형태로 반환"""
    # pred_long과 df_all을 병합하여 subject 정보 추가
    merged = pred_long.merge(df_all[['id', 'subject']], on='id', how='left')
    
    # 정답 여부 계산
    def _is_correct(pred: float, s: Set[int]) -> float:
        if np.isnan(pred) or not s:
            return np.nan
        return float(int(pred) in s)
    
    # answer_set 정보 추가
    merged = merged.merge(df_all[['id', 'answer_set']], on='id', how='left')
    merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"]), axis=1)
    
    # Subject별 정확도 계산 (모델별 컬럼 형태)
    subject_acc = (
        merged.groupby(["subject", "model_name"], dropna=False)["correct"]
        .mean()
        .reset_index()
        .pivot(index="subject", columns="model_name", values="correct")
        .reset_index()
    )
    
    return subject_acc

def save_results_to_excel(df_all: pd.DataFrame, pred_wide: pd.DataFrame, acc: pd.DataFrame, pred_long: pd.DataFrame = None, filename: str = None):
    """결과를 Excel 파일로 저장 (domain, subdomain 분석 포함)"""
    
    # ONEDRIVE_PATH 기반 경로 사용
    try:
        from pipeline.config import ONEDRIVE_PATH
        default_base_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'result')
    except ImportError:
        import platform
        system = platform.system()
        home_dir = os.path.expanduser("~")
        if system == "Windows":
            default_base_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar", "evaluation", "result")
        else:
            default_base_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar", "evaluation", "result")
    
    if filename is None:
        timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{default_base_path}evaluation_results_{timestamp}.xlsx"
    elif not filename.startswith(('/', './', 'evaluation/')):
        # 파일명만 주어진 경우 (확장자 포함 여부 확인)
        timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        if filename.endswith('.xlsx'):
            # 확장자가 있는 경우
            name = filename[:-5]  # .xlsx 제거
            filename = f"{default_base_path}{name}_{timestamp}.xlsx"
        else:
            # 확장자가 없는 경우
            filename = f"{default_base_path}{filename}_{timestamp}.xlsx"
    elif filename.startswith('evaluation/'):
        # evaluation/로 시작하는 경우 기본 경로 사용
        filename = f"{default_base_path}{filename}"
    
    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    logger.info(f"결과를 {filename}에 저장 중...")
    
    # 분석 결과 변수 초기화
    domain_acc = None
    
    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as w:
            # 기본 시트들
            df_all.to_excel(w, index=False, sheet_name="전체데이터")
            pred_wide.to_excel(w, index=False, sheet_name="모델별예측")
            acc.to_excel(w, index=False, sheet_name="정확도")
            
            # Subject, Domain, Subdomain 분석 추가 (pred_long이 제공된 경우)
            if pred_long is not None and 'domain' in df_all.columns:
                # Subject별 정확도 계산 (subject 컬럼이 있는 경우)
                if 'subject' in df_all.columns:
                    logger.info("Subject별 정확도 계산 중...")
                    subject_acc = calculate_subject_accuracy(pred_long, df_all)
                    subject_acc.to_excel(w, index=False, sheet_name="Subject별정확도")
                    
                    # Subject별 문제 수 통계
                    subject_stats = df_all.groupby('subject').size().reset_index(name='question_count')
                    subject_stats.to_excel(w, index=False, sheet_name="Subject별문제수")
                
                logger.info("Domain별 정확도 계산 중...")
                domain_acc = calculate_domain_accuracy(pred_long, df_all)
                domain_acc.to_excel(w, index=False, sheet_name="Domain별정확도")
                
                # Domain별 문제 수 통계
                domain_stats = df_all.groupby('domain').size().reset_index(name='question_count')
                domain_stats.to_excel(w, index=False, sheet_name="Domain별문제수")
                
                logger.info("Subdomain별 정확도 계산 중...")
                subdomain_acc = calculate_subdomain_accuracy(pred_long, df_all)
                subdomain_acc.to_excel(w, index=False, sheet_name="Subdomain별정확도")
                
                # Subdomain별 문제 수 통계
                subdomain_stats = df_all.groupby(['domain', 'subdomain']).size().reset_index(name='question_count')
                subdomain_stats.to_excel(w, index=False, sheet_name="Subdomain별문제수")
            
        logger.info(f"결과 저장 완료: {filename}")
        print(f"\n📁 결과 파일 저장 완료: {filename}")
        
        # Domain 분석 요약 출력
        if pred_long is not None and 'domain' in df_all.columns and domain_acc is not None:
            print_domain_analysis_summary(df_all, domain_acc)
        
    except Exception as e:
        logger.error(f"결과 저장 실패: {str(e)}")
        print(f"결과 저장 중 오류 발생: {str(e)}")

def print_domain_analysis_summary(df_all: pd.DataFrame, domain_acc: pd.DataFrame):
    """Domain 분석 요약 출력"""
    print("\n" + "="*80)
    print("📊 분야별 분석 요약")
    print("="*80)
    
    # Domain별 문제 수
    domain_counts = df_all['domain'].value_counts()
    print("📈 Domain별 문제 수:")
    for domain, count in domain_counts.items():
        print(f"  - {domain}: {count}개")
    
    # Subject별 문제 수 (subject 컬럼이 있는 경우)
    if 'subject' in df_all.columns:
        subject_counts = df_all['subject'].value_counts()
        print("\n📚 Subject별 문제 수:")
        for subject, count in subject_counts.items():
            if subject:  # 빈 문자열이 아닌 경우만 출력
                print(f"  - {subject}: {count}개")
    
    # Domain별 정확도 (모델별)
    print(f"\n🏆 Domain별 정확도 (상위 모델 기준):")
    for domain in domain_counts.index:
        domain_data = domain_acc[domain_acc['domain'] == domain]
        if len(domain_data) > 0:
            # 모델별 컬럼에서 최고 정확도 찾기
            model_columns = [col for col in domain_data.columns if col != 'domain']
            if model_columns:
                best_accuracy = 0
                best_model = ""
                for model in model_columns:
                    acc = domain_data[model].iloc[0]
                    if not pd.isna(acc) and acc > best_accuracy:
                        best_accuracy = acc
                        best_model = model
                if best_model:
                    print(f"  - {domain}: {best_model} ({best_accuracy:.3f})")
    
    print("="*80)

# -----------------------------
# 태그 대치 함수들
# -----------------------------

# TagProcessor를 직접 사용
from qna.qna_processor import TagProcessor

# -----------------------------
# 유틸리티 함수들
# -----------------------------

def extract_subject_from_filename(filename: str) -> str:
    """파일명에서 subject 정보를 추출합니다.
    
    Args:
        filename: 파일명 (예: "금융실무1_exam.json" 또는 "금융실무1_exam_transformed.json")
    
    Returns:
        str: 추출된 subject (예: "금융실무1")
    """
    if '_exam_transformed.json' in filename:
        # 변형된 exam 파일인 경우 파일명에서 subject 추출
        # 파일명 형식: "{exam_name}_exam_transformed.json" (예: "금융실무1_exam_transformed.json")
        subject = filename.split("_exam_transformed.json")[0]
        return subject
    elif '_exam.json' in filename:
        # exam 파일인 경우 파일명에서 subject 추출
        # 파일명 형식: "{exam_name}_exam.json" (예: "금융실무1_exam.json")
        subject = filename.split("_exam.json")[0]
        return subject
    else:
        # 일반 파일인 경우 빈 문자열 반환
        return ""

# -----------------------------
# 데이터 로딩 함수
# -----------------------------

def load_data_from_directory(data_path: str, apply_tag_replacement: bool = False) -> List[dict]:
    """디렉토리 또는 파일 경로에서 JSON 파일들을 로드하여 데이터 리스트 반환
    
    Args:
        data_path: 디렉토리 경로 또는 JSON 파일 경로
        apply_tag_replacement: 태그 대치 적용 여부
    
    Returns:
        List[dict]: 데이터 리스트
    """
    json_files = []
    
    # 파일 경로인지 디렉토리 경로인지 확인
    # 먼저 경로가 존재하는지 확인
    logger.info(f"경로 확인 중: {data_path}")
    logger.info(f"  - 경로 존재: {os.path.exists(data_path)}")
    logger.info(f"  - 파일인지: {os.path.isfile(data_path)}")
    logger.info(f"  - 디렉토리인지: {os.path.isdir(data_path)}")
    
    if not os.path.exists(data_path):
        logger.warning(f"경로를 찾을 수 없습니다: {data_path}")
        return []
    
    if os.path.isfile(data_path):
        # 파일 경로인 경우
        logger.info(f"파일 경로로 인식: {data_path}")
        if data_path.endswith(".json") and ('merged' not in os.path.basename(data_path)):
            json_files.append(data_path)
            logger.info(f"JSON 파일 추가: {data_path}")
        else:
            logger.warning(f"JSON 파일이 아니거나 merged 파일입니다: {data_path}")
            logger.warning(f"  - 파일명: {os.path.basename(data_path)}")
            logger.warning(f"  - .json으로 끝나는지: {data_path.endswith('.json')}")
            logger.warning(f"  - merged 포함: {'merged' in os.path.basename(data_path)}")
    elif os.path.isdir(data_path):
        # 디렉토리 경로인 경우
        logger.debug(f"디렉토리 경로로 인식: {data_path}")
        for root, _, files in os.walk(data_path):
            for f in files:
                if f.endswith(".json") and ('merged' not in f):
                    json_files.append(os.path.join(root, f))
    else:
        logger.warning(f"경로를 찾을 수 없습니다: {data_path}")
        logger.warning(f"  - 파일 존재: {os.path.exists(data_path)}")
        logger.warning(f"  - 파일인지: {os.path.isfile(data_path)}")
        logger.warning(f"  - 디렉토리인지: {os.path.isdir(data_path)}")
        return []
    
    logger.info(f"발견된 JSON 파일 수: {len(json_files)}")
    
    all_data = []
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 파일명에서 subject 추출 (fallback용)
                filename = os.path.basename(file_path)
                subject_from_filename = extract_subject_from_filename(filename)
                
                if isinstance(data, list):
                    # 리스트인 경우 각 항목에 subject 추가
                    for item in data:
                        # JSON 내부에 이미 subject가 있고 비어있지 않으면 우선 사용, 없거나 비어있으면 파일명에서 추출한 값 사용
                        if 'subject' not in item or not item.get('subject'):
                            if subject_from_filename:
                                item['subject'] = subject_from_filename
                    all_data.extend(data)
                else:
                    # 단일 객체인 경우 subject 추가
                    # JSON 내부에 이미 subject가 있고 비어있지 않으면 우선 사용, 없거나 비어있으면 파일명에서 추출한 값 사용
                    if 'subject' not in data or not data.get('subject'):
                        if subject_from_filename:
                            data['subject'] = subject_from_filename
                    all_data.append(data)
        except Exception as e:
            logger.warning(f"파일 로딩 실패: {file_path} - {str(e)}")
    
    logger.info(f"로드된 총 데이터 수: {len(all_data)}")
    
    # 태그 대치 적용
    if apply_tag_replacement:
        logger.info("태그 대치 적용 중...")
        processed_count = 0
        for item in all_data:
            if 'additional_tags_found' in item and item['additional_tags_found']:
                if 'additional_tag_data' in item:
                    item['qna_data'] = TagProcessor.replace_tags_in_qna_data(
                        item['qna_data'], 
                        item['additional_tag_data']
                    )
                    processed_count += 1
        logger.info(f"태그 대치 완료: {processed_count}개 항목 처리")
    
    return all_data

def filter_multiple_choice_questions(data: List[dict]) -> List[dict]:
    """객관식 문제만 필터링"""
    multiple_choice = []
    for item in data:
        if item.get('qna_type') == "multiple-choice":
            multiple_choice.append(item)
    
    logger.info(f"객관식 문제 수: {len(multiple_choice)}")
    return multiple_choice

# -----------------------------
# 메인 실행 함수
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description='LLM 평가 시스템')
    parser.add_argument('--data_path', type=str, required=True, help='데이터 디렉토리 경로')
    parser.add_argument('--sample_size', type=int, default=1000, help='샘플 크기 (기본값: 1000)')
    parser.add_argument('--batch_size', type=int, default=10, help='배치 크기 (기본값: 10)')
    parser.add_argument('--models', nargs='+', default=['anthropic/claude-sonnet-4.5', 'google/gemini-2.5-flash', 'openai/gpt-5', 'google/gemini-2.5-pro', 'google/gemma-3-27b-it:free'], help='평가할 모델 목록')
    parser.add_argument('--use_ox_support', action='store_true', help='O, X 문제 지원 활성화')
    parser.add_argument('--apply_tag_replacement', action='store_true', default=False, help='태그 대치 적용 (기본값: False)')
    parser.add_argument('--no_tag_replacement', action='store_true', help='태그 대치 비활성화 (deprecated: 기본값이 False이므로 더 이상 필요 없음)')
    parser.add_argument('--seed', type=int, default=42, help='랜덤 시드 (기본값: 42)')
    parser.add_argument('--output_filename', type=str, help='결과 Excel 파일명 (기본값: 자동 생성)')
    parser.add_argument('--debug', action='store_true', help='디버그 로그 활성화')
    
    # API 모드 옵션 추가
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--api', action='store_true', help='OpenRouter API 모드로 실행 (기본값)')
    mode_group.add_argument('--server', action='store_true', help='vLLM 서버 모드로 실행')
    
    args = parser.parse_args()
    
    # 디버그 모드 설정
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("디버그 모드 활성화")
    
    logger.info("=" * 60)
    logger.info("LLM 평가 시스템 시작")
    logger.info("=" * 60)
    logger.info(f"데이터 경로: {args.data_path}")
    logger.info(f"샘플 크기: {args.sample_size}")
    logger.info(f"배치 크기: {args.batch_size}")
    logger.info(f"모델: {args.models}")
    logger.info(f"O, X 문제 지원: {args.use_ox_support}")
    logger.info(f"출력 파일명: {args.output_filename or '자동 생성'}")
    
    # API 모드 확인
    use_server_mode = args.server
    if use_server_mode:
        logger.info("모드: vLLM 서버 모드")
    else:
        logger.info("모드: OpenRouter API 모드 (기본값)")
    
    # 태그 대치 옵션 처리
    apply_tag_replacement = args.apply_tag_replacement
    if args.no_tag_replacement:
        apply_tag_replacement = False
        logger.warning("--no_tag_replacement 옵션은 deprecated입니다. --apply_tag_replacement를 사용하지 않으면 기본값이 False입니다.")
    logger.info(f"태그 대치 적용: {apply_tag_replacement}")
    
    try:
        # 데이터 로딩
        logger.info("데이터 로딩 중...")
        all_data = load_data_from_directory(args.data_path, apply_tag_replacement)
        
        # 모든 데이터 사용
        multiple_choice_data = all_data
        
        # 샘플링
        if len(multiple_choice_data) > args.sample_size:
            random.seed(args.seed)
            sample_data = random.sample(multiple_choice_data, args.sample_size)
        else:
            sample_data = multiple_choice_data
            logger.info(f"전체 데이터 사용: {len(sample_data)}개")
        
        # 데이터 품질 검사
        df_temp = json_to_df_all(sample_data, use_ox_support=args.use_ox_support)
        
        quality_report = check_data_quality(sample_data, df_temp)
        
        # O, X 문제 분석 (지원하는 경우)
        if args.use_ox_support:
            ox_questions, regular_questions = analyze_ox_questions(df_temp)
        
        # 평가 실행
        logger.info("평가 실행 중...")
        df_all, pred_long, pred_wide, acc = run_eval_pipeline(
            sample_data, args.models, args.sample_size, args.batch_size, args.seed, use_server_mode, args.use_ox_support
        )
        
        # 결과 출력
        print_evaluation_summary(acc, pred_long)
        
        # O, X 문제별 정확도 분석 (지원하는 경우)
        if args.use_ox_support and 'is_ox_question' in df_all.columns:
            sample_with_type = df_all[df_all['id'].isin(pred_long['id'])][['id', 'is_ox_question']].copy()
            merged_with_type = pred_long.merge(sample_with_type, on='id', how='left')
            
            if len(merged_with_type[merged_with_type['is_ox_question'] == True]) > 0:
                print("\n" + "="*60)
                print("📊 O, X 문제 vs 일반 객관식 정확도 비교")
                print("="*60)
                
                # O, X 문제 정확도
                ox_correct = merged_with_type[merged_with_type['is_ox_question'] == True]['answer'].notna().sum()
                ox_total = len(merged_with_type[merged_with_type['is_ox_question'] == True])
                ox_acc = ox_correct / ox_total if ox_total > 0 else 0
                
                # 일반 객관식 정확도
                regular_correct = merged_with_type[merged_with_type['is_ox_question'] == False]['answer'].notna().sum()
                regular_total = len(merged_with_type[merged_with_type['is_ox_question'] == False])
                regular_acc = regular_correct / regular_total if regular_total > 0 else 0
                
                print(f"O, X 문제: {ox_correct}/{ox_total} ({ox_acc:.1%})")
                print(f"일반 객관식: {regular_correct}/{regular_total} ({regular_acc:.1%})")
        
        # 상세 로그 저장
        # save_detailed_logs(pred_long, "evaluation")
        
        # Excel 파일 저장
        save_results_to_excel(df_all, pred_wide, acc, pred_long, args.output_filename)
        
        logger.info("=" * 60)
        logger.info("평가 완료")
        logger.info("=" * 60)
        
        # 평가 완료 후 캐시 정리 (선택적)
        if not use_server_mode:  # API 모드에서는 캐시 정리하지 않음 (재사용 가능)
            logger.info("[CACHE] API 모드이므로 캐시를 유지합니다.")
        else:
            logger.info("[CACHE] vLLM 서버 모드이므로 캐시를 정리합니다.")
            clear_model_cache()
        
    except Exception as e:
        logger.error(f"평가 실행 중 오류 발생: {str(e)}")
        # 오류 발생 시에도 캐시 정리
        clear_model_cache()
        raise

if __name__ == "__main__":
    main()
