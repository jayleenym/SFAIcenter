#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report 패키지 - 통계 분석 및 리포트 생성

이 패키지는 통계 분석 및 마크다운 리포트 생성 기능을 제공합니다:
- MarkdownWriter: 공통 마크다운 생성 유틸리티
- ExamReportGenerator: 시험 통계 및 README 마크다운 생성
- TransformReportGenerator: 변형 통계 저장 및 집계
- QnAReportGenerator: QnA 통계 리포트 생성
- QnAStatisticsAnalyzer: QnA 통계 분석
- CleanupReportGenerator: JSON 정리 리포트 생성
- CrossFileDuplicatesReportGenerator: 파일 간 중복 리포트 생성
"""

from .markdown_writer import MarkdownWriter
from .exam_report import ExamReportGenerator, MultipleChoiceValidationReportGenerator
from .transform_report import TransformReportGenerator
from .qna_report import QnAReportGenerator
from .qna_analyzer import QnAStatisticsAnalyzer
from .validation_report import ValidationReportGenerator
from .cleanup_report import CleanupReportGenerator
from .cross_file_duplicates_report import CrossFileDuplicatesReportGenerator


__all__ = [
    # 리포트 생성
    'MarkdownWriter',
    'ExamReportGenerator',
    'MultipleChoiceValidationReportGenerator',
    'TransformReportGenerator',
    'QnAReportGenerator',
    'QnAStatisticsAnalyzer',
    'ValidationReportGenerator',
    'CleanupReportGenerator',
    'CrossFileDuplicatesReportGenerator',
]

