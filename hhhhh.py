from typing import List, Dict, Any, Tuple
import json
from tqdm import tqdm
import configparser
from openai import OpenAI
import time
import os

config = configparser.ConfigParser()
config.read('/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/llm_config.ini', encoding='utf-8')

client = OpenAI(
            api_key=config["OPENROUTER"]["key"], 
            base_url=config["OPENROUTER"]["url"]
        )

qtype = input("qtype을 입력하세요: ")

with open('/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/domain_subdomain.json', 'r', encoding='utf-8') as f:
    domain_subdomain = json.load(f)

if qtype == 'short-fail':
    with open(f'/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/2_subdomain/short_subdomain_classified_ALL_fail_response.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
elif qtype == 'multiple-fail':
    with open(f'/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/2_subdomain/multiple_subdomain_classified_ALL_fail_response.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
elif qtype == 'multiple-re':
    with open(f'/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/2_subdomain/multiple.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
else:
    with open(f'/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/1_filter/{qtype}.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)

print("총 문제 수: ", len(questions))

prompt_domain = ''

for domain in domain_subdomain.keys():
    # if domain == '디지털' or domain == '통계':
    #     continue
    subdomain_list = domain_subdomain[domain]
    # domain_list = []
    prompt_domain += f'{domain}\n'
    for i, subdomain_item in enumerate(subdomain_list):
        subdomain_name = subdomain_item.split('(')[0].strip()
        # domain_list.append(subdomain_name)
        subdomain_ex = subdomain_item.split('(')[1].split(')')[0].strip()
        prompt_domain += f'{i+1}. {subdomain_name}\n   - {subdomain_ex}\n'

system_prompt = f"""
당신은 금융 시험 문제를 세부 주제별로 정확히 분류하는 전문가입니다.  
당신의 임무는 이 문제를 아래의 세부 분류체계 중 하나로 정확히 분류하고, 계산이 필요한 문제인지 판단하는 것입니다.

### 세부 분류체계
{prompt_domain}

분류 기준:
- 문제의 핵심 개념, 등장 용어, 계산 대상, 제시된 사례를 기준으로 판단합니다.
- 특정 학문적 이론이나 모형이 등장한다면 그 이론이 속한 학문 영역으로 분류합니다.
- 판단이 애매할 경우, **'가장 관련성이 높은 영역 하나만** 선택해야 합니다.

출력은 아래 JSON 형태로 작성합니다. 각 문제마다 하나의 객체를 생성하세요.
문제 ID는 "file_id_tag" 형태로 제공됩니다.

[
{{
  "qna_id": "file_id_tag",
  "domain": "도메인명",
  "subdomain": "서브도메인명",
  "reason": "간단한 이유 (문제의 핵심키워드와 근거 중심으로)",
  "is_calculation": "계산 여부 (True/False)"
}},
{{
  "qna_id": "file_id_tag",
  "domain": "도메인명",
  "subdomain": "서브도메인명", 
  "reason": "간단한 이유 (문제의 핵심키워드와 근거 중심으로)",
  "is_calculation": "계산 여부 (True/False)"
}}
]
"""


def create_user_prompt(questions: List[Dict[str, Any]]) -> str:
        """사용자 프롬프트 생성"""
        user_prompt = ''
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['tag']}"
            
            # 옵션이 있는 경우 (multiple choice)
            if qna['options']:
                options_text = '\n'.join(qna['options']) if isinstance(qna['options'], list) else qna['options']
                single_prompt = f"""
문제 ID: {unique_id}
책 제목: {qna['title']}
챕터: {qna['chapter']}
질문: {qna['question']}
선지: {options_text}
답변: {qna['answer']}
해설: {qna['explanation']}
===================="""
            else:
                # 옵션이 없는 경우 (short answer, essay)
                single_prompt = f"""
문제 ID: {unique_id}
책 제목: {qna['title']}
챕터: {qna['chapter']}
질문: {qna['question']}
답변: {qna['answer']}
해설: {qna['explanation']}
===================="""
            user_prompt += single_prompt
        
        return user_prompt


def call_api(system_prompt: str, user_prompt: str, model: str = "google/gemini-2.5-flash") -> str:
        """API 호출"""
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=float(config["PARAMS"]["temperature"]),
                frequency_penalty=float(config["PARAMS"]["frequency_penalty"]),
                presence_penalty=float(config["PARAMS"]["presence_penalty"]),
                top_p=float(config["PARAMS"]["top_p"]),
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": user_prompt}
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API 호출 실패: {e}")
            return None
        


def parse_api_response(response: str) -> List[Dict[str, Any]]:
        """API 응답 파싱"""
        try:
            # JSON 응답에서 배열 부분만 추출
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                print("JSON 배열을 찾을 수 없습니다.")
                return response
            
            json_str = response[start_idx:end_idx]
            parsed_data = json.loads(json_str)
            
            if not isinstance(parsed_data, list):
                print("응답이 배열 형태가 아닙니다.")
                return response
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 실패: {e}")
            print(f"응답 내용: {response}...")
            return response
        except Exception as e:
            print(f"응답 파싱 중 오류: {e}")
            return response
        


def update_qna_subdomain(questions: List[Dict[str, Any]], 
                           classifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Q&A 데이터에 서브도메인 분류 결과 업데이트"""
        # file_id + tag 조합을 키로 하는 딕셔너리 생성
        classification_dict = {item['qna_id']: item for item in classifications}
        
        updated_questions = []
        failed_questions = []  # 분류 실패한 문제들 수집
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['tag']}"
            if unique_id in classification_dict:
                qna['domain'] = classification_dict[unique_id]['domain']
                qna['subdomain'] = classification_dict[unique_id]['subdomain']
                qna['classification_reason'] = classification_dict[unique_id]['reason']
                qna['is_calculation'] = classification_dict[unique_id]['is_calculation']
            else:
                print(f"분류 결과를 찾을 수 없음: {unique_id}")
                qna['domain'] = "분류실패"
                qna['subdomain'] = "분류실패"
                qna['classification_reason'] = "API 응답에서 해당 문제를 찾을 수 없음"
                qna['is_calculation'] = "분류실패"
                failed_questions.append(qna)
            
            updated_questions.append(qna)
        
        # 분류 실패한 문제들이 있고, 도메인과 배치 번호가 제공된 경우 파일에 저장
        # if failed_questions and domain and batch_num is not None:
            # save_failure_response(domain, batch_num, "분류실패", 
                                    #  error_message=f"{len(failed_questions)}개 문제 분류 실패", 
                                    #  batch=failed_questions)
        
        return updated_questions, failed_questions


batch_size = 10
all_updated_questions = []
fail_response = []
fail_question = []


for i in tqdm(range(0, len(questions), batch_size)):
    batch = questions[i:i + batch_size]
    batch_num = i // batch_size + 1
    
    # print(f"배치 {batch_num} 처리 중... ({len(batch)}개 문제)")
    
    # 사용자 프롬프트 생성
    user_prompt = create_user_prompt(batch)
    
    # API 호출
    try:
        response = call_api(system_prompt, user_prompt, 'x-ai/grok-4-fast')
    except Exception as e:
        print(f"배치 {batch_num} API 호출 실패: {e}")
        fail_response.append(response)    
        # 실패한 경우 기본값으로 설정
        for qna in batch:
            qna['subdomain'] = "API호출실패"
            qna['classification_reason'] = "API 호출에 실패했습니다"
        all_updated_questions.extend(batch)
        continue

    # 응답 파싱
    try:
        classifications = parse_api_response(response)
    except Exception as e:
        print(f"배치 {batch_num} 응답 파싱 실패: {e}")
        fail_response.append(response)
        # 파싱 실패한 경우 기본값으로 설정
        for qna in batch:
            qna['is_calculation'] = "파싱실패"
            qna['domain'] = "파싱실패"
            qna['subdomain'] = "파싱실패"
            qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
        all_updated_questions.extend(batch)
        continue
    
    # Q&A 데이터 업데이트
    try:
        updated_batch, fail_batch = update_qna_subdomain(batch, classifications)
        all_updated_questions.extend(updated_batch)
        fail_question.extend(fail_batch)
    except Exception as e:
        fail_response.append(response)
    
    # API 호출 간격 조절
    time.sleep(1.2)
    
    # 중간 결과 저장
    if batch_num:  # 중간 저장
        if qtype == 'multiple-fail':
            filename = f"{qtype}_response.json"
        else:
            filename = f"{qtype}_subdomain_classified_ALL.json"
        filepath = '/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/2_subdomain'
        
        with open(os.path.join(filepath, filename), 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        if qtype == 'multiple-fail' or qtype == 'multiple-re':
            with open(os.path.join(filepath, f"{qtype}_response_fail_again.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_response, f, ensure_ascii=False, indent=2)
            with open(os.path.join(filepath, f"{qtype}_response_fail_q_again.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_question, f, ensure_ascii=False, indent=2)
        else:
            with open(os.path.join(filepath, f"{qtype}_subdomain_classified_ALL_fail_response.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_response, f, ensure_ascii=False, indent=2)
            with open(os.path.join(filepath, f"{qtype}_subdomain_classified_ALL_fail_q.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_question, f, ensure_ascii=False, indent=2)
    # break