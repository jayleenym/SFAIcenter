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
    
    # 지원하는 태그 타입들
    TAG_TYPES = ['tb', 'f', 'note', 'etc', 'img']
    
    @staticmethod
    def extract_tags_from_qna_content(qna_item: Dict) -> List[str]:
        """
        Q&A 내용에서 태그 추출
        
        question, answer, explanation, options 필드에서 태그를 추출합니다.
        지원 태그: tb, f, note, etc, img
        
        Args:
            qna_item: Q&A 데이터 (최상위 레벨에 question, answer, explanation, options 포함)
        
        Raises:
            ValueError: qna_data.description 구조가 전달된 경우
        """
        # qna_data.description 구조는 지원하지 않음
        if 'qna_data' in qna_item and 'description' in qna_item.get('qna_data', {}):
            raise ValueError(
                "qna_data.description 구조는 지원되지 않습니다. "
                "최상위 레벨에 question, answer, explanation, options 필드를 사용하세요."
            )
        
        content_parts = []
        
        # question, answer, explanation, options 필드에서 추출
        for field in ['question', 'answer', 'explanation']:
            if field in qna_item and qna_item[field]:
                content_parts.append(str(qna_item[field]))
        
        if 'options' in qna_item and qna_item['options']:
            opts = qna_item['options']
            if isinstance(opts, list):
                content_parts.extend(str(opt) for opt in opts)
            else:
                content_parts.append(str(opts))
        
        qna_content = " ".join(content_parts)
        
        # 모든 태그 타입 추출 (tb, f, note, etc, img)
        tag_types = '|'.join(TagProcessor.TAG_TYPES)
        return re.findall(rf'\{{(?:{tag_types})_\d{{4}}_\d{{4}}\}}', qna_content)
    
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
    
    @staticmethod
    def _extract_tags_from_tag_data(tag_data: Dict) -> List[str]:
        """
        태그 데이터 (description, caption 등)에서 중첩된 태그를 추출합니다.
        예: note의 description에 {f_0287_0001}가 있는 경우
        
        Args:
            tag_data: 태그 데이터 딕셔너리
            
        Returns:
            추출된 태그 리스트
        """
        tag_types = '|'.join(TagProcessor.TAG_TYPES)
        pattern = rf'\{{(?:{tag_types})_\d{{4}}_\d{{4}}\}}'
        
        tags = []
        # 태그 데이터의 description, caption, content, text 필드에서 중첩 태그 추출
        for field in ['description', 'caption', 'content', 'text']:
            value = tag_data.get(field)
            if value and isinstance(value, str):
                found_tags = re.findall(pattern, value)
                tags.extend(found_tags)
        
        # data 필드가 딕셔너리인 경우에도 확인
        data = tag_data.get('data', {})
        if isinstance(data, dict):
            for field in ['description', 'caption', 'content', 'text']:
                value = data.get(field)
                if value and isinstance(value, str):
                    found_tags = re.findall(pattern, value)
                    tags.extend(found_tags)
        
        return tags
    
    def add_missing_tags(self, qna_data: List[Dict], source_data: Dict) -> tuple:
        """
        additional_tags_found에 있지만 additional_tag_data에 없는 태그 추가
        중첩된 태그도 재귀적으로 추가합니다.
        """
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
            
            # 중첩 태그를 포함하여 모든 필요한 태그 수집 (최대 3단계까지)
            max_depth = 3
            for _ in range(max_depth):
                additional_tag_data_tags = {item.get("tag", "") for item in entry.get("additional_tag_data", [])}
                missing_in_data = additional_tags_found - additional_tag_data_tags
                
                if not missing_in_data:
                    break
                
                for tag_with_braces in missing_in_data:
                    tag_without_braces = tag_with_braces.strip('{}')
                    
                    if tag_without_braces in source_tags_data:
                        if "additional_tag_data" not in entry:
                            entry["additional_tag_data"] = []
                        
                        tag_data = source_tags_data[tag_without_braces].copy()
                        tag_data["tag"] = tag_with_braces
                        entry["additional_tag_data"].append(tag_data)
                        tags_added_from_source += 1
                        
                        # 이 태그 데이터에서 중첩된 태그 추출하여 추가
                        nested_tags = self._extract_tags_from_tag_data(tag_data)
                        for nested_tag in nested_tags:
                            additional_tags_found.add(nested_tag)
                    else:
                        if "additional_tag_data" not in entry:
                            entry["additional_tag_data"] = []
                        entry["additional_tag_data"].append({
                            "tag": tag_with_braces,
                            "data": {}
                        })
                        tags_added_empty += 1
                
                # additional_tags_found 업데이트
                entry["additional_tags_found"] = list(additional_tags_found)
        
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
        텍스트에서 태그를 additional_tag_data에서 찾아서 대치합니다.
        중첩된 태그도 재귀적으로 처리합니다.
        
        지원 태그: tb, f, note, etc, img
        
        Args:
            text: 대치할 텍스트
            additional_tag_data: 태그 데이터 리스트
            max_depth: 최대 재귀 깊이 (무한 루프 방지)
        
        Returns:
            태그가 대치된 텍스트
        """
        if not text or not additional_tag_data or max_depth <= 0:
            return text
        
        # 태그 패턴 매칭: {tb_0000_0000}, {f_0000_0000}, {note_0000_0000}, {etc_0000_0000}, {img_0000_0000}
        tag_types = '|'.join(TagProcessor.TAG_TYPES)
        tag_pattern = rf'\{{({tag_types})_\d{{4}}_\d{{4}}\}}'
        
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
            qna_item: Q&A 데이터 (최상위 레벨에 question, answer, explanation, options 포함)
            additional_tag_data: 추가 태그 데이터 리스트
        
        Returns:
            태그가 대치된 Q&A 데이터
            
        Raises:
            ValueError: qna_data.description 구조가 전달된 경우
        """
        if not qna_item or not additional_tag_data:
            return qna_item
        
        # qna_data.description 구조는 지원하지 않음
        if 'qna_data' in qna_item and 'description' in qna_item.get('qna_data', {}):
            raise ValueError(
                "qna_data.description 구조는 지원되지 않습니다. "
                "최상위 레벨에 question, answer, explanation, options 필드를 사용하세요."
            )
        
        # question, answer, explanation 필드 처리
        for field in ['question', 'answer', 'explanation']:
            if field in qna_item and qna_item[field]:
                qna_item[field] = TagProcessor.replace_tags_in_text(
                    qna_item[field], additional_tag_data
                )
        
        # options 필드 처리
        if 'options' in qna_item and qna_item['options']:
            opts = qna_item['options']
            if isinstance(opts, list):
                qna_item['options'] = [
                    TagProcessor.replace_tags_in_text(opt, additional_tag_data)
                    for opt in opts
                ]
            else:
                qna_item['options'] = TagProcessor.replace_tags_in_text(
                    opts, additional_tag_data
                )
        
        return qna_item

