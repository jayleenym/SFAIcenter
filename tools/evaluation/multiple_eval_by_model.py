#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 평가 시스템 - 통합 버전
O, X 문제를 포함한 객관식 문제 평가 시스템

사용법:
    # OpenRouter API 모드 (기본값)
    python multiple_eval_by_model.py --data_path /path/to/data --sample_size 1000 --api --mock_mode
    
    # vLLM 서버 모드
    python multiple_eval_by_model.py --data_path /path/to/data --sample_size 1000 --server --mock_mode
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
from typing import List, Dict, Tuple, Iterable, Set
from dataclasses import dataclass
from tqdm import tqdm
import argparse

# -----------------------------
# 로깅 설정
# -----------------------------
# 홈 디렉토리에서 프로젝트 루트 찾기
global home_dir
home_dir = os.path.expanduser("~")
global project_root
project_root = None

# 홈 디렉토리에서 SFAIcenter 프로젝트 찾기
for root, dirs, files in os.walk(home_dir):
    if 'SFAIcenter' in dirs:
        project_root = os.path.join(root, 'SFAIcenter')
        break

# 프로젝트 루트를 찾지 못한 경우 현재 스크립트 기준으로 설정
if project_root is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

log_dir = os.path.join(project_root, 'logs')
log_file = os.path.join(log_dir, 'multiple_eval_by_model.log')

# logs 디렉토리가 없으면 생성
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# -----------------------------
# 유틸: 텍스트 정규화
# -----------------------------
CIRCLED_MAP = {"①":"1","②":"2","③":"3","④":"4","⑤":"5"}

def normalize_option_text(s: str) -> str:
    """선지 앞에 붙은 ①~⑤, 1), (1), 1. 등 번호 표기를 제거하고 본문만 남김."""
    if s is None:
        return ""
    s = str(s).strip()
    # ①~⑤ 제거
    s = re.sub(r"^\s*[①-⑤]\s*", "", s)
    # 1), (1), 1. 등 제거
    s = re.sub(r"^\s*(?:\(?([1-5])\)?[.)])\s*", "", s)
    return s.strip()

def parse_answer_set(ans: str) -> Set[int]:
    """'①, ⑤' 같은 복수정답도 {1,5}로 파싱. 빈/이상값은 빈 set."""
    if not ans:
        return set()
    s = str(ans)
    # ①~⑤ 를 1~5로 치환
    for k, v in CIRCLED_MAP.items():
        s = s.replace(k, v)
    # 쉼표/슬래시/공백 구분 모두 허용하여 1~5 추출
    nums = re.findall(r"[1-5]", s)
    return set(int(n) for n in nums)

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

def parse_answer_set_improved(ans: str, question: str = "", options: list = None) -> Set[int]:
    """개선된 정답 파싱 함수 - O, X 문제도 처리"""
    if not ans:
        return set()
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

def json_to_df_all(json_list: List[dict]) -> pd.DataFrame:
    """
    입력 JSON(list[dict])을 파싱해 df_all 생성.
    컬럼: subject, domain, subdomain, book_id, tag, id, question, opt1..opt5, answer_set
    """
    rows = []
    for item in json_list:
        book_id = str(item.get("file_id", ""))
        
        # Mock exam 파일 구조 처리 (qna_data가 없는 경우)
        if "qna_data" in item:
            # 일반 파일 구조
            qna = item.get("qna_data", {}) or {}
            tag  = qna.get("tag", "")
            desc = qna.get("description", {}) or {}
            q    = (desc.get("question") or "").strip()
            opts = desc.get("options") or []
            ans_set = parse_answer_set(desc.get("answer", ""))
            domain = item.get("qna_domain", "")
            subdomain = item.get("qna_subdomain", "")
        else:
            # Mock exam 파일 구조
            tag = item.get("tag", "")
            q = (item.get("question") or "").strip()
            opts = item.get("options") or []
            ans_set = parse_answer_set(item.get("answer", ""))
            domain = item.get("domain", "")
            subdomain = item.get("subdomain", "")
        
        # subject 정보 추출
        subject = item.get("subject", "")
        
        # 5지선다 기준으로 빈칸 보정
        opts = list(opts)[:5] + [""] * max(0, 5 - len(opts))
        opts = [normalize_option_text(x) for x in opts]

        rows.append({
            "subject": subject,
            "domain": domain,
            "subdomain": subdomain,
            "book_id": book_id,
            "tag": tag,
            "id": f"{book_id}_{tag}",
            "question": q,
            "opt1": opts[0], "opt2": opts[1], "opt3": opts[2], "opt4": opts[3], "opt5": opts[4],
            "answer_set": ans_set
        })
    df = pd.DataFrame(rows)
    # 혹시 id 중복이 있으면 마지막 것 유지(필요시 정책 변경)
    df = df.drop_duplicates("id", keep="last").reset_index(drop=True)
    return df

