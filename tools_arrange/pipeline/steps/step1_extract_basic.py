#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1단계: 기본 문제 추출
"""

import os
from typing import List, Dict, Any
from ..base import PipelineBase
from qna.qna_processor import QnAExtractor


class Step1ExtractBasic(PipelineBase):
    """1단계: 기본 문제 추출"""
    
    def execute(self, cycle: int, levels: List[str] = None) -> Dict[str, Any]:
        """
        1단계: 문제 추출 (Lv2, Lv3_4)
        - 문제/선지/정답/해설 추출 및 포맷화
        """
        self.logger.info(f"=== 1단계: 문제 추출 (Cycle {cycle}) ===")
        
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

