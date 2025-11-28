# transformed 패키지 - 문제 변형 관련 기능
import os
import json
import sys

# 공통 import 처리
try:
    from tools import ONEDRIVE_PATH
    from tools.core.llm_query import LLMQuery
except ImportError:
    # fallback: 상대 경로 import 시도
    current_dir = os.path.dirname(os.path.abspath(__file__))
    _temp_tools_dir = os.path.dirname(current_dir)
    if _temp_tools_dir not in sys.path:
        sys.path.insert(0, _temp_tools_dir)
    try:
        from tools import ONEDRIVE_PATH
        from tools.core.llm_query import LLMQuery
    except ImportError:
        ONEDRIVE_PATH = None
        LLMQuery = None

# 공통 상수
ROUND_NUMBER_TO_FOLDER = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th', '5': '5th'}


def _init_common(llm=None, onedrive_path=None, log_func=None, logger=None):
    """공통 초기화 함수"""
    if onedrive_path is None:
        onedrive_path = ONEDRIVE_PATH
    if llm is None:
        llm = LLMQuery()
    if log_func is None:
        log_func = logger.info if logger else print
    return llm, onedrive_path, log_func


def _validate_round_number(round_number, log_func):
    """round_number 검증"""
    if not round_number:
        log_func("오류: round_number가 필요합니다.")
        return None
    return ROUND_NUMBER_TO_FOLDER.get(round_number, '1st')


def _get_essay_dir(onedrive_path):
    """essay 디렉토리 경로 반환"""
    return os.path.join(onedrive_path, 'evaluation', 'eval_data', '9_multiple_to_essay')


def _load_questions(input_file, log_func, step_name):
    """입력 파일에서 질문 데이터 로드"""
    if not os.path.exists(input_file):
        log_func(f"오류: 입력 파일이 존재하지 않습니다: {input_file}")
        return None
    
    log_func(f"{step_name} 입력 파일 읽기: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    log_func(f"총 {len(questions)}개의 문제 처리 시작")
    return questions


def _save_questions(questions, output_file, log_func, step_name):
    """질문 데이터를 파일에 저장"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    log_func(f"{step_name} 저장: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    log_func(f"{step_name} 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")


def _clean_question_data(q):
    """질문 데이터의 특수 문자 정리"""
    q['question'] = q['question'].replace("\\'", "'")
    q['options'] = [opt.replace("\\'", "'") for opt in q['options']]
    if 'explanation' in q:
        q['explanation'] = q['explanation'].replace("\\'", "'")


# 기존 import들
try:
    from .multiple_change_question_and_options import MultipleChoiceTransformer
    from .multiple_load_transformed_questions import load_transformed_questions
    from .multiple_create_transformed_exam import create_transformed_exam
    __all__ = [
        'MultipleChoiceTransformer',
        'load_transformed_questions',
        'create_transformed_exam',
        'ROUND_NUMBER_TO_FOLDER',
        '_init_common',
        '_validate_round_number',
        '_get_essay_dir',
        '_load_questions',
        '_save_questions',
        '_clean_question_data'
    ]
except ImportError:
    MultipleChoiceTransformer = None
    load_transformed_questions = None
    create_transformed_exam = None
    __all__ = [
        'ROUND_NUMBER_TO_FOLDER',
        '_init_common',
        '_validate_round_number',
        '_get_essay_dir',
        '_load_questions',
        '_save_questions',
        '_clean_question_data'
    ]

try:
    from .essay_create_model_answers import generate_essay_answers
    if 'generate_essay_answers' not in __all__:
        __all__.append('generate_essay_answers')
except ImportError:
    generate_essay_answers = None