def json_to_df_all_improved(json_list: List[dict], use_ox_support: bool = False) -> pd.DataFrame:
    """
    개선된 JSON → df_all 변환 함수 - O, X 문제도 처리
    컬럼: subject, domain, subdomain, book_id, tag, id, question, opt1..opt5, answer_set [, is_ox_question]
    """
    rows = []
    for item in json_list:
        book_id = str(item.get("file_id", ""))
        
        # Mock exam 파일 구조 처리 (qna_data가 없는 경우)
        if "qna_data" in item:
            # 일반 파일 구조
            qna = item.get("qna_data", {}) or {}
            tag  = qna.get("tag", "")
            desc = qna.get("description", {}) or {}
            q    = (desc.get("question") or "").strip()
            opts = desc.get("options") or []
            ans_set = parse_answer_set_improved(desc.get("answer", ""), q, opts)
            domain = item.get("qna_domain", "")
            subdomain = item.get("qna_subdomain", "")
        else:
            # Mock exam 파일 구조
            tag = item.get("tag", "")
            q = (item.get("question") or "").strip()
            opts = item.get("options") or []
            ans_set = parse_answer_set_improved(item.get("answer", ""), q, opts)
            domain = item.get("domain", "")
            subdomain = item.get("subdomain", "")
        
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
    # 혹시 id 중복이 있으면 마지막 것 유지(필요시 정책 변경)
    df = df.drop_duplicates("id", keep="last").reset_index(drop=True)
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

def build_user_prompt(batch_df: pd.DataFrame) -> str:
    lines = []
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
        lines.append(f"{r['id']}\\t{{번호}}")
    return "\n".join(lines)

# -----------------------------
# LLM 호출 추상화
# -----------------------------

# 모델 캐시를 위한 전역 변수
_model_cache = {}
_config_cache = None
_query_models_module = None

def _load_config():
    """Config 파일을 한 번만 로드하고 캐시"""
    global _config_cache
    if _config_cache is None:
        import configparser
        config_path = os.popen(f"find {home_dir} -type f -name 'llm_config.ini'").read().strip()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config 파일을 찾을 수 없습니다: {config_path}")
        
        _config_cache = configparser.ConfigParser()
        _config_cache.read(config_path, encoding='utf-8')
        logger.info(f"[CACHE] Config 파일 로드 완료: {config_path}")
    
    return _config_cache

def _load_query_models():
    """QueryModels 모듈을 한 번만 로드하고 캐시"""
    global _query_models_module
    if _query_models_module is None:
        import sys
        import os
        tools_dir = os.popen(f"find {home_dir}/SFAIcenter/ -type d -name 'tools'").read().strip()
        sys.path.append(tools_dir)
        try:
            import QueryModels
            _query_models_module = QueryModels
            logger.info(f"[CACHE] QueryModels 모듈 로드 완료: {tools_dir}")
        except Exception as e:
            logger.error(f"[CACHE] QueryModels 모듈 로드 실패: {e}")
            raise
    return _query_models_module

def _load_model_cached(model_name: str):
    """모델을 캐시에서 로드하거나 새로 로드"""
    global _model_cache
    
    if model_name not in _model_cache:
        logger.info(f"[CACHE] 모델 로드 중: {model_name}")
        config = _load_config()
        QueryModels = _load_query_models()
        
        llm, tokenizer, sampling_params = QueryModels.load_model(model_name, config)
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

def call_llm(model_name: str, system_prompt: str, user_prompt: str, mock_mode: bool=False, use_server_mode: bool=False, max_retries: int=3) -> str:
    """
    - mock_mode=True면 임의 번호(1~5)를 생성해 파이프라인 검증용 출력 반환.
    - use_server_mode=True면 vLLM 서버 모드로 호출
    - use_server_mode=False면 OpenRouter API로 호출
    - 에러 핸들링 및 재시도 로직 포함
    """
    if mock_mode:
        logger.info(f"[MOCK] 모델 {model_name} 호출 시작")
        # 입력 user_prompt에서 ID 목록 회수
        ids = [ln.split("\t")[0] for ln in user_prompt.splitlines() if "\t{번호}" in ln]
        if not ids:
            # ID를 찾지 못한 경우 다른 방법으로 시도
            ids = [ln.split("ID: ")[1].strip() for ln in user_prompt.splitlines() if ln.startswith("ID: ")]
        
        # 무작위 예측(1~5)
        rng = np.random.default_rng(42)
        preds = rng.integers(1, 6, size=len(ids))
        result = "\n".join(f"{_id}\t{int(a)}" for _id, a in zip(ids, preds))
        logger.info(f"[MOCK] 모델 {model_name} 호출 완료 - {len(ids)}개 문제 처리")
        return result
    
    else:
        for attempt in range(max_retries):
            try:
                if use_server_mode:
                    # vLLM 서버 모드 - 캐시된 모델 사용
                    logger.info(f"[VLLM] 모델 {model_name} 호출 시작 (시도 {attempt + 1}/{max_retries})")
                    start_time = time.time()
                    
                    # 캐시된 모델 로드
                    llm, tokenizer, sampling_params = _load_model_cached(model_name)
                    QueryModels = _load_query_models()
                    
                    ans = QueryModels.query_vllm(llm, tokenizer, sampling_params, system_prompt, user_prompt, model_name)
                    
                    elapsed_time = time.time() - start_time
                    logger.info(f"[VLLM] 모델 {model_name} 호출 완료 - 소요시간: {elapsed_time:.2f}초")
                    
                    return ans
                else:
                    # OpenRouter API 모드
                    logger.info(f"[API] 모델 {model_name} 호출 시작 (시도 {attempt + 1}/{max_retries})")
                    start_time = time.time()
                    
                    # 캐시된 config와 모듈 사용
                    config = _load_config()
                    QueryModels = _load_query_models()
                    
                    ans = QueryModels.query_openrouter(config, system_prompt, user_prompt, model_name)
                    
                    elapsed_time = time.time() - start_time
                    logger.info(f"[API] 모델 {model_name} 호출 완료 - 소요시간: {elapsed_time:.2f}초")
                    
                    return ans
                
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

