#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 타입 분류 모듈
- _extracted_qna.json 파일들을 읽어서 타입별로 분류하여 2_subdomain에 저장
- 중복 문제는 exam_question_lists.json 우선으로 하나만 선택하여 포함
"""

import os
import logging
from typing import Dict, Any, Optional, List

# tools 모듈 import를 위한 경로 설정 (필요한 경우)
from .formatting import format_qna_item, should_include_qna_item
from .duplicate_filter import DuplicateFilter

class QnAOrganizer:
    """Q&A 타입별 정리 클래스"""
    
    def __init__(self, file_manager, json_handler, logger=None):
        self.file_manager = file_manager
        self.json_handler = json_handler
        self.logger = logger or logging.getLogger(__name__)
        self._duplicate_filter = None  # lazy initialization

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
        
        output_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '2_subdomain')
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
                    
                    # 필터링 조건 확인 (img/etc 태그 포함 여부 및 타입별 조건 확인)
                    # formatting.should_include_qna_item에서 img/etc 태그가 포함된 문제는 자동으로 제외됨
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
        total_duplicates_removed = 0
        all_cross_file_duplicates = {}  # qna_type -> cross_file_duplicates
        
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
                
                # 중복 문제 필터링 (exam_question_lists.json 우선, 문제/정답/해설/선택지 기준)
                if self._duplicate_filter is None:
                    self._duplicate_filter = DuplicateFilter(
                        onedrive_path=onedrive_path, 
                        logger=self.logger
                    )
                filtered_items, duplicates_removed, cross_file_dups = self._duplicate_filter.filter_duplicates(
                    merged_items, track_duplicates=True
                )
                if duplicates_removed > 0:
                    self.logger.info(f"{qna_type}: 중복 문제 {duplicates_removed}개 제거됨 ({len(merged_items)}개 → {len(filtered_items)}개)")
                    total_duplicates_removed += duplicates_removed
                    all_cross_file_duplicates[qna_type] = cross_file_dups
                
                self.json_handler.save(filtered_items, output_file, backup=debug, logger=self.logger)
                
                self.logger.info(f"{qna_type}: 저장 완료 (총 {len(filtered_items)}개, 신규 {len(new_items)}개)")
        
        # Cross-file duplicates 리포트 생성
        if all_cross_file_duplicates:
            from tools.report import CrossFileDuplicatesReportGenerator
            report_path = os.path.join(workbook_base, 'CROSS_FILE_DUPLICATES.md')
            try:
                CrossFileDuplicatesReportGenerator.save_report(all_cross_file_duplicates, report_path)
                self.logger.info(f"Cross-file duplicates 리포트 저장: {report_path}")
            except Exception as e:
                self.logger.error(f"Cross-file duplicates 리포트 저장 실패: {e}")
        
        return {
            'classified_data': {k: len(v) for k, v in classified_data.items()},
            'duplicates_removed': total_duplicates_removed
        }
