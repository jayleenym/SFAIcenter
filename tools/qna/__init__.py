#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qna 패키지 - Q&A 처리 클래스

이 패키지는 Q&A 추출, 처리, 검증 기능을 제공합니다:

extraction/
    - QnAExtractor: Q&A 태그 추출
    - TagProcessor: 태그 처리 및 데이터 채우기
    - ExtractedQnABuilder: 일괄 추출 + validation + 리포트

processing/
    - QnATypeClassifier: Q&A 타입 분류 (multiple-choice/short-answer/essay)
    - QnASubdomainClassifier: 도메인/서브도메인 분류
    - QnAOrganizer: 타입별 Q&A 정리
    - DomainFiller: 도메인 정보 채우기

validation/
    - check_duplicates: 중복 QnA 검사 및 삭제
    - find_invalid_options: 유효하지 않은 선택지 찾기
"""

# 추출 클래스
from .extraction.qna_extractor import QnAExtractor
from .extraction.tag_processor import TagProcessor
from .extraction.extracted_qna_builder import ExtractedQnABuilder

# 처리 클래스
from .processing.qna_type_classifier import QnATypeClassifier

# 선택적 import
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
    'ExtractedQnABuilder',
    # 처리
    'QnATypeClassifier',
    'QnASubdomainClassifier',
    'QnAOrganizer',
    'DomainFiller',
]
