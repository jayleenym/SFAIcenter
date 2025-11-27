#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
태그 처리 클래스
"""

import re
import os
from typing import List, Dict, Any, Optional


class TagProcessor:
    """태그 처리 클래스"""
    
    @staticmethod
    def extract_tags_from_qna_content(qna_item: Dict) -> List[str]:
        """Q&A 내용에서 태그 추출 (img, etc 태그 제외)"""
        qna_content = ""
        if 'qna_data' in qna_item and 'description' in qna_item['qna_data']:
            desc = qna_item['qna_data']['description']
            # question, answer, explanation, options에서 태그 추출
            for field in ['question', 'answer', 'explanation', 'options']:
                if field in desc and desc[field]:
                    if field == 'options' and isinstance(desc[field], list):
                        for option in desc[field]:
                            qna_content += str(option) + " "
                    else:
                        qna_content += str(desc[field]) + " "
        
        # tb, f, note 태그만 추출 (img, etc 제외)
        tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
        f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
        footnote_tags = re.findall(r'\{note_\d{4}_\d{4}\}', qna_content)
        
        return tb_tags + f_tags + footnote_tags
    
    @staticmethod
    def extract_page_from_tag(tag: str) -> Optional[str]:
        """태그에서 페이지 번호 추출"""
        clean_tag = tag.strip('{}')
        match = re.match(r'^(f|tb|note|etc)_(\d{4})_\d+$', clean_tag)
        if match:
            return match.group(2)
        return None
    
    @staticmethod
    def find_tag_data_in_add_info(add_info: List[Dict], tag: str) -> Optional[Dict[str, Any]]:
        """add_info에서 특정 tag에 해당하는 데이터를 찾습니다"""
        clean_tag = tag.strip('{}')
        for item in add_info:
            if item.get('tag') == clean_tag:
                return item
        return None
    
    def add_missing_tags(self, qna_data: List[Dict], source_data: Dict) -> tuple:
        """additional_tags_found에 있지만 additional_tag_data에 없는 태그 추가"""
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
    
    def fill_empty_tag_data(self, qna_data: List[Dict], source_data: Dict) -> tuple:
        """빈 additional_tag_data의 data 필드를 원본 파일의 add_info에서 채우기"""
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
                                found_data = self.find_tag_data_in_add_info(page_add_info[page_num], tag)
                                if found_data:
                                    tag_data['data'] = found_data
                                    filled_count += 1
        
        return filled_count, total_empty
    
    @staticmethod
    def replace_tags_in_text(text: str, additional_tag_data: list, max_depth: int = 3) -> str:
        """
        텍스트에서 {f_0000_0000}이나 {tb_0000_0000} 같은 태그를 additional_tag_data에서 찾아서 대치합니다.
        중첩된 태그도 재귀적으로 처리합니다.
        
        Args:
            text: 대치할 텍스트
            additional_tag_data: 태그 데이터 리스트
            max_depth: 최대 재귀 깊이 (무한 루프 방지)
        
        Returns:
            태그가 대치된 텍스트
        """
        if not text or not additional_tag_data or max_depth <= 0:
            return text
        
        # 태그 패턴 매칭: {f_0000_0000}, {tb_0000_0000}, {note_0000_0000}
        tag_pattern = r'\{(f_\d{4}_\d{4}|tb_\d{4}_\d{4}|note_\d{4}_\d{4})\}'
        
        def replace_tag(match):
            tag_with_braces = match.group(0)  # {f_0000_0000}
            tag_without_braces = match.group(1)  # f_0000_0000
            
            # additional_tag_data에서 해당 태그 찾기
            for tag_data in additional_tag_data:
                if tag_data.get('tag') == tag_with_braces:
                    replacement_text = None
                    
                    # data 필드가 있는 경우
                    if 'data' in tag_data:
                        data = tag_data.get('data', {})
                        if isinstance(data, dict):
                            # data에서 적절한 필드 찾기 (우선순위: content, text, description, caption)
                            for field in ['content', 'text', 'description', 'caption']:
                                if field in data and data[field]:
                                    replacement_text = str(data[field])
                                    break
                            
                            # file_path가 있으면 파일명 표시
                            if replacement_text is None and 'file_path' in data and data['file_path']:
                                replacement_text = f"[{os.path.basename(data['file_path'])}]"
                        
                        # data가 문자열이면 그대로 사용
                        elif isinstance(data, str) and data:
                            replacement_text = data
                        
                        # data가 리스트면 첫 번째 요소 사용
                        elif isinstance(data, list) and data:
                            replacement_text = str(data[0])
                    
                    # data 필드가 없는 경우, 직접 필드에서 찾기
                    else:
                        # 직접 필드에서 적절한 내용 찾기 (우선순위: content, text, description, caption)
                        for field in ['content', 'text', 'description', 'caption']:
                            if field in tag_data and tag_data[field]:
                                replacement_text = str(tag_data[field])
                                break
                        
                        # file_path가 있으면 파일명 표시
                        if replacement_text is None and 'file_path' in tag_data and tag_data['file_path']:
                            replacement_text = f"[{os.path.basename(tag_data['file_path'])}]"
                    
                    # 대치 텍스트를 찾은 경우, 재귀적으로 중첩된 태그도 처리
                    if replacement_text is not None:
                        return TagProcessor.replace_tags_in_text(replacement_text, additional_tag_data, max_depth - 1)
            
            # 태그를 찾지 못한 경우 원본 태그 유지
            return tag_with_braces
        
        return re.sub(tag_pattern, replace_tag, text)
    
    @staticmethod
    def replace_tags_in_qna_data(qna_item: dict, additional_tag_data: list) -> dict:
        """
        Q&A 데이터의 question, answer, explanation, options에서 태그를 대치합니다.
        
        Args:
            qna_item: Q&A 데이터 딕셔너리
            additional_tag_data: 추가 태그 데이터 리스트
        
        Returns:
            태그가 대치된 Q&A 데이터
        """
        if not qna_item or not additional_tag_data:
            return qna_item
        
        # qna_data가 전체 qna 객체인 경우 qna_data 부분을 추출
        if 'qna_data' in qna_item:
            qna_info = qna_item['qna_data']
        else:
            # 이미 qna_data 부분만 전달된 경우
            qna_info = qna_item
        
        if 'description' in qna_info:
            desc = qna_info['description']
            
            # question 필드 처리
            if 'question' in desc and desc['question']:
                desc['question'] = TagProcessor.replace_tags_in_text(desc['question'], additional_tag_data)
            
            # options 필드 처리 (리스트)
            if 'options' in desc and desc['options']:
                if isinstance(desc['options'], list):
                    desc['options'] = [TagProcessor.replace_tags_in_text(option, additional_tag_data) for option in desc['options']]
                else:
                    desc['options'] = TagProcessor.replace_tags_in_text(desc['options'], additional_tag_data)
            
            # answer 필드 처리
            if 'answer' in desc and desc['answer']:
                desc['answer'] = TagProcessor.replace_tags_in_text(desc['answer'], additional_tag_data)
            
            # explanation 필드 처리
            if 'explanation' in desc and desc['explanation']:
                desc['explanation'] = TagProcessor.replace_tags_in_text(desc['explanation'], additional_tag_data)
        
        return qna_item

