#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 평가 시스템 - 통합 버전 (Class-based Refactoring)
O, X 문제를 포함한 객관식 문제 평가 시스템
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
from typing import List, Dict, Tuple, Set, Any, Optional
from tqdm import tqdm
import argparse

# Core tools imports
try:
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.dirname(os.path.dirname(current_dir)) # tools -> root
    sys.path.insert(0, project_root_dir)
    from tools import PROJECT_ROOT_PATH, ONEDRIVE_PATH, SFAICENTER_PATH
    from tools.core.logger import setup_logger
    from tools.core.llm_query import LLMQuery
    from tools.core.utils import TextProcessor
    from tools.qna.extraction.tag_processor import TagProcessor
except ImportError:
    # Fallback for standalone execution
    PROJECT_ROOT_PATH = os.getcwd()
    ONEDRIVE_PATH = os.getcwd()
    SFAICENTER_PATH = os.getcwd()
    setup_logger = logging.getLogger
    LLMQuery = None
    TextProcessor = None
    TagProcessor = None

# Logger setup
_log_file = 'multiple_eval_by_model.log'
if __name__ == "__main__":
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    _log_file = f'{script_name}.log'

logger = setup_logger(
    name=__name__,
    log_file=_log_file,
    use_console=True,
    use_file=True
)

