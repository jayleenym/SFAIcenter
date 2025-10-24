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
                'tag': qna_data.get('tag'),
                'domain': m.get('qna_domain'),
                'domain_reason': m.get('qna_reason'),
                "subdomain": "",
                "subdomain_reason": "",
                'question': qna_data.get('description').get('question'),
                'answer': qna_data.get('description').get('answer'),
                'options': qna_data.get('description').get('options'),
                'explanation': qna_data.get('description').get('explanation')            
            }
            multiple_for_grp.append(qna)
    print("정제된 multiple-choice 문제 수: ", len(multiple_for_grp))

    return multiple_for_grp


if __name__ == "__main__":
    FINAL_DATA_PATH = '/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/data/FIN_workbook'
    json_files = get_json_files(FINAL_DATA_PATH)

    
