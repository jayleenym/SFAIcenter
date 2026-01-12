#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1단계: 서술형 문제로 변환
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
            log_file='essay_change_question_to_essay.log',
            use_console=True,
            use_file=True
        )
    return _module_logger


def change_question_to_essay(llm=None, onedrive_path=None, log_func=None, round_number=None, input_file=None, output_file=None):
    """
    1단계: 서술형 문제로 변환
    
    Args:
        llm: LLMQuery 인스턴스 (None이면 새로 생성)
        onedrive_path: OneDrive 경로 (None이면 ONEDRIVE_PATH 사용)
        log_func: 로깅 함수 (None이면 logger.info 또는 print 사용)
        round_number: 회차 번호 (예: '1', '2', '3', '4', '5')
        input_file: 입력 파일 경로 (None이면 기본 경로 사용)
        output_file: 출력 파일 경로 (None이면 기본 경로 사용)
    Returns:
        int: 처리된 문제 개수
    """
    logger = _get_module_logger() if log_func is None else None
    llm, onedrive_path, log_func = init_common(llm, onedrive_path, log_func, logger)
    
    round_folder = validate_round_number(round_number, log_func)
    if round_folder is None:
        return 0
    
    essay_dir = get_essay_dir(onedrive_path)
    if input_file is None:
        input_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}.json')
    if output_file is None:
        output_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}_서술형문제로변환.json')
    
    questions = load_questions(input_file, log_func, '1단계')
    if questions is None:
        return 0
    
    # 서술형 문제로 변환
    system_prompt = """당신은 25년 경력의 서술형 문제 전문가입니다. 아래 지시사항을 정확히 이해하고 수행하여 서술형 문제로 변환하시오.
    
    지시사항:
    1. 주어진 question에서 주요 주제를 식별하라.
    2. 주요 주제를 바탕으로 서술형 문제로 변환하라. 조사와 띄어쓰기 모두 반드시 유지해서 변환하라.
    3. 수식이나 표는 모두 유지하라. 
    예시:
     - 수요의 가격탄력성에 관한 설명으로 옳지 않은 것은? (단, Q는 수량, P는 가격이다.) -> 다음 키워드를 활용하여 수요의 가격탄력성에 대해 서술하시오. (단, Q는 수량, P는 가격이다.)
     - 소비자 행동 이론 중 '고관여 제품'의 특징으로 옳지 않은 것은? -> 다음 키워드를 활용하여 소비자 행동 이론 중 '고관여 제품'의 특징에 대해 서술하시오.
     - 다음 중 금융투자회사의 투자설명서 이외에 추가로 핵심설명서 교부대상이 아닌 것은? -> 다음 키워드를 활용하여 금융투자회사의 투자설명서 이외에 추가로 핵심설명서 교부대상에 대해 서술하시오.
     - 다음 중 IS곡선상의 이동이 아닌 IS곡선 자체의 이동과 관련이 없는 것은? -> 다음 키워드를 활용하여 IS곡선상의 이동이 아닌 IS곡선 자체의 이동에 대해 서술하시오.
    
    출력 형식:
    - 서술형 문제: 다음 키워드를 활용하여 [주제]에 대해 서술하시오. (단서조항, 수식, 조건, 표 등 모두 유지)
    """
    log_func("서술형 문제 변환 중...")
    for q in tqdm(questions, desc="서술형 문제 변환"):
        clean_question_data(q)
        
        user_prompt = f"""
        입력:
        - question: {q['question']}

        """
        response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-2.5-flash')
        q['essay_question'] = response.replace('서술형 문제: ', '').replace("[", "").replace("]", "").replace("-", "").strip()
    
    save_questions(questions, output_file, log_func, '1단계')
    return len(questions)


def main(round_number='1'):
    """메인 함수"""
    change_question_to_essay(round_number=round_number)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='서술형 문제로 변환')
    parser.add_argument('--round', type=str, default='1', help='회차 번호 (1-5)')
    args = parser.parse_args()
    main(round_number=args.round)

