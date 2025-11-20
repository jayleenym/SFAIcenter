#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중앙화된 로깅 유틸리티
모든 tools 모듈에서 일관된 로깅을 사용하도록 제공
"""

import os
import logging
from typing import Optional, Tuple
from logging.handlers import RotatingFileHandler

# 기본 로깅 설정이 이미 되어있는지 확인
_logging_configured = False


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    use_console: bool = True,
    use_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    로거 설정 및 반환
    
    Args:
        name: 로거 이름 (보통 __name__)
        log_file: 로그 파일명 (None이면 name 기반으로 자동 생성)
        log_dir: 로그 디렉토리 경로 (None이면 SFAICENTER_PATH/logs 사용)
        level: 로깅 레벨 (기본값: INFO)
        format_string: 로그 포맷 문자열 (None이면 기본 포맷 사용)
        use_console: 콘솔 출력 여부
        use_file: 파일 출력 여부
        max_bytes: 로그 파일 최대 크기 (회전 기준)
        backup_count: 보관할 백업 파일 수
    
    Returns:
        설정된 Logger 인스턴스
    """
    global _logging_configured
    
    # 경로 설정
    if log_dir is None:
        try:
            from pipeline.config import SFAICENTER_PATH
            log_dir = os.path.join(SFAICENTER_PATH, 'logs')
        except ImportError:
            # fallback: 현재 파일 기준으로 프로젝트 루트 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))  # core -> tools -> project_root
            log_dir = os.path.join(project_root, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일명 설정
    if log_file is None:
        # name에서 모듈명 추출 (예: tools.pipeline.steps.step1 -> step1)
        module_name = name.split('.')[-1]
        log_file = os.path.join(log_dir, f'{module_name}.log')
    elif not os.path.isabs(log_file):
        log_file = os.path.join(log_dir, log_file)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 이미 핸들러가 있으면 중복 추가 방지
    if logger.handlers:
        return logger
    
    # 부모 로거로의 전파 방지 (중복 로그 방지)
    logger.propagate = False
    
    # 포맷 설정
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format_string)
    
    # 콘솔 핸들러
    if use_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러 (회전 로그)
    if use_file:
        file_handler = RotatingFileHandler(
            log_file,
            mode='a',
            encoding='utf-8',
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 기본 로깅 설정 (한 번만)
    if not _logging_configured:
        logging.basicConfig(
            level=level,
            format=format_string,
            handlers=[]  # 핸들러는 각 로거에서 개별 설정
        )
        _logging_configured = True
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    기존 로거 가져오기 (설정 없이)
    
    Args:
        name: 로거 이름
    
    Returns:
        Logger 인스턴스
    """
    return logging.getLogger(name)


def setup_step_logger(
    step_name: str,
    step_number: Optional[int] = None,
    log_dir: Optional[str] = None,
    level: int = logging.INFO
) -> Tuple[logging.Logger, logging.Handler]:
    """
    파이프라인 step용 로거 설정
    
    Args:
        step_name: step 이름 (예: 'extract_basic')
        step_number: step 번호 (예: 1) - None이면 step_name에서 추출 시도
        log_dir: 로그 디렉토리 경로
        level: 로깅 레벨
    
    Returns:
        (logger, file_handler) 튜플 - file_handler는 나중에 제거할 수 있도록 반환
    """
    # step 번호 추출
    if step_number is None:
        # step_name에서 숫자 추출 시도 (예: 'step1_extract_basic' -> 1)
        import re
        match = re.search(r'step(\d+)', step_name.lower())
        if match:
            step_number = int(match.group(1))
        else:
            step_number = 0
    
    # 로거 이름 생성
    logger_name = f'pipeline.step{step_number}'
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # 부모 로거로의 전파 방지 (중복 로그 방지)
    logger.propagate = False
    
    # 경로 설정
    if log_dir is None:
        try:
            from pipeline.config import SFAICENTER_PATH
            log_dir = os.path.join(SFAICENTER_PATH, 'logs')
        except ImportError:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            log_dir = os.path.join(project_root, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # 로그 파일명
    log_file = os.path.join(log_dir, f'step{step_number}_{step_name}.log')
    
    # 파일 핸들러 생성 (append 모드)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    
    logger.info(f"로그 파일 생성/추가: {log_file}")
    
    return logger, file_handler

