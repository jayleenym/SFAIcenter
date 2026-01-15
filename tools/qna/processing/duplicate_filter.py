#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중복 문제 필터링 모듈
- 파일 간 중복(cross-file duplicates) 필터링
- exam_question_lists.json에 있는 문제 우선 선택
"""

import os
import json
import logging
from collections import defaultdict
from typing import Dict, Any, List, Set, Tuple, Optional


class DuplicateFilter:
    """중복 문제 필터링 클래스"""
    
    def __init__(self, onedrive_path: str = None, logger: logging.Logger = None):
        """
        Args:
            onedrive_path: OneDrive 경로 (exam_question_lists.json 로드용)
            logger: 로거
        """
        self.onedrive_path = onedrive_path
        self.logger = logger or logging.getLogger(__name__)
        self._preferred_questions: Set[Tuple[str, str]] = set()
        
        # 항상 preferred questions 로드 시도 (프로젝트 루트에서도 찾을 수 있음)
        self._load_preferred_questions()
    
    def _load_preferred_questions(self) -> None:
        """exam_question_lists.json에서 우선 선택할 문제 목록 로드"""
        # 여러 경로에서 exam_question_lists.json 탐색
        candidate_paths = []
        
        if self.onedrive_path:
            candidate_paths.append(os.path.join(
                self.onedrive_path, 
                'evaluation', 'eval_data', '4_multiple_exam', 
                'exam_question_lists.json'
            ))
        
        # 프로젝트 루트에서도 탐색 (현재 파일 기준)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        candidate_paths.append(os.path.join(
            project_root,
            'evaluation', 'eval_data', '4_multiple_exam',
            'exam_question_lists.json'
        ))
        
        exam_list_path = None
        for path in candidate_paths:
            if os.path.exists(path):
                exam_list_path = path
                break
        
        if exam_list_path is None:
            self.logger.warning(f"exam_question_lists.json 파일을 찾을 수 없음. 탐색 경로: {candidate_paths}")
            return
        
        try:
            with open(exam_list_path, 'r', encoding='utf-8') as f:
                exam_lists = json.load(f)
            
            # 모든 과목의 문제 ID를 수집
            for exam_name, questions in exam_lists.items():
                for q in questions:
                    file_id = q.get('file_id', '')
                    tag = q.get('tag', '')
                    if file_id and tag:
                        self._preferred_questions.add((file_id, tag))
            
            self.logger.info(f"exam_question_lists.json 로드 완료: {exam_list_path} ({len(self._preferred_questions)}개 문제)")
        except Exception as e:
            self.logger.warning(f"exam_question_lists.json 로드 실패: {e}")
    
    def get_content_key(self, qna_item: Dict[str, Any]) -> str:
        """
        문제/정답/해설/선택지를 조합한 중복 확인용 키 생성
        
        포맷화된 항목 (question, options 등이 최상위에 있음)과 
        원본 항목 (qna_data.description에 있음) 모두 지원
        """
        # 포맷화된 항목인지 확인 (format_qna_item으로 변환된 경우)
        if 'question' in qna_item and 'qna_data' not in qna_item:
            # 포맷화된 형식
            question = str(qna_item.get('question', '')).strip()
            answer = str(qna_item.get('answer', '')).strip()
            explanation = str(qna_item.get('explanation', '')).strip()
            options = qna_item.get('options', [])
        else:
            # 원본 형식
            qna_data = qna_item.get('qna_data', {})
            description = qna_data.get('description', {})
            
            question = str(description.get('question', '')).strip()
            answer = str(description.get('answer', '')).strip()
            explanation = str(description.get('explanation', '')).strip()
            options = description.get('options', [])
        
        options_str = '|'.join([str(opt).strip() for opt in options]) if options else ''
        return f"{question}|{answer}|{explanation}|{options_str}"
    
    def is_preferred(self, qna_item: Dict[str, Any]) -> bool:
        """해당 문제가 exam_question_lists.json에 있는지 확인"""
        file_id = qna_item.get('file_id', '')
        tag = qna_item.get('tag', '')
        return (file_id, tag) in self._preferred_questions
    
    def filter_duplicates(self, qna_items: List[Dict[str, Any]], 
                          track_duplicates: bool = False) -> Tuple[List[Dict[str, Any]], int, Dict]:
        """
        중복 문제를 필터링하여 그룹당 하나만 남김
        
        선택 우선순위:
        1. exam_question_lists.json에 있는 문제
        2. 그 외의 경우 첫 번째 항목
        
        Args:
            qna_items: QnA 항목 리스트
            track_duplicates: 중복 상세 정보 추적 여부
            
        Returns:
            (필터링된 리스트, 제거된 중복 수, 중복 그룹 상세정보)
        """
        # 1단계: content_key 기준으로 그룹화
        content_groups = defaultdict(list)  # content_key -> list of items
        
        for item in qna_items:
            content_key = self.get_content_key(item)
            content_groups[content_key].append(item)
        
        # 2단계: 각 그룹에서 하나만 선택 (우선순위 적용)
        filtered_items = []
        removed_count = 0
        cross_file_duplicates = {}  # content_key -> [file_id_tag, ...]
        
        for content_key, items in content_groups.items():
            if len(items) == 1:
                # 중복 없음
                filtered_items.append(items[0])
            else:
                # 중복 있음 - 우선순위에 따라 선택
                selected_item = None
                
                # 1순위: exam_question_lists.json에 있는 문제 찾기
                for item in items:
                    if self.is_preferred(item):
                        selected_item = item
                        break
                
                # 2순위: 없으면 첫 번째 항목 선택
                if selected_item is None:
                    selected_item = items[0]
                
                filtered_items.append(selected_item)
                removed_count += len(items) - 1
                
                # 중복 그룹 정보 기록
                if track_duplicates:
                    selected_key = f"{selected_item.get('file_id', '')}_{selected_item.get('tag', '')}"
                    all_keys = [f"{item.get('file_id', '')}_{item.get('tag', '')}" for item in items]
                    
                    # 선택된 항목을 맨 앞으로
                    all_keys.remove(selected_key)
                    all_keys.insert(0, selected_key)
                    
                    cross_file_duplicates[content_key] = all_keys
        
        return filtered_items, removed_count, cross_file_duplicates


def create_duplicate_filter(onedrive_path: str = None, 
                            logger: logging.Logger = None) -> DuplicateFilter:
    """
    DuplicateFilter 인스턴스 생성 헬퍼 함수
    
    Args:
        onedrive_path: OneDrive 경로
        logger: 로거
        
    Returns:
        DuplicateFilter 인스턴스
    """
    return DuplicateFilter(onedrive_path=onedrive_path, logger=logger)

