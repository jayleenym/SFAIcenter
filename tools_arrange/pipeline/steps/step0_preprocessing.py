#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
0단계: 텍스트 전처리
"""

import os
from typing import List, Dict, Any
from ..base import PipelineBase


class Step0Preprocessing(PipelineBase):
    """0단계: 텍스트 전처리"""
    
    def execute(self, cycle: int, levels: List[str] = None) -> Dict[str, Any]:
        """
        0단계: 텍스트 전처리 (Lv2 폴더)
        - 문장내 엔터 제거
        - 빈 챕터정보 채우기
        - 문단 병합(안함)
        - 선지 텍스트 정규화
        """
        self.logger.info(f"=== 0단계: 텍스트 전처리 (Cycle {cycle}) ===")
        
        if levels is None:
            levels = ['Lv2']
        
        data_path = self.file_manager.final_data_path
        cycle_path = os.path.join(data_path, self.file_manager.cycle_path[cycle])
        
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
                    json_data = self.json_handler.load(json_file)
                    
                    # 텍스트 전처리
                    json_data = self.text_processor.fill_missing_chapters(json_data)
                    
                    # 선지 텍스트 정규화
                    for page_data in json_data.get('contents', []):
                        for add_item in page_data.get('add_info', []):
                            if 'description' in add_item and 'options' in add_item['description']:
                                options = add_item['description']['options']
                                if isinstance(options, list):
                                    normalized_options = []
                                    for option in options:
                                        normalized = self.text_processor.remove_inline_newlines(str(option))
                                        normalized = self.text_processor.normalize_option_text(normalized)
                                        normalized_options.append(normalized)
                                    add_item['description']['options'] = normalized_options
                    
                    # 저장
                    self.json_handler.save(json_data, json_file)
                    processed_files += 1
                    
                except Exception as e:
                    self.logger.error(f"파일 처리 오류 ({json_file}): {e}")
        
        self.logger.info(f"처리 완료: {processed_files}개 파일")
        return {'success': True, 'processed_files': processed_files}

