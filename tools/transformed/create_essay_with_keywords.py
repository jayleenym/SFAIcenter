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
from tqdm import tqdm
from tools.pipeline.config import ONEDRIVE_PATH
from tools.core.llm_query import LLMQuery


def is_full_explanation(llm, question, answer, options, explanation):
    """해설이 문제의 모든 선지에 대한 설명을 포함하는지 확인"""
    system_prompt = """다음은 문제, 정답, 해설입니다. 해설이 문제의 모든 선지에 대한 설명을 포함하는지 확인해주세요.
    만약 모든 선지에 대한 설명이 포함되어 있으면 'full'을 반환하고, 포함하지 않으면 'notfull'을 반환해주세요.
    """
    user_prompt = f"""
    문제: {question}
    정답: {answer}
    선지: {options}
    해설: {explanation}
    """
    response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-2.5-flash')
    return response.strip()


def filter_full_explanation_questions(llm, wrong_questions):
    """옳지 않은 문제 중 해설이 모든 선지를 포함하는 문제만 선별"""
    full_explanation = []
    notfull_explanation = []
    fail = []
    
    print("해설이 많은 문제 선별 중...")
    for wd in tqdm(wrong_questions, desc="해설 검증"):
        if wd['explanation'] == '':
            fail.append(wd)
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
    
    print(f"\n선별 결과:")
    print(f"  - full (해설 완전): {len(full_explanation)}개")
    print(f"  - notfull (해설 불완전): {len(notfull_explanation)}개")
    print(f"  - fail (분류 실패): {len(fail)}개")
    print(f"  - 총합: {len(full_explanation) + len(notfull_explanation) + len(fail)}개")
    
    return full_explanation


def extract_keywords(llm, questions):
    """키워드 추출 및 서술형 문제 변환"""
    system_prompt = """
다음 지시문을 따르세요. 당신의 역할은 주어진 객관식 항목(선지)과 해설만을 근거로 문제의 핵심 주제를 추론하고, 이를 서술형 문제로 변환하는 것입니다.

입력으로 제공되는 것
- 선택지: 문자열 배열
- 정답: 정답 표기(예: '①' 또는 인덱스)
- 해설: 정답에 관한 설명 또는 정오 수정 설명

필수 규칙
1) 자료 제한: 질문지와 선택지, 해설만 사용하세요. 최대한 원 질문을 보존하세요.
2) 주제 추출: "~에 관해 적절하지 않은 것은?"의 앞부분을 주제로 도출하세요.
3) 서술형 변환: "[주제]에 관해 서술하시오." 형태로 만들되, 앞에 "다음 키워드를 활용하여"를 붙여 한 문장으로 제시하세요.
4) 선지 분류: 해설을 근거로 틀린 선지 1개와 옳은 선지 3~4개를 식별하세요. 옳은 선지가 3개 미만이면 가능한 만큼만 사용하세요.
   - 정답 표기가 있는 경우, 해설과의 정합성을 우선으로 판단하여 틀린 선지를 확정하세요.
5) 키워드 추출: 틀린 선지 1개와 옳은 선지 3~4개 각각에서 핵심 개념을 1개씩 뽑아 키워드를 구성하세요. 총 5~10개 이내로 하며, 다음 원칙을 지키세요.
   - 중복 키워드는 제거하고, 명사구 중심으로 간결히 표현하세요.
6) 출력은 정확히 두 줄만 생성하세요.
   - 1행: 서술형 문제: 다음 키워드를 활용하여 [주제]에 관해 서술하시오.
   - 2행: 키워드: 키워드1, 키워드2, 키워드3, …

검증 체크리스트
- 키워드는 10개 이내인가?
- 키워드가 주제를 적절하게 반영하고 있는가?
- 주제 문구가 명확하고 간결한가?

예시 입력 형식
선택지: ['① ...', '② ...', '③ ...', '④ ...']
정답: '①'
해설: '...'

예시 출력 형식
서술형 문제: 다음 키워드를 활용하여 [도출한 주제]에 관해 서술하시오.
키워드: [키워드A], [키워드B], [키워드C], ...
"""
    
    print("키워드 추출 중...")
    for q in tqdm(questions, desc="키워드 추출"):
        user_prompt = f"""
========= 문제 ========
- 문제 지문: {q['question']}
- 선지: {q['options']}
- 정답: {q['answer']}
- 해설: {q['explanation']}
"""
        response = llm.query_openrouter(system_prompt, user_prompt, model_name='google/gemini-2.5-flash')
        q['essay_question'], q['essay_keyword'] = response.strip().split('\n')
        q['essay_question'] = q['essay_question'].replace('서술형 문제: ', '')
        q['essay_keyword'] = q['essay_keyword'].replace('키워드: ', '')