class MultipleChoiceEvaluator:
    """객관식 문제 평가 클래스"""
    
    CIRCLED_MAP = {"①":"1","②":"2","③":"3","④":"4","⑤":"5"}
    
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
- 정답 개수는 두 개 이상 다섯 개 이하입니다.
- 다른 글자, 마크다운, 이유, 기호는 절대 출력하지 않습니다.
- 모든 문제는 보기(1~5) 중 두 개 이상을 선택합니다.
- 출력 줄 수는 입력 문제 개수와 동일해야 합니다.
"""

    def __init__(self, api_key: str = None, use_server_mode: bool = False):
        self.api_key = api_key
        self.use_server_mode = use_server_mode
        self.llm_query = None
        self._model_cache = {}
        
        # 서버 모드에서는 HuggingFace Hub 오프라인 모드 활성화 (로컬 모델 사용 시 불필요한 원격 요청 방지)
        if use_server_mode:
            os.environ['HF_HUB_OFFLINE'] = '1'
            logger.info("HF_HUB_OFFLINE=1 설정 (서버 모드)")
        
        self._init_llm()

    def _init_llm(self):
        """LLMQuery 초기화"""
        if LLMQuery:
            try:
                self.llm_query = LLMQuery(api_key=self.api_key)
                logger.info(f"LLMQuery 초기화 완료 (API Key: {'Yes' if self.api_key else 'No'})")
            except Exception as e:
                logger.error(f"LLMQuery 초기화 실패: {e}")
    
    def _load_model_cached(self, model_name: str):
        """vLLM 모델 캐싱 (서버 모드용)"""
        if model_name not in self._model_cache:
            logger.info(f"[CACHE] 모델 로드 중: {model_name}")
            self.llm_query.load_vllm_model(model_name)
            self._model_cache[model_name] = True # Simply marker
            logger.info(f"[CACHE] 모델 로드 완료: {model_name}")
        return self.llm_query

    def call_llm(self, model_name: str, system_prompt: str, user_prompt: str, max_retries: int = 3) -> Tuple[str, float]:
        """LLM 호출"""
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                if self.use_server_mode:
                    logger.debug(f"[VLLM] 모델 {model_name} 호출 (시도 {attempt + 1})")
                    self._load_model_cached(model_name)
                    ans = self.llm_query.query_vllm(system_prompt, user_prompt)
                else:
                    logger.debug(f"[API] 모델 {model_name} 호출 (시도 {attempt + 1})")
                    ans = self.llm_query.query_openrouter(system_prompt, user_prompt, model_name)
                    time.sleep(1.5) # Rate limit buffer
                
                elapsed_time = time.time() - start_time
                return ans, elapsed_time
            
            except Exception as e:
                logger.warning(f"모델 호출 실패 ({model_name}, 시도 {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)

    def parse_answer_set(self, ans, question: str = "", options: list = None) -> Set[int]:
        """정답 파싱"""
        if not ans:
            return set()
        
        # 리스트 답안 처리
        if isinstance(ans, list):
            result_set = set()
            for item in ans:
                if not item: continue
                s = str(item).strip()
                for k, v in self.CIRCLED_MAP.items():
                    s = s.replace(k, v)
                nums = re.findall(r"[1-5]", s)
                result_set.update(int(n) for n in nums)
            return result_set
        
        s = str(ans).strip()
        # O, X 처리
        if s.upper() in ['O', 'X']:
            return {1} if s.upper() == 'O' else {2}
        
        for k, v in self.CIRCLED_MAP.items():
            s = s.replace(k, v)
        nums = re.findall(r"[1-5]", s)
        return set(int(n) for n in nums)

    def is_ox_question(self, question: str, options: list) -> bool:
        """O, X 문제 판단"""
        if not options or len(options) == 0: return False
        if len(options) <= 2:
            option_text = " ".join(options).upper()
            return "O" in option_text or "X" in option_text
        return False

    def normalize_option(self, text: str) -> str:
        if TextProcessor:
            return TextProcessor.normalize_option_text(text)
        return str(text).strip()

    def json_to_df(self, json_list: List[dict], use_ox_support: bool = False, transformed: bool = False) -> pd.DataFrame:
        """JSON 데이터를 DataFrame으로 변환"""
        rows = []
        for item in json_list:
            book_id = str(item.get("file_id", ""))
            tag = item.get("tag", "")
            q = (item.get("question") or "").strip()
            opts = item.get("options", [])
            answer = item.get("answer", "")
            
            ans_set = self.parse_answer_set(answer, q, opts)
            
            is_ox = False
            if use_ox_support:
                is_ox = self.is_ox_question(q, opts)
                if is_ox:
                    opts = ["O", "X"] + [""] * 3
                else:
                    opts = list(opts)[:5] + [""] * max(0, 5 - len(opts))
            else:
                opts = list(opts)[:5] + [""] * max(0, 5 - len(opts))
            
            opts = [self.normalize_option(x) for x in opts]
            
            row_data = {
                "subject": item.get("subject", ""),
                "domain": item.get("domain", ""),
                "subdomain": item.get("subdomain", ""),
                "book_id": book_id,
                "tag": tag,
                "id": f"{book_id}_{tag}",
                "question": q,
                "opt1": opts[0], "opt2": opts[1], "opt3": opts[2], "opt4": opts[3], "opt5": opts[4],
                "answer_set": ans_set
            }
            if use_ox_support:
                row_data["is_ox_question"] = is_ox
            rows.append(row_data)
            
        df = pd.DataFrame(rows)
        
        # ID 중복 처리
        if not df.empty:
            duplicate_ids = df[df.duplicated(subset=["id"], keep=False)]
            if not duplicate_ids.empty:
                logger.info(f"ID 중복 발견: {len(duplicate_ids)}개. 고유 ID 생성.")
                unique_duplicate_ids = set(duplicate_ids["id"].unique())
                df = df.reset_index(drop=True)
                df['id'] = df.apply(
                    lambda row: f"{row['id']}_{row.name}" if row['id'] in unique_duplicate_ids else row['id'],
                    axis=1
                )
        
        return df

    def build_prompt(self, batch_df: pd.DataFrame, transformed: bool = False) -> str:
        """배치 프롬프트 생성"""
        lines = []
        if transformed:
            lines.append("다음은 금융 객관식 문제들입니다. 각 문제는 '모두 고르시오' 유형입니다. 정답이 되는 모든 번호를 선택하세요.\n")
        else:
            lines.append("다음은 금융 객관식 문제들입니다. 각 문제에 대해 정답 번호만 고르세요.\n")
        
        lines.append("문제들")
        for _, r in batch_df.iterrows():
            lines.append(f"ID: {r['id']}")
            lines.append(f"Q: {r['question']}")
            for i in range(1, 6):
                lines.append(f"{i}) {r[f'opt{i}']}")
            lines.append("")
            
        lines.append("출력 형식(중요)")
        for _, r in batch_df.iterrows():
            if transformed:
                lines.append(f"{r['id']}\\t{{번호1,번호2,...}}  (예: 1,3 또는 1 3)")
            else:
                lines.append(f"{r['id']}\\t{{번호}}")
        return "\n".join(lines)

    def parse_output(self, raw: str, expected_ids: List[str], transformed: bool = False) -> Dict[str, Any]:
        """모델 출력 파싱"""
        id_set = set(expected_ids)
        out = {k: (set() if transformed else np.nan) for k in expected_ids}
        
        if not raw or not raw.strip():
            return out
            
        for ln in raw.splitlines():
            ln = ln.strip().replace("<TAB>", "\t").replace("\\t", "\t")
            if not ln: continue
            
            if "\t" in ln:
                left, right = ln.split("\t", 1)
            else:
                parts = ln.split(None, 1)
                if len(parts) < 2: continue
                left, right = parts[0], parts[1]
            
            _id = left.strip()
            if _id not in id_set: continue
            
            if transformed:
                answer_str = right
                for k, v in self.CIRCLED_MAP.items():
                    answer_str = answer_str.replace(k, v)
                nums = re.findall(r"[1-5]", answer_str)
                if nums:
                    out[_id] = set(int(n) for n in nums)
            else:
                m = re.search(r"\{?([1-5])\}?", right)
                if m:
                    out[_id] = float(m.group(1))
        return out

    def run_eval(self, json_list: List[dict], models: List[str], 
                 sample_size: int = 300, batch_size: int = 50, seed: int = 42,
                 use_ox_support: bool = True, output_base_dir: str = None, 
                 transformed: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """평가 실행"""
        # 1. DataFrame 변환
        df_all = self.json_to_df(json_list, use_ox_support, transformed)
        df_all = df_all.sort_values(by=['book_id', 'tag'], ascending=False).reset_index(drop=True)
        
        # 2. 샘플링
        actual_sample_size = min(sample_size, len(df_all))
        if actual_sample_size < len(df_all):
            df_sample = df_all.sample(n=actual_sample_size, random_state=seed).reset_index(drop=True)
        else:
            df_sample = df_all
            
        # 3. 배치 처리 및 모델 호출
        batches = [df_sample.iloc[i:i+batch_size] for i in range(0, len(df_sample), batch_size)]
        rows = []
        system_prompt = self.SYSTEM_PROMPT_TRANSFORMED if transformed else self.SYSTEM_PROMPT
        
        total_batches = len(batches)
        total_models = len(models)
        logger.info(f"평가 시작: 총 {len(df_sample)}개 문제, {total_batches}개 배치, {total_models}개 모델")
        logger.info(f"평가 대상 모델: {models}")
        
        for bidx, bdf in enumerate(batches, 1):
            user_prompt = self.build_prompt(bdf, transformed)
            ids = bdf["id"].tolist()
            
            for midx, model in enumerate(models, 1):
                logger.info(f"[진행] 배치 {bidx}/{total_batches}, 모델 {midx}/{total_models}: {model} (문제 {len(ids)}개)")
                try:
                    raw, elapsed = self.call_llm(model, system_prompt, user_prompt)
                    
                    # 로그 저장
                    if output_base_dir:
                        log_dir = os.path.join(output_base_dir, 'model_output')
                        os.makedirs(log_dir, exist_ok=True)
                        with open(os.path.join(log_dir, f"output_{model.replace('/','_')}.txt"), "a") as f:
                            f.write(f"Batch {bidx}\nIDs: {ids}\n{raw}\n\n")
                            
                    parsed = self.parse_output(raw, ids, transformed)
                    parsed_count = sum(1 for v in parsed.values() if (isinstance(v, set) and v) or (not isinstance(v, set) and not pd.isna(v)))
                    logger.info(f"[완료] 배치 {bidx}/{total_batches}, 모델 {model}: {parsed_count}/{len(ids)}개 응답 파싱 완료 ({elapsed:.1f}초)")
                    for _id in ids:
                        rows.append({"id": _id, "model_name": model, "answer": parsed[_id]})
                        
                except Exception as e:
                    logger.error(f"[오류] 배치 {bidx}/{total_batches}, 모델 {model}: {e}")
                    for _id in ids:
                        rows.append({"id": _id, "model_name": model, "answer": (set() if transformed else np.nan)})

        # 4. 결과 정리
        logger.info(f"평가 완료: 총 {len(rows)}개 결과 수집")
        pred_long = pd.DataFrame(rows).sort_values('id').reset_index(drop=True)
        pred_wide = pred_long.pivot(index="id", columns="model_name", values="answer").reset_index()
        
        # 5. 정확도 계산
        key = df_sample[["id", "answer_set"]].copy()
        merged = pred_long.merge(key, on="id", how="left")
        
        def _is_correct(pred, ans_set):
            if not ans_set: return np.nan
            if transformed:
                return float(pred == ans_set) if isinstance(pred, set) else np.nan
            
            if pd.isna(pred): return np.nan
            return float(int(pred) in ans_set)
            
        merged["correct"] = merged.apply(lambda r: _is_correct(r["answer"], r["answer_set"]), axis=1)
        
        acc_by_model = (
            merged.groupby("model_name", dropna=False)["correct"]
            .mean().reset_index()
            .rename(columns={"correct": "accuracy"})
            .sort_values("accuracy", ascending=False)
        )
        
        return df_all, pred_long, pred_wide, acc_by_model

# Wrapper functions for backward compatibility
def load_data_from_directory(data_path: str, apply_tag_replacement: bool = False) -> List[dict]:
    """데이터 로딩 래퍼"""
    if not os.path.exists(data_path): return []
    
    json_files = []
    if os.path.isfile(data_path):
        json_files = [data_path]
    else:
        for root, _, files in os.walk(data_path):
            for f in files:
                if f.endswith(".json") and 'merged' not in f:
                    json_files.append(os.path.join(root, f))
    
    all_data = []
    for fpath in json_files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list): all_data.extend(data)
                else: all_data.append(data)
        except Exception as e:
            logger.warning(f"File load error {fpath}: {e}")
            
    if apply_tag_replacement and TagProcessor:
        for item in all_data:
            if 'additional_tag_data' in item:
                item['qna_data'] = TagProcessor.replace_tags_in_qna_data(item.get('qna_data', {}), item['additional_tag_data'])
                
    return all_data

def run_eval_pipeline(json_list, models, sample_size=300, batch_size=50, seed=42, 
                     use_server_mode=False, use_ox_support=True, api_key=None, 
                     output_base_dir=None, transformed=False):
    """평가 실행 래퍼"""
    evaluator = MultipleChoiceEvaluator(api_key=api_key, use_server_mode=use_server_mode)
    return evaluator.run_eval(json_list, models, sample_size, batch_size, seed, 
                            use_ox_support, output_base_dir, transformed)

def save_results_to_excel(df_all, pred_wide, acc, pred_long=None, filename=None):
    """결과 저장 래퍼"""
    if not filename:
        timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"evaluation_results_{timestamp}.xlsx"
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with pd.ExcelWriter(filename, engine="openpyxl") as w:
        df_all.to_excel(w, index=False, sheet_name="전체데이터")
        pred_wide.to_excel(w, index=False, sheet_name="모델별예측")
        acc.to_excel(w, index=False, sheet_name="정확도")
        if pred_long is not None:
            # Domain analysis if available
            if 'domain' in df_all.columns:
                merged = pred_long.merge(df_all[['id', 'domain']], on='id', how='left')
                merged = merged.merge(df_all[['id', 'answer_set']], on='id', how='left')
                # Simple correctness check for domain stats
                # ... (simplified logic for wrapper) ...


def save_combined_results_to_excel(df_all: pd.DataFrame, pred_wide: pd.DataFrame, 
                                    acc: pd.DataFrame, pred_long: pd.DataFrame,
                                    models: List[str], filename: str, 
                                    transformed: bool = False):
    """
    통합 평가 결과를 xlsx 파일로 저장
    
    시트 구성:
    1) 전체데이터 - 모든 문제와 정답
    2) 모델별예측 - 각 모델의 예측 결과
    3) 정확도 - 전체 정확도 (모델별)
    4) Subject별정확도 - 금융일반/심화/실무1/실무2 별 정확도
    5) Domain별정확도 - 경영/경제/내부통제 등 domain별 정확도
    6) Subdomain별정확도 - 세부 subdomain별 정확도
    
    Args:
        df_all: 전체 데이터 DataFrame (subject, domain, subdomain, id, question 등 포함)
        pred_wide: 모델별 예측 결과 (wide format)
        acc: 전체 정확도 DataFrame
        pred_long: 모델별 예측 결과 (long format)
        models: 평가에 사용된 모델 리스트
        filename: 저장할 xlsx 파일 경로
        transformed: 변형 문제 평가 여부
    """
    if df_all is None or df_all.empty:
        logger.warning("저장할 데이터가 없습니다.")
        return
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    # 정답 여부 계산을 위한 merged DataFrame 생성
    merged = pred_long.merge(df_all[['id', 'subject', 'domain', 'subdomain', 'answer_set']], on='id', how='left')
    
    def _is_correct(pred, ans_set):
        if not ans_set:
            return np.nan
        if transformed:
            return float(pred == ans_set) if isinstance(pred, set) else np.nan
        if pd.isna(pred):
            return np.nan
        return float(int(pred) in ans_set)
    
    merged['correct'] = merged.apply(lambda r: _is_correct(r['answer'], r['answer_set']), axis=1)
    
    with pd.ExcelWriter(filename, engine="openpyxl") as w:
        # 1. 전체데이터
        df_all.to_excel(w, index=False, sheet_name="전체데이터")
        
        # 2. 모델별예측
        pred_wide.to_excel(w, index=False, sheet_name="모델별예측")
        
        # 3. 정확도 (전체)
        acc.to_excel(w, index=False, sheet_name="정확도")
        
        # 4. Subject별 정확도 (금융일반/심화/실무1/실무2)
        if 'subject' in df_all.columns:
            subject_acc = merged.pivot_table(
                index='subject',
                columns='model_name',
                values='correct',
                aggfunc='mean'
            ).reset_index()
            subject_acc.to_excel(w, index=False, sheet_name="Subject별정확도")
        
        # 5. Domain별 정확도
        if 'domain' in df_all.columns:
            domain_acc = merged.pivot_table(
                index='domain',
                columns='model_name',
                values='correct',
                aggfunc='mean'
            ).reset_index()
            domain_acc.to_excel(w, index=False, sheet_name="Domain별정확도")
        
        # 6. Subdomain별 정확도
        if 'subdomain' in df_all.columns and 'domain' in df_all.columns:
            subdomain_acc = merged.pivot_table(
                index=['domain', 'subdomain'],
                columns='model_name',
                values='correct',
                aggfunc='mean'
            ).reset_index()
            subdomain_acc.to_excel(w, index=False, sheet_name="Subdomain별정확도")
    
    logger.info(f"통합 평가 결과 저장 완료: {filename}")

def print_evaluation_summary(acc, pred_long):
    """요약 출력 래퍼"""
    print("\n=== Evaluation Summary ===")
    print(acc)

def main():
    parser = argparse.ArgumentParser(description='Multiple Choice Evaluator')
    parser.add_argument('--data_path', required=True)
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--api_key', default=None)
    args = parser.parse_args()
    
    data = load_data_from_directory(args.data_path)
    run_eval_pipeline(data, args.models, api_key=args.api_key)

if __name__ == "__main__":
    main()
