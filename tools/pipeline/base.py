#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파이프라인 기본 클래스

모든 파이프라인 단계의 기본이 되는 클래스를 정의합니다.
공통 유틸리티 인스턴스와 로깅 설정을 제공합니다.
"""

from typing import Optional, Any

# 프로젝트 경로 설정 (tools 패키지에서 관리)
from tools import ONEDRIVE_PATH, PROJECT_ROOT_PATH

# core 유틸리티
from tools.core import (
    FileManager, 
    TextProcessor, 
    JSONHandler,
    LLMQuery,
    setup_logger,
    setup_step_logger,
)

# 데이터 처리
from tools.data_processing import JSONCleaner


class PipelineBase:
    """
    파이프라인 기본 클래스
    
    모든 파이프라인 단계에서 상속받아 사용합니다.
    공통 유틸리티 인스턴스와 로깅을 제공합니다.
    
    Attributes:
        onedrive_path: OneDrive 데이터 경로
        project_root_path: 프로젝트 루트 경로
        config_path: LLM 설정 파일 경로
        file_manager: 파일 관리 유틸리티
        text_processor: 텍스트 처리 유틸리티
        json_handler: JSON 처리 유틸리티
        json_cleaner: JSON 정리 유틸리티
        llm_query: LLM 쿼리 클라이언트
        logger: 로거 인스턴스
    """
    
    def __init__(
        self, 
        base_path: Optional[str] = None, 
        config_path: Optional[str] = None, 
        onedrive_path: Optional[str] = None, 
        project_root_path: Optional[str] = None
    ):
        """
        Args:
            base_path: 기본 데이터 경로 (None이면 ONEDRIVE_PATH 사용)
            config_path: LLM 설정 파일 경로 (None이면 PROJECT_ROOT_PATH/llm_config.ini 사용)
            onedrive_path: OneDrive 경로 (None이면 전역 ONEDRIVE_PATH 사용)
            project_root_path: 프로젝트 루트 경로 (None이면 전역 PROJECT_ROOT_PATH 사용)
        """
        import os
        
        # 경로 설정
        self.onedrive_path = onedrive_path or ONEDRIVE_PATH
        self.project_root_path = project_root_path or PROJECT_ROOT_PATH
        
        # base_path가 지정되지 않으면 onedrive_path 사용
        if base_path is None:
            base_path = self.onedrive_path
        
        # config_path 결정
        if config_path is None:
            default_config = os.path.join(self.project_root_path, 'llm_config.ini')
            config_path = default_config if os.path.exists(default_config) else None
        elif not os.path.isabs(config_path):
            config_path = os.path.join(self.project_root_path, config_path)
        
        self.config_path = config_path
        
        # 유틸리티 인스턴스/클래스 참조
        self.file_manager = FileManager(base_path)
        # TextProcessor, JSONHandler는 모든 메서드가 @staticmethod이므로 클래스 참조
        self.text_processor = TextProcessor
        self.json_handler = JSONHandler
        self.json_cleaner = JSONCleaner()
        
        # LLM 클라이언트 (config가 있을 때만)
        self.llm_query: Optional[LLMQuery] = None
        if config_path and os.path.exists(config_path):
            try:
                self.llm_query = LLMQuery(config_path)
            except Exception as e:
                # LLM 초기화 실패해도 파이프라인은 동작 가능
                pass
        
        # 로깅 설정
        self._step_log_handler = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """기본 로깅 설정"""
        self.logger = setup_logger(
            name=__name__,
            use_file=False,  # step별로 파일 핸들러 추가
            use_console=True
        )
    
    def _setup_step_logging(self, step_name: str, step_number: int) -> None:
        """
        단계별 로그 파일 핸들러 설정
        
        Args:
            step_name: 단계 이름 (예: 'preprocessing', 'extract_basic')
            step_number: 단계 번호 (1~9)
        """
        step_logger, file_handler = setup_step_logger(
            step_name=step_name,
            step_number=step_number
        )
        self.logger.addHandler(file_handler)
        self._step_log_handler = file_handler
    
    def _remove_step_logging(self) -> None:
        """단계별 로그 파일 핸들러 제거"""
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
            self._step_log_handler.close()
            self._step_log_handler = None


# 하위 호환성을 위한 export (steps에서 사용)
# 실제 import는 필요할 때 각 모듈에서 직접 수행
__all__ = ['PipelineBase']
