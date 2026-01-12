#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline 패키지 - 데이터 처리 파이프라인

이 패키지는 Q&A 추출부터 평가까지의 전체 파이프라인을 제공합니다.

단계 구성:
    - Step1 (extract_qna_w_domain): Q&A 추출 및 Domain/Subdomain 분류
    - Step2 (create_exam): 시험문제 생성 (일반/변형)
    - Step3 (transform_questions): 객관식 문제 변형 (right↔wrong, abcd)
    - Step6 (evaluate_exams): 시험지 평가 (객관식/서술형)
    - Step9 (evaluate_essay): 객관식 → 서술형 변환

사용 방법:
    # 전체 파이프라인 실행
    from tools.pipeline import Pipeline
    pipeline = Pipeline()
    result = pipeline.run_full_pipeline(steps=['extract_qna_w_domain', 'create_exam'])
    
    # 개별 단계 실행
    from tools.pipeline.steps import Step1ExtractQnAWDomain
    step1 = Step1ExtractQnAWDomain()
    result = step1.execute(cycle=1)

주요 클래스:
    - Pipeline: 전체 파이프라인 오케스트레이터
    - PipelineBase: 모든 단계의 기본 클래스 (유틸리티 및 로깅 제공)
"""

from tools import ONEDRIVE_PATH, PROJECT_ROOT_PATH
from .base import PipelineBase
from .main import Pipeline

__all__ = [
    # 경로 (하위 호환성)
    'ONEDRIVE_PATH',
    'PROJECT_ROOT_PATH',
    # 클래스
    'PipelineBase',
    'Pipeline',
]

__version__ = '1.1.0'

