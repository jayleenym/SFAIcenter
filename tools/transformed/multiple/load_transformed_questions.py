#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
변형된 문제 로드 유틸리티
- pick_right, pick_wrong, pick_abcd의 result.json 파일들을 로드
"""

import os
from typing import Dict, Any
from tools.core.utils import JSONHandler


def load_transformed_questions(onedrive_path: str, json_handler: JSONHandler, logger) -> Dict[str, Dict[str, Any]]:
    """
    pick_right, pick_wrong, pick_abcd의 result.json 파일들을 모두 로드하여
    question_id를 키로 하는 딕셔너리로 반환
    각 항목에 transform_type과 set_num 정보도 포함
    
    Args:
        onedrive_path: OneDrive 경로
        json_handler: JSONHandler 인스턴스
        logger: 로거 인스턴스
    
    Returns:
        변형된 문제 딕셔너리
    """
    transformed = {
        'pick_right': {},
        'pick_wrong': {},
        'pick_abcd': {}
    }
    
    def create_question_id(file_id: str, tag: str) -> str:
        """question_id 생성 (file_id_tag 형식)"""
        return f"{file_id}_{tag}"
    
    # pick_abcd는 루트에 result.json이 있음
    abcd_path = os.path.join(
        onedrive_path,
        'evaluation', 'eval_data', '7_multiple_rw', 'pick_abcd', 'result.json'
    )
    if os.path.exists(abcd_path):
        abcd_data = json_handler.load(abcd_path)
        if not isinstance(abcd_data, list):
            abcd_data = []
        logger.info(f"pick_abcd: {len(abcd_data)}개 문제 로드")
        for item in abcd_data:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            if file_id and tag:
                question_id = create_question_id(file_id, tag)
                # 세트 정보 추가 (pick_abcd는 세트 정보 없음)
                item_with_meta = item.copy()
                item_with_meta['_transform_type'] = 'pick_abcd'
                item_with_meta['_set_num'] = None
                transformed['pick_abcd'][question_id] = item_with_meta
    
    # pick_right와 pick_wrong은 여러 세트 폴더에 있음 (2, 3, 4, 5)
    for transform_type in ['pick_right', 'pick_wrong']:
        transform_dir = os.path.join(
            onedrive_path,
            'evaluation', 'eval_data', '7_multiple_rw', transform_type
        )
        if not os.path.exists(transform_dir):
            logger.warning(f"디렉토리를 찾을 수 없습니다: {transform_dir}")
            continue
        
        # 각 세트 폴더 확인 (2, 3, 4, 5)
        for set_num in [2, 3, 4, 5]:
            result_path = os.path.join(transform_dir, str(set_num), 'result.json')
            if os.path.exists(result_path):
                data = json_handler.load(result_path)
                if not isinstance(data, list):
                    data = []
                logger.info(f"{transform_type}/{set_num}: {len(data)}개 문제 로드")
                for item in data:
                    # question_id가 있으면 사용, 없으면 file_id와 tag로 생성
                    question_id = item.get('question_id', '')
                    if not question_id:
                        # file_id와 tag로 question_id 생성
                        file_id = item.get('file_id', '')
                        tag = item.get('tag', '')
                        if file_id and tag:
                            question_id = create_question_id(file_id, tag)
                    
                    if question_id:
                        # 세트 정보 추가
                        item_with_meta = item.copy()
                        item_with_meta['_transform_type'] = transform_type
                        item_with_meta['_set_num'] = set_num
                        # 이미 있으면 덮어쓰기 (나중 세트가 우선)
                        transformed[transform_type][question_id] = item_with_meta
    
    return transformed

