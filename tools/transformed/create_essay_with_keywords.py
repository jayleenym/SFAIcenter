#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
객관식 문제를 서술형 문제로 변환하고 모범답안 생성
- 옳지 않은 문제 중 해설이 많은 문제 선별 (gemini-2.5-flash)
- 키워드 추출 (gemini-2.5-flash)
- 모범답안 생성 (gemini-3-pro-preview)
- 최종 결과를 best_ans.json으로 저장
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
    llm, onedrive_path, log_func = _init_common(llm, onedrive_path, log_func)
    
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


# 공통 상수
ROUND_NUMBER_TO_FOLDER = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th', '5': '5th'}


def _init_common(llm, onedrive_path, log_func):
    """공통 초기화 함수"""
    if onedrive_path is None:
        onedrive_path = ONEDRIVE_PATH
    if llm is None:
        llm = LLMQuery()
    if log_func is None:
        log_func = logger.info if logger else print
    return llm, onedrive_path, log_func


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
    llm, onedrive_path, log_func = _init_common(llm, onedrive_path, log_func)
    
    if not round_number:
        log_func("오류: round_number가 필요합니다.")
        return 0
    
    essay_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '9_multiple_to_essay')
    round_folder = ROUND_NUMBER_TO_FOLDER.get(round_number, '1st')
    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}.json')
    output_file = os.path.join(essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}.json')
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if not os.path.exists(input_file):
        log_func(f"오류: 입력 파일이 존재하지 않습니다: {input_file}")
        return 0
    
    log_func(f"2단계 입력 파일 읽기: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    log_func(f"총 {len(questions)}개의 문제 처리 시작")
    
    # 키워드 추출
    system_prompt = """
아래 #요청사항#을 정확하게 이해한 후, 틀림없이 #입력#에 적용하여 #출력#을 도출하시오.
#요청사항#
1. 주어진 questions 키 값이 가진 주요 주제를 먼저 식별하라.
2. 주어진 options은 questions 키 값을 설명하는 contents이다. answer를 참고하여 '옳지 않은' 선지(answer 1개)와 '옳은' 선지(answer외 3~4개)를 식별하라.
3. explanation을 참고하여 '옳지 않은' 선지(answer 1개)의 해설과 '옳은' 선지(answer외 3~4개)에서 문제의 주요 주제를 설명하기에 핵심적인 의미라고 판단되는 명사형 단어 또는 파생 명사 1개씩 추출하라. 조사를 반드시 제외하고 순수한 명사 또는 핵심 명사구만 추출하라.
4. 키워드는 주제와 겹치지 않도록 추출하라. 중복된 키워드는 제거하라. 총 5개 이내로 추출하라.
5. 단, 단어,표현 추출은 원문이 가진 텍스트 원본을 그대로 유지하라. 반드시 유지해서 추출하라
    - 예1) 재화가격의 인상을 통해서
    - 올바른 추출 예시 : 재화가격의 인상
    - 틀린 추출 예시 : 재화가격 인상, 재화가격의 인상을 통해서,
    - 예2) 소비자에게 전가될 수 있다
    - 올바른 추출 예시 : 소비자에게 전가
    - 틀린 추출 예시 : 소비자 전가
    
#출력 형식#
- 서술형 문제: 다음 키워드를 활용하여 [주제]에 관해 서술하시오.
- 키워드: [키워드1], [키워드2], [키워드3], [키워드4], [키워드5]

#입력#
    """
    
    log_func("키워드 추출 중...")
    for q in tqdm(questions, desc="키워드 추출"):
        user_prompt = f"""
- questions: {q['question']}
- options: {q['options']}
- answer: {q['answer']}
- explanation: {q['explanation']}

#출력#
"""
        response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-2.5-flash')
        try:
            q['essay_question'], q['essay_keyword'] = response.strip().split('\n')
            q['essay_question'] = q['essay_question'].replace('서술형 문제: ', '').replace("[", "").replace("]", "").replace("-", "").strip()
            q['essay_keyword'] = q['essay_keyword'].replace('키워드: ', '').replace("[", "").replace("]", "").replace("-", "").strip()
        except Exception as e:
            log_func(f"오류: 키워드 추출 실패 - {e}")
            q['essay_question'] = response.strip()
            q['essay_keyword'] = ''
            continue
        
    
    # 출력 저장
    log_func(f"2단계 저장: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    log_func(f"2단계 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")
    return len(questions)


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
    llm, onedrive_path, log_func = _init_common(llm, onedrive_path, log_func)
    
    if not round_number:
        log_func("오류: round_number가 필요합니다.")
        return 0
    
    essay_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '9_multiple_to_essay')
    round_folder = ROUND_NUMBER_TO_FOLDER.get(round_number, '1st')
    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}.json')
    output_file = os.path.join(essay_dir, 'answers', f'best_ans_{round_folder}.json')
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if not os.path.exists(input_file):
        log_func(f"오류: 입력 파일이 존재하지 않습니다: {input_file}")
        return 0
    
    log_func(f"3단계 입력 파일 읽기: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    log_func(f"총 {len(questions)}개의 문제 처리 시작")
    
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
    
    # 출력 저장
    log_func(f"3단계 저장: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    log_func(f"3단계 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")
    return len(questions)


def main(llm=None, onedrive_path=None, log_func=None, round_number=None):
    """
    메인 함수 (2단계와 3단계를 모두 수행)
    
    Args:
        llm: LLMQuery 인스턴스 (None이면 새로 생성)
        onedrive_path: OneDrive 경로 (None이면 ONEDRIVE_PATH 사용)
        log_func: 로깅 함수 (None이면 logger.info 또는 print 사용)
        round_number: 회차 번호 (예: '1', '2', '3', '4', '5'). None이면 '1' 사용
    """
    llm, onedrive_path, log_func = _init_common(llm, onedrive_path, log_func)
    
    if not round_number:
        round_number = '1'
    
    # 2단계: 키워드 추출
    extract_keywords(
        llm=llm,
        onedrive_path=onedrive_path,
        log_func=log_func,
        round_number=round_number
    )
    
    # 3단계: 모범답안 생성
    create_best_answers(
        llm=llm,
        onedrive_path=onedrive_path,
        log_func=log_func,
        round_number=round_number
    )
    
    # 결과 파일 확인
    essay_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '9_multiple_to_essay')
    round_folder = ROUND_NUMBER_TO_FOLDER.get(round_number, '1st')
    output_file = os.path.join(essay_dir, 'answers', f'best_ans_{round_folder}.json')
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        log_func(f"\n처리 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")
        return len(questions)
    else:
        log_func(f"오류: 출력 파일이 생성되지 않았습니다: {output_file}")
        return 0

if __name__ == '__main__':
    main()

