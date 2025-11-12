#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파이프라인 기본 클래스
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

from .config import ONEDRIVE_PATH, PROJECT_ROOT_PATH, SFAICENTER_PATH

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))
sys.path.insert(0, PROJECT_ROOT_PATH)

from core.utils import FileManager, TextProcessor, JSONHandler
from core.llm_query import LLMQuery
from data_processing.json_cleaner import JSONCleaner

# qna processing 및 evaluation 모듈 import (tools 폴더에서 우선 시도)
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(current_dir)  # pipeline -> tools
sys.path.insert(0, tools_dir)

# 전역 변수로 export (steps에서 사용)
try:
    from qna.processing.qna_subdomain_classifier import QnASubdomainClassifier
    from evaluation.fill_multiple_choice_data import (
        load_json_file, create_lookup_dict, fill_multiple_choice_data
    )
    from evaluation.multiple_eval_by_model import (
        run_eval_pipeline,
        load_data_from_directory,
        save_results_to_excel,
        print_evaluation_summary
    )
except ImportError:
    # fallback: tools 폴더에서 시도
    tools_dir = os.path.dirname(current_dir)  # pipeline -> tools
    sys.path.insert(0, tools_dir)
    try:
        from qna.processing.qna_subdomain_classifier import QnASubdomainClassifier
        from evaluation.fill_multiple_choice_data import (
            load_json_file, create_lookup_dict, fill_multiple_choice_data
        )
        from evaluation.multiple_eval_by_model import (
            run_eval_pipeline,
            load_data_from_directory,
            save_results_to_excel,
            print_evaluation_summary
        )
    except ImportError:
        QnASubdomainClassifier = None
        load_json_file = None
        create_lookup_dict = None
        fill_multiple_choice_data = None
        run_eval_pipeline = None
        load_data_from_directory = None
        save_results_to_excel = None
        print_evaluation_summary = None

# steps에서 사용할 수 있도록 export
__all__ = [
    'PipelineBase',
    'QnASubdomainClassifier',
    'load_json_file',
    'create_lookup_dict',
    'fill_multiple_choice_data',
    'run_eval_pipeline',
    'load_data_from_directory',
    'save_results_to_excel',
    'print_evaluation_summary'
]


class PipelineBase:
    """파이프라인 기본 클래스"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        """
        Args:
            base_path: 기본 데이터 경로 (None이면 ONEDRIVE_PATH 사용)
            config_path: LLM 설정 파일 경로 (None이면 PROJECT_ROOT_PATH/llm_config.ini 사용)
            onedrive_path: OneDrive 경로 (None이면 전역 ONEDRIVE_PATH 사용)
            project_root_path: 프로젝트 루트 경로 (None이면 전역 PROJECT_ROOT_PATH 사용)
        """
        # 경로 설정
        self.onedrive_path = onedrive_path if onedrive_path else ONEDRIVE_PATH
        self.project_root_path = project_root_path if project_root_path else PROJECT_ROOT_PATH
        
        # base_path가 지정되지 않으면 onedrive_path 사용
        if base_path is None:
            base_path = self.onedrive_path
        
        # config_path가 지정되지 않으면 프로젝트 루트에서 찾기
        if config_path is None:
            config_path = os.path.join(self.project_root_path, 'llm_config.ini')
            if not os.path.exists(config_path):
                config_path = None
        
        self.file_manager = FileManager(base_path)
        self.text_processor = TextProcessor()
        self.json_handler = JSONHandler()
        self.json_cleaner = JSONCleaner()
        self.llm_query = LLMQuery(config_path) if config_path else None
        
        # 로깅 설정
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 설정"""
        # SFAICENTER_PATH/logs에 로그 저장
        log_dir = os.path.join(SFAICENTER_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

