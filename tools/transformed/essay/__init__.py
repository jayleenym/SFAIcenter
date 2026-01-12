#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
essay 패키지 - 서술형 문제 변환 기능

이 패키지는 객관식 문제를 서술형 문제로 변환하는 기능을 제공합니다 (Step9):
- filter_full_explanation: 해설이 많은 문제 선별
- classify_by_exam: 시험별 분류
- change_question_to_essay: 서술형 문제로 변환
- extract_keywords: 키워드 추출
- create_best_answers: 모범답안 생성
- generate_essay_answers: 모델 답변 생성

사용 예시:
    # Step9에서 개별 함수 사용
    from tools.transformed.essay import filter_full_explanation
    count = filter_full_explanation(llm=llm_query, onedrive_path=onedrive_path)
    
    # 키워드 추출
    from tools.transformed.essay import extract_keywords
    count = extract_keywords(llm=llm_query, onedrive_path=onedrive_path, round_number='1')
"""

# 공통 유틸리티
from .common import (
    ROUND_NUMBER_TO_FOLDER,
    validate_round_number,
    get_essay_dir,
    load_questions,
    save_questions,
    clean_question_data,
    init_common,
)

# 0단계: 해설이 많은 문제 선별
from .filter_full_explanation import filter_full_explanation

# 시험별 분류
from .classify_by_exam import main as classify_by_exam

# 1단계: 서술형 문제로 변환
from .change_question_to_essay import change_question_to_essay

# 2단계: 키워드 추출
from .extract_keywords import extract_keywords

# 3단계: 모범답안 생성
from .create_best_answers import create_best_answers

# 모델 답변 생성
try:
    from .create_model_answers import generate_essay_answers, process_essay_questions, get_api_key
except ImportError:
    generate_essay_answers = None
    process_essay_questions = None
    get_api_key = None


__all__ = [
    # 공통 유틸리티
    'ROUND_NUMBER_TO_FOLDER',
    'validate_round_number',
    'get_essay_dir',
    'load_questions',
    'save_questions',
    'clean_question_data',
    'init_common',
    # 변환 함수들
    'filter_full_explanation',
    'classify_by_exam',
    'change_question_to_essay',
    'extract_keywords',
    'create_best_answers',
    # 모델 답변 생성
    'generate_essay_answers',
    'process_essay_questions',
    'get_api_key',
]

