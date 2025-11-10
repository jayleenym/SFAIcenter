#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 파일 정리 클래스
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
import shutil


class JSONCleaner:
    """JSON 파일 정리 클래스"""
    
    @staticmethod
    def is_empty_page(page: Dict[str, Any]) -> bool:
        """페이지가 비어있는지 확인"""
        return (
            page.get("page_contents", "") == "" and 
            page.get("add_info", []) == []
        )
    
    def cleanup_file(self, file_path: Path, create_backup: bool = True) -> Tuple[int, int]:
        """
        JSON 파일에서 빈 페이지 제거
        
        Args:
            file_path: JSON 파일 경로
            create_backup: 백업 파일 생성 여부
            
        Returns:
            (제거된 페이지 수, 원본 페이지 수)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'contents' not in data or not isinstance(data['contents'], list):
                return 0, 0
            
            original_count = len(data['contents'])
            filtered_contents = [
                page for page in data['contents'] 
                if not self.is_empty_page(page)
            ]
            
            removed_count = original_count - len(filtered_contents)
            
            if removed_count > 0:
                data['contents'] = filtered_contents
                
                if create_backup:
                    backup_path = file_path.with_suffix('.json.bak')
                    if not backup_path.exists():
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            return removed_count, original_count
            
        except Exception as e:
            print(f"❌ {file_path}: 처리 중 오류 - {e}")
            return 0, 0
    
    def cleanup_directory(self, directory: Path, create_backup: bool = True) -> Dict[str, Any]:
        """디렉토리의 모든 JSON 파일 정리"""
        json_files = list(directory.rglob('*.json'))
        
        total_removed = 0
        total_original = 0
        processed_files = 0
        
        for json_file in json_files:
            removed, original = self.cleanup_file(json_file, create_backup)
            total_removed += removed
            total_original += original
            if removed > 0 or original > 0:
                processed_files += 1
        
        return {
            'processed_files': processed_files,
            'total_removed': total_removed,
            'total_original': total_original,
            'removal_rate': total_removed / total_original * 100 if total_original > 0 else 0
        }

