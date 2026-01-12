#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline.steps 패키지 - 파이프라인 각 단계 구현

각 단계는 PipelineBase를 상속받아 execute() 메서드로 실행됩니다.

단계 목록:
    - Step1ExtractQnAWDomain: Q&A 추출 및 Domain/Subdomain 분류
    - Step2CreateExams: 시험문제 생성 (일반/변형)
    - Step3TransformQuestions: 객관식 문제 변형 (right↔wrong, abcd)
    - Step6Evaluate: 시험지 평가 (객관식/서술형)
    - Step9MultipleEssay: 객관식 → 서술형 변환

실행 흐름:
    Step1 → Step2 → Step3 → Step6 (일반)
    Step1 → Step9 → Step6 (서술형)

사용 예시:
    from tools.pipeline.steps import Step1ExtractQnAWDomain
    step1 = Step1ExtractQnAWDomain()
    result = step1.execute(cycle=1, levels=['Lv2', 'Lv3_4'])
"""

from .step1_extract_qna_w_domain import Step1ExtractQnAWDomain
from .step2_create_exams import Step2CreateExams
from .step3_transform_questions import Step3TransformQuestions
from .step6_evaluate import Step6Evaluate
from .step9_multiple_essay import Step9MultipleEssay

__all__ = [
    'Step1ExtractQnAWDomain',
    'Step2CreateExams',
    'Step3TransformQuestions',
    'Step6Evaluate',
    'Step9MultipleEssay',
]

