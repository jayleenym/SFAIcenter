#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류
"""

import os
import sys
import re
from typing import List, Dict, Any, Optional
from ..base import PipelineBase
from qna.qna_processor import QnAExtractor

# 포맷화 유틸리티 import
current_dir = os.path.dirname(os.path.abspath(__file__))
# tools 모듈 import를 위한 경로 설정
_temp_tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)
from qna.formatting import format_qna_item, should_include_qna_item


class Step2ExtractFull(PipelineBase):
    """2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: Optional[int] = None, levels: List[str] = None) -> Dict[str, Any]:
        """
        2단계: 전체 문제 추출 (Lv3, Lv3_4, Lv5) + Q&A 타입별 분류
        - 태그들을 재귀로 돌면서 전체 대치 시키고 ~_extracted_qna.json으로 저장
        - qtype별로 나눠서 임시로 2_subdomain에 저장 후 삭제
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클의 파일을 자동으로 찾아서 처리)
            levels: 처리할 레벨 목록 (None이면 ['Lv2', 'Lv3_4', 'Lv5'])
        """
        if cycle is None:
            self.logger.info("=== 2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류 (모든 사이클) ===")
        else:
            self.logger.info(f"=== 2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류 (Cycle {cycle}) ===")
        
        # 로깅 설정
        self._setup_step_logging('extract_full', 2)
        
        try:
            if levels is None:
                levels = ['Lv2', 'Lv3_4', 'Lv5']
            
            data_path = self.file_manager.final_data_path
            extractor = QnAExtractor(self.file_manager)
            total_extracted = 0
            processed_files = 0
            
            # cycle이 None이면 final_data_path에서 모든 사이클의 원본 파일 찾기
            if cycle is None:
                workbook_base = os.path.join(self.onedrive_path, 'evaluation', 'workbook_data')
                
                # 모든 사이클의 레벨 경로 찾기 (final_data_path에서)
                for level in levels:
                    # final_data_path에서 모든 사이클 디렉토리 찾기
                    if os.path.exists(data_path):
                        for cycle_dir in os.listdir(data_path):
                            cycle_dir_path = os.path.join(data_path, cycle_dir)
                            if not os.path.isdir(cycle_dir_path):
                                continue
                            
                            # cycle_path 형식인지 확인 (1C, 2C, 3C 등)
                            if cycle_dir not in self.file_manager.cycle_path.values():
                                continue
                            
                            level_path = os.path.join(cycle_dir_path, level)
                            if not os.path.exists(level_path):
                                continue
                            
                            # 출력 경로는 workbook_data의 해당 사이클 디렉토리
                            output_path = os.path.join(workbook_base, cycle_dir, level)
                            os.makedirs(output_path, exist_ok=True)
                            
                            # 직접 JSON 파일 찾기 (SS0000.json 형식만)
                            json_files = []
                            for root, _, files in os.walk(level_path):
                                for f in files:
                                    # ss로 시작하고 4자리 숫자 + .json 형식만 찾기
                                    if re.match(r'^SS\d{4}\.json$', f, re.IGNORECASE):
                                        json_files.append(os.path.join(root, f))
                            
                            json_files = sorted(json_files)
                            self.logger.info(f"{cycle_dir}/{level}: 총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
                            
                            for json_file in json_files:
                                try:
                                    file_name = os.path.splitext(os.path.basename(json_file))[0]
                                    file_output_path = os.path.join(output_path, f"{file_name}.json")
                                    
                                    # Q&A 추출
                                    result = extractor.extract_from_file(json_file, file_output_path)
                                    
                                    # 태그 대치는 exam 생성 시점에 수행 (additional_tag_data는 유지)
                                    
                                    # 저장 (덮어쓰기)
                                    qna_output_path = file_output_path.replace('.json', '_extracted_qna.json')
                                    
                                    # 내용이 비어있으면 저장하지 않음
                                    if not result['extracted_qna']:
                                        self.logger.warning(f"추출된 Q&A가 없어 파일을 저장하지 않습니다: {qna_output_path}")
                                        continue
                                    
                                    # 중복 체크 없이 덮어쓰기
                                    self.json_handler.save(result['extracted_qna'], qna_output_path)
                                    self.logger.info(f"추출된 Q&A {len(result['extracted_qna'])}개 저장: {qna_output_path}")
                                    
                                    total_extracted += len(result['extracted_qna'])
                                    processed_files += 1
                                    
                                    self.logger.info(f"추출된 Q&A: {len(result['extracted_qna'])}개")
                                    
                                except Exception as e:
                                    self.logger.error(f"파일 처리 오류 ({json_file}): {e}")
                
                # extracted_dir는 workbook_base 전체
                extracted_dir = workbook_base
            else:
                # 기존 로직 (cycle이 지정된 경우)
                cycle_path = os.path.join(data_path, self.file_manager.cycle_path[cycle])
                
                # cycle이 있을 때는 항상 cycle_path를 포함해서 저장
                output_base = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'workbook_data', self.file_manager.cycle_path[cycle]
                )
                
                for level in levels:
                    level_path = os.path.join(cycle_path, level)
                    if not os.path.exists(level_path):
                        self.logger.warning(f"경로가 존재하지 않습니다: {level_path}")
                        continue
                    
                    output_path = os.path.join(output_base, level)
                    os.makedirs(output_path, exist_ok=True)
                    
                    # SS0000.json 형식만 필터링
                    all_json_files = self.file_manager.get_json_file_list(cycle, level_path)
                    json_files = [
                        f for f in all_json_files
                        if re.match(r'^SS\d{4}\.json$', os.path.basename(f), re.IGNORECASE)
                    ]
                    self.logger.info(f"{level}: 총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
                    
                    for json_file in json_files:
                        try:
                            file_name = os.path.splitext(os.path.basename(json_file))[0]
                            file_output_path = os.path.join(output_path, f"{file_name}.json")
                            
                            # Q&A 추출
                            result = extractor.extract_from_file(json_file, file_output_path)
                            
                            # 태그 대치는 exam 생성 시점에 수행 (additional_tag_data는 유지)
                            
                            # 저장 (덮어쓰기)
                            qna_output_path = file_output_path.replace('.json', '_extracted_qna.json')
                            
                            # 내용이 비어있으면 저장하지 않음
                            if not result['extracted_qna']:
                                self.logger.warning(f"추출된 Q&A가 없어 파일을 저장하지 않습니다: {qna_output_path}")
                                continue
                            
                            # 중복 체크 없이 덮어쓰기
                            self.json_handler.save(result['extracted_qna'], qna_output_path)
                            self.logger.info(f"추출된 Q&A {len(result['extracted_qna'])}개 저장: {qna_output_path}")
                            
                            total_extracted += len(result['extracted_qna'])
                            processed_files += 1
                            
                            self.logger.info(f"추출된 Q&A: {len(result['extracted_qna'])}개")
                            
                        except Exception as e:
                            self.logger.error(f"파일 처리 오류 ({json_file}): {e}")
                
                # extracted_dir 설정 (cycle이 지정된 경우)
                workbook_base = os.path.join(self.onedrive_path, 'evaluation', 'workbook_data')
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
            
            self.logger.info(f"추출 완료: {processed_files}개 파일, {total_extracted}개 Q&A 추출")
            
            # Q&A 타입별 분류 및 임시 저장
            self.logger.info("=== Q&A 타입별 분류 시작 ===")
            
            # 임시 저장 디렉토리 (2_subdomain)
            temp_output_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '2_subdomain'
            )
            os.makedirs(temp_output_dir, exist_ok=True)
            
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
                    
                    for qna_item in qna_data:
                        qna_type = qna_item.get('qna_type', 'etc')
                        
                        # 필터링 조건 확인 (img/etc 태그가 있는 문제 제외)
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
            
            # 타입별로 임시 파일 저장 후 삭제 (2_subdomain)
            temp_files = []
            for qna_type, items in classified_data.items():
                if items:
                    temp_file = os.path.join(temp_output_dir, f'{qna_type}.json')
                    self.json_handler.save(items, temp_file)
                    temp_files.append(temp_file)
                    self.logger.info(f"{qna_type}: {len(items)}개 항목을 임시 파일에 저장: {temp_file}")
            
            # 임시 파일 삭제
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    self.logger.info(f"임시 파일 삭제: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"임시 파일 삭제 실패 ({temp_file}): {e}")
            
            self.logger.info("Q&A 타입별 분류 및 정리 완료")
            
            return {
                'success': True,
                'processed_files': processed_files,
                'total_extracted': total_extracted,
                'classified_data': {k: len(v) for k, v in classified_data.items()}
            }
        finally:
            self._remove_step_logging()
    

