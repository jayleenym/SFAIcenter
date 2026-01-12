#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 키워드 추출
"""

import os
from tqdm import tqdm

from tools.core.llm_query import LLMQuery
from tools.core.logger import setup_logger
from .common import (
    ROUND_NUMBER_TO_FOLDER,
    init_common,
    validate_round_number,
    get_essay_dir,
    load_questions,
    save_questions,
    clean_question_data
)

# 모듈 레벨 로거 (독립 실행 시 사용)
_module_logger = None


def _get_module_logger():
    """모듈 레벨 로거 생성"""
    global _module_logger
    if _module_logger is None:
        _module_logger = setup_logger(
            name=__name__,
            log_file='essay_extract_keywords.log',
            use_console=True,
            use_file=True
        )
    return _module_logger


def extract_keywords(llm=None, onedrive_path=None, log_func=None, round_number=None):
    """
    2단계: 키워드 추출만 수행
    
    Args:
        llm: LLMQuery 인스턴스 (None이면 새로 생성)
        onedrive_path: OneDrive 경로 (None이면 ONEDRIVE_PATH 사용)
        log_func: 로깅 함수 (None이면 logger.info 또는 print 사용)
        round_number: 회차 번호 (예: '1', '2', '3', '4', '5')
    
    Returns:
        int: 처리된 문제 개수
    """
    logger = _get_module_logger() if log_func is None else None
    llm, onedrive_path, log_func = init_common(llm, onedrive_path, log_func, logger)
    
    round_folder = validate_round_number(round_number, log_func)
    if round_folder is None:
        return 0
    
    essay_dir = get_essay_dir(onedrive_path)
    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}_서술형문제로변환.json')
    output_file = os.path.join(essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json')
    
    questions = load_questions(input_file, log_func, '2단계')
    if questions is None:
        return 0
    
    # 키워드 추출
    system_prompt = """당신은 25년 경력의 서술형 문제 전문가입니다. 아래 지시사항을 정확히 이해하고 수행하여 키워드를 추출하시오.
    
지시사항:
1. 주어진 essay_question에서 주요 주제를 식별하라. 
2. 주어진 options, answer, explanation을 참고하여 완벽한 서술형 답변을 작성하기에 핵심적이라고 판단되는 단어 또는 종결어미를 뺀 어절 1개씩 추출하라. 이때 어절은 최대 2개의 단어까지 허용한다.
3. 키워드는 essay_question의 주제와 겹치지 않도록 추출하라. 중복된 키워드는 제거하고, 총 5개 이내로 추출하라.
4. 단, 단어,표현 추출은 원문이 가진 텍스트 원본을 그대로 유지하라. 조사와 띄어쓰기 모두 반드시 유지해서 추출하라

출력 형식:
- 키워드: [키워드1], [키워드2], [키워드3], [키워드4], [키워드5]
    """
    
    log_func("키워드 추출 중...")
    for q in tqdm(questions, desc="키워드 추출"):
        clean_question_data(q)
        
        user_prompt = f"""
입력:
    - essay_question: {q['essay_question']}
    - options: {q['options']}
    - answer: {q['answer']}
    - explanation: {q['explanation']}
"""
        response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-2.5-flash')
        try:
            q['essay_keyword'] = response.strip().split('키워드: ')[1].replace("[", "").replace("]", "").replace("-", "").strip()
        except Exception as e:
            log_func(f"오류: 키워드 추출 실패 - {e}")
            q['essay_keyword'] = ''
            continue
    
    save_questions(questions, output_file, log_func, '2단계')
    return len(questions)


def main(round_number='1'):
    """메인 함수"""
    extract_keywords(round_number=round_number)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='키워드 추출')
    parser.add_argument('--round', type=str, default='1', help='회차 번호 (1-5)')
    args = parser.parse_args()
    main(round_number=args.round)