def parse_model_output(raw: str, expected_ids: List[str], reasoning: bool = False) -> Dict[str, float]:
    """
    모델 원시 출력(raw)을 {id: answer(1~5)}로 변환.
    - 'ID\\t번호' 포맷 기준 (일반 모델)
    - reasoning=True일 경우, 답변에서 ID와 정답을 직접 찾음
    - 잘못된 줄/누락 줄은 NaN 처리
    """
    id_set = set(expected_ids)
    out: Dict[str, float] = {k: np.nan for k in expected_ids}
    
    if not raw or not raw.strip():
        logger.warning("모델 출력이 비어있습니다.")
        return out

    # 추론 모델일 경우, 전체 텍스트에서 ID와 정답을 직접 찾기
    if reasoning:
        logger.debug("추론 모델 모드: 답변에서 ID와 정답을 직접 찾는 중...")
        for _id in expected_ids:
            # ID 패턴으로 해당 ID가 포함된 부분 찾기
            id_pattern = re.escape(_id)
            # 여러 패턴을 시도 (우선순위 순서)
            patterns = [
                rf"{id_pattern}.*?정답은\s*(?:보기\s*)?([1-5])",  # "정답은 4" 또는 "정답은 보기 4"
                rf"{id_pattern}.*?가장\s*근접한\s*것은\s*(?:보기\s*)?([1-5])",  # "가장 근접한 것은 4" 또는 "가장 근접한 것은 보기 4"
                rf"{id_pattern}.*?가장\s*근접한\s*것은\s*([1-5])\s*번",  # "가장 근접한 것은 4번"
            ]
            
            found = False
            for pattern in patterns:
                match = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
                if match:
                    answer = float(match.group(1))
                    out[_id] = answer
                    logger.debug(f"ID '{_id}' -> 답변 {answer} (추론 모델에서 추출)")
                    found = True
                    break
            
            if not found:
                # '정답은' 또는 '가장 근접한 것은' 키워드가 없으면 0으로 표시
                out[_id] = 0.0
                logger.debug(f"ID '{_id}' -> '정답은' 또는 '가장 근접한 것은' 키워드를 찾을 수 없어 0으로 설정")
        return out

    # 일반 모델: 탭 구분 포맷 처리
    lines = raw.splitlines()
    logger.debug(f"파싱할 줄 수: {len(lines)}")
    
    for i, ln in enumerate(lines):
        ln = ln.strip()
        logger.debug(f"줄 {i+1}: '{ln}'")
        
        if not ln:
            logger.debug(f"줄 {i+1}: 빈 줄, 스킵")
            continue
        
        # 이중 이스케이프 처리: \\t -> \t
        ln = ln.replace("\\t", "\t")
        logger.debug(f"줄 {i+1} (이스케이프 처리 후): '{ln}'")
            
        if "\t" not in ln:
            logger.debug(f"줄 {i+1}: 탭이 없음, 스킵")
            continue
            
        left, right = ln.split("\t", 1)
        _id = left.strip()
        logger.debug(f"줄 {i+1}: ID='{_id}', 답변='{right}'")
        
        if _id not in id_set:
            logger.debug(f"줄 {i+1}: ID '{_id}'가 예상 목록에 없음, 스킵")
            continue
            
        # 첫 번째 1~5 추출
        m = re.search(r"[1-5]", right)
        if m:
            answer = float(m.group(0))
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
    mock_mode: bool = False,
    use_server_mode: bool = False,
    reasoning: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    반환:
      df_all      : 전체 원장 (정규화 선지 + answer_set)
      pred_long   : (id, model_name, answer) 롱 포맷
      pred_wide   : id 기준 모델별 예측 와이드
      acc_by_model: 모델별 정확도 (복수정답 지원: 예측 ∈ answer_set 이면 정답)
    """
    logger.info(f"평가 파이프라인 시작 - 샘플수: {sample_size}, 배치크기: {batch_size}, 모델수: {len(models)}")
    
    # (1) JSON → df_all
    logger.info("1단계: JSON 데이터를 DataFrame으로 변환 중...")
    df_all = json_to_df_all(json_list)
    df_all = df_all.sort_values(by=['book_id', 'tag'], ascending=False).reset_index(drop=True)
    logger.info(f"전체 데이터: {len(df_all)}개 문제")

    # (2) 샘플링
    logger.info(f"2단계: {sample_size}개 샘플 추출 중...")
    # 샘플 크기가 전체 데이터보다 큰 경우, 전체 데이터 크기로 조정
    actual_sample_size = min(sample_size, len(df_all))
    if actual_sample_size < sample_size:
        logger.warning(f"요청한 샘플 크기({sample_size})가 전체 데이터({len(df_all)})보다 큼. {actual_sample_size}개로 조정합니다.")
    df_sample = df_all.sample(n=actual_sample_size, random_state=seed).reset_index(drop=True)
    logger.info(f"샘플 데이터: {len(df_sample)}개 문제")

    # (3) 배치 분할
    batches = [df_sample.iloc[i:i+batch_size] for i in range(0, len(df_sample), batch_size)]
    logger.info(f"3단계: {len(batches)}개 배치로 분할 완료")

    # (4) 모델 호출/파싱 누적
    logger.info("4단계: 모델 호출 및 예측 시작...")
    rows = []
    invalid_responses = []  # 무효 예측 응답 저장용
    total_calls = len(batches) * len(models)
    
    # 전체 진행상황 표시
    with tqdm(total=total_calls, desc="모델 호출 진행", unit="call") as pbar:
        for bidx, bdf in enumerate(batches, 1):
            user_prompt = build_user_prompt(bdf)
            ids = bdf["id"].tolist()
            
            for model in models:
                try:
                    # 배치별 진행상황 표시
                    pbar.set_description(f"배치 {bidx}/{len(batches)} - {model}")
                    
                    raw = call_llm(model, SYSTEM_PROMPT, user_prompt, mock_mode=mock_mode, use_server_mode=use_server_mode)
                    if reasoning:
                        logger.info(f"추론 모델 원시 출력 저장 완료")
                        with open(f"reasoning_model_output_{model}.txt", "w") as f:
                            f.write(raw)
                    else:
                        pass
                    parsed = parse_model_output(raw, ids, reasoning=reasoning)
                    
                    # 파싱 결과 검증
                    valid_predictions = sum(1 for v in parsed.values() if not np.isnan(v))
                    logger.info(f"배치 {bidx} - {model}: {valid_predictions}/{len(ids)}개 유효 예측")
                    
                    # 무효 예측이 있는 경우 디버깅 정보 출력 및 저장
                    if valid_predictions < len(ids):
                        logger.warning(f"배치 {bidx} - {model}: 무효 예측 감지!")
                        logger.warning(f"예상 ID: {ids}")
                        logger.warning(f"모델 원시 출력:\n{raw}")
                        logger.warning(f"파싱된 결과: {parsed}")
                        
                        # 무효 예측 응답 저장 (모델명, 문제, 답변 포함)
                        for _id in ids:
                            if np.isnan(parsed[_id]):
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
                                    "parsed_result": parsed[_id],
                                    "timestamp": dt.datetime.now().isoformat()
                                }
                                invalid_responses.append(invalid_response)
                    
                    for _id in ids:
                        rows.append({"id": _id, "model_name": model, "answer": parsed[_id]})
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"배치 {bidx} - {model} 처리 중 오류: {str(e)}")
                    # 오류 발생 시 NaN으로 채움
                    for _id in ids:
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
    
    def _is_correct(pred: float, s: Set[int]) -> float:
        if np.isnan(pred) or not s:
            return np.nan
        return float(int(pred) in s)

    merged = pred_long.merge(key, on="id", how="left")
    merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"]), axis=1)

    acc_by_model = (
        merged.groupby("model_name", dropna=False)["correct"]
        .mean()
        .reset_index()
        .rename(columns={"correct": "accuracy"})
        .sort_values("accuracy", ascending=False)
    )
    
    # 결과 요약 로깅
    logger.info("평가 완료!")
    logger.info("모델별 정확도:")
    for _, row in acc_by_model.iterrows():
        logger.info(f"  {row['model_name']}: {row['accuracy']:.3f}")
    
    # 캐시 정보 로깅
    cache_info = get_cache_info()
    logger.info(f"[CACHE] 평가 완료 후 캐시 상태: {len(cache_info['cached_models'])}개 모델 캐시됨")
    
    # 무효 예측 응답 저장
    if 'invalid_responses' in locals() and invalid_responses:
        save_invalid_responses(invalid_responses, "evaluation")
    
    return df_all, pred_long, pred_wide, acc_by_model

def run_eval_pipeline_improved(
    json_list: List[dict],
    models: List[str],
    sample_size: int = 300,
    batch_size: int = 50,
    seed: int = 42,
    mock_mode: bool = False,
    use_server_mode: bool = False,
    reasoning: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    O, X 문제를 지원하는 개선된 평가 파이프라인
    반환:
      df_all      : 전체 원장 (정규화 선지 + answer_set + is_ox_question)
      pred_long   : (id, model_name, answer) 롱 포맷
      pred_wide   : id 기준 모델별 예측 와이드
      acc_by_model: 모델별 정확도 (복수정답 지원: 예측 ∈ answer_set 이면 정답)
    """
    logger.info(f"개선된 평가 파이프라인 시작 - 샘플수: {sample_size}, 배치크기: {batch_size}, 모델수: {len(models)}")
    
    # (1) JSON → df_all (O, X 문제 지원)
    logger.info("1단계: JSON 데이터를 DataFrame으로 변환 중...")
    df_all = json_to_df_all_improved(json_list, use_ox_support=True)
    df_all = df_all.sort_values(by=['book_id', 'tag'], ascending=False).reset_index(drop=True)
    logger.info(f"전체 데이터: {len(df_all)}개 문제")

    # O, X 문제 분석
    ox_questions, regular_questions = analyze_ox_questions(df_all)

    # (2) 샘플링
    logger.info(f"2단계: {sample_size}개 샘플 추출 중...")
    # 샘플 크기가 전체 데이터보다 큰 경우, 전체 데이터 크기로 조정
    actual_sample_size = min(sample_size, len(df_all))
    if actual_sample_size < sample_size:
        logger.warning(f"요청한 샘플 크기({sample_size})가 전체 데이터({len(df_all)})보다 큼. {actual_sample_size}개로 조정합니다.")
    df_sample = df_all.sample(n=actual_sample_size, random_state=seed).reset_index(drop=True)
    logger.info(f"샘플 데이터: {len(df_sample)}개 문제")

    # 샘플에서 O, X 문제 비율 확인
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

    if reasoning:
        SYSTEM_PROMPT = SYSTEM_PROMPT + "<think> </think>"
    else:
        pass
    
    # 전체 진행상황 표시
    with tqdm(total=total_calls, desc="모델 호출 진행", unit="call") as pbar:
        for bidx, bdf in enumerate(batches, 1):
            user_prompt = build_user_prompt(bdf)
            ids = bdf["id"].tolist()
            
            for model in models:
                try:
                    # 배치별 진행상황 표시
                    pbar.set_description(f"배치 {bidx}/{len(batches)} - {model}")
                    
                    raw = call_llm(model, SYSTEM_PROMPT, user_prompt, mock_mode=mock_mode, use_server_mode=use_server_mode)
                    parsed = parse_model_output(raw, ids, reasoning=reasoning)
                    
                    # 파싱 결과 검증
                    valid_predictions = sum(1 for v in parsed.values() if not np.isnan(v))
                    logger.info(f"배치 {bidx} - {model}: {valid_predictions}/{len(ids)}개 유효 예측")
                    
                    # 무효 예측이 있는 경우 디버깅 정보 출력 및 저장
                    if valid_predictions < len(ids):
                        logger.warning(f"배치 {bidx} - {model}: 무효 예측 감지!")
                        logger.warning(f"예상 ID: {ids}")
                        logger.warning(f"모델 원시 출력:\n{raw}")
                        logger.warning(f"파싱된 결과: {parsed}")
                        
                        # 무효 예측 응답 저장 (모델명, 문제, 답변 포함)
                        for _id in ids:
                            if np.isnan(parsed[_id]):
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
                                    "parsed_result": parsed[_id],
                                    "timestamp": dt.datetime.now().isoformat()
                                }
                                invalid_responses.append(invalid_response)
                    
                    for _id in ids:
                        rows.append({"id": _id, "model_name": model, "answer": parsed[_id]})
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"배치 {bidx} - {model} 처리 중 오류: {str(e)}")
                    # 오류 발생 시 NaN으로 채움
                    for _id in ids:
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
    
    def _is_correct(pred: float, s: Set[int]) -> float:
        if np.isnan(pred) or not s:
            return np.nan
        return float(int(pred) in s)

    merged = pred_long.merge(key, on="id", how="left")
    merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"]), axis=1)

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
        save_invalid_responses(invalid_responses, "evaluation")
    
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

