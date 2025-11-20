#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1단계: 기본 문제 추출
"""

import os
import logging
from typing import List, Dict, Any
from ..base import PipelineBase
from ..config import SFAICENTER_PATH
from core.logger import setup_step_logger
from qna.qna_processor import QnAExtractor


class Step1ExtractBasic(PipelineBase):
    """1단계: 기본 문제 추출"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: int, levels: List[str] = None) -> Dict[str, Any]:
        """
        1단계: 문제 추출 (Lv2, Lv3_4)
        - 문제/선지/정답/해설 추출 및 포맷화
        """
        self.logger.info(f"=== 1단계: 문제 추출 (Cycle {cycle}) ===")
        
        # 로깅 설정
        self._setup_step_logging('extract_basic')
        
        try:
            if levels is None:
                levels = ['Lv2', 'Lv3_4']
            
            data_path = self.file_manager.final_data_path
            cycle_path = os.path.join(data_path, self.file_manager.cycle_path[cycle])
            
            extractor = QnAExtractor(self.file_manager)
            total_extracted = 0
            processed_files = 0
            
            for level in levels:
                level_path = os.path.join(cycle_path, level)
                if not os.path.exists(level_path):
                    self.logger.warning(f"경로가 존재하지 않습니다: {level_path}")
                    continue
                
                json_files = self.file_manager.get_json_file_list(cycle, level_path)
                self.logger.info(f"{level}: 총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
                
                for json_file in json_files:
                    try:
                        result = extractor.extract_from_file(json_file, None)
                        total_extracted += len(result['extracted_qna'])
                        processed_files += 1
                    except Exception as e:
                        self.logger.error(f"파일 처리 오류 ({json_file}): {e}")
            
            self.logger.info(f"처리 완료: {processed_files}개 파일, {total_extracted}개 Q&A 추출")
            return {
                'success': True,
                'processed_files': processed_files,
                'total_extracted': total_extracted
            }
        finally:
            self._remove_step_logging()
    
    def _setup_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 설정"""
        step_logger, file_handler = setup_step_logger(
            step_name=step_name,
            step_number=1
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

