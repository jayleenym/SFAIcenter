#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core 패키지 - 핵심 유틸리티 클래스

이 패키지는 프로젝트 전체에서 사용되는 핵심 유틸리티를 제공합니다:
- FileManager: 파일 및 경로 관리, Excel 데이터 처리
- TextProcessor: 텍스트 처리 유틸리티  
- JSONHandler: JSON 파일 읽기/쓰기, 포맷 변환
- LLMQuery: LLM API 쿼리 (OpenRouter, vLLM)
- ExamConfig: 시험 설정 파일 로더
- Logger 유틸리티: 로깅 설정
"""

from .utils import FileManager, TextProcessor, JSONHandler
from .llm_query import LLMQuery
from .exam_config import ExamConfig, load_exam_config
from .logger import setup_logger, get_logger, setup_step_logger

__all__ = [
    # 파일 및 데이터 처리
    'FileManager',
    'TextProcessor', 
    'JSONHandler',
    # LLM 쿼리
    'LLMQuery',
    # 시험 설정
    'ExamConfig',
    'load_exam_config',
    # 로깅
    'setup_logger',
    'get_logger',
    'setup_step_logger',
]
