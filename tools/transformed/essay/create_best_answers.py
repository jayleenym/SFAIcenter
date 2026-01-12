#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계: 모범답안 생성
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
    save_questions
)

# 모듈 레벨 로거 (독립 실행 시 사용)
_module_logger = None


def _get_module_logger():
    """모듈 레벨 로거 생성"""
    global _module_logger
    if _module_logger is None:
        _module_logger = setup_logger(
            name=__name__,
            log_file='essay_create_best_answers.log',
            use_console=True,
            use_file=True
        )
    return _module_logger


def create_best_answers(llm=None, onedrive_path=None, log_func=None, round_number=None):
    """
    3단계: 모범답안 생성만 수행
    
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
    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json')
    output_file = os.path.join(essay_dir, 'answers', f'best_ans_{round_folder}.json')
    
    questions = load_questions(input_file, log_func, '3단계')
    if questions is None:
        return 0
    
    # 모범답안 생성
    system_prompt = """
당신은 주어진 여러 정보를 조합하여 서술형 문제에 대한 '모범답안'을 생성하는 AI입니다.

**[역할]**
- '서술형 질문'의 요구사항을 정확히 파악합니다.
- '원래 질문/선지/정답/해설'에서 서술형 질문에 답변하는 데 필요한 핵심 정보를 추출합니다.
- 추출한 정보와 '키워드'를 논리적으로 엮어 하나의 완성된 글로 재구성합니다.

**[수행 절차]**
1.  **주제 파악:** '서술형 질문'과 '키워드'를 통해 모범답안이 다루어야 할 핵심 주제와 포함해야 할 요소를 확인합니다.
2.  **정보 추출:** '원래 선지'와 '선지별 해설'을 분석하여 각 '키워드'에 해당하는 구체적인 내용을 찾아냅니다.
3.  **논리적 구성:** 추출한 정보들을 활용하여 '서술형 질문'에 대한 답변이 되도록 문장을 자연스럽게 연결하고 문단을 구성합니다. 이때, 모든 '키워드'가 '그대로' 포함되어야 합니다.
4.  **답안 생성:** 위의 과정을 거쳐 최종 '모범답안'을 작성합니다.

**[규칙]**
- **절대 외부 지식을 사용하지 마세요.** 반드시 '원래 질문/선지/정답/해설'에 명시된 정보만을 근거로 답안을 작성해야 합니다.
- 제시된 모든 '키워드'를 반드시 답안에 '그대로' 포함해야 합니다.
- 최종 결과물은 "모범답안:"으로 시작하는 완성된 형태의 글이어야 합니다.
"""
    
    log_func("모범답안 생성 중...")
    for q in tqdm(questions, desc="모범답안 생성"):
        user_prompt = f"""
========= 문제 ========
- 서술형 질문: {q['essay_question']}
- 키워드: {q['essay_keyword']}
- 원래 질문: {q['question']}
- 원래 선지: {q['options']}
- 원래 정답: {q['answer']}
- 선지별 해설: {q['explanation']}
"""
        response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-3-pro-preview')
        q['essay_answer'] = response.replace('모범답안:', '').strip()
    
    save_questions(questions, output_file, log_func, '3단계')
    return len(questions)


def main(round_number='1'):
    """메인 함수"""
    create_best_answers(round_number=round_number)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='모범답안 생성')
    parser.add_argument('--round', type=str, default='1', help='회차 번호 (1-5)')
    args = parser.parse_args()
    main(round_number=args.round)

