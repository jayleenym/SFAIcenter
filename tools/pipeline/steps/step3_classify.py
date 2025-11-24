#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계: Q&A 타입별 분류
"""

import os
import sys
from typing import Dict, Any, Optional
from ..base import PipelineBase
from qna.qna_processor import QnATypeClassifier

# 포맷화 유틸리티 import
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, tools_dir)
from qna.formatting import format_qna_item, should_include_qna_item


class Step3Classify(PipelineBase):
    """3단계: Q&A 타입별 분류"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: Optional[int] = None) -> Dict[str, Any]:
        """
        3단계: qna_type별 분류
        - multiple/short/essay/etc로 분류 및 필터링
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클의 파일을 자동으로 찾아서 처리)
        """
        if cycle is None:
            self.logger.info("=== 3단계: Q&A 타입별 분류 (모든 사이클) ===")
        else:
            self.logger.info(f"=== 3단계: Q&A 타입별 분류 (Cycle {cycle}) ===")
        
        # 로깅 설정
        self._setup_step_logging('classify', 3)
        
        try:
            workbook_base = os.path.join(self.onedrive_path, 'evaluation', 'workbook_data')
            
            # cycle이 None이면 workbook_data 전체에서 모든 파일 찾기
            if cycle is None:
                extracted_dir = workbook_base
                self.logger.info(f"모든 사이클의 파일을 찾습니다: {extracted_dir}")
            else:
                # Lv2, Lv3_4만 있는 경우를 확인
                lv2_path = os.path.join(workbook_base, 'Lv2')
                lv3_4_path = os.path.join(workbook_base, 'Lv3_4')
                
                # Lv2, Lv3_4가 직접 있는 경우 (cycle_path 없이)
                if os.path.exists(lv2_path) or os.path.exists(lv3_4_path):
                    extracted_dir = workbook_base
                else:
                    # 기존 방식 (cycle_path 포함)
                    extracted_dir = os.path.join(
                        self.onedrive_path,
                        'evaluation', 'workbook_data', self.file_manager.cycle_path[cycle]
                    )
            
            output_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '1_filter_with_tags'
            )
            os.makedirs(output_dir, exist_ok=True)
            
            # 모든 extracted_qna 파일 찾기
            extracted_files = []
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    if file.endswith('_extracted_qna.json'):
                        extracted_files.append(os.path.join(root, file))
            
            self.logger.info(f"총 {len(extracted_files)}개의 extracted_qna 파일을 찾았습니다.")
            
            # 타입별로 분류
            type_classifier = QnATypeClassifier()
            classified_data = {
                'multiple-choice': [],
                'short-answer': [],
                'essay': [],
                'etc': []
            }
            
            for extracted_file in extracted_files:
                try:
                    qna_data = self.json_handler.load(extracted_file)
                    
                    for qna_item in qna_data:
                        qna_type = qna_item.get('qna_type', 'etc')
                        
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
                    
                    # 기존 파일이 있으면 로드해서 병합
                    existing_items = []
                    if os.path.exists(output_file):
                        try:
                            existing_items = self.json_handler.load(output_file)
                            if not isinstance(existing_items, list):
                                existing_items = []
                            self.logger.info(f"{qna_type}: 기존 파일 발견: {len(existing_items)}개 항목 로드")
                        except Exception as e:
                            self.logger.warning(f"{qna_type}: 기존 파일 로드 실패: {e}")
                            existing_items = []
                    
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
                    self.json_handler.save(merged_items, output_file)
                    
                    if new_items:
                        self.logger.info(f"{qna_type}: 새 항목 {len(new_items)}개 추가 (기존 {len(existing_items)}개 + 새 {len(new_items)}개 = 총 {len(merged_items)}개)")
                    else:
                        self.logger.info(f"{qna_type}: 중복 항목으로 인해 새 항목 없음 (기존 {len(existing_items)}개 유지)")
            
            self.logger.info("Q&A 타입별 분류 완료")
            return {
                'success': True,
                'classified_data': {k: len(v) for k, v in classified_data.items()}
            }
        finally:
            self._remove_step_logging()
    

