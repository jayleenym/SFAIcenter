#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류
"""

import os
import logging
from typing import List, Dict, Any
from ..base import PipelineBase
from ..config import SFAICENTER_PATH
from qna.qna_processor import QnAExtractor, TagProcessor


class Step2ExtractFull(PipelineBase):
    """2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: int, levels: List[str] = None) -> Dict[str, Any]:
        """
        2단계: 전체 문제 추출 (Lv3, Lv3_4, Lv5) + Q&A 타입별 분류
        - 태그들을 재귀로 돌면서 전체 대치 시키고 ~_extracted_qna.json으로 저장
        - qtype별로 나눠서 임시로 2_subdomain에 저장
        - classified_ALL.json 생성 후 임시 파일 삭제
        """
        self.logger.info(f"=== 2단계: 전체 문제 추출 (태그 대치 포함) + Q&A 타입별 분류 (Cycle {cycle}) ===")
        
        # 로깅 설정
        self._setup_step_logging('extract_full')
        
        try:
            if levels is None:
                levels = ['Lv2', 'Lv3_4', 'Lv5']
            
            data_path = self.file_manager.final_data_path
            cycle_path = os.path.join(data_path, self.file_manager.cycle_path[cycle])
            
            # cycle이 있을 때는 항상 cycle_path를 포함해서 저장
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
            
            self.logger.info(f"추출 완료: {processed_files}개 파일, {total_extracted}개 Q&A 추출")
            
            # Q&A 타입별 분류 및 임시 저장
            self.logger.info("=== Q&A 타입별 분류 시작 ===")
            
            # Lv2, Lv3_4만 있는 경우를 확인
            workbook_base = os.path.join(self.onedrive_path, 'evaluation/workbook_data')
            lv2_path = os.path.join(workbook_base, 'Lv2')
            lv3_4_path = os.path.join(workbook_base, 'Lv3_4')
            
            # Lv2, Lv3_4가 직접 있는 경우 (cycle_path 없이)
            if os.path.exists(lv2_path) or os.path.exists(lv3_4_path):
                extracted_dir = workbook_base
            else:
                # 기존 방식 (cycle_path 포함)
                extracted_dir = os.path.join(
                    self.onedrive_path,
                    f'evaluation/workbook_data/{self.file_manager.cycle_path[cycle]}'
                )
            
            # 임시 저장 디렉토리 (2_subdomain)
            temp_output_dir = os.path.join(
                self.onedrive_path,
                f'evaluation/eval_data/2_subdomain'
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
                            'question': qna_item.get('qna_data', {}).get('description', {}).get('question', ''),
                            'options': qna_item.get('qna_data', {}).get('description', {}).get('options', []),
                            'answer': qna_item.get('qna_data', {}).get('description', {}).get('answer', ''),
                            'explanation': qna_item.get('qna_data', {}).get('description', {}).get('explanation', '')
                        }
                        
                        if qna_type in classified_data:
                            classified_data[qna_type].append(formatted_item)
                        else:
                            classified_data['etc'].append(formatted_item)
                            
                except Exception as e:
                    self.logger.error(f"파일 처리 오류 ({extracted_file}): {e}")
            
            # 타입별로 임시 파일 저장 (2_subdomain)
            temp_files = []
            for qna_type, items in classified_data.items():
                if items:
                    temp_file = os.path.join(temp_output_dir, f'{qna_type}.json')
                    self.json_handler.save(items, temp_file)
                    temp_files.append(temp_file)
                    self.logger.info(f"{qna_type}: {len(items)}개 항목을 임시 파일에 저장: {temp_file}")
            
            # 모든 타입을 합쳐서 classified_ALL.json 생성
            all_classified_data = []
            for qna_type, items in classified_data.items():
                all_classified_data.extend(items)
            
            if all_classified_data:
                classified_all_file = os.path.join(temp_output_dir, 'classified_ALL.json')
                self.json_handler.save(all_classified_data, classified_all_file)
                self.logger.info(f"classified_ALL.json 생성 완료: {len(all_classified_data)}개 항목")
            
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

