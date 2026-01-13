#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 파일 정리 클래스

JSON 파일에서 빈 페이지를 제거하고 데이터를 정리하는 기능을 제공합니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CleanupResult:
    """정리 작업 결과를 담는 데이터 클래스"""
    removed_count: int
    original_count: int
    file_path: Optional[Path] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class DirectoryCleanupResult:
    """디렉토리 정리 결과를 담는 데이터 클래스"""
    processed_files: int
    total_removed: int
    total_original: int
    
    @property
    def removal_rate(self) -> float:
        """제거 비율 계산"""
        return self.total_removed / self.total_original * 100 if self.total_original > 0 else 0.0


class JSONCleaner:
    """JSON 파일 정리 클래스"""
    
    def __init__(self, verbose: bool = False):
        """
        JSONCleaner 초기화
        
        Args:
            verbose: 상세 출력 여부
        """
        self.verbose = verbose
    
    @staticmethod
    def is_empty_page(page: Dict[str, Any]) -> bool:
        """
        페이지가 비어있는지 확인
        
        Args:
            page: 페이지 딕셔너리
            
        Returns:
            페이지가 비어있으면 True, 그렇지 않으면 False
        """
        return (
            page.get("page_contents", "") == "" and 
            page.get("add_info", []) == []
        )
    
    def _log(self, message: str) -> None:
        """상세 모드일 때만 메시지 출력"""
        if self.verbose:
            print(message)
    
    def cleanup_file(
        self, 
        file_path: Path, 
        create_backup: bool = True,
        dry_run: bool = False
    ) -> CleanupResult:
        """
        JSON 파일에서 빈 페이지 제거
        
        Args:
            file_path: JSON 파일 경로
            create_backup: 백업 파일 생성 여부
            dry_run: True면 실제 수정하지 않고 분석만 수행
            
        Returns:
            CleanupResult: 정리 결과
        """
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'contents' not in data or not isinstance(data['contents'], list):
                self._log(f"⚠️  {file_path}: 'contents' 필드가 없거나 리스트가 아닙니다.")
                return CleanupResult(0, 0, file_path)
            
            original_count = len(data['contents'])
            filtered_contents = [
                page for page in data['contents'] 
                if not self.is_empty_page(page)
            ]
            removed_count = original_count - len(filtered_contents)
            
            if dry_run:
                if removed_count > 0:
                    self._log(f"🔍 {file_path}: {removed_count}개 빈 페이지 발견 (총 {original_count}개 중)")
                else:
                    self._log(f"ℹ️  {file_path}: 빈 페이지 없음")
                return CleanupResult(removed_count, original_count, file_path)
            
            if removed_count > 0:
                data['contents'] = filtered_contents
                
                if create_backup:
                    backup_path = file_path.with_suffix('.json.bak')
                    if not backup_path.exists():
                        # 백업은 원본 데이터로 생성
                        with open(file_path, 'r', encoding='utf-8') as f:
                            original_data = json.load(f)
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            json.dump(original_data, f, ensure_ascii=False, indent=2)
                        self._log(f"📁 백업 파일 생성: {backup_path}")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self._log(f"✅ {file_path}: {removed_count}개 페이지 제거 "
                         f"(총 {original_count}개 → {len(filtered_contents)}개)")
            else:
                self._log(f"ℹ️  {file_path}: 제거할 빈 페이지가 없습니다.")
            
            return CleanupResult(removed_count, original_count, file_path)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 파싱 오류 - {e}"
            print(f"❌ {file_path}: {error_msg}")
            return CleanupResult(0, 0, file_path, success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"처리 중 오류 - {e}"
            print(f"❌ {file_path}: {error_msg}")
            return CleanupResult(0, 0, file_path, success=False, error_message=error_msg)
    
    def find_json_files(self, path: Path) -> List[Path]:
        """
        경로에서 JSON 파일들을 찾습니다.
        
        Args:
            path: 파일 또는 디렉토리 경로
            
        Returns:
            JSON 파일 경로 리스트
        """
        path = Path(path)
        
        if path.is_file() and path.suffix == '.json':
            return [path]
        elif path.is_dir():
            return list(path.rglob('*.json'))
        else:
            print(f"❌ {path}: 유효하지 않은 경로입니다.")
            return []
    
    def cleanup_directory(
        self, 
        directory: Path, 
        create_backup: bool = True,
        dry_run: bool = False
    ) -> DirectoryCleanupResult:
        """
        디렉토리의 모든 JSON 파일 정리
        
        Args:
            directory: 디렉토리 경로
            create_backup: 백업 파일 생성 여부
            dry_run: True면 실제 수정하지 않고 분석만 수행
            
        Returns:
            DirectoryCleanupResult: 디렉토리 정리 결과
        """
        json_files = self.find_json_files(directory)
        
        total_removed = 0
        total_original = 0
        processed_files = 0
        
        for json_file in json_files:
            result = self.cleanup_file(json_file, create_backup, dry_run)
            total_removed += result.removed_count
            total_original += result.original_count
            if result.removed_count > 0 or result.original_count > 0:
                processed_files += 1
        
        return DirectoryCleanupResult(
            processed_files=processed_files,
            total_removed=total_removed,
            total_original=total_original
        )
    
    def get_empty_pages_info(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        파일에서 빈 페이지들의 정보를 반환
        
        Args:
            file_path: JSON 파일 경로
            
        Returns:
            빈 페이지들의 정보 리스트
        """
        file_path = Path(file_path)
        empty_pages = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'contents' not in data or not isinstance(data['contents'], list):
                return []
            
            for page in data['contents']:
                if self.is_empty_page(page):
                    empty_pages.append({
                        'page': page.get('page', 'N/A'),
                        'chapter': page.get('chapter', 'N/A')
                    })
            
            return empty_pages
            
        except Exception:
            return []
