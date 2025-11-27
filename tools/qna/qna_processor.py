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

# tools 모듈 import를 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(current_dir)  # qna -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)

from core.utils import FileManager, TextProcessor, JSONHandler
from core.llm_query import LLMQuery
from qna.tag_processor import TagProcessor


class QnATypeClassifier:
    """Q&A 타입 분류 클래스"""
    
    @staticmethod
    def classify_qna_type(qna_info: dict) -> str:
        """Q&A 타입 분류 (multiple-choice/short-answer/essay/etc)"""
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
        self.tag_processor = TagProcessor()
    
    def extract_qna_from_json(self, json_data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
        """JSON 데이터에서 Q&A 태그를 찾아 추출"""
        extracted_qna = []
        
        # 전체 파일의 모든 페이지에서 add_info를 인덱싱 (태그가 다른 페이지에 있을 수 있음)
        all_add_info = {}  # {tag: info_item}
        for page_data in json_data.get('contents', []):
            add_info = page_data.get('add_info', [])
            for info_item in add_info:
                tag = info_item.get('tag')
                if tag:
                    # 이미 있으면 덮어쓰지 않음 (먼저 발견된 것 우선)
                    if tag not in all_add_info:
                        all_add_info[tag] = info_item
        
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
                    # 추가 태그 추출 (TagProcessor의 메서드 사용)
                    temp_qna_item = {'qna_data': {'description': qna_item.get('description', {})}}
                    additional_tags = self.tag_processor.extract_tags_from_qna_content(temp_qna_item)
                    
                    # 추가 태그 데이터 수집 (전체 파일의 모든 페이지에서 검색)
                    additional_tag_data = []
                    for additional_tag in additional_tags:
                        tag_without_braces = additional_tag[1:-1]
                        # 전체 파일의 add_info에서 검색
                        if tag_without_braces in all_add_info:
                            additional_tag_data.append({
                                'tag': additional_tag,
                                'data': all_add_info[tag_without_braces]
                            })
                        else:
                            # 찾지 못한 경우 빈 데이터로 추가 (나중에 process_additional_tags로 채울 수 있음)
                            additional_tag_data.append({
                                'tag': additional_tag,
                                'data': {}
                            })
                    
                    # Q&A 타입 분류
                    qna_type = self.type_classifier.classify_qna_type(qna_item)
                    
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
    
    def _find_source_files_for_file_id(self, file_path: str, file_id: str) -> List[Dict[str, Any]]:
        """file_path에서 cycle과 level을 추출하여 Lv2, Lv3_4, Lv5의 source 파일들을 찾아 로드"""
        source_data_list = []
        
        # file_path에서 cycle과 level 추출 시도
        # 예: .../data/FINAL/2C/Lv5/SS0250/SS0250.json
        path_parts = file_path.replace('\\', '/').split('/')
        cycle = None
        base_path = None
        
        # FINAL 경로에서 cycle 찾기
        for i, part in enumerate(path_parts):
            if part.endswith('C') and part[:-1].isdigit():
                cycle = part
                # base_path는 FINAL까지의 경로
                base_path = '/'.join(path_parts[:i+1])
                break
        
        if not cycle or not base_path:
            # 경로에서 찾지 못한 경우, file_manager의 base_path 사용
            base_path = self.file_manager.final_data_path
            # file_path에서 cycle 추출 재시도
            for part in path_parts:
                if part.endswith('C') and part[:-1].isdigit():
                    cycle = part
                    break
        
        if not cycle:
            return source_data_list
        
        # Lv2, Lv3_4, Lv5의 source 파일 찾기
        levels = ['Lv2', 'Lv3_4', 'Lv5']
        for level in levels:
            source_path = os.path.join(base_path, cycle, level, file_id, f'{file_id}.json')
            if os.path.exists(source_path):
                try:
                    source_data = JSONHandler.load(source_path)
                    source_data_list.append(source_data)
                except Exception as e:
                    # 로드 실패해도 계속 진행
                    pass
        
        return source_data_list
    
    def _fill_empty_tags_from_sources(self, extracted_qna: List[Dict[str, Any]], 
                                     source_data_list: List[Dict[str, Any]]) -> None:
        """빈 additional_tag_data의 data를 source 파일들에서 채움"""
        if not source_data_list:
            return
        
        # 여러 source 파일에서 페이지별 add_info를 인덱싱 (우선순위: Lv5 > Lv3_4 > Lv2)
        page_add_info = {}
        for source_data in source_data_list:
            if not source_data:
                continue
            for page_data in source_data.get('contents', []):
                page_num = page_data.get('page')
                if page_num:
                    # 이미 있으면 덮어쓰지 않음 (우선순위 유지)
                    if page_num not in page_add_info:
                        page_add_info[page_num] = page_data.get('add_info', [])
        
        # 전체 파일의 모든 태그를 인덱싱 (페이지를 넘나드는 태그도 찾기 위해)
        all_tags_data = {}  # {tag_without_braces: info_item}
        for source_data in source_data_list:
            if not source_data:
                continue
            for page_data in source_data.get('contents', []):
                add_info = page_data.get('add_info', [])
                for info_item in add_info:
                    tag = info_item.get('tag')
                    if tag:
                        # 이미 있으면 덮어쓰지 않음 (우선순위 유지)
                        if tag not in all_tags_data:
                            all_tags_data[tag] = info_item
        
        # extracted_qna의 각 항목 처리
        for item in extracted_qna:
            if 'additional_tag_data' in item:
                for tag_data in item['additional_tag_data']:
                    if tag_data.get('data') == {}:  # 빈 data 객체
                        tag = tag_data.get('tag')
                        
                        if tag:
                            tag_without_braces = tag.strip('{}')
                            
                            # 먼저 전체 태그 인덱스에서 검색
                            if tag_without_braces in all_tags_data:
                                tag_data['data'] = all_tags_data[tag_without_braces]
                            else:
                                # 페이지별로 검색 (태그에서 페이지 번호 추출)
                                page_num = self.tag_processor.extract_page_from_tag(tag)
                                
                                if page_num and page_num in page_add_info:
                                    found_data = self.tag_processor.find_tag_data_in_add_info(
                                        page_add_info[page_num], tag
                                    )
                                    if found_data:
                                        tag_data['data'] = found_data
    
    def _process_additional_tags(self, extracted_qna: List[Dict[str, Any]], 
                                 source_data_list: List[Dict[str, Any]]) -> None:
        """process_additional_tags의 로직을 수행 (누락된 태그 추가 + 빈 데이터 채우기)"""
        if not source_data_list:
            return
        
        # process_additional_tags의 함수들을 import
        try:
            from qna.processing.process_additional_tags import (
                fix_missing_tags_with_add_info,
                fill_additional_tag_data
            )
        except ImportError:
            # import 실패 시 기본 로직만 수행
            self._fill_empty_tags_from_sources(extracted_qna, source_data_list)
            return
        
        # 1단계: 누락된 태그 추가 (additional_tags_found에 있지만 additional_tag_data에 없는 태그)
        fix_missing_tags_with_add_info(extracted_qna, source_data_list)
        
        # 2단계: 빈 data 채우기
        fill_additional_tag_data(extracted_qna, source_data_list)
    
    def extract_from_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """파일에서 Q&A 추출 (기존 파일이 있으면 덮어쓰기, 비어있는 태그 자동 채우기)"""
        json_data = JSONHandler.load(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        
        result = self.extract_qna_from_json(json_data, file_name)
        
        if len(result['extracted_qna']) > 0:
            # process_additional_tags 로직 수행 (저장 전에)
            source_data_list = self._find_source_files_for_file_id(file_path, file_name)
            if source_data_list:
                self._process_additional_tags(result['extracted_qna'], source_data_list)
            
            if output_path:
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                
                qna_output_path = output_path.replace('.json', '_extracted_qna.json')
                # 기존 파일이 있어도 덮어쓰기
                JSONHandler.save(result['extracted_qna'], qna_output_path)
        
        return result

