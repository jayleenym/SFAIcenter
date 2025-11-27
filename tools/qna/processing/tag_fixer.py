#!/usr/bin/env python3
"""
Q&A 태그 대치 모듈 (TagFixer)
- JSON 파일의 Q&A 데이터에서 태그를 찾아 내용으로 대치
"""

import os
import shutil
import logging
from typing import Dict, Any, List, Optional

from tools.core.utils import FileManager, JSONHandler
from tools.qna.tag_processor import TagProcessor

class TagFixer:
    """Q&A 태그 대치 클래스"""
    
    def __init__(self, file_manager: FileManager = None, json_handler: JSONHandler = None, logger: logging.Logger = None):
        self.file_manager = file_manager or FileManager()
        self.json_handler = json_handler or JSONHandler()
        self.logger = logger or logging.getLogger(__name__)
        
    def process_file(self, file_path: str, backup: bool = True) -> bool:
        """
        JSON 파일을 로드하고 태그 대치를 수행한 후 저장합니다.
        
        Args:
            file_path: 처리할 JSON 파일 경로
            backup: 백업 파일 생성 여부
        
        Returns:
            성공 여부
        """
        try:
            # JSON 파일 로드
            data = self.json_handler.load(file_path)
            
            # extracted_qna 데이터가 있는 경우 처리
            if 'extracted_qna' in data and isinstance(data['extracted_qna'], list):
                self.logger.info(f"Processing {os.path.basename(file_path)}: {len(data['extracted_qna'])} Q&A items")
                
                # additional_tag_data 가져오기 (파일 레벨)
                additional_tag_data = data.get('additional_tag_data', [])
                
                # 각 Q&A 항목에 대해 태그 대치 수행
                changed_count = 0
                for i, qna_item in enumerate(data['extracted_qna']):
                    # 항목별 additional_tag_data가 있으면 우선 사용
                    item_tag_data = qna_item.get('additional_tag_data', additional_tag_data)
                    if item_tag_data:
                        # 태그 대치 전후 비교를 위해 복사
                        # (하지만 replace_tags_in_qna_data가 inplace 수정일 수도 있고 아닐 수도 있음.
                        #  TagProcessor는 return qna_item을 하지만 내부에서 desc 등을 직접 수정함)
                        #  여기서는 그냥 호출하고 저장.
                        TagProcessor.replace_tags_in_qna_data(qna_item, item_tag_data)
                        changed_count += 1
                
                if backup:
                    backup_path = file_path + '.backup'
                    shutil.copy2(file_path, backup_path)
                    self.logger.info(f"Backup created: {backup_path}")
                
                # 수정된 데이터 저장
                self.json_handler.save(data, file_path)
                
                self.logger.info(f"Tag replacement completed for {os.path.basename(file_path)}")
                return True
            
            else:
                self.logger.info(f"No extracted_qna data found in {os.path.basename(file_path)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return False

    def process_cycle(self, cycle: int, data_path: str = None) -> Dict[str, Any]:
        """
        지정된 사이클의 모든 JSON 파일에 대해 태그 대치를 수행합니다.
        
        Args:
            cycle: 사이클 번호 (1, 2, 3)
            data_path: 데이터 경로 (None이면 FileManager의 기본 경로 사용)
            
        Returns:
            처리 결과 통계
        """
        if data_path is None:
            data_path = self.file_manager.final_data_path
        
        cycle_name = self.file_manager.cycle_path.get(cycle)
        if not cycle_name:
            self.logger.error(f"Invalid cycle: {cycle}")
            return {'success': False, 'error': 'Invalid cycle'}
            
        final_path = os.path.join(data_path, cycle_name)
        
        if not os.path.exists(final_path):
            self.logger.error(f"경로가 존재하지 않습니다: {final_path}")
            return {'success': False, 'error': 'Path not found'}
        
        self.logger.info(f"Processing cycle {cycle} files in: {final_path}")
        
        # 모든 JSON 파일 찾기
        json_files = []
        for root, _, files in os.walk(final_path):
            for f in files:
                if f.endswith(".json") and ('_' not in f):
                    json_files.append(os.path.join(root, f))
        
        if not json_files:
            self.logger.warning("처리할 JSON 파일이 없습니다.")
            return {'success': True, 'count': 0}
        
        self.logger.info(f"발견된 JSON 파일: {len(json_files)}개")
        
        success_count = 0
        error_count = 0
        error_files = []
        
        for i, file_path in enumerate(json_files, 1):
            self.logger.info(f"[{i}/{len(json_files)}] 처리 중: {os.path.basename(file_path)}")
            
            if self.process_file(file_path):
                success_count += 1
            else:
                error_count += 1
                error_files.append(os.path.basename(file_path))
        
        return {
            'success': True,
            'total': len(json_files),
            'success_count': success_count,
            'error_count': error_count,
            'error_files': error_files
        }

