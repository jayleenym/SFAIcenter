#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multiple 패키지 - 객관식 문제 변형 기능

이 패키지는 객관식 문제 변형 기능을 제공합니다:
- QuestionTransformerOrchestrator: 변형 프로세스 전체 관리 (Step3 진입점)
- AnswerTypeClassifier: 답변 유형 분류 (right/wrong/abcd)
- MultipleChoiceTransformer: 객관식 문제 변형 (right↔wrong, ABCD)
- load_transformed_questions: 변형된 문제 로드
- create_transformed_exam: 변형 시험지 생성

사용 예시:
    # Step3에서 사용
    from tools.transformed.multiple import QuestionTransformerOrchestrator
    orchestrator = QuestionTransformerOrchestrator(...)
    result = orchestrator.transform_questions(...)
    
    # 분류기 직접 사용
    from tools.transformed.multiple import AnswerTypeClassifier
    classifier = AnswerTypeClassifier(onedrive_path=onedrive_path)
    result = classifier.process_all_questions(data_path=data_path)
"""

# 오케스트레이터 (Step3 진입점)
from .question_transformer import QuestionTransformerOrchestrator

# 답변 유형 분류
from .answer_type_classifier import AnswerTypeClassifier

# 객관식 문제 변형
from .change_question_and_options import MultipleChoiceTransformer

# 변형 문제 로드 유틸리티
from .load_transformed_questions import load_transformed_questions

# 변형 시험지 생성
from .create_transformed_exam import create_transformed_exam


__all__ = [
    # 오케스트레이터 (Step3 진입점)
    'QuestionTransformerOrchestrator',
    # 답변 유형 분류
    'AnswerTypeClassifier',
    # 객관식 변형
    'MultipleChoiceTransformer',
    'load_transformed_questions',
    'create_transformed_exam',
]

