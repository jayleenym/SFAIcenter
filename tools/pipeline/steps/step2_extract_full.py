#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 전체 문제 추출 (태그 대치 포함)
"""

import os
import logging
from typing import List, Dict, Any
from ..base import PipelineBase
from ..config import SFAICENTER_PATH
from qna.qna_processor import QnAExtractor, TagProcessor


class Step2ExtractFull(PipelineBase):
    """2단계: 전체 문제 추출 (태그 대치 포함)"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: int, levels: List[str] = None) -> Dict[str, Any]:
        """
        2단계: 전체 문제 추출 (Lv3, Lv3_4, Lv5)
        - 태그들을 재귀로 돌면서 전체 대치 시키고 ~_extracted_qna.json으로 저장
        """
        self.logger.info(f"=== 2단계: 전체 문제 추출 (태그 대치 포함) (Cycle {cycle}) ===")
        
        # 로깅 설정
        self._setup_step_logging('extract_full')
        
        try:
            if levels is None:
                levels = ['Lv3', 'Lv3_4', 'Lv5']
            
            data_path = self.file_manager.final_data_path
            cycle_path = os.path.join(data_path, self.file_manager.cycle_path[cycle])
            
            output_base = os.path.join(
                self.onedrive_path,
                f'evaluation/workbook_data/{self.file_manager.cycle_path[cycle]}'
            )
            
            extractor = QnAExtractor(self.file_manager)
            tag_processor = TagProcessor()
            total_extracted = 0
            processed_files = 0
            
            for level in levels:
                level_path = os.path.join(cycle_path, level)
                if not os.path.exists(level_path):
                    self.logger.warning(f"경로가 존재하지 않습니다: {level_path}")
                    continue
                
                output_path = os.path.join(output_base, level)
                os.makedirs(output_path, exist_ok=True)
                
                json_files = self.file_manager.get_json_file_list(cycle, level_path)
                self.logger.info(f"{level}: 총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
                
                for json_file in json_files:
                    try:
                        file_name = os.path.splitext(os.path.basename(json_file))[0]
                        file_output_path = os.path.join(output_path, f"{file_name}.json")
                        
                        # Q&A 추출
                        result = extractor.extract_from_file(json_file, file_output_path)
                        
                        # 태그 대치 처리
                        for qna_item in result['extracted_qna']:
                            additional_tag_data = qna_item.get('additional_tag_data', [])
                            if additional_tag_data:
                                # 태그 대치
                                qna_item = tag_processor.replace_tags_in_qna_data(qna_item, additional_tag_data)
                        
                        # 저장
                        qna_output_path = file_output_path.replace('.json', '_extracted_qna.json')
                        self.json_handler.save(result['extracted_qna'], qna_output_path)
                        
                        total_extracted += len(result['extracted_qna'])
                        processed_files += 1
                        
                        self.logger.info(f"추출된 Q&A: {len(result['extracted_qna'])}개")
                        
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
        log_dir = os.path.join(SFAICENTER_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'step2_{step_name}.log')
        
        # 파일 핸들러 생성 (append 모드)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # 로거에 핸들러 추가
        self.logger.addHandler(file_handler)
        self._step_log_handler = file_handler
        
        self.logger.info(f"로그 파일 생성/추가: {log_file}")
    
    def _remove_step_logging(self):
        """단계별 로그 파일 핸들러 제거"""
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
            self._step_log_handler.close()
            self._step_log_handler = None

