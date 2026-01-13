#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_processing 패키지 - 데이터 처리 및 정제

이 패키지는 데이터 전처리 및 분석 기능을 제공합니다:

JSON 처리:
- JSONCleaner: 빈 페이지 제거 및 JSON 파일 정리
- CleanupResult: 정리 작업 결과 데이터 클래스
- DirectoryCleanupResult: 디렉토리 정리 결과 데이터 클래스

Crop 파일 분석:
- CropAnalyzer: Crop 파일 BEFORE/AFTER 비교 분석
- FolderStats: 폴더별 파일 통계 데이터 클래스

EPUB/PDF 분석:
- epub_to_pdf: EPUB을 PDF로 변환
- check_pdf_pages: PDF/EPUB 페이지 수 확인
"""

from .json_cleaner import JSONCleaner, CleanupResult, DirectoryCleanupResult
from .crop_analysis import CropAnalyzer, FolderStats
from .epubstats import epub_to_pdf, check_pdf_pages

__all__ = [
    # JSON 처리
    'JSONCleaner',
    'CleanupResult',
    'DirectoryCleanupResult',
    # Crop 분석
    'CropAnalyzer',
    'FolderStats',
    # EPUB/PDF
    'epub_to_pdf',
    'check_pdf_pages',
]
