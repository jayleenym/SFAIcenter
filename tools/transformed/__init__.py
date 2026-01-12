#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transformed 패키지 - 문제 변형 관련 기능

이 패키지는 객관식/서술형 문제 변형 기능을 제공합니다:
- AnswerTypeClassifier: 답변 유형 분류 (right/wrong/abcd)
- MultipleChoiceTransformer: 객관식 문제 변형 (right↔wrong, ABCD)
- 서술형 변환: 객관식 → 서술형 문제 변환
- 모범답안 생성: 키워드 추출 및 답안 생성
"""

# 공통 유틸리티 (다른 모듈에서 import해서 사용)
from .common import (
    ROUND_NUMBER_TO_FOLDER,
    validate_round_number,
    get_essay_dir,
    load_questions,
    save_questions,
    clean_question_data,
    init_common,
)

# 답변 유형 분류
try:
    from .answer_type_classifier import AnswerTypeClassifier
except ImportError:
    AnswerTypeClassifier = None

# 객관식 문제 변형
try:
    from .multiple_change_question_and_options import MultipleChoiceTransformer
except ImportError:
    MultipleChoiceTransformer = None

# 변형 문제 로드 유틸리티
try:
    from .multiple_load_transformed_questions import load_transformed_questions
except ImportError:
    load_transformed_questions = None

# 변형 시험지 생성
try:
    from .multiple_create_transformed_exam import create_transformed_exam
except ImportError:
    create_transformed_exam = None

# 서술형 모델 답변 생성
try:
    from .essay_create_model_answers import generate_essay_answers
except ImportError:
    generate_essay_answers = None


__all__ = [
    # 공통 유틸리티
    'ROUND_NUMBER_TO_FOLDER',
    'validate_round_number',
    'get_essay_dir',
    'load_questions',
    'save_questions',
    'clean_question_data',
    'init_common',
    # 답변 유형 분류
    'AnswerTypeClassifier',
    # 객관식 변형
    'MultipleChoiceTransformer',
    'load_transformed_questions',
    'create_transformed_exam',
    # 서술형
    'generate_essay_answers',
]
