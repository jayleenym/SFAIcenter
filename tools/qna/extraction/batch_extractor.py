#!/usr/bin/env python3
"""
Q&A 일괄 추출 모듈 (Batch Extractor)
- 여러 JSON 파일에서 Q&A를 추출하여 _extracted_qna.json 생성
- 중단된 작업 재개 (Resume) 기능 지원
- 페이지별 임시 저장 기능 지원
"""

import os
import json
import glob
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from tools.core.utils import FileManager, JSONHandler
from tools.qna.extraction.qna_extractor import QnAExtractor

class BatchExtractor:
    """Q&A 일괄 추출 클래스"""
    
    def __init__(self, file_manager: FileManager = None, json_handler: JSONHandler = None, logger: logging.Logger = None):
        self.file_manager = file_manager or FileManager()
        self.json_handler = json_handler or JSONHandler()
        self.logger = logger or logging.getLogger(__name__)
        self.extractor = QnAExtractor(self.file_manager)
        
    def find_last_processed_page(self, output_dir: str, file_name: str) -> int:
        """
        특정 파일의 마지막으로 처리된 페이지 번호를 찾습니다.
        
        Args:
            output_dir: 출력 디렉토리 경로
            file_name: 파일명 (확장자 제외)
            
        Returns:
            마지막으로 처리된 페이지 번호 (없으면 0)
        """
        # tmp 파일 패턴: {file_name}_temp_page_{page_number}.json
        pattern = os.path.join(output_dir, f"{file_name}_temp_page_*.json")
        tmp_files = glob.glob(pattern)
        
        if not tmp_files:
            return 0
        
        # 페이지 번호 추출
        page_numbers = []
        for tmp_file in tmp_files:
            match = re.search(r'_temp_page_(\d+)\.json$', tmp_file)
            if match:
                page_numbers.append(int(match.group(1)))
        
        if not page_numbers:
            return 0
        
        return max(page_numbers)

    def process_file_with_resume(self, input_file: str, output_file: str, debug: bool = False) -> Dict[str, Any]:
        """
        단일 파일 처리 (재개 기능 포함)
        
        Args:
            input_file: 입력 JSON 파일 경로
            output_file: 출력 JSON 파일 경로
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            
        Returns:
            처리 결과
        """
        file_name = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        final_qna_file = output_file.replace('.json', '_extracted_qna.json')
        
        # debug 모드일 때는 기존 파일 백업, 아니면 덮어쓰기
        if os.path.exists(final_qna_file):
            if debug:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{final_qna_file}.backup_{timestamp}"
                try:
                    import shutil
                    shutil.copy2(final_qna_file, backup_path)
                    self.logger.info(f"기존 extracted_qna 파일 백업: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"백업 실패: {e}")
            else:
                self.logger.info(f"기존 extracted_qna 파일을 덮어쓰기: {os.path.basename(final_qna_file)}")
        
        # 마지막으로 처리된 페이지 확인 (resume 기능 유지)
        last_page = self.find_last_processed_page(output_dir, file_name)
        
        try:
            json_data = self.json_handler.load(input_file)
        except Exception as e:
            self.logger.error(f"JSON 파싱 오류 ({input_file}): {e}")
            return {'extracted_qna': [], 'status': 'error', 'error': str(e)}
            
        all_qna = []
        
        # 이전에 처리된 임시 파일 로드 (resume 기능)
        if last_page > 0:
            self.logger.info(f"재개: {file_name} (마지막 페이지: {last_page})")
            temp_files = glob.glob(os.path.join(output_dir, f"{file_name}_temp_page_*.json"))
            for temp_file in temp_files:
                try:
                    temp_data = self.json_handler.load(temp_file)
                    if isinstance(temp_data, list):
                        all_qna.extend(temp_data)
                except Exception as e:
                    self.logger.warning(f"임시 파일 로드 오류 ({temp_file}): {e}")
        
        # 남은 페이지 처리
        contents = json_data.get('contents', [])
        remaining_contents = [p for p in contents if int(p.get('page', 0)) > last_page]
        
        if not remaining_contents and last_page > 0:
            self.logger.info("모든 페이지가 이미 처리되었습니다.")
        elif remaining_contents:
            # 남은 페이지 처리
            for page in remaining_contents:
                page_num = page.get('page', 0)
                single_page_json = json_data.copy()
                single_page_json['contents'] = [page]
                
                try:
                    result = self.extractor.extract_qna_from_json(single_page_json, file_name)
                    extracted_items = result.get('extracted_qna', [])
                    
                    if extracted_items:
                        all_qna.extend(extracted_items)
                        
                        # 임시 저장 (resume을 위해)
                        temp_output = os.path.join(output_dir, f"{file_name}_temp_page_{page_num}.json")
                        self.json_handler.save(extracted_items, temp_output)
                        self.logger.debug(f"페이지 {page_num} 처리 및 임시 저장 ({len(extracted_items)}개)")
                except Exception as e:
                    self.logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                    continue

        # 5. 최종 저장
        if all_qna:
            # debug 모드일 때는 기존 파일과 병합
            if debug and os.path.exists(final_qna_file):
                try:
                    existing_qna = self.json_handler.load(final_qna_file)
                    if isinstance(existing_qna, list):
                        # file_id와 tag 기준으로 중복 제거
                        existing_keys = set()
                        for item in existing_qna:
                            file_id = item.get('file_id', '')
                            tag = item.get('qna_data', {}).get('tag', '')
                            existing_keys.add((file_id, tag))
                        
                        # 새 항목 중 중복이 아닌 것만 추가
                        new_items = []
                        for item in all_qna:
                            file_id = item.get('file_id', '')
                            tag = item.get('qna_data', {}).get('tag', '')
                            key = (file_id, tag)
                            if key not in existing_keys:
                                new_items.append(item)
                                existing_keys.add(key)
                        
                        # 기존 항목과 새 항목 병합
                        all_qna = existing_qna + new_items
                        self.logger.info(f"기존 파일과 병합: 기존 {len(existing_qna)}개, 신규 {len(new_items)}개")
                except Exception as e:
                    self.logger.warning(f"기존 파일 병합 실패, 새로 생성: {e}")
            
            self.json_handler.save(all_qna, final_qna_file, backup=debug, logger=self.logger)
            self.logger.info(f"처리 완료: {final_qna_file} (총 {len(all_qna)}개)")
            
            # 임시 파일 삭제
            temp_files = glob.glob(os.path.join(output_dir, f"{file_name}_temp_page_*.json"))
            for f in temp_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
        else:
            self.logger.info(f"추출된 Q&A 없음: {file_name}")
            
        return {'extracted_qna': all_qna, 'status': 'completed'}

    def process_directory(self, cycle: Optional[int], levels: List[str], onedrive_path: str, debug: bool = False) -> Dict[str, Any]:
        """
        디렉토리 단위 일괄 처리
        
        Args:
            cycle: 사이클 번호
            levels: 레벨 목록
            onedrive_path: OneDrive 경로
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            
        Returns:
            통계 정보
        """
        data_path = self.file_manager.final_data_path
        processed_count = 0
        total_extracted = 0
        
        target_dirs = []
        
        # 대상 디렉토리 수집 (QnAMaker와 동일 로직)
        if cycle is None:
            if os.path.exists(data_path):
                for cycle_dir in os.listdir(data_path):
                    cycle_dir_path = os.path.join(data_path, cycle_dir)
                    if not os.path.isdir(cycle_dir_path): continue
                    if cycle_dir not in self.file_manager.cycle_path.values(): continue
                    
                    for level in levels:
                        level_path = os.path.join(cycle_dir_path, level)
                        if os.path.exists(level_path):
                            output_path = os.path.join(onedrive_path, 'evaluation', 'workbook_data', cycle_dir, level)
                            target_dirs.append((level_path, output_path))
        else:
            cycle_path_name = self.file_manager.cycle_path.get(cycle)
            if cycle_path_name:
                cycle_dir_path = os.path.join(data_path, cycle_path_name)
                for level in levels:
                    level_path = os.path.join(cycle_dir_path, level)
                    if os.path.exists(level_path):
                        output_path = os.path.join(onedrive_path, 'evaluation', 'workbook_data', cycle_path_name, level)
                        target_dirs.append((level_path, output_path))
                        
        # 파일 처리
        for level_path, output_path in target_dirs:
            os.makedirs(output_path, exist_ok=True)
            
            # JSON 파일 찾기
            json_files = []
            for root, _, files in os.walk(level_path):
                for f in files:
                    if re.match(r'^SS\d{4}\.json$', f, re.IGNORECASE):
                        json_files.append(os.path.join(root, f))
            
            json_files = sorted(json_files)
            self.logger.info(f"디렉토리 {level_path}: {len(json_files)}개 파일")
            
            for json_file in json_files:
                file_name = os.path.splitext(os.path.basename(json_file))[0]
                file_output_path = os.path.join(output_path, f"{file_name}.json")
                
                result = self.process_file_with_resume(json_file, file_output_path, debug=debug)
                
                if result.get('extracted_qna'):
                    processed_count += 1
                    total_extracted += len(result['extracted_qna'])
                    
        return {
            'processed_files': processed_count,
            'total_extracted': total_extracted
        }

