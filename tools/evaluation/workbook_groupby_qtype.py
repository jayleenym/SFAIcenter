import os
import sys
import pandas as pd
from tqdm import tqdm
import requests
import json
from openai import OpenAI
import configparser
import argparse
import subprocess

# Import handling for both script and module execution
try:
    from .multiple_eval_by_model import replace_tags_in_qna_data
except ImportError:
    from multiple_eval_by_model import replace_tags_in_qna_data


EXTRACTED_DIR = '/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/FIN_workbook'
EVAL_DATA_DIR = '/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data'
BRONZE_LAYER_0_DIR = os.path.join(EVAL_DATA_DIR, '0_bronze_layer_grpby')
BRONZE_LAYER_1_DIR = os.path.join(EVAL_DATA_DIR, '1_bronze_layer_filter')
BRONZE_LAYER_2_DIR = os.path.join(EVAL_DATA_DIR, '2_bronze_layer_subdomain')

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

    with open(os.path.join(BRONZE_LAYER_0_DIR, 'multiple.json'), "w", encoding="utf-8") as f:
        json.dump(multiple, f, ensure_ascii=False, indent=4)
    with open(os.path.join(BRONZE_LAYER_0_DIR, 'short.json'), "w", encoding="utf-8") as f:
        json.dump(short, f, ensure_ascii=False, indent=4)
    with open(os.path.join(BRONZE_LAYER_0_DIR, 'essay.json'), "w", encoding="utf-8") as f:
        json.dump(essay, f, ensure_ascii=False, indent=4)

    return multiple, short, essay



def rearrange_data(data_path: list or str = None, qtype: str = None):
    """
    multiple 리스트에서 객관식 문제 추출
    Args:
        data_path: multiple-choice 문제 파일 경로 또는 문제 리스트
        qtype: 문제 타입
    Returns:
        multiple_for_grp: 정제된 multiple-choice 문제 리스트 (OX 문제 제외, 선지가 3개 이상인 경우)
    """
    if isinstance(data_path, str):
        data = json.load(open(data_path, 'r', encoding='utf-8'))
    elif isinstance(data_path, list):
        data = data_path
    else:
        raise ValueError("data_path는 문제 파일 경로 또는 문제 리스트여야 합니다.")
    

    rearranged_data = []
    for m in data:
        qna_data = replace_tags_in_qna_data(m.get('qna_data'), m.get('additional_tag_data'))
        # 객관식: OX 문제 제외, 선지가 3개 이상인 경우
        if (qtype == "multiple") and (qna_data.get('description').get('options') is not None) and (len(qna_data.get('description').get('options')) > 2): 
            pass
        # 단답형: 답변이 있고, 답변이 삭제되지 않은 경우
        elif (qtype == "short") and (qna_data.get('description').get('answer') is not None) and (qna_data.get('description').get('answer') != "삭제"):
            pass
        # 서술형: 답변이 있는 경우
        elif (qtype == "essay") and (qna_data.get('description').get('answer') is not None):
            pass
        else:
            continue

        qna = {
                    'file_id': m.get('file_id'),
                    'title': m.get('title'),
                    'chapter': m.get('chapter'),
                    'tag': qna_data.get('tag'),
                    'domain': m.get('qna_domain'),
                    'domain_reason': m.get('qna_reason'),
                    "subdomain": "",
                    "subdomain_reason": "",
                    'question': qna_data.get('description').get('question'),
                    'options': qna_data.get('description').get('options'),
                    'answer': qna_data.get('description').get('answer'),
                    'explanation': qna_data.get('description').get('explanation')
                }
        rearranged_data.append(qna)
        print(f"정제된 {qtype} 문제 수: ", len(rearranged_data))
        with open(os.path.join(BRONZE_LAYER_1_DIR, f'{qtype}.json'), "w", encoding="utf-8") as f:
            json.dump(rearranged_data, f, ensure_ascii=False, indent=4)




def main():

    # 1. FIN_workbook 하위 extracted_qna.json 파일 찾기
    json_files = get_json_files(EXTRACTED_DIR)
    # 2. 0_bronze_layer_grpby 하위 multiple.json, short.json, essay.json 파일 생성
    multiple, short, essay = get_qna_type(json_files)
    # 3. 1_bronze_layer_filter 하위 multiple.json, short.json, essay.json 파일 생성
    rearrange_data(multiple, "multiple")
    rearrange_data(short, "short")
    rearrange_data(essay, "essay")

    # 4. 2_bronze_layer_subdomain 하위 multiple.json, short.json, essay.json 파일 생성
    # qna_subdomain_classifier.py 실행
    # subprocess.run(["python", "qna_subdomain_classifier.py", "--data_path", os.path.join(BRONZE_LAYER_1_DIR, "multiple.json"), "--model", "x-ai/grok-4-fast", "--batch_size", "50", "--mode", "multiple"])
    # subprocess.run(["python", "qna_subdomain_classifier.py", "--data_path", os.path.join(BRONZE_LAYER_1_DIR, "short.json"), "--model", "x-ai/grok-4-fast", "--batch_size", "50", "--mode", "short"])
    # subprocess.run(["python", "qna_subdomain_classifier.py", "--data_path", os.path.join(BRONZE_LAYER_1_DIR, "essay.json"), "--model", "x-ai/grok-4-fast", "--batch_size", "50", "--mode", "essay"])


if __name__ == "__main__":
    main()