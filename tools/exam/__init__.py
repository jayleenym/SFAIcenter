#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam 패키지 - 시험지 생성 관련 기능

이 패키지는 시험지 생성 및 검증 기능을 제공합니다:

클래스:
    - ExamMaker: 일반 시험지 생성 (5세트)
    - ExamPlusMaker: 변형 시험지 생성
    - ExamValidator: 시험지 검증 및 업데이트

유틸리티 함수:
    - extract_question_ids_from_exam: 시험지에서 문제 번호 추출
    - extract_all_exam_question_lists: 모든 회차별 시험지에서 문제 번호 추출
    - load_question_lists: 저장된 문제 번호 리스트 로드

Note:
    리포트 생성 기능은 tools.report 패키지로 분리되었습니다.
    - ExamReportGenerator: 시험 통계 및 README 마크다운 생성
    - MultipleChoiceValidationReportGenerator: 객관식 검증 리포트 생성
"""

from .exam_validator import ExamValidator, CIRCLED_NUMBERS, CIRCLED_NUMBERS_PATTERN
from .extract_exam_question_list import (
    extract_question_ids_from_exam,
    extract_all_exam_question_lists,
    load_question_lists,
    save_question_lists,
)

# 선택적 import (의존성이 누락될 수 있는 모듈)
try:
    from .exam_create import ExamMaker
except ImportError:
    ExamMaker = None

try:
    from .exam_plus_create import ExamPlusMaker
except ImportError:
    ExamPlusMaker = None


__all__ = [
    # 시험지 생성 클래스
    'ExamMaker',
    'ExamPlusMaker',
    'ExamValidator',
    # 유틸리티 함수
    'extract_question_ids_from_exam',
    'extract_all_exam_question_lists',
    'load_question_lists',
    'save_question_lists',
    # 상수
    'CIRCLED_NUMBERS',
    'CIRCLED_NUMBERS_PATTERN',
]
