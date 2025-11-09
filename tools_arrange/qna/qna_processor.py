#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 처리 클래스
"""

import re
import json
import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import FileManager, TextProcessor, JSONHandler
from core.llm_query import LLMQuery


class QnATypeClassifier:
    """Q&A 타입 분류 클래스"""
    
    @staticmethod
    def analyze_extracted_qna(qna_info: dict) -> str:
        """Q&A 타입 분석"""
        try:
            if 'description' in qna_info and 'options' in qna_info['description']:
                options = qna_info['description']['options']
                answer = qna_info['description']['answer']
                
                if len(options) >= 2:
                    if len(answer) == 1 and (answer in ['O', 'X'] or answer in ['①', '②', '③', '④', '⑤']):
                        return 'multiple-choice'
                    else:
                        return 'etc'
                else:
                    sentence_count = answer.count('.') + answer.count('!') + answer.count('?') + answer.count('\n')
                    pattern_only_answer = re.match(r'^\{[ft]b?_\d{4}_\d{4}\}$', answer.strip())
                    
                    if len(answer) == 0:
                        return "etc"
                    elif (sentence_count <= 1) or pattern_only_answer:
                        return 'short-answer'
                    else:
                        return 'essay'
        except Exception as e:
            print(f"분석 오류: {e}")
            return "etc"
        
        return "etc"


class QnAExtractor:
    """Q&A 추출 클래스"""
    
    def __init__(self, file_manager: FileManager = None):
        """
        Args:
            file_manager: FileManager 인스턴스
        """
        self.file_manager = file_manager or FileManager()
        self.type_classifier = QnATypeClassifier()
    
    def extract_qna_tags(self, json_data: Dict[str, Any], file_name: str, output_path: str = None) -> Dict[str, Any]:
        """Q&A 태그 추출"""
        extracted_qna = []
        
        for page_data in json_data.get('contents', []):
            page_contents = page_data.get('page_contents', '')
            if page_contents == "":
                continue
            
            add_info = page_data.get('add_info', [])
            qna_tags = re.findall(r'\{q_\d{4}_\d{4}\}', page_contents)
            
            qna_items_to_extract = []
            
            for tag in qna_tags:
                tag_without_braces = tag.removeprefix('{').removesuffix('}')
                
                qna_item = None
                for info_item in add_info:
                    if info_item.get('tag') == tag_without_braces:
                        qna_item = info_item
                        break
                
                if qna_item is not None:
                    # 추가 태그 추출
                    qna_content = ""
                    if 'description' in qna_item:
                        desc = qna_item['description']
                        for field in ['question', 'answer', 'explanation', 'options']:
                            if field in desc and desc[field]:
                                if field == 'options' and isinstance(desc[field], list):
                                    for option in desc[field]:
                                        qna_content += str(option) + " "
                                else:
                                    qna_content += str(desc[field]) + " "
                    
                    # 추가 태그 추출
                    tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
                    img_tags = re.findall(r'\{img_\d{4}_\d{4}\}', qna_content)
                    f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
                    etc_tags = re.findall(r'\{etc_\d{4}_\d{4}\}', qna_content)
                    footnote_tags = re.findall(r'\{note_\d{4}_\d{4}\}', qna_content)
                    additional_tags = tb_tags + img_tags + f_tags + etc_tags + footnote_tags
                    
                    # 추가 태그 데이터 수집
                    additional_tag_data = []
                    for additional_tag in additional_tags:
                        tag_without_braces = additional_tag[1:-1]
                        for info_item in add_info:
                            if info_item.get('tag') == tag_without_braces:
                                additional_tag_data.append({
                                    'tag': additional_tag,
                                    'data': info_item
                                })
                                break
                    
                    # Q&A 타입 분류
                    qna_type = self.type_classifier.analyze_extracted_qna(qna_item)
                    
                    # Q&A 정보 저장
                    qna_items_to_extract.append({
                        'file_id': file_name,
                        'title': json_data['title'],
                        'cat1_domain': json_data.get('cat1_domain'),
                        'cat2_sub': json_data.get('cat2_sub'),
                        'cat3_specific': json_data.get('cat3_specific'),
                        'chapter': page_data.get('chapter'),
                        'page': page_data.get('page'),
                        "qna_type": qna_type,
                        'qna_data': qna_item,
                        'additional_tags_found': additional_tags,
                        'additional_tag_data': additional_tag_data
                    })
            
            extracted_qna.extend(qna_items_to_extract)
        
        return {'extracted_qna': extracted_qna}
    
    def extract_from_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """파일에서 Q&A 추출"""
        json_data = JSONHandler.load(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        
        result = self.extract_qna_tags(json_data, file_name, output_path)
        
        if len(result['extracted_qna']) > 0 and output_path:
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            qna_output_path = output_path.replace('.json', '_extracted_qna.json')
            JSONHandler.save(result['extracted_qna'], qna_output_path)
        
        return result


class TagProcessor:
    """태그 처리 클래스"""
    
    @staticmethod
    def extract_tags_from_qna_content(qna_item: Dict) -> List[str]:
        """Q&A 내용에서 태그 추출"""
        qna_content = ""
        if 'qna_data' in qna_item and 'description' in qna_item['qna_data']:
            desc = qna_item['qna_data']['description']
            for field in ['question', 'answer', 'explanation', 'options']:
                if field in desc and desc[field]:
                    if field == 'options' and isinstance(desc[field], list):
                        for option in desc[field]:
                            qna_content += str(option) + " "
                    else:
                        qna_content += str(desc[field]) + " "
        
        tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
        img_tags = re.findall(r'\{img_\d{4}_\d{4}\}', qna_content)
        f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
        etc_tags = re.findall(r'\{etc_\d{4}_\d{4}\}', qna_content)
        footnote_tags = re.findall(r'\{note_\d{4}_\d{4}\}', qna_content)
        
        return tb_tags + img_tags + f_tags + etc_tags + footnote_tags
    
    @staticmethod
    def extract_page_from_tag(tag: str) -> Optional[str]:
        """태그에서 페이지 번호 추출"""
        clean_tag = tag.strip('{}')
        match = re.match(r'^(img|f|tb|note|etc)_(\d{4})_\d+$', clean_tag)
        if match:
            return match.group(2)
        return None
    
    def fix_missing_tags(self, qna_data: List[Dict], source_data: Dict) -> tuple:
        """누락된 태그 추가"""
        source_tags_data = {}
        for item in source_data.get('contents', []):
            if "add_info" in item and isinstance(item["add_info"], list):
                for add_item in item["add_info"]:
                    if "tag" in add_item:
                        source_tags_data[add_item["tag"]] = add_item
        
        tags_added_from_source = 0
        tags_added_empty = 0
        tags_found_in_content = 0
        
        for entry in qna_data:
            additional_tags_found = set(entry.get("additional_tags_found", []))
            
            content_tags = self.extract_tags_from_qna_content(entry)
            if content_tags:
                for tag in content_tags:
                    additional_tags_found.add(tag)
                tags_found_in_content += len(content_tags)
            
            entry["additional_tags_found"] = list(additional_tags_found)
            
            additional_tag_data_tags = {item["tag"] for item in entry.get("additional_tag_data", [])}
            missing_in_data = additional_tags_found - additional_tag_data_tags
            
            if missing_in_data:
                for tag_with_braces in missing_in_data:
                    tag_without_braces = tag_with_braces.strip('{}')
                    
                    if tag_without_braces in source_tags_data:
                        if "additional_tag_data" not in entry:
                            entry["additional_tag_data"] = []
                        
                        tag_data = source_tags_data[tag_without_braces].copy()
                        tag_data["tag"] = tag_with_braces
                        entry["additional_tag_data"].append(tag_data)
                        tags_added_from_source += 1
                    else:
                        if "additional_tag_data" not in entry:
                            entry["additional_tag_data"] = []
                        entry["additional_tag_data"].append({
                            "tag": tag_with_braces,
                            "data": {}
                        })
                        tags_added_empty += 1
        
        return tags_added_from_source, tags_added_empty, tags_found_in_content
    
    def fill_additional_tag_data(self, qna_data: List[Dict], source_data: Dict) -> tuple:
        """빈 additional_tag_data 채우기"""
        page_add_info = {}
        for page_data in source_data.get('contents', []):
            page_num = page_data.get('page')
            if page_num:
                page_add_info[page_num] = page_data.get('add_info', [])
        
        filled_count = 0
        total_empty = 0
        
        for item in qna_data:
            if 'additional_tag_data' in item:
                for tag_data in item['additional_tag_data']:
                    if tag_data.get('data') == {}:
                        total_empty += 1
                        tag = tag_data.get('tag')
                        
                        if tag:
                            page_num = self.extract_page_from_tag(tag)
                            
                            if page_num and page_num in page_add_info:
                                for add_item in page_add_info[page_num]:
                                    if add_item.get('tag') == tag.strip('{}'):
                                        tag_data['data'] = add_item
                                        filled_count += 1
                                        break
        
        return filled_count, total_empty

