#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qna 패키지 - Q&A 처리 클래스

이 패키지는 Q&A 추출, 처리, 분석 기능을 제공합니다:

extraction/
    - QnAExtractor: Q&A 태그 추출
    - TagProcessor: 태그 처리 및 데이터 채우기
    - BatchExtractor: 배치 추출 처리

processing/
    - QnATypeClassifier: Q&A 타입 분류 (multiple-choice/short-answer/essay)
    - QnASubdomainClassifier: 도메인/서브도메인 분류
    - QnAOrganizer: 타입별 Q&A 정리
    - DomainFiller: 도메인 정보 채우기

analysis/
    - QnAStatisticsAnalyzer: 통계 분석
"""

# 핵심 추출 클래스
from .extraction.qna_extractor import QnAExtractor
from .extraction.tag_processor import TagProcessor

# 핵심 처리 클래스
from .processing.qna_type_classifier import QnATypeClassifier

# 선택적 import (모듈이 없을 수 있음)
try:
    from .extraction.batch_extractor import BatchExtractor
except ImportError:
    BatchExtractor = None

try:
    from .processing.qna_subdomain_classifier import QnASubdomainClassifier
except ImportError:
    QnASubdomainClassifier = None

try:
    from .processing.organize_qna_by_type import QnAOrganizer
except ImportError:
    QnAOrganizer = None

try:
    from .processing.fill_domain import DomainFiller
except ImportError:
    DomainFiller = None


__all__ = [
    # 추출
    'QnAExtractor',
    'TagProcessor',
    'BatchExtractor',
    # 처리
    'QnATypeClassifier',
    'QnASubdomainClassifier',
    'QnAOrganizer',
    'DomainFiller',
]
