#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline 패키지 - 데이터 처리 파이프라인

이 패키지는 Q&A 추출부터 평가까지의 전체 파이프라인을 제공합니다:
- Step1: Q&A 추출 및 Domain 분류
- Step2: 시험문제 생성 (일반/변형)
- Step3: 문제 변형
- Step6: 시험 평가
- Step9: 서술형 변환 및 평가
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

__version__ = '1.0.0'

