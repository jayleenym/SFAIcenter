#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 키워드 추출
"""

import os
import json
import sys
from tqdm import tqdm

# tools 모듈 import를 위한 경로 설정 (모듈로 사용될 때를 대비)
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(current_dir)  # transformed -> tools
if _temp_tools_dir not in sys.path:
    sys.path.insert(0, _temp_tools_dir)

# 독립 실행 시와 모듈로 사용 시 import 처리
if __name__ == '__main__':
    # 독립 실행 시: 절대 경로 import
    project_root = os.path.dirname(_temp_tools_dir)  # tools -> project_root
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from tools import ONEDRIVE_PATH
    from tools.core.llm_query import LLMQuery
    from tools.core.logger import setup_logger
    
    # 독립 실행 시 파일명.log로 로깅 설정
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    logger = setup_logger(
        name=__name__,
        log_file=f'{script_name}.log',
        use_console=True,
        use_file=True
    )
else:
    # 모듈로 사용 시: tools 경로가 이미 설정되어 있다고 가정
    try:
        from tools import ONEDRIVE_PATH
        from tools.core.llm_query import LLMQuery
    except ImportError:
        # fallback: 상대 경로 import 시도
        from ..core.llm_query import LLMQuery
        # ONEDRIVE_PATH는 tools.__init__에서 가져와야 하므로 경로 설정 필요
        from tools import tools_dir
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from tools import ONEDRIVE_PATH
    logger = None

# 공통 함수 import
try:
    from . import (
        ROUND_NUMBER_TO_FOLDER,
        _init_common,
        _validate_round_number,
        _get_essay_dir,
        _load_questions,
        _save_questions,
        _clean_question_data
    )
except ImportError:
    # fallback: 직접 import 시도
    try:
        from tools.transformed import (
            ROUND_NUMBER_TO_FOLDER,
            _init_common,
            _validate_round_number,
            _get_essay_dir,
            _load_questions,
            _save_questions,
            _clean_question_data
        )
    except ImportError:
        ROUND_NUMBER_TO_FOLDER = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th', '5': '5th'}
        _init_common = None
        _validate_round_number = None
        _get_essay_dir = None
        _load_questions = None
        _save_questions = None
        _clean_question_data = None


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
    llm, onedrive_path, log_func = _init_common(llm, onedrive_path, log_func, logger)
    
    round_folder = _validate_round_number(round_number, log_func)
    if round_folder is None:
        return 0
    
    essay_dir = _get_essay_dir(onedrive_path)
    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}_서술형문제로변환.json')
    output_file = os.path.join(essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json')
    
    questions = _load_questions(input_file, log_func, '2단계')
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
        _clean_question_data(q)
        
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
    
    _save_questions(questions, output_file, log_func, '2단계')
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

