import os
import sys
import pandas as pd
from tqdm import tqdm
import requests
import json
from openai import OpenAI
import configparser
import argparse

# Import handling for both script and module execution
try:
    from .multiple_eval_by_model import replace_tags_in_qna_data
except ImportError:
    from multiple_eval_by_model import replace_tags_in_qna_data


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

    # return multiple, short, essay


def rearrange_data(data_path: str, qtype: str):
    """
    multiple 리스트에서 객관식 문제 추출
    Args:
        multiple_data_path: multiple-choice 문제 파일 경로
    Returns:
        multiple_for_grp: 정제된 multiple-choice 문제 리스트 (OX 문제 제외, 선지가 3개 이상인 경우)
    """
    data = json.load(open(data_path, 'r', encoding='utf-8'))
    
    if qtype == "multiple":
        multiple_for_grp = []
        for m in data:
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
                    'options': qna_data.get('description').get('options'),
                    'answer': qna_data.get('description').get('answer'),
                    'explanation': qna_data.get('description').get('explanation')            
                }
                multiple_for_grp.append(qna)
        print("정제된 multiple-choice 문제 수: ", len(multiple_for_grp))
        with open('evaluation/eval_data/multiple_for_grp.json', "w", encoding="utf-8") as f:
            json.dump(multiple_for_grp, f, ensure_ascii=False, indent=4)
        return multiple_for_grp

    elif qtype == "short":
        short_for_grp = []
        for s in data:
            qna_data = replace_tags_in_qna_data(s.get('qna_data'), s.get('additional_tag_data'))
            if (qna_data.get('description').get('answer') is not None) and (qna_data.get('description').get('answer') != "삭제"):
                # and (qna_data.get('description').get('options') is None):
                qna = {
                    'file_id': s.get('file_id'),
                    'title': s.get('title'),
                    'chapter': s.get('chapter'),
                    'tag': qna_data.get('tag'),
                    'domain': s.get('qna_domain'),
                    'domain_reason': s.get('qna_reason'),
                    "subdomain": "",
                    "subdomain_reason": "",
                    'question': qna_data.get('description').get('question'),
                    'options': qna_data.get('description').get('options'),
                    'answer': qna_data.get('description').get('answer'),
                    'explanation': qna_data.get('description').get('explanation')            
                }
                short_for_grp.append(qna)
        print("정제된 short-answer 문제 수: ", len(short_for_grp))
        with open('evaluation/eval_data/short_for_grp.json', "w", encoding="utf-8") as f:
            json.dump(short_for_grp, f, ensure_ascii=False, indent=4)
        return short_for_grp
    
    elif qtype == "essay":
        essay_for_grp = []
        for e in data:
            qna_data = replace_tags_in_qna_data(e.get('qna_data'), e.get('additional_tag_data'))
            if qna_data.get('description').get('answer') is not None:
                qna = {
                    'file_id': e.get('file_id'),
                    'title': e.get('title'),
                    'chapter': e.get('chapter'),
                    'tag': qna_data.get('tag'),
                    'domain': e.get('qna_domain'),
                    'domain_reason': e.get('qna_reason'),
                    "subdomain": "",
                    "subdomain_reason": "",
                    'question': qna_data.get('description').get('question'),
                    'options': qna_data.get('description').get('options'),
                    'answer': qna_data.get('description').get('answer'),
                    'explanation': qna_data.get('description').get('explanation')
                }
                essay_for_grp.append(qna)
        print("정제된 essay 문제 수: ", len(essay_for_grp))
        with open('evaluation/eval_data/essay_for_grp.json', "w", encoding="utf-8") as f:
            json.dump(essay_for_grp, f, ensure_ascii=False, indent=4)
        return essay_for_grp



if __name__ == "__main__":
    FINAL_DATA_PATH = '/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/data/FIN_workbook'
    json_files = get_json_files(FINAL_DATA_PATH)
    get_qna_type(json_files)
    multiple_for_grp = rearrange_data('evaluation/eval_data/multiple.json', "multiple")
    short_for_grp = rearrange_data('evaluation/eval_data/short.json', "short")
    essay_for_grp = rearrange_data('evaluation/eval_data/essay.json', "essay")