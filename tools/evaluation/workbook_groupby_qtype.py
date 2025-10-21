import os
import pandas as pd
from tqdm import tqdm
import requests
import json
from openai import OpenAI
import configparser
import argparse

import tools.ProcessFiles as pf



def get_json_files(final_data_path):
    """
    FINAL_DATA_PATH 하위의 모든 json 파일을 찾아서 리스트로 반환
    Args:
        final_data_path: FINAL_DATA_PATH
    Returns:
        json_files: 모든 json 파일 리스트
    """
    json_files = []
    for root, _, files in os.walk(final_data_path):
        for f in files:
            if f.endswith(".json") and ('merged' not in f):
                json_files.append(os.path.join(root, f))
    print("총 도서 개수: ", len(json_files))
    return json_files


def get_qna_type(data: list):
    """
    data 리스트에서 qna_type별로 분류
    Args:
        data: 모든 json 파일 리스트
    Returns:
        multiple: multiple-choice 문제 리스트
        short: short-answer 문제 리스트
        essay: essay 문제 리스트
    """
    multiple = []
    short = []
    essay = []

    for file in data:
        origin = json.load(open(file, 'r', encoding='utf-8'))
        for qna in origin:
            if len(qna['qna_data']['description']['answer']) > 0:
                if qna.get('qna_type') == "multiple-choice":
                    multiple.append(qna)
                elif qna.get('qna_type') == "short-answer":
                    short.append(qna)
                elif qna.get('qna_type') == "essay":
                    essay.append(qna)
    
    print("multiple-choice: ", len(multiple))
    print("short-answer: ", len(short))
    print("essay: ", len(essay))

    with open('evaluation/eval_data/multiple.json', "w", encoding="utf-8") as f:
        json.dump(multiple, f, ensure_ascii=False, indent=4)
    with open('evaluation/eval_data/short.json', "w", encoding="utf-8") as f:
        json.dump(short, f, ensure_ascii=False, indent=4)
    with open('evaluation/eval_data/essay.json', "w", encoding="utf-8") as f:
        json.dump(essay, f, ensure_ascii=False, indent=4)

    return multiple, short, essay


def rearrange_multiple_data(multiple_data_path: str):
    """
    multiple 리스트에서 객관식 문제 추출
    Args:
        multiple_data_path: multiple-choice 문제 파일 경로
    Returns:
        multiple_for_grp: 정제된 multiple-choice 문제 리스트 (OX 문제 제외, 선지가 3개 이상인 경우)
    """
    from evaluation.multiple_eval_by_model import replace_tags_in_qna_data

    multiple = json.load(open(multiple_data_path, 'r', encoding='utf-8'))
    multiple_for_grp = []

    for m in multiple:
        qna_data = replace_tags_in_qna_data(m.get('qna_data'), m.get('additional_tag_data'))
        # OX 문제 제외, 선지가 3개 이상인 경우
        if (qna_data.get('description').get('options') is not None) and (len(qna_data.get('description').get('options')) > 2): 
            
            qna = {
                'file_id': m.get('file_id'),
                'title': m.get('title'),
                'chapter': m.get('chapter'),
                'qna_id': qna_data.get('tag'),
                'qna_domain': m.get('qna_domain'),
                "qna_subdomain": "",
                'qna_reason': m.get('qna_reason'),
                'qna_question': qna_data.get('description').get('question'),
                'qna_answer': qna_data.get('description').get('answer'),
                'qna_options': qna_data.get('description').get('options'),
                'qna_explanation': qna_data.get('description').get('explanation')            
            }
            multiple_for_grp.append(qna)
    print("정제된 multiple-choice 문제 수: ", len(multiple_for_grp))

    return multiple_for_grp

def add_subdomain_to_multiple_data(multiple_data: list, domain: str):
    """
    multiple-choice 문제 리스트에 subdomain 추가
    Args:
        multiple_data: 정제된 multiple-choice 문제 리스트
    Returns:
        multiple_data: subdomain이 추가된 multiple-choice 문제 리스트
    """






def create_system_prompt(domain: str):
    """
    domain 별 system prompt 생성
    Args:
        domain: 도메인
    Returns:
        system_prompt: system prompt
    """
    with open('evaluation/eval_data/domain_subdomain.json', 'r', encoding='utf-8') as f:
        domain_subdomain = json.load(f)

    subdomain_list = domain_subdomain[domain]
    prompt_domain = ''
    domain_list = []

    for i, subdomain_item in enumerate(subdomain_list):
        subdomain_name = subdomain_item.split('(')[0].strip()
        domain_list.append(subdomain_name)
        subdomain_ex = subdomain_item.split('(')[1].split(')')[0].strip()
        prompt_domain += f'{i+1}. {subdomain_name}\n   - {subdomain_ex}\n'
    
    system_prompt = f"""
당신은 금융·{domain} 시험 문제를 세부 주제별로 정확히 분류하는 전문가입니다.  
주어진 문제는 이미 '{domain}' 영역으로 1차 분류된 것입니다.  
당신의 임무는 이 문제를 아래의 세부 분류체계 중 하나로 정확히 분류하는 것입니다.

### 세부 분류체계
{prompt_domain}

분류 기준:
- 문제의 핵심 개념, 등장 용어, 계산 대상, 제시된 사례를 기준으로 판단합니다.
- 특정 학문적 이론이나 모형이 등장한다면 그 이론이 속한 학문 영역으로 분류합니다.
- 판단이 애매할 경우, **'가장 관련성이 높은 영역 하나만** 선택해야 합니다.

출력은 아래 JSON 형태로 작성합니다. 각 문제마다 하나의 객체를 생성하세요.

[
{{
  "qna_id": "SS0000_q_0000_0000",
  "category_detail": "{' | '.join(domain_list)}",
  "reason": "간단한 이유 (문제의 핵심 키워드와 근거 중심으로)"
}},
{{
  "qna_id": "SS0000_q_0000_0000",
  "category_detail": "{' | '.join(domain_list)}", 
  "reason": "간단한 이유 (문제의 핵심 키워드와 근거 중심으로)"
}}
]
"""
    return system_prompt






if __name__ == "__main__":
    FINAL_DATA_PATH = '/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/data/FIN_workbook'
    json_files = get_json_files(FINAL_DATA_PATH)

    
