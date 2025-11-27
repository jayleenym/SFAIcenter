#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 추출 모듈
- 원본 JSON 파일에서 Q&A 추출하여 _extracted_qna.json 생성
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional

# tools 모듈 import를 위한 경로 설정 (필요한 경우)
# 이 파일이 tools/qna/ 에 위치하므로 상위 디렉토리 접근 가능해야 함

from .qna_processor import QnAExtractor

class QnAMaker:
    """Q&A 추출 및 저장 클래스"""
    
    def __init__(self, file_manager, json_handler, logger=None):
        self.file_manager = file_manager
        self.json_handler = json_handler
        self.logger = logger or logging.getLogger(__name__)
        self.extractor = QnAExtractor(self.file_manager)

    def process_cycle(self, cycle: Optional[int], levels: List[str], onedrive_path: str) -> Dict[str, Any]:
        """
        지정된 사이클과 레벨의 파일들에서 Q&A 추출
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클)
            levels: 처리할 레벨 목록
            onedrive_path: OneDrive 경로
            
        Returns:
            처리 결과 통계
        """
        data_path = self.file_manager.final_data_path
        total_extracted = 0
        processed_files = 0
        
        workbook_base = os.path.join(onedrive_path, 'evaluation', 'workbook_data')
        
        # 처리할 대상 디렉토리 목록 수집
        target_dirs = []
        
        if cycle is None:
            # 모든 사이클 처리
            if os.path.exists(data_path):
                for cycle_dir in os.listdir(data_path):
                    cycle_dir_path = os.path.join(data_path, cycle_dir)
                    if not os.path.isdir(cycle_dir_path):
                        continue
                    
                    # cycle_path 형식인지 확인 (1C, 2C, 3C 등)
                    if cycle_dir not in self.file_manager.cycle_path.values():
                        continue
                    
                    for level in levels:
                        level_path = os.path.join(cycle_dir_path, level)
                        if os.path.exists(level_path):
                            output_path = os.path.join(workbook_base, cycle_dir, level)
                            target_dirs.append((level_path, output_path))
        else:
            # 특정 사이클 처리
            cycle_path_name = self.file_manager.cycle_path.get(cycle)
            if cycle_path_name:
                cycle_dir_path = os.path.join(data_path, cycle_path_name)
                for level in levels:
                    level_path = os.path.join(cycle_dir_path, level)
                    if os.path.exists(level_path):
                        output_path = os.path.join(workbook_base, cycle_path_name, level)
                        target_dirs.append((level_path, output_path))
            else:
                self.logger.warning(f"Cycle {cycle}에 해당하는 경로를 찾을 수 없습니다.")

        # 수집된 디렉토리 처리
        for level_path, output_path in target_dirs:
            os.makedirs(output_path, exist_ok=True)
            
            # JSON 파일 찾기 (SS0000.json 형식)
            json_files = []
            for root, _, files in os.walk(level_path):
                for f in files:
                    if re.match(r'^SS\d{4}\.json$', f, re.IGNORECASE):
                        json_files.append(os.path.join(root, f))
            
            json_files = sorted(json_files)
            self.logger.info(f"경로 {level_path}: {len(json_files)}개 파일 발견")
            
            for json_file in json_files:
                try:
                    file_name = os.path.splitext(os.path.basename(json_file))[0]
                    file_output_path = os.path.join(output_path, f"{file_name}.json")
                    
                    # Q&A 추출
                    result = self.extractor.extract_from_file(json_file, file_output_path)
                    
                    # 저장 (덮어쓰기)
                    qna_output_path = file_output_path.replace('.json', '_extracted_qna.json')
                    
                    if not result['extracted_qna']:
                        self.logger.warning(f"추출된 Q&A 없음: {qna_output_path}")
                        continue
                    
                    self.json_handler.save(result['extracted_qna'], qna_output_path)
                    
                    count = len(result['extracted_qna'])
                    total_extracted += count
                    processed_files += 1
                    
                    self.logger.info(f"추출 완료 ({count}개): {qna_output_path}")
                    
                except Exception as e:
                    self.logger.error(f"파일 처리 오류 ({json_file}): {e}")
        
        return {
            'processed_files': processed_files,
            'total_extracted': total_extracted
        }
