#!/usr/bin/env python3
"""
Q&A 추출 빌더 (Extracted QnA Builder)
- 여러 JSON 파일에서 Q&A를 추출하여 _extracted_qna.json 생성
- 중단된 작업 재개 (Resume) 기능 지원
- Validation 리포트 생성
"""

import os
import glob
import re
import logging
from typing import List, Dict, Any, Optional

from tools.core.utils import FileManager, JSONHandler
from tools.qna.extraction.qna_extractor import QnAExtractor
from tools.qna.validation.check_duplicates import check_duplicates_single_file
from tools.qna.validation.find_invalid_options import find_invalid_options_in_file
from tools.report import ValidationReportGenerator


class ExtractedQnABuilder:
    """
    Q&A 추출 빌더
    
    원본 JSON 파일들에서 Q&A를 추출하여 _extracted_qna.json 파일을 생성합니다.
    - 일괄 처리 (여러 파일/사이클)
    - Resume 지원 (중단된 작업 재개)
    - Validation (중복, 선택지 검증)
    - 리포트 생성
    """
    
    def __init__(self, file_manager: FileManager = None, json_handler: JSONHandler = None, logger: logging.Logger = None):
        self.file_manager = file_manager or FileManager()
        self.json_handler = json_handler or JSONHandler()
        self.logger = logger or logging.getLogger(__name__)
        self.extractor = QnAExtractor(self.file_manager)
    
    def validate_extracted_qna(self, file_path: str) -> Dict[str, Any]:
        """
        추출된 QnA 파일에 대해 validation을 수행합니다.
        
        Args:
            file_path: extracted_qna.json 파일 경로
            
        Returns:
            validation 결과 딕셔너리
        """
        validation_result = {
            'file': file_path,
            'duplicates': {'total': 0, 'groups': 0, 'details': []},
            'invalid_options': {'total': 0, 'empty': 0, 'invalid_format': 0},
            'issues': []
        }
        
        if not os.path.exists(file_path):
            return validation_result
        
        # 1. 중복 검사
        try:
            total_qna, duplicate_groups, duplicate_details = check_duplicates_single_file(file_path, return_details=True)
            
            # 중복 그룹 상세 정보 추출 (각 그룹별 태그 목록)
            duplicate_group_list = []
            if duplicate_details:
                for content_key, items in duplicate_details.items():
                    tags = [item.get('tag', '') for item in items if item.get('tag')]
                    if tags:
                        duplicate_group_list.append(tags)
            
            validation_result['duplicates'] = {
                'total': total_qna,
                'groups': duplicate_groups,
                'details': duplicate_group_list  # 각 그룹별 태그 리스트
            }
            if duplicate_groups > 0:
                validation_result['issues'].append(f"중복 {duplicate_groups}개 그룹 발견")
        except Exception as e:
            self.logger.warning(f"중복 검사 오류: {e}")
        
        # 2. 유효하지 않은 선택지 검사
        try:
            invalid_cases = find_invalid_options_in_file(file_path)
            empty_count = sum(1 for c in invalid_cases if c.get('invalid_type') == 'empty')
            invalid_format_count = sum(1 for c in invalid_cases if c.get('invalid_type') == 'invalid_format')
            
            validation_result['invalid_options'] = {
                'total': len(invalid_cases),
                'empty': empty_count,
                'invalid_format': invalid_format_count
            }
            if invalid_cases:
                validation_result['issues'].append(f"유효하지 않은 선택지 {len(invalid_cases)}개")
        except Exception as e:
            self.logger.warning(f"선택지 검사 오류: {e}")
        
        return validation_result
        
    def find_last_processed_page(self, output_dir: str, file_name: str) -> int:
        """특정 파일의 마지막으로 처리된 페이지 번호를 찾습니다."""
        pattern = os.path.join(output_dir, f"{file_name}_temp_page_*.json")
        tmp_files = glob.glob(pattern)
        
        if not tmp_files:
            return 0
        
        page_numbers = []
        for tmp_file in tmp_files:
            match = re.search(r'_temp_page_(\d+)\.json$', tmp_file)
            if match:
                page_numbers.append(int(match.group(1)))
        
        return max(page_numbers) if page_numbers else 0

    def process_file(self, input_file: str, output_file: str, debug: bool = False) -> Dict[str, Any]:
        """
        단일 파일 처리 (재개 기능 포함)
        
        Args:
            input_file: 입력 JSON 파일 경로
            output_file: 출력 JSON 파일 경로
            debug: 디버그 모드
            
        Returns:
            처리 결과
        """
        file_name = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        final_qna_file = output_file.replace('.json', '_extracted_qna.json')
        
        # 기존 파일 처리
        if os.path.exists(final_qna_file):
            if debug:
                from datetime import datetime
                import shutil
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{final_qna_file}.backup_{timestamp}"
                try:
                    shutil.copy2(final_qna_file, backup_path)
                    self.logger.info(f"기존 extracted_qna 파일 백업: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"백업 실패: {e}")
            else:
                self.logger.info(f"기존 extracted_qna 파일을 덮어쓰기: {os.path.basename(final_qna_file)}")
        
        last_page = self.find_last_processed_page(output_dir, file_name)
        
        try:
            json_data = self.json_handler.load(input_file)
        except Exception as e:
            self.logger.error(f"JSON 파싱 오류 ({input_file}): {e}")
            return {'extracted_qna': [], 'status': 'error', 'error': str(e)}
            
        all_qna = []
        
        # Resume: 이전 임시 파일 로드
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
            for page in remaining_contents:
                page_num = page.get('page', 0)
                single_page_json = json_data.copy()
                single_page_json['contents'] = [page]
                
                try:
                    result = self.extractor.extract_qna_from_json(single_page_json, file_name, all_contents=contents)
                    extracted_items = result.get('extracted_qna', [])
                    
                    if extracted_items:
                        all_qna.extend(extracted_items)
                        temp_output = os.path.join(output_dir, f"{file_name}_temp_page_{page_num}.json")
                        self.json_handler.save(extracted_items, temp_output)
                        self.logger.debug(f"페이지 {page_num} 처리 ({len(extracted_items)}개)")
                except Exception as e:
                    self.logger.error(f"페이지 {page_num} 처리 중 오류: {e}")
                    continue

        # 최종 저장
        if all_qna:
            if debug and os.path.exists(final_qna_file):
                try:
                    existing_qna = self.json_handler.load(final_qna_file)
                    if isinstance(existing_qna, list):
                        existing_keys = {(item.get('file_id', ''), item.get('qna_data', {}).get('tag', '')) for item in existing_qna}
                        new_items = [item for item in all_qna if (item.get('file_id', ''), item.get('qna_data', {}).get('tag', '')) not in existing_keys]
                        all_qna = existing_qna + new_items
                        self.logger.info(f"기존 파일과 병합: 기존 {len(existing_qna)}개, 신규 {len(new_items)}개")
                except Exception as e:
                    self.logger.warning(f"기존 파일 병합 실패: {e}")
            
            self.json_handler.save(all_qna, final_qna_file, backup=debug, logger=self.logger)
            self.logger.info(f"처리 완료: {final_qna_file} (총 {len(all_qna)}개)")
            
            # 임시 파일 삭제
            for f in glob.glob(os.path.join(output_dir, f"{file_name}_temp_page_*.json")):
                try:
                    os.remove(f)
                except Exception:
                    pass
        else:
            self.logger.info(f"추출된 Q&A 없음: {file_name}")
        
        # Validation 수행
        validation_result = None
        if all_qna and os.path.exists(final_qna_file):
            validation_result = self.validate_extracted_qna(final_qna_file)
            if validation_result['issues']:
                self.logger.warning(f"Validation 이슈: {', '.join(validation_result['issues'])}")
            
        return {'extracted_qna': all_qna, 'status': 'completed', 'validation': validation_result}

    def build(self, cycle: Optional[int], levels: List[str], onedrive_path: str, debug: bool = False) -> Dict[str, Any]:
        """
        지정된 사이클과 레벨의 파일들에서 Q&A를 추출하여 _extracted_qna.json 생성
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클)
            levels: 처리할 레벨 목록
            onedrive_path: OneDrive 경로
            debug: 디버그 모드
            
        Returns:
            처리 결과 통계
        """
        data_path = self.file_manager.final_data_path
        processed_count = 0
        total_extracted = 0
        all_validation_results = []
        
        target_dirs = []
        
        # 대상 디렉토리 수집
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
                            target_dirs.append((level_path, output_path, cycle_dir))
        else:
            cycle_path_name = self.file_manager.cycle_path.get(cycle)
            if cycle_path_name:
                cycle_dir_path = os.path.join(data_path, cycle_path_name)
                for level in levels:
                    level_path = os.path.join(cycle_dir_path, level)
                    if os.path.exists(level_path):
                        output_path = os.path.join(onedrive_path, 'evaluation', 'workbook_data', cycle_path_name, level)
                        target_dirs.append((level_path, output_path, cycle_path_name))
                        
        # 파일 처리
        for level_path, output_path, cycle_name in target_dirs:
            os.makedirs(output_path, exist_ok=True)
            
            json_files = []
            for root, _, files in os.walk(level_path):
                for f in files:
                    if re.match(r'^SS\d+\.json$', f, re.IGNORECASE):
                        json_files.append(os.path.join(root, f))
            
            json_files = sorted(json_files)
            self.logger.info(f"디렉토리 {level_path}: {len(json_files)}개 파일")
            
            for json_file in json_files:
                file_name = os.path.splitext(os.path.basename(json_file))[0]
                file_output_path = os.path.join(output_path, f"{file_name}.json")
                
                result = self.process_file(json_file, file_output_path, debug=debug)
                
                if result.get('extracted_qna'):
                    processed_count += 1
                    total_extracted += len(result['extracted_qna'])
                
                if result.get('validation'):
                    all_validation_results.append(result['validation'])
        
        # Validation 리포트 저장 (workbook_data 바로 밑에)
        if all_validation_results:
            workbook_data_path = os.path.join(onedrive_path, 'evaluation', 'workbook_data')
            report_path = os.path.join(workbook_data_path, 'VALIDATION_REPORT.md')
            ValidationReportGenerator.save_report(all_validation_results, report_path)
            self.logger.info(f"Validation 리포트 저장: {report_path}")
                    
        return {
            'processed_files': processed_count,
            'total_extracted': total_extracted,
            'validation_issues': sum(1 for r in all_validation_results if r.get('issues'))
        }
