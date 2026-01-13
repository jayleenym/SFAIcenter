#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 파일 정리 클래스

JSON 파일에서 빈 페이지를 제거하고 데이터를 정리하는 기능을 제공합니다.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field


# Lv4 타입 (image, table, formula, etc)
LV4_TYPES = {'image', 'table', 'formula', 'etc'}


@dataclass
class PageStats:
    """페이지 통계를 담는 데이터 클래스"""
    total_pages: int = 0
    lv3_pages: int = 0
    lv4_pages: int = 0


@dataclass
class CleanupResult:
    """정리 작업 결과를 담는 데이터 클래스"""
    removed_count: int
    original_count: int
    file_path: Optional[Path] = None
    success: bool = True
    error_message: Optional[str] = None
    before_stats: PageStats = field(default_factory=PageStats)
    after_stats: PageStats = field(default_factory=PageStats)


@dataclass
class DirectoryCleanupResult:
    """디렉토리 정리 결과를 담는 데이터 클래스"""
    processed_files: int
    total_removed: int
    total_original: int
    file_results: List[CleanupResult] = field(default_factory=list)
    
    @property
    def removal_rate(self) -> float:
        """제거 비율 계산"""
        return self.total_removed / self.total_original * 100 if self.total_original > 0 else 0.0
    
    @property
    def total_before_stats(self) -> PageStats:
        """전체 삭제 전 통계"""
        stats = PageStats()
        for result in self.file_results:
            stats.total_pages += result.before_stats.total_pages
            stats.lv3_pages += result.before_stats.lv3_pages
            stats.lv4_pages += result.before_stats.lv4_pages
        return stats
    
    @property
    def total_after_stats(self) -> PageStats:
        """전체 삭제 후 통계"""
        stats = PageStats()
        for result in self.file_results:
            stats.total_pages += result.after_stats.total_pages
            stats.lv3_pages += result.after_stats.lv3_pages
            stats.lv4_pages += result.after_stats.lv4_pages
        return stats


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
    
    @staticmethod
    def is_lv4_page(page: Dict[str, Any]) -> bool:
        """
        페이지가 Lv4 페이지인지 확인 (type이 image, table, formula, etc인 태그가 있는 페이지)
        
        Args:
            page: 페이지 딕셔너리
            
        Returns:
            Lv4 페이지면 True, 그렇지 않으면 False
        """
        add_info = page.get("add_info", [])
        if not add_info:
            return False
        
        for item in add_info:
            item_type = item.get("type", "")
            if item_type in LV4_TYPES:
                return True
        return False
    
    @staticmethod
    def calculate_page_stats(pages: List[Dict[str, Any]]) -> PageStats:
        """
        페이지 목록의 Lv3, Lv4, 전체 페이지 수 계산
        
        Args:
            pages: 페이지 딕셔너리 리스트
            
        Returns:
            PageStats: 페이지 통계
        """
        stats = PageStats()
        stats.total_pages = len(pages)
        
        for page in pages:
            if JSONCleaner.is_lv4_page(page):
                stats.lv4_pages += 1
            else:
                stats.lv3_pages += 1
        
        return stats
    
    def _log(self, message: str) -> None:
        """상세 모드일 때만 메시지 출력"""
        if self.verbose:
            print(message)
    
    def cleanup_file(
        self, 
        file_path: Path, 
        create_backup: bool = True,
        dry_run: bool = False,
        generate_report: bool = False
    ) -> CleanupResult:
        """
        JSON 파일에서 빈 페이지 제거
        
        Args:
            file_path: JSON 파일 경로
            create_backup: 백업 파일 생성 여부
            dry_run: True면 실제 수정하지 않고 분석만 수행
            generate_report: True면 MD 리포트 파일 생성
            
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
            
            # 삭제 전 통계 계산
            before_stats = self.calculate_page_stats(data['contents'])
            
            filtered_contents = [
                page for page in data['contents'] 
                if not self.is_empty_page(page)
            ]
            removed_count = original_count - len(filtered_contents)
            
            # 삭제 후 통계 계산
            after_stats = self.calculate_page_stats(filtered_contents)
            
            if dry_run:
                if removed_count > 0:
                    self._log(f"🔍 {file_path}: {removed_count}개 빈 페이지 발견 (총 {original_count}개 중)")
                else:
                    self._log(f"ℹ️  {file_path}: 빈 페이지 없음")
                result = CleanupResult(
                    removed_count, original_count, file_path,
                    before_stats=before_stats, after_stats=after_stats
                )
                if generate_report:
                    self._generate_file_report(result)
                return result
            
            if removed_count > 0:
                data['contents'] = filtered_contents
                
                if create_backup:
                    backup_path = file_path.with_suffix('.json.bak')
                    should_create_backup = True
                    
                    # 기존 백업 파일이 있으면 생성 시간 확인
                    if backup_path.exists():
                        backup_mtime = backup_path.stat().st_mtime
                        current_time = time.time()
                        one_day_seconds = 24 * 60 * 60
                        # 하루 이내면 백업 생성 안 함
                        if (current_time - backup_mtime) < one_day_seconds:
                            should_create_backup = False
                    
                    if should_create_backup:
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
            
            result = CleanupResult(
                removed_count, original_count, file_path,
                before_stats=before_stats, after_stats=after_stats
            )
            
            if generate_report:
                self._generate_file_report(result)
            
            return result
            
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
        dry_run: bool = False,
        generate_report: bool = False
    ) -> DirectoryCleanupResult:
        """
        디렉토리의 모든 JSON 파일 정리
        
        Args:
            directory: 디렉토리 경로
            create_backup: 백업 파일 생성 여부
            dry_run: True면 실제 수정하지 않고 분석만 수행
            generate_report: True면 MD 리포트 파일 생성
            
        Returns:
            DirectoryCleanupResult: 디렉토리 정리 결과
        """
        json_files = self.find_json_files(directory)
        
        total_removed = 0
        total_original = 0
        processed_files = 0
        file_results = []
        
        for json_file in json_files:
            result = self.cleanup_file(json_file, create_backup, dry_run, generate_report=False)
            total_removed += result.removed_count
            total_original += result.original_count
            if result.removed_count > 0 or result.original_count > 0:
                processed_files += 1
            file_results.append(result)
        
        dir_result = DirectoryCleanupResult(
            processed_files=processed_files,
            total_removed=total_removed,
            total_original=total_original,
            file_results=file_results
        )
        
        if generate_report:
            self._generate_directory_report(directory, dir_result)
        
        return dir_result
    
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
    
    def _generate_file_report(self, result: CleanupResult) -> Path:
        """
        개별 파일 정리 결과 MD 리포트 생성
        
        Args:
            result: 정리 결과
            
        Returns:
            생성된 MD 파일 경로
        """
        from tools.report import CleanupReportGenerator
        
        report_path = CleanupReportGenerator.generate_file_report(result)
        if report_path:
            self._log(f"📝 리포트 생성: {report_path}")
        return report_path
    
    def _generate_directory_report(
        self, 
        directory: Path, 
        result: DirectoryCleanupResult
    ) -> Path:
        """
        디렉토리 정리 결과 MD 리포트 생성
        
        Args:
            directory: 정리한 디렉토리 경로
            result: 디렉토리 정리 결과
            
        Returns:
            생성된 MD 파일 경로
        """
        from tools.report import CleanupReportGenerator
        
        report_path = CleanupReportGenerator.generate_directory_report(directory, result)
        if report_path:
            self._log(f"📝 디렉토리 리포트 생성: {report_path}")
        return report_path