def save_invalid_responses(invalid_responses: List[Dict], filename_prefix: str = "evaluation"):
    """무효 예측 응답을 별도 파일로 저장 (모델명, 문제, 답변 포함)"""
    if not invalid_responses:
        logger.info("무효 예측이 없어 저장할 파일이 없습니다.")
        return
    
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    invalid_filename = f"evaluation/result/{filename_prefix}_invalid_responses_{timestamp}.json"
    
    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(invalid_filename), exist_ok=True)
    
    try:
        with open(invalid_filename, 'w', encoding='utf-8') as f:
            json.dump(invalid_responses, f, ensure_ascii=False, indent=2)
        logger.info(f"무효 예측 응답 저장: {invalid_filename}")
        logger.info(f"총 {len(invalid_responses)}개의 무효 예측 응답이 저장되었습니다.")
        
        # 요약 정보도 출력
        model_counts = {}
        for resp in invalid_responses:
            model = resp.get('model_name', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        logger.info("모델별 무효 예측 수:")
        for model, count in model_counts.items():
            logger.info(f"  {model}: {count}개")
            
    except Exception as e:
        logger.error(f"무효 예측 응답 저장 실패: {str(e)}")

def save_detailed_logs(pred_long_df: pd.DataFrame, filename_prefix: str = "evaluation"):
    """상세한 로그를 CSV로 저장"""
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    
    # 예측 결과 상세 로그
    pred_log_filename = f"evaluation/result/log/{filename_prefix}_predictions_{timestamp}.csv"
    os.makedirs(os.path.dirname(pred_log_filename), exist_ok=True)
    pred_long_df.to_csv(pred_log_filename, index=False, encoding='utf-8-sig')
    logger.info(f"상세 예측 로그 저장: {pred_log_filename}")
    
    # 모델별 통계
    model_stats = pred_long_df.groupby('model_name').agg({
        'answer': [lambda x: x.count(), lambda x: x.notna().sum(), lambda x: x.isna().sum()]
    }).round(3)
    model_stats.columns = ['총_예측수', '유효_예측수', '무효_예측수']
    model_stats['유효율'] = (model_stats['유효_예측수'] / model_stats['총_예측수'] * 100).round(1)
    
    stats_filename = f"evaluation/result/log/{filename_prefix}_model_stats_{timestamp}.csv"
    os.makedirs(os.path.dirname(stats_filename), exist_ok=True)
    model_stats.to_csv(stats_filename, encoding='utf-8-sig')
    logger.info(f"모델 통계 저장: {stats_filename}")

def check_data_quality(df_all: pd.DataFrame, df_sample: pd.DataFrame):
    """데이터 품질 검사"""
    logger.info("데이터 품질 검사 시작...")
    
    issues = []
    
    # 1. 빈 문제 검사
    empty_questions = df_all[df_all['question'].str.strip() == '']
    if len(empty_questions) > 0:
        issues.append(f"빈 문제: {len(empty_questions)}개")
    
    # 2. 빈 선지 검사
    empty_options = df_all[(df_all['opt1'].str.strip() == '') & 
                          (df_all['opt2'].str.strip() == '') & 
                          (df_all['opt3'].str.strip() == '') & 
                          (df_all['opt4'].str.strip() == '') & 
                          (df_all['opt5'].str.strip() == '')]
    if len(empty_options) > 0:
        issues.append(f"빈 선지 문제: {len(empty_options)}개")
    
    # 3. 정답 없는 문제 검사
    no_answer = df_all[df_all['answer_set'].apply(len) == 0]
    if len(no_answer) > 0:
        issues.append(f"정답 없는 문제: {len(no_answer)}개")
    
    # 4. 중복 문제 검사
    duplicates = df_all[df_all.duplicated(subset=['question'], keep=False)]
    if len(duplicates) > 0:
        issues.append(f"중복 문제: {len(duplicates)}개")
    
    if issues:
        logger.warning("데이터 품질 이슈 발견:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("데이터 품질 검사 통과 ✅")
    
    return issues

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

def save_results_to_excel(df_all: pd.DataFrame, pred_wide: pd.DataFrame, acc: pd.DataFrame, pred_long: pd.DataFrame = None, filename: str = None, mock_mode: bool = False):
    """결과를 Excel 파일로 저장 (domain, subdomain 분석 포함)"""
    
    # 기본 저장 경로 설정 (현재 사용자 기준)
    # current_user = os.path.expanduser("~").split("/")[-1]  # 현재 사용자명 추출
    current_user = os.path.dirname(__file__)
    default_base_path = f"{home_dir}/result/"
    
    if filename is None:
        timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        if mock_mode:
            filename = f"{default_base_path}evaluation_results_test_{timestamp}.xlsx"
        else:
            filename = f"{default_base_path}evaluation_results_{timestamp}.xlsx"
    elif not filename.startswith(('/', './', 'evaluation/')):
        # 파일명만 주어진 경우 (확장자 포함 여부 확인)
        timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        if filename.endswith('.xlsx'):
            # 확장자가 있는 경우
            name = filename[:-5]  # .xlsx 제거
            if mock_mode and 'test' not in name:
                filename = f"{default_base_path}{name}_test_{timestamp}.xlsx"
            else:
                filename = f"{default_base_path}{name}_{timestamp}.xlsx"
        else:
            # 확장자가 없는 경우
            if mock_mode and 'test' not in filename:
                filename = f"{default_base_path}{filename}_test_{timestamp}.xlsx"
            else:
                filename = f"{default_base_path}{filename}_{timestamp}.xlsx"
    elif filename.startswith('evaluation/'):
        # evaluation/로 시작하는 경우 기본 경로 사용
        if mock_mode and 'test' not in filename:
            name, ext = os.path.splitext(filename)
            filename = f"{default_base_path}{name}_test{ext}"
        else:
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

def replace_tags_in_text(text: str, additional_tag_data: list) -> str:
    """
    텍스트에서 {f_0000_0000}이나 {tb_0000_0000} 같은 태그를 additional_tag_data에서 찾아서 대치합니다.
    
    Args:
        text: 대치할 텍스트
        additional_tag_data: 태그 데이터 리스트
    
    Returns:
        태그가 대치된 텍스트
    """
    if not text or not additional_tag_data:
        return text
    
    # 태그 패턴 매칭: {f_0000_0000}, {tb_0000_0000}, {img_0000_0000}, {etc_0000_0000}, {note_0000_0000}
    tag_pattern = r'\{(f_\d{4}_\d{4}|tb_\d{4}_\d{4}|note_\d{4}_\d{4})\}'
    
    def replace_tag(match):
        tag_with_braces = match.group(0)  # {f_0000_0000}
        tag_without_braces = match.group(1)  # f_0000_0000
        
        # additional_tag_data에서 해당 태그 찾기
        for tag_data in additional_tag_data:
            if tag_data.get('tag') == tag_with_braces:
                # data 필드가 있는 경우
                if 'data' in tag_data:
                    data = tag_data.get('data', {})
                    if isinstance(data, dict):
                        # data에서 적절한 필드 찾기 (우선순위: content, text, description, caption)
                        for field in ['content', 'text', 'description', 'caption']:
                            if field in data and data[field]:
                                return str(data[field])
                        
                        # file_path가 있으면 파일명 표시
                        if 'file_path' in data and data['file_path']:
                            return f"[{os.path.basename(data['file_path'])}]"
                    
                    # data가 문자열이면 그대로 사용
                    elif isinstance(data, str) and data:
                        return data
                    
                    # data가 리스트면 첫 번째 요소 사용
                    elif isinstance(data, list) and data:
                        return str(data[0])
                
                # data 필드가 없는 경우, 직접 필드에서 찾기
                else:
                    # 직접 필드에서 적절한 내용 찾기 (우선순위: content, text, description, caption)
                    for field in ['content', 'text', 'description', 'caption']:
                        if field in tag_data and tag_data[field]:
                            return str(tag_data[field])
                    
                    # file_path가 있으면 파일명 표시
                    if 'file_path' in tag_data and tag_data['file_path']:
                        return f"[{os.path.basename(tag_data['file_path'])}]"
        
        # 태그를 찾지 못한 경우 원본 태그 유지
        return tag_with_braces
    
    return re.sub(tag_pattern, replace_tag, text)

def replace_tags_in_qna_data(qna_data: dict, additional_tag_data: list) -> dict:
    """
    Q&A 데이터의 question과 options에서 태그를 대치합니다.
    
    Args:
        qna_data: Q&A 데이터 딕셔너리 (전체 qna 객체 또는 qna_data 부분)
        additional_tag_data: 추가 태그 데이터 리스트
    
    Returns:
        태그가 대치된 Q&A 데이터
    """
    if not qna_data:
        return qna_data
    
    if not additional_tag_data:
        return qna_data
    
    # qna_data가 전체 qna 객체인 경우 qna_data 부분을 추출
    if 'qna_data' in qna_data:
        qna_info = qna_data['qna_data']
    else:
        # 이미 qna_data 부분만 전달된 경우
        qna_info = qna_data
    
    if 'description' in qna_info:
        desc = qna_info['description']
        
        # question 필드 처리
        if 'question' in desc and desc['question']:
            desc['question'] = replace_tags_in_text(desc['question'], additional_tag_data)
        
        # options 필드 처리 (리스트)
        if 'options' in desc and desc['options']:
            if isinstance(desc['options'], list):
                desc['options'] = [replace_tags_in_text(option, additional_tag_data) for option in desc['options']]
            else:
                desc['options'] = replace_tags_in_text(desc['options'], additional_tag_data)
        
        # answer 필드 처리
        if 'answer' in desc and desc['answer']:
            desc['answer'] = replace_tags_in_text(desc['answer'], additional_tag_data)
        
        # explanation 필드 처리
        if 'explanation' in desc and desc['explanation']:
            desc['explanation'] = replace_tags_in_text(desc['explanation'], additional_tag_data)
    
    return qna_data

# -----------------------------
# 유틸리티 함수들
# -----------------------------

def extract_subject_from_filename(filename: str) -> str:
    """파일명에서 subject 정보를 추출합니다.
    
    Args:
        filename: 파일명 (예: "금융실무1_mock_exam_set1.json")
    
    Returns:
        str: 추출된 subject (예: "금융실무1")
    """
    if '_mock_exam' in filename:
        # mock_exam 파일인 경우 파일명에서 subject 추출
        subject = filename.split("_")[0]
        return subject
    else:
        # 일반 파일인 경우 빈 문자열 반환
        return ""

# -----------------------------
# 데이터 로딩 함수
# -----------------------------

def load_data_from_directory(data_path: str, apply_tag_replacement: bool = True) -> Tuple[List[dict], bool]:
    """디렉토리에서 JSON 파일들을 로드하여 데이터 리스트 반환
    
    Returns:
        Tuple[List[dict], bool]: (데이터 리스트, mock_exam 파일 포함 여부)
    """
    json_files = []
    is_mock_exam = False
    
    for root, _, files in os.walk(data_path):
        for f in files:
            if f.endswith(".json") and ('merged' not in f):
                json_files.append(os.path.join(root, f))
                # mock_exam 파일인지 확인
                if '_mock_exam' in f:
                    is_mock_exam = True
    
    logger.info(f"발견된 JSON 파일 수: {len(json_files)}")
    if is_mock_exam:
        logger.info("Mock exam 파일이 감지되었습니다. 객관식 필터링을 건너뜁니다.")
    
    all_data = []
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 파일명에서 subject 추출 (mock_exam 파일인 경우)
                filename = os.path.basename(file_path)
                subject = extract_subject_from_filename(filename)
                
                if isinstance(data, list):
                    # 리스트인 경우 각 항목에 subject 추가
                    for item in data:
                        item['subject'] = subject
                    all_data.extend(data)
                else:
                    # 단일 객체인 경우 subject 추가
                    data['subject'] = subject
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
                    item['qna_data'] = replace_tags_in_qna_data(
                        item['qna_data'], 
                        item['additional_tag_data']
                    )
                    processed_count += 1
        logger.info(f"태그 대치 완료: {processed_count}개 항목 처리")
    
    return all_data, is_mock_exam

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
    parser.add_argument('--mock_mode', action='store_true', help='Mock 모드로 실행 (실제 API 호출 없음)')
    parser.add_argument('--use_ox_support', action='store_true', help='O, X 문제 지원 활성화')
    parser.add_argument('--apply_tag_replacement', action='store_true', help='태그 대치 적용 (기본값: True)')
    parser.add_argument('--no_tag_replacement', action='store_true', help='태그 대치 비활성화')
    parser.add_argument('--seed', type=int, default=42, help='랜덤 시드 (기본값: 42)')
    parser.add_argument('--output_filename', type=str, help='결과 Excel 파일명 (기본값: 자동 생성)')
    parser.add_argument('--debug', action='store_true', help='디버그 로그 활성화')
    parser.add_argument('--reasoning', action='store_true', default=False, help='추론 모델 여부')
    
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
    logger.info(f"Mock 모드: {args.mock_mode}")
    logger.info(f"O, X 문제 지원: {args.use_ox_support}")
    logger.info(f"추론 모델 여부: {args.reasoning}")
    logger.info(f"출력 파일명: {args.output_filename or '자동 생성'}")
    
    # API 모드 확인
    use_server_mode = args.server
    if use_server_mode:
        logger.info("모드: vLLM 서버 모드")
    else:
        logger.info("모드: OpenRouter API 모드 (기본값)")
    
    # 태그 대치 옵션 처리
    apply_tag_replacement = not args.no_tag_replacement
    logger.info(f"태그 대치 적용: {apply_tag_replacement}")
    
    try:
        # 데이터 로딩
        logger.info("데이터 로딩 중...")
        all_data, is_mock_exam = load_data_from_directory(args.data_path, apply_tag_replacement)
        
        # mock_exam 파일이 아닌 경우에만 객관식 필터링 적용
        if is_mock_exam:
            multiple_choice_data = all_data
            logger.info("Mock exam 파일이므로 모든 데이터를 사용합니다.")
        else:
            multiple_choice_data = filter_multiple_choice_questions(all_data)
            logger.info(f"객관식 문제 필터링 완료: {len(multiple_choice_data)}개")
        
        if len(multiple_choice_data) == 0:
            logger.error("처리할 데이터를 찾을 수 없습니다.")
            return
        
        # 샘플링
        if len(multiple_choice_data) > args.sample_size:
            random.seed(args.seed)
            sample_data = random.sample(multiple_choice_data, args.sample_size)
        else:
            sample_data = multiple_choice_data
            logger.info(f"전체 데이터 사용: {len(sample_data)}개")
        
        # 데이터 품질 검사
        if args.use_ox_support:
            df_temp = json_to_df_all_improved(sample_data, use_ox_support=True)
        else:
            df_temp = json_to_df_all(sample_data)
        
        quality_issues = check_data_quality(df_temp, df_temp.sample(n=min(50, len(df_temp)), random_state=args.seed))
        
        # O, X 문제 분석 (지원하는 경우)
        if args.use_ox_support:
            ox_questions, regular_questions = analyze_ox_questions(df_temp)
        
        # 평가 실행
        logger.info("평가 실행 중...")
        if args.use_ox_support:
            df_all, pred_long, pred_wide, acc = run_eval_pipeline_improved(
                sample_data, args.models, args.sample_size, args.batch_size, args.seed, args.mock_mode, use_server_mode, args.reasoning
            )
        else:
            df_all, pred_long, pred_wide, acc = run_eval_pipeline(
                sample_data, args.models, args.sample_size, args.batch_size, args.seed, args.mock_mode, use_server_mode, args.reasoning
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
        save_results_to_excel(df_all, pred_wide, acc, pred_long, args.output_filename, args.mock_mode)
        
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
