#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transformed 패키지 - 문제 변형 관련 기능

이 패키지는 객관식/서술형 문제 변형 기능을 제공합니다.

하위 패키지:
    - multiple: 객관식 문제 변형 (Step3)
    - essay: 서술형 문제 변환 (Step9)

객관식 문제 변형 (tools.transformed.multiple):
    - QuestionTransformerOrchestrator: 변형 프로세스 전체 관리 (Step3 진입점)
    - AnswerTypeClassifier: 답변 유형 분류 (right/wrong/abcd)
    - MultipleChoiceTransformer: 객관식 문제 변형 (right↔wrong, ABCD)
    - load_transformed_questions: 변형된 문제 로드
    - create_transformed_exam: 변형 시험지 생성

서술형 변환 (tools.transformed.essay, Step9):
    - filter_full_explanation: 문제 선별
    - classify_by_exam: 시험별 분류
    - change_question_to_essay: 서술형 변환
    - extract_keywords: 키워드 추출
    - create_best_answers: 모범답안 생성
    - generate_essay_answers: 모델 답변 생성

사용 예시:
    # Step3: 객관식 문제 변형
    from tools.transformed.multiple import QuestionTransformerOrchestrator
    orchestrator = QuestionTransformerOrchestrator(...)
    result = orchestrator.transform_questions(...)
    
    # Step9: 서술형 문제 변환
    from tools.transformed.essay import filter_full_explanation
    count = filter_full_explanation(llm=llm_query, onedrive_path=onedrive_path)
"""

# multiple 패키지에서 import
from .multiple import (
    QuestionTransformerOrchestrator,
    AnswerTypeClassifier,
    MultipleChoiceTransformer,
    load_transformed_questions,
    create_transformed_exam,
)

# essay 패키지에서 import
from .essay import (
    ROUND_NUMBER_TO_FOLDER,
    validate_round_number,
    get_essay_dir,
    load_questions,
    save_questions,
    clean_question_data,
    init_common,
    filter_full_explanation,
    classify_by_exam,
    change_question_to_essay,
    extract_keywords,
    create_best_answers,
)

# 모델 답변 생성 (선택적 import)
try:
    from .essay import generate_essay_answers, process_essay_questions, get_api_key
except ImportError:
    generate_essay_answers = None
    process_essay_questions = None
    get_api_key = None


__all__ = [
    # 객관식 변형 (multiple)
    'QuestionTransformerOrchestrator',
    'AnswerTypeClassifier',
    'MultipleChoiceTransformer',
    'load_transformed_questions',
    'create_transformed_exam',
    # 서술형 변환 (essay)
    'filter_full_explanation',
    'classify_by_exam',
    'change_question_to_essay',
    'extract_keywords',
    'create_best_answers',
    'generate_essay_answers',
    'process_essay_questions',
    'get_api_key',
    # 공통 유틸리티 (essay에서 export)
    'ROUND_NUMBER_TO_FOLDER',
    'validate_round_number',
    'get_essay_dir',
    'load_questions',
    'save_questions',
    'clean_question_data',
    'init_common',
]
