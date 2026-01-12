#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0단계: 옳지 않은 문제 중 해설이 많은 문제 선별
"""

import os
import json
from tqdm import tqdm

from tools.core.llm_query import LLMQuery
from tools.core.logger import setup_logger
from .common import init_common

# 모듈 레벨 로거 (독립 실행 시 사용)
_module_logger = None


def _get_module_logger():
    """모듈 레벨 로거 생성"""
    global _module_logger
    if _module_logger is None:
        _module_logger = setup_logger(
            name=__name__,
            log_file='essay_filter_full_explanation.log',
            use_console=True,
            use_file=True
        )
    return _module_logger


def is_full_explanation(llm, question, answer, options, explanation):
    """해설이 문제의 모든 선지에 대한 설명을 포함하는지 확인"""
    system_prompt = """다음은 문제, 정답, 해설입니다.
    해설에 모든 선지에 대한 설명이 포함되어 있으면 'full'을 반환하고, 아니라면 'notfull'을 반환해주세요.
    """
    user_prompt = f"""
    문제: {question}
    정답: {answer}
    선지: {options}
    해설: {explanation}
    """
    response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-2.5-flash')
    return response.strip()


def filter_full_explanation(llm=None, onedrive_path=None, log_func=None):
    """
    0단계: 옳지 않은 문제 중 해설이 많은 문제 선별
    
    Args:
        llm: LLMQuery 인스턴스 (None이면 새로 생성)
        onedrive_path: OneDrive 경로 (None이면 ONEDRIVE_PATH 사용)
        log_func: 로깅 함수 (None이면 logger.info 또는 print 사용)
    
    Returns:
        int: 선별된 문제 개수
    """
    logger = _get_module_logger() if log_func is None else None
    llm, onedrive_path, log_func = init_common(llm, onedrive_path, log_func, logger)
    
    classified_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw')
    essay_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '9_multiple_to_essay')
    
    classified_file = os.path.join(classified_dir, 'answer_type_classified.json')
    output_file = os.path.join(essay_dir, 'full_explanation.json')
    
    os.makedirs(essay_dir, exist_ok=True)
    
    # 입력 파일 확인
    if not os.path.exists(classified_file):
        log_func(f"오류: 입력 파일이 존재하지 않습니다: {classified_file}")
        return 0
    
    # 입력 파일 읽기
    log_func(f"0단계 입력 파일 읽기: {classified_file}")
    with open(classified_file, 'r', encoding='utf-8') as f:
        classified_data = json.load(f)
    
    # answer_type이 'wrong'인 문제만 필터링
    wrong_questions = [p for p in classified_data if p.get('answer_type') == 'wrong']
    log_func(f"옳지 않은 문제: {len(wrong_questions)}개")
    
    # 해설이 모든 선지를 포함하는 문제만 선별
    full_explanation = []
    notfull_explanation = []
    fail = []
    
    log_func("해설이 많은 문제 선별 중...")
    for wd in tqdm(wrong_questions, desc="해설 검증"):
        if wd['explanation'] == '':
            notfull_explanation.append(wd)
            continue
        else:
            response = is_full_explanation(
                llm, 
                wd['question'], 
                wd['answer'], 
                wd['options'], 
                wd['explanation']
            )
            if 'full' in response.lower():
                full_explanation.append(wd)
            elif 'notfull' in response.lower():
                notfull_explanation.append(wd)
            else:
                fail.append(wd)
    
    log_func(f"\n선별 결과:")
    log_func(f"  - full (해설 완전): {len(full_explanation)}개")
    log_func(f"  - notfull (해설 불완전): {len(notfull_explanation)}개")
    log_func(f"  - fail (분류 실패): {len(fail)}개")
    log_func(f"  - 총합: {len(full_explanation) + len(notfull_explanation) + len(fail)}개")
    
    questions = full_explanation
    
    # 결과 저장
    log_func(f"0단계 저장: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    log_func(f"0단계 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")
    return len(questions)


def main():
    """메인 함수"""
    filter_full_explanation()


if __name__ == '__main__':
    main()