def create_best_answers(llm, questions):
    """모범답안 생성"""
    system_prompt = """
당신은 주어진 여러 정보를 조합하여 서술형 문제에 대한 '모범답안'을 생성하는 AI입니다.

**[역할]**
- '서술형 질문'의 요구사항을 정확히 파악합니다.
- '원래 질문/선지/정답/해설'에서 서술형 질문에 답변하는 데 필요한 핵심 정보를 추출합니다.
- 추출한 정보와 '키워드'를 논리적으로 엮어 하나의 완성된 글로 재구성합니다.

**[수행 절차]**
1.  **주제 파악:** '서술형 질문'과 '키워드'를 통해 모범답안이 다루어야 할 핵심 주제와 포함해야 할 요소를 확인합니다.
2.  **정보 추출:** '원래 선지'와 '선지별 해설'을 분석하여 각 '키워드'에 해당하는 구체적인 내용을 찾아냅니다.
3.  **논리적 구성:** 추출한 정보들을 활용하여 '서술형 질문'에 대한 답변이 되도록 문장을 자연스럽게 연결하고 문단을 구성합니다. 이때, 모든 '키워드'가 포함되어야 합니다.
4.  **답안 생성:** 위의 과정을 거쳐 최종 '모범답안'을 작성합니다.

**[규칙]**
- **절대 외부 지식을 사용하지 마세요.** 반드시 '원래 질문/선지/정답/해설'에 명시된 정보만을 근거로 답안을 작성해야 합니다.
- 제시된 모든 '키워드'를 반드시 답안에 포함해야 합니다.
- 최종 결과물은 "모범답안:"으로 시작하는 완성된 형태의 글이어야 합니다.
"""
    
    print("모범답안 생성 중...")
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


def main():
    # 경로 설정
    classified_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '7_multiple_rw')
    essay_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay')
    
    classified_file = os.path.join(classified_dir, 'answer_type_classified.json')
    full_explanation_file = os.path.join(essay_dir, 'full_explanation.json')
    intermediate_file = os.path.join(essay_dir, 'essay_w_keyword.json')
    output_file = os.path.join(essay_dir, 'best_ans.json')
    
    # 디렉토리 생성
    os.makedirs(essay_dir, exist_ok=True)
    
    # LLM 초기화
    llm = LLMQuery()
    
    # 0단계: 옳지 않은 문제 중 해설이 많은 문제 선별
    print(f"입력 파일 읽기: {classified_file}")
    with open(classified_file, 'r', encoding='utf-8') as f:
        classified_data = json.load(f)
    
    # answer_type이 'wrong'인 문제만 필터링
    wrong_questions = [p for p in classified_data if p.get('answer_type') == 'wrong']
    print(f"옳지 않은 문제: {len(wrong_questions)}개")
    
    # 해설이 모든 선지를 포함하는 문제만 선별
    questions = filter_full_explanation_questions(llm, wrong_questions)
    
    # 선별 결과 저장 (안전장치)
    print(f"\n선별 결과 저장: {full_explanation_file}")
    with open(full_explanation_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    print(f"\n총 {len(questions)}개의 문제 처리 시작")
    
    # 1단계: 키워드 추출
    extract_keywords(llm, questions)
    
    # 중간 저장 (안전장치)
    print(f"중간 저장: {intermediate_file}")
    with open(intermediate_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    # 2단계: 모범답안 생성
    create_best_answers(llm, questions)
    
    # 최종 저장
    print(f"최종 저장: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    # 중간 파일 삭제
    if os.path.exists(intermediate_file):
        os.remove(intermediate_file)
        print(f"중간 파일 삭제 완료: {intermediate_file}")
    
    # 선별 결과 파일도 삭제 (이미 best_ans.json에 포함되어 있음)
    if os.path.exists(full_explanation_file):
        os.remove(full_explanation_file)
        print(f"선별 결과 파일 삭제 완료: {full_explanation_file}")
    
    print(f"\n처리 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")


if __name__ == '__main__':
    main()

