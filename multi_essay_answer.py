from tools.pipeline.config import ONEDRIVE_PATH
import os, json
from tqdm import tqdm
from tools.core.llm_query import LLMQuery

llm = LLMQuery(api_key = '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')

with open(os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', 'essay_w_keyword.json'), 'r', encoding='utf-8') as f:
    full_explanation = json.load(f)

eval_model_list = ['google/gemini-2.5-pro', 'openai/gpt-5', 'anthropic/claude-sonnet-4.5', 'anthropic/claude-3.7-sonnet', 'google/gemini-2.5-flash', 'openai/gpt-4.1']

number = input("평가 모델 번호 입력(1: google/gemini-2.5-pro, 2: openai/gpt-5, 3: anthropic/claude-sonnet-4.5, 4: anthropic/claude-3.7-sonnet, 5: google/gemini-2.5-flash, 6: openai/gpt-4.1): ")
model = eval_model_list[int(number) - 1]


eval_model_answer = []
print(f"평가 모델: {model}")
for q in tqdm(full_explanation):
    user_prompt = f"""
서술형 질문: {q['essay_question']}
키워드: {q['essay_keyword']}
"""
    answer = llm.query_openrouter("주어진 키워드를 모두 사용하여 서술형 문제에 대한 답변을 작성해주세요.", user_prompt, model_name = model)
    
    answers = {
        'file_id': q['file_id'],
        'tag': q['tag'],
        'question': q['essay_question'],
        'keyword': q['essay_keyword'],
        'answer': answer
    }
    eval_model_answer.append(answers)

with open(os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', f'{model}_answer.json'), 'w', encoding='utf-8') as f:
    json.dump(eval_model_answer, f, ensure_ascii=False, indent=4)