# Generated from notebook: qna_extract.ipynb
# This file was auto-created to expose reusable code as a module.

import json
import os
import pandas as pd
import warnings
import shutil
from glob import glob
import re
from typing import List, Dict, Any

base_dir = "/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar"
analysis = {1:'1차 분석', 2:'2차 분석', 3: '3차 분석'}
buy = {1:'1차 구매', 2:'2차 구매', 3: '3차 구매'}
i = 1
json_files = []
total_extracted = 0
processed_files = 0

def analyze_extracted_qna(qna_info: dict):
    # qna_info = qna_data['qna_data']
    # print(qna_info)
    try:
        if 'description' in qna_info and 'options' in qna_info['description']:
            options = qna_info['description']['options']
            answer = qna_info['description']['answer']
            if (len(options) >= 4 and len(options) <= 5) and (len(answer) == 4 or len(answer) == 1):
                # 객관식
                return 'multiple-choice'
            else:
                # 주관식 - 답변의 문장 수로 단답형/서술형 구분
                sentence_count = answer.count('.') + answer.count('!') + answer.count('?')
                if sentence_count <= 1:
                    # 한 문장 또는 한 단어 (단답형)
                    return 'short-answer'
                else:
                    # 2문장 이상 (서술형)
                    return 'essay'
    except Exception as e:
        print("분석 오류:", e)
def extract_qna_tags(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    page_contents에서 {q_0000_0000} 형태의 태그를 추출하고,
    add_info에서 해당 태그를 찾아서 별도 리스트로 분리하는 함수
    Q&A 내용 안의 tb, img, f 태그도 함께 추출하여 제거 (수정된 정규식)
    
    Args:
        json_data: JSON 데이터
        
    Returns:
        수정된 JSON 데이터와 추출된 Q&A 리스트
    """
    # 추출된 Q&A를 저장할 리스트
    extracted_qna = []

    # 각 페이지를 순회
    for page_data in json_data.get('contents', []):
        page_contents = page_data.get('page_contents', '')
        if page_contents != "":
            add_info = page_data.get('add_info', [])
            
            # page_contents에서 {q_0000_0000} 형태의 태그 추출
            qna_tags = re.findall(r'\{q_\d{4}_\d{4}\}', page_contents)
            
            # 제거할 인덱스들을 수집
            indices_to_remove = set()
            qna_items_to_extract = []
            
            # 각 태그에 대해 add_info에서 해당하는 항목 찾기
            for tag in qna_tags:
                # add_info에서 해당 태그를 가진 항목 찾기
                qna_item_index = None
                qna_item = None
                tag = tag.removeprefix('{').removesuffix('}')
                
                for i, info_item in enumerate(add_info):
                    if info_item.get('tag') == tag:
                        qna_item_index = i
                        qna_item = info_item
                        break
                
                if qna_item is not None:
                    # Q&A 내용에서 추가 태그들 추출
                    qna_content = ""
                    if 'description' in qna_item:
                        desc = qna_item['description']
                        # question, answer, explanation, options에서 태그 추출
                        for field in ['question', 'answer', 'explanation', 'options']:
                            if field in desc and desc[field]:
                                if field == 'options' and isinstance(desc[field], list):
                                    # options는 리스트이므로 각 항목을 합침
                                    for option in desc[field]:
                                        qna_content += str(option) + " "
                                else:
                                    qna_content += str(desc[field]) + " "
                    
                    # Q&A 내용에서 tb, img, f 태그 추출 (수정된 정규식)
                    tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
                    img_tags = re.findall(r'\{img_\d{4}_\d{4}\}', qna_content)
                    f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
                    additional_tags = tb_tags + img_tags + f_tags
                    
                    # 디버깅: 추가 태그 발견 시 출력
                    # if additional_tags:
                    #     print(f"  추가 태그 발견 - Q&A: {tag}")
                    #     print(f"    TB: {tb_tags}, IMG: {img_tags}, F: {f_tags}")
                    
                    # 추가 태그들의 실제 데이터 수집
                    additional_tag_data = []
                    
                    # 추가 태그들도 add_info에서 찾아서 인덱스 수집 및 데이터 저장
                    for additional_tag in additional_tags:
                        tag_without_braces = additional_tag[1:-1]  # {tag} -> tag
                        for j, additional_info_item in enumerate(add_info):
                            if additional_info_item.get('tag') == tag_without_braces:
                                indices_to_remove.add(j)
                                # 추가 태그의 실제 데이터도 저장
                                additional_tag_data.append({
                                    'tag': additional_tag,
                                    # 'tag_type': additional_tag.split('_')[0][1:],  # {tb_0000_0000} -> tb
                                    'data': additional_info_item
                                })
                                # print(f"    -> 추가 태그 데이터 수집: {additional_tag}")
                                break
                    
                    # Q&A 항목도 제거 대상에 추가
                    indices_to_remove.add(qna_item_index)
        
                    # 추출할 Q&A 정보 저장
                    qna_items_to_extract.append({
                        'file_id': json_data.get("file_id"),
                        'title': json_data.get('title'),
                        'chapter': page_data.get('chapter'),
                        'page': page_data.get('page'),
                        "qna_type": analyze_extracted_qna(qna_item),
                        "qna_domain": "",
                        'qna_data': qna_item,
                        'additional_tags_found': additional_tags,
                        'additional_tag_data': additional_tag_data
                    })
            
            # 인덱스를 역순으로 정렬하여 제거 (뒤에서부터 제거)
            sorted_indices = sorted(indices_to_remove, reverse=True)
            for idx in sorted_indices:
                if 0 <= idx < len(add_info):
                    add_info.pop(idx)
            
            # 추출된 Q&A들을 리스트에 추가
            extracted_qna.extend(qna_items_to_extract)

            # 수정된 add_info로 업데이트
            page_data['add_info'] = add_info
            page_data['page_contents'] = re.sub(r'\{q_\d{4}_\d{4}\}', "", page_contents)
            page_data['page_contents'] = page_data['page_contents'].replace('\n\n', '\n')
    
    # 정제 끝나고 빈 페이지 삭제
    pages_to_remove = []
    for i, page_data in enumerate(json_data.get('contents', [])):
        page_contents = page_data.get('page_contents', '')
        if page_contents.strip() == "":
            pages_to_remove.append(i)
    
    # 역순으로 제거
    for i in reversed(pages_to_remove):
        json_data['contents'].pop(i)
    
    return {
        'modified_json': json_data,
        'extracted_qna': extracted_qna
    }
def process_json_file(file_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    JSON 파일을 처리하여 Q&A 태그를 추출하고 분리하는 함수
    
    Args:
        file_path: 입력 JSON 파일 경로
        output_path: 출력 JSON 파일 경로 (None이면 원본 파일 덮어쓰기)
        
    Returns:
        처리 결과
    """
    # JSON 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Q&A 태그 추출 및 분리
    result = extract_qna_tags(json_data)
    
    # 수정된 JSON 저장
    output_file = output_path if output_path else file_path
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result['modified_json'], f, ensure_ascii=False, indent=4)
    

    # 추출된 Q&A를 별도 파일로 저장
    if len(result['extracted_qna']) != 0:
        qna_output_path = output_path.replace('.json', '_extracted_qna.json')
        with open(qna_output_path, 'w', encoding='utf-8') as f:
            json.dump(result['extracted_qna'], f, ensure_ascii=False, indent=4)

        # analyze_extracted_qna(qna_output_path)
        return result
    else:
        qna_output_path = ""
    
    print(f"처리 완료:")
    print(f"- 수정된 JSON: {output_file}")
    # print(f"- 추출된 Q&A: {qna_output_path}")
    if len(result['extracted_qna']) > 0:
        print(f"- 추출된 Q&A 개수: {len(result['extracted_qna'])}")
    
    return result

__all__ = ['analysis', 'analyze_extracted_qna', 'base_dir', 'buy', 'extract_qna_tags', 'i', 'json_files', 'process_json_file', 'processed_files', 'total_extracted']
