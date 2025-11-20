#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계: Q&A 타입별 분류
"""

import os
import logging
from typing import Dict, Any, Optional
from ..base import PipelineBase
from ..config import SFAICENTER_PATH
from core.logger import setup_step_logger
from qna.qna_processor import QnATypeClassifier


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
        self._setup_step_logging('classify')
        
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
                        
                        # workbook_groupby_qtype.py와 동일한 필터링 로직 적용
                        qna_data_desc = qna_item.get('qna_data', {}).get('description', {})
                        options = qna_data_desc.get('options', [])
                        answer = qna_data_desc.get('answer', '')
                        
                        # 각 타입별 필터링 조건 확인
                        should_include = False
                        if qna_type == "multiple-choice":
                            # 객관식: OX 문제 제외, 선지가 3개 이상인 경우
                            if (options is not None) and (len(options) > 2):
                                should_include = True
                        elif qna_type == "short-answer":
                            # 단답형: 답변이 있고, 답변이 삭제되지 않은 경우
                            if (answer is not None) and (answer != "삭제"):
                                should_include = True
                        elif qna_type == "essay":
                            # 서술형: 답변이 있는 경우
                            if answer is not None:
                                should_include = True
                        elif qna_type == "etc":
                            # etc 타입은 모두 포함
                            should_include = True
                        
                        # 조건을 만족하지 않으면 건너뛰기
                        if not should_include:
                            continue
                        
                        # 포맷화된 데이터 생성
                        formatted_item = {
                            'file_id': qna_item.get('file_id'),
                            'tag': qna_item.get('qna_data', {}).get('tag', ''),
                            'title': qna_item.get('title'),
                            'cat1_domain': qna_item.get('cat1_domain'),
                            'cat2_sub': qna_item.get('cat2_sub'),
                            'cat3_specific': qna_item.get('cat3_specific'),
                            'chapter': qna_item.get('chapter'),
                            'page': qna_item.get('page'),
                            'qna_type': qna_type,
                            'question': qna_data_desc.get('question', ''),
                            'options': options,
                            'answer': answer,
                            'explanation': qna_data_desc.get('explanation', '')
                        }
                        
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
    
    def _setup_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 설정"""
        step_logger, file_handler = setup_step_logger(
            step_name=step_name,
            step_number=3
        )
        # 기존 로거에 핸들러 추가
        self.logger.addHandler(file_handler)
        self._step_log_handler = file_handler
    
    def _remove_step_logging(self):
        """단계별 로그 파일 핸들러 제거"""
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
            self._step_log_handler.close()
            self._step_log_handler = None

