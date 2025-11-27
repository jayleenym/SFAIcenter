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
    from qna.tag_processor import TagProcessor
    from qna.formatting import should_include_qna_item
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, project_root)
    from qna.tag_processor import TagProcessor
    from qna.formatting import should_include_qna_item


# pipeline/config에서 ONEDRIVE_PATH import 시도
try:
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, project_root)
    from tools import ONEDRIVE_PATH
except ImportError:
    # fallback: pipeline이 없는 경우 플랫폼별 기본값 사용
    import platform
    system = platform.system()
    home_dir = os.path.expanduser("~")
    if system == "Windows":
        ONEDRIVE_PATH = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
    else:
        ONEDRIVE_PATH = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")


EXTRACTED_DIR = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data')
EVAL_DATA_DIR = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data')
# BRONZE_LAYER_0_DIR = os.path.join(EVAL_DATA_DIR, '0_grpby')
BRONZE_LAYER_1_DIR = os.path.join(EVAL_DATA_DIR, '1_filter_with_tags')
BRONZE_LAYER_2_DIR = os.path.join(EVAL_DATA_DIR, '2_subdomain')

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
    etc = []

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
                elif qna.get('qna_type') == "etc":
                    etc.append(qna)
    print("------------- 데이터 형식 변경 & 필터링 -------------------")
    print("기본 multiple-choice: ", len(multiple))
    rearrange_data(multiple, "multiple-choice")
    print("기본 short-answer: ", len(short))
    rearrange_data(short, "short-answer")
    print("기본 essay: ", len(essay))
    rearrange_data(essay, "essay")
    print("기본 etc: ", len(etc))
    rearrange_data(etc, "etc")


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
        # 태그 치환 처리
        qna_data = TagProcessor.replace_tags_in_qna_data(m.get('qna_data'), m.get('additional_tag_data'))
        
        # qtype 유효성 검사
        if qtype not in ["multiple-choice", "short-answer", "essay", "etc"]:
            raise ValueError(f"올바르지 않은 문제 타입: {qtype}")
        
        # formatting.py의 필터링 함수 재사용 (태그 치환된 qna_data 전달)
        if not should_include_qna_item(m, qtype, qna_data=qna_data):
            continue

        qna = {
                    'file_id': m.get('file_id'),
                    'title': m.get('title'),
                    'chapter': m.get('chapter'),
                    'tag': qna_data.get('tag'),
                    # 'domain': m.get('qna_domain'),
                    # 'domain_reason': m.get('qna_reason'),
                    "domain": "",
                    "subdomain": "",
                    "classification_reason": "",
                    "is_calculation": "",
                    'question': qna_data.get('description').get('question'),
                    'options': qna_data.get('description').get('options'),
                    'answer': qna_data.get('description').get('answer'),
                    'explanation': qna_data.get('description').get('explanation')
                }
        rearranged_data.append(qna)
    print(f"정제된 {qtype} 수: ", len(rearranged_data))
    with open(os.path.join(BRONZE_LAYER_2_DIR, f'{qtype}.json'), "w", encoding="utf-8") as f:
        json.dump(rearranged_data, f, ensure_ascii=False, indent=4)


def classify_subdomain(data_path: list or str = None, qtype: str = None):
    """
    subdomain 분류
    Args:
        data_path: subdomain 분류 문제 파일 경로 또는 문제 리스트
        qtype: 문제 타입
    Returns:
        subdomain_classified: 분류된 문제 리스트
    """
    if isinstance(data_path, str):
        data = json.load(open(data_path, 'r', encoding='utf-8'))
    elif isinstance(data_path, list):
        data = data_path
    else:
        raise ValueError("data_path는 문제 파일 경로 또는 문제 리스트여야 합니다.")
    
    subdomain_classified = []
    for m in data:
        subdomain_classified.append(m)
    print(f"분류된 {qtype} 수: ", len(subdomain_classified))
    with open(os.path.join(BRONZE_LAYER_2_DIR, f'{qtype}.json'), "w", encoding="utf-8") as f:
        json.dump(subdomain_classified, f, ensure_ascii=False, indent=4)


def main():
    # 1. workbook_data 하위 extracted_qna.json 파일 찾기
    json_files = get_json_files(EXTRACTED_DIR)
    # 2. 0_bronze_layer_grpby 하위 multiple.json, short.json, essay.json 파일 생성
    get_qna_type(json_files)
    # 3. 1_bronze_layer_filter 하위 multiple.json, short.json, essay.json 파일 생성
    
    # 4. 2_bronze_layer_subdomain 하위 multiple.json, short.json, essay.json 파일 생성
    # qna_subdomain_classifier.py 실행
    # subprocess.run(["python", "qna_subdomain_classifier.py", "--data_path", os.path.join(BRONZE_LAYER_1_DIR, "multiple.json"), "--model", "x-ai/grok-4-fast", "--batch_size", "50", "--mode", "multiple"])
    # subprocess.run(["python", "qna_subdomain_classifier.py", "--data_path", os.path.join(BRONZE_LAYER_1_DIR, "short.json"), "--model", "x-ai/grok-4-fast", "--batch_size", "50", "--mode", "short"])
    # subprocess.run(["python", "qna_subdomain_classifier.py", "--data_path", os.path.join(BRONZE_LAYER_1_DIR, "essay.json"), "--model", "x-ai/grok-4-fast", "--batch_size", "50", "--mode", "essay"])


if __name__ == "__main__":
    main()