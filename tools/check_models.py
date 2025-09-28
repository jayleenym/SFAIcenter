import numpy as np
import json
import os
import pandas as pd
import warnings
import shutil

import tools.ProcessFiles as pf
import tools.ProcessQnA as pq
import tools.Openrouter as Openrouter

# origin_data_dir = os.path.join(pf.FINAL_DATA_PATH, '1C')#.replace('jinym', 'yejin')
data_dir = pf.FINAL_DATA_PATH.replace('FINAL', 'FIN_workbook/1C')#.replace('jinym', 'yejin')
# origin_data_dir, data_dir

file_path = os.path.join(data_dir, 'merged_extracted_qna.json')

with open(file_path, 'r', encoding='utf-8') as f:
        qna_data = json.load(f)


np.random.seed()
idx = np.random.randint(0, len(qna_data), 35)
sample_data = [qna_data[i] for i in idx]

with open(os.path.join(data_dir, 'merge_test2.json'), 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=4)

models = ['anthropic/claude-sonnet-4', 'google/gemini-2.5-flash', 'x-ai/grok-4-fast:free', 'openai/gpt-4.1', 'openai/gpt-oss-120b', 'openai/gpt-5', 'qwen/qwen3-next-80b-a3b-thinking', 'qwen/qwen3-235b-a22b-thinking-2507']

df = pd.DataFrame(columns = ['title', 'question'] + models)

for d in sample_data:
    question = d['qna_data']['description']['question']
    title = d['title']
    df.loc[len(df)] = {'title': title, 'question': question}

# df.to_csv('qna_test.csv', index=False)


system_prompt = """
당신은 금융 문제지를 분류하는 전문가입니다.  
당신의 임무는 주어진 정보(책 제목, 책 분류, 챕터 제목)를 바탕으로 질문을 아래 분류 체계 중 하나로 정확하게 분류하는 것입니다.  

## 분류 체계

1. 금융기초
- 경제 (미시경제, 거시경제, 국제경제, 계량경제 등)
- 경영 (인사/조직, 전략/마케팅, 재무기초 등)
- 회계 (회계사 관련 자격증 및 회계 관련 학문적 내용)
- 세무 (세무사 관련 자격증 및 세법 관련 학문적 내용)
- 노무 (노무사 관련 자격증 및 노동법, 사회보험법 관련 학문적 내용)
- 통계 (통계 관련 자격증 및 통계학 관련 학문적 내용)

2. 금융실무
- 내부통제 (컴플라이언스, 법률, 규제, 협회규정 등)
- 영업 (세일즈, 화법, 고객관리 등)
- 디지털 (마이데이터, 가상자산, 블록체인, 핀테크 등)
- 자산운용 (트레이딩, 채권, 부동산PF, 퇴직연금, 신탁 등)
- 리스크관리 (채권수심, 신용리스크, 대체심사, 헷징 등)
- 보험계약 (장기보험, 자동차보험, 해상보험, 지급, 보전 등)
- 보상처리 (손해사정, 보험금 심사, 자동차 보상 등)

---

## 분류 지침
1. 반드시 위 체계 중 하나를 선택합니다.  
2. 질문의 핵심 주제가 학문적 개념·이론이면 → 금융기초,  
   실제 업무·규제·법률·실무 절차라면 → 금융실무로 분류합니다.  
3. 모호한 경우 더 구체적인 문맥을 고려해 대분류와 세부 카테고리를 명확히 결정합니다.  
4. 출력은 분류 결과만 JSON 형식으로 작성합니다.
5. 출력에는 코드 블록 표시(```json, ```)를 절대 포함하지 않습니다.  

---

## 출력 형식
[{
  "대분류": "금융기초 또는 금융실무",
  "카테고리": "세부 카테고리명",
  "근거": "간단한 분류 이유"
},
{
  "대분류": "금융기초 또는 금융실무",
  "카테고리": "세부 카테고리명",
  "근거": "간단한 분류 이유"
}]
"""


qna_data = sample_data

for model in models[5:]:
    # 5개씩 처리
    for i in range(0, len(qna_data), 5):
        user_prompt = ''
        qna_items = qna_data[i:i+5]
        for qna_item in qna_items:
            question = qna_item['qna_data']['description']['question']
            single_prompt = f"""
    책 제목: {qna_item['title']}
    책 분류: {qna_item['cat1_domain']}/{qna_item['cat2_sub']}/{qna_item['cat3_specific']}
    챕터: {qna_item['chapter']}
    질문: {question}
    ===================="""
            user_prompt += single_prompt
            
        domain = Openrouter.query_model_openrouter(system_prompt, user_prompt, model)
        domain = json.loads(domain)
        for idx in range(i, i+5):
            dom = domain[idx-i]
            df.loc[idx, model] = dom['카테고리']

df.to_excel('qna_test_model.xlsx', index=False)