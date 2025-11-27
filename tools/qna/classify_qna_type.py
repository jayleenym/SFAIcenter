#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 타입 분류 모듈
- _extracted_qna.json 파일들을 읽어서 타입별로 분류하여 1_filter_with_tags에 저장
"""

import os
import logging
from typing import Dict, Any, Optional

# tools 모듈 import를 위한 경로 설정 (필요한 경우)
from .formatting import format_qna_item, should_include_qna_item
# QnATypeClassifier가 필요하다면 import (step3에서는 사용했지만, 여기서는 로직을 직접 구현하거나 import)
# step3에서는 qna.qna_processor.QnATypeClassifier를 사용했음.
from .qna_processor import QnATypeClassifier

class QnAClassifier:
    """Q&A 타입 분류 클래스"""
    
    def __init__(self, file_manager, json_handler, logger=None):
        self.file_manager = file_manager
        self.json_handler = json_handler
        self.logger = logger or logging.getLogger(__name__)

    def classify_and_save(self, cycle: Optional[int], onedrive_path: str, debug: bool = False) -> Dict[str, Any]:
        """
        추출된 Q&A 파일들을 읽어서 타입별로 분류 및 저장
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클)
            onedrive_path: OneDrive 경로
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            
        Returns:
            분류 결과 통계
        """
        workbook_base = os.path.join(onedrive_path, 'evaluation', 'workbook_data')
        
        # 대상 디렉토리 설정
        if cycle is None:
            extracted_dir = workbook_base
        else:
            cycle_path_name = self.file_manager.cycle_path.get(cycle)
            if not cycle_path_name:
                self.logger.warning(f"Cycle {cycle}에 해당하는 경로를 찾을 수 없습니다.")
                return {'success': False}
            
            # Lv2, Lv3_4가 직접 있는 경우 (cycle_path 없이)
            lv2_path = os.path.join(workbook_base, 'Lv2')
            lv3_4_path = os.path.join(workbook_base, 'Lv3_4')
            
            if os.path.exists(lv2_path) or os.path.exists(lv3_4_path):
                extracted_dir = workbook_base
            else:
                extracted_dir = os.path.join(workbook_base, cycle_path_name)
        
        output_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '1_filter_with_tags')
        os.makedirs(output_dir, exist_ok=True)
        
        # 모든 extracted_qna 파일 찾기
        extracted_files = []
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.endswith('_extracted_qna.json'):
                    extracted_files.append(os.path.join(root, file))
        
        self.logger.info(f"총 {len(extracted_files)}개의 extracted_qna 파일을 찾았습니다.")
        
        # 타입별로 분류
        classified_data = {
            'multiple-choice': [],
            'short-answer': [],
            'essay': [],
            'etc': []
        }
        
        for extracted_file in extracted_files:
            try:
                qna_data = self.json_handler.load(extracted_file)
                if not isinstance(qna_data, list):
                    continue
                
                for qna_item in qna_data:
                    qna_type = qna_item.get('qna_type', 'etc')
                    
                    # 문제에 {img_ 가 포함되어 있으면 etc로 분류
                    question = qna_item.get('question', '')
                    if '{img_' in question:
                        qna_type = 'etc'
                    
                    # 필터링 조건 확인
                    if not should_include_qna_item(qna_item, qna_type):
                        continue
                    
                    # 포맷화된 데이터 생성
                    formatted_item = format_qna_item(qna_item)
                    
                    if qna_type in classified_data:
                        classified_data[qna_type].append(formatted_item)
                    else:
                        classified_data['etc'].append(formatted_item)
                        
            except Exception as e:
                self.logger.error(f"파일 처리 오류 ({extracted_file}): {e}")
        
        # 타입별로 저장 (기존 파일이 있으면 병합)
        for qna_type, items in classified_data.items():
            if items:
                output_file = os.path.join(output_dir, f'{qna_type}.json')
                
                # debug 모드일 때만 기존 파일 로드해서 병합, 아니면 덮어쓰기
                existing_items = []
                if debug and os.path.exists(output_file):
                    try:
                        existing_items = self.json_handler.load(output_file)
                        if not isinstance(existing_items, list):
                            existing_items = []
                    except Exception as e:
                        self.logger.warning(f"{qna_type}: 기존 파일 로드 실패: {e}")
                        existing_items = []
                
                if debug and existing_items:
                    # 중복 제거: file_id와 tag 기준
                    existing_keys = set()
                    for item in existing_items:
                        file_id = item.get('file_id', '')
                        tag = item.get('tag', '')
                        existing_keys.add((file_id, tag))
                    
                    # 새 항목 중 중복이 아닌 것만 추가
                    new_items = []
                    for item in items:
                        file_id = item.get('file_id', '')
                        tag = item.get('tag', '')
                        key = (file_id, tag)
                        if key not in existing_keys:
                            new_items.append(item)
                            existing_keys.add(key)
                    
                    # 기존 항목과 새 항목 병합
                    merged_items = existing_items + new_items
                    self.logger.info(f"{qna_type}: 기존 파일과 병합 (기존 {len(existing_items)}개, 신규 {len(new_items)}개)")
                else:
                    merged_items = items
                    new_items = items
                
                self.json_handler.save(merged_items, output_file, backup=debug, logger=self.logger)
                
                self.logger.info(f"{qna_type}: 저장 완료 (총 {len(merged_items)}개, 신규 {len(new_items)}개)")
        
        return {
            'classified_data': {k: len(v) for k, v in classified_data.items()}
        }
