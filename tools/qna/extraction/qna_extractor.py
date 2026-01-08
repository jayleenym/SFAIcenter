#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 추출 클래스

JSON 데이터에서 Q&A 태그를 추출하고 처리합니다.
"""

import re
import os
from typing import List, Dict, Any, Optional, Tuple

from tools.core.utils import FileManager, JSONHandler
from tools.qna.processing.qna_type_classifier import QnATypeClassifier
from tools.qna.extraction.tag_processor import TagProcessor


class QnAExtractor:
    """Q&A 추출 클래스"""
    
    def __init__(self, file_manager: FileManager = None):
        self.file_manager = file_manager or FileManager()
        self.type_classifier = QnATypeClassifier()
        self.tag_processor = TagProcessor()
    
    def _build_tag_indices(self, contents: List[Dict]) -> Tuple[Dict[str, Any], Dict[str, List]]:
        """
        전체 contents에서 태그 인덱스를 구축합니다.
        
        Returns:
            (all_add_info, page_add_info) 튜플
            - all_add_info: {tag: info_item} - 태그명으로 검색
            - page_add_info: {page_num: [add_info_items]} - 페이지별 검색
        """
        all_add_info = {}
        page_add_info = {}
        
        for page_data in contents:
            add_info = page_data.get('add_info', [])
            page_num = page_data.get('page')
            
            if page_num is not None:
                page_num_str = str(page_num).zfill(4)
                if page_num_str not in page_add_info:
                    page_add_info[page_num_str] = []
                page_add_info[page_num_str].extend(add_info)
            
            for info_item in add_info:
                tag = info_item.get('tag')
                if tag and tag not in all_add_info:
                    all_add_info[tag] = info_item
        
        return all_add_info, page_add_info
    
    def _find_additional_tag_data(self, additional_tags: List[str], 
                                   all_add_info: Dict, page_add_info: Dict) -> List[Dict]:
        """추가 태그들의 데이터를 찾아서 반환합니다."""
        additional_tag_data = []
        
        for tag in additional_tags:
            tag_without_braces = tag[1:-1]  # 중괄호 제거
            found_data = None
            
            # 1차: 전체 태그 인덱스에서 검색
            if tag_without_braces in all_add_info:
                found_data = all_add_info[tag_without_braces]
            else:
                # 2차: 페이지별 검색
                tag_page_num = self.tag_processor.extract_page_from_tag(tag)
                if tag_page_num and tag_page_num in page_add_info:
                    found_data = self.tag_processor.find_tag_data_in_add_info(
                        page_add_info[tag_page_num], tag
                    )
            
            additional_tag_data.append({
                'tag': tag,
                'data': found_data if found_data else {}
            })
        
        return additional_tag_data
    
    def _extract_qna_item(self, qna_item: Dict, page_data: Dict, json_data: Dict,
                          file_name: str, all_add_info: Dict, page_add_info: Dict) -> Dict:
        """단일 Q&A 항목을 추출합니다."""
        # 추가 태그 추출 (description 안의 필드들에서 추출)
        description = qna_item.get('description', {})
        additional_tags = self.tag_processor.extract_tags_from_qna_content(description)
        
        # 추가 태그 데이터 수집
        additional_tag_data = self._find_additional_tag_data(
            additional_tags, all_add_info, page_add_info
        )
        
        # Q&A 타입 분류
        qna_type = self.type_classifier.classify_qna_type(qna_item)
        
        return {
            'file_id': file_name,
            'title': json_data['title'],
            'cat1_domain': json_data.get('cat1_domain'),
            'cat2_sub': json_data.get('cat2_sub'),
            'cat3_specific': json_data.get('cat3_specific'),
            'chapter': page_data.get('chapter'),
            'page': page_data.get('page'),
            'qna_type': qna_type,
            'qna_data': qna_item,
            'additional_tags_found': additional_tags,
            'additional_tag_data': additional_tag_data
        }
    
    def extract_qna_from_json(self, json_data: Dict[str, Any], file_name: str, 
                               all_contents: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        JSON 데이터에서 Q&A 태그를 찾아 추출합니다.
        
        Args:
            json_data: 처리할 JSON 데이터
            file_name: 파일명
            all_contents: 전체 파일의 contents (페이지 단위 처리 시 사용)
        """
        extracted_qna = []
        contents_for_indexing = all_contents or json_data.get('contents', [])
        
        # 태그 인덱스 구축
        all_add_info, page_add_info = self._build_tag_indices(contents_for_indexing)
        
        # 각 페이지 처리
        for page_data in json_data.get('contents', []):
            page_contents = page_data.get('page_contents', '')
            if not page_contents:
                continue
            
            add_info = page_data.get('add_info', [])
            qna_tags = re.findall(r'\{q_\d{4}_\d{4}\}', page_contents)
            
            for tag in qna_tags:
                tag_without_braces = tag[1:-1]
                
                # add_info에서 해당 Q&A 항목 찾기
                qna_item = next(
                    (item for item in add_info if item.get('tag') == tag_without_braces),
                    None
                )
                
                if qna_item:
                    extracted = self._extract_qna_item(
                        qna_item, page_data, json_data, file_name,
                        all_add_info, page_add_info
                    )
                    extracted_qna.append(extracted)
        
        return {'extracted_qna': extracted_qna}
    
    def _find_source_files_for_file_id(self, file_path: str, file_id: str) -> List[Dict[str, Any]]:
        """file_path에서 cycle을 추출하여 Lv2, Lv3_4, Lv5의 source 파일들을 찾아 로드합니다."""
        source_data_list = []
        path_parts = file_path.replace('\\', '/').split('/')
        
        # FINAL 경로에서 cycle과 base_path 찾기
        cycle = None
        base_path = None
        
        for i, part in enumerate(path_parts):
            if part.endswith('C') and part[:-1].isdigit():
                cycle = part
                base_path = '/'.join(path_parts[:i+1])
                break
        
        if not cycle:
            base_path = self.file_manager.final_data_path
            for part in path_parts:
                if part.endswith('C') and part[:-1].isdigit():
                    cycle = part
                    break
        
        if not cycle:
            return source_data_list
        
        # 각 레벨에서 source 파일 로드
        for level in ['Lv2', 'Lv3_4', 'Lv5']:
            source_path = os.path.join(base_path, cycle, level, file_id, f'{file_id}.json')
            if os.path.exists(source_path):
                try:
                    source_data_list.append(JSONHandler.load(source_path))
                except Exception:
                    pass
        
        return source_data_list
    
    def _fill_empty_tags_from_sources(self, extracted_qna: List[Dict], 
                                       source_data_list: List[Dict]) -> None:
        """빈 additional_tag_data의 data를 source 파일들에서 채웁니다."""
        if not source_data_list:
            return
        
        # source 파일들에서 태그 인덱스 구축
        all_tags_data = {}
        page_add_info = {}
        
        for source_data in source_data_list:
            if not source_data:
                continue
            for page_data in source_data.get('contents', []):
                page_num = page_data.get('page')
                add_info = page_data.get('add_info', [])
                
                if page_num and page_num not in page_add_info:
                    page_add_info[page_num] = add_info
                
                for info_item in add_info:
                    tag = info_item.get('tag')
                    if tag and tag not in all_tags_data:
                        all_tags_data[tag] = info_item
        
        # 빈 태그 데이터 채우기
        for item in extracted_qna:
            for tag_data in item.get('additional_tag_data', []):
                if tag_data.get('data') == {}:
                    tag = tag_data.get('tag')
                    if not tag:
                        continue
                    
                    tag_without_braces = tag.strip('{}')
                    
                    if tag_without_braces in all_tags_data:
                        tag_data['data'] = all_tags_data[tag_without_braces]
                    else:
                        page_num = self.tag_processor.extract_page_from_tag(tag)
                        if page_num and page_num in page_add_info:
                            found = self.tag_processor.find_tag_data_in_add_info(
                                page_add_info[page_num], tag
                            )
                            if found:
                                tag_data['data'] = found
    
    def _process_additional_tags(self, extracted_qna: List[Dict], 
                                  source_data_list: List[Dict]) -> None:
        """누락된 태그 추가 및 빈 데이터 채우기를 수행합니다."""
        if not source_data_list:
            return
        
        try:
            from tools.qna.processing.process_additional_tags import (
                fix_missing_tags_with_add_info,
                fill_additional_tag_data
            )
            fix_missing_tags_with_add_info(extracted_qna, source_data_list)
            fill_additional_tag_data(extracted_qna, source_data_list)
        except ImportError:
            self._fill_empty_tags_from_sources(extracted_qna, source_data_list)
    
    def extract_from_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """파일에서 Q&A를 추출합니다."""
        json_data = JSONHandler.load(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        
        result = self.extract_qna_from_json(json_data, file_name)
        
        if result['extracted_qna']:
            source_data_list = self._find_source_files_for_file_id(file_path, file_name)
            if source_data_list:
                self._process_additional_tags(result['extracted_qna'], source_data_list)
            
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                qna_output_path = output_path.replace('.json', '_extracted_qna.json')
                JSONHandler.save(result['extracted_qna'], qna_output_path)
        
        return result
