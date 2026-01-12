#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stats 패키지 - 통계 분석 및 리포트 생성

이 패키지는 통계 분석 및 마크다운 리포트 생성 기능을 제공합니다:
- MarkdownWriter: 공통 마크다운 생성 유틸리티
- ExamReportGenerator: 시험 통계 및 README 마크다운 생성
- TransformReportGenerator: 변형 통계 저장 및 집계
- QnAReportGenerator: QnA 통계 리포트 생성
- QnAStatisticsAnalyzer: QnA 통계 분석
"""

from .markdown_writer import MarkdownWriter
from .exam_report import ExamReportGenerator
from .transform_report import TransformReportGenerator
from .qna_report import QnAReportGenerator
from .qna_analyzer import QnAStatisticsAnalyzer
from .validation_report import ValidationReportGenerator

# 하위 호환성을 위한 별칭
StatisticsSaver = TransformReportGenerator

__all__ = [
    # 리포트 생성
    'MarkdownWriter',
    'ExamReportGenerator', 
    'TransformReportGenerator',
    'QnAReportGenerator',
    'QnAStatisticsAnalyzer',
    'ValidationReportGenerator',
    'StatisticsSaver',  # 하위 호환성
]

