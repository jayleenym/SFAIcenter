#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서술형 평가 유틸리티
- 모범답안 로드
- API 키 설정
"""

import os
import json
import configparser
from typing import Dict, Tuple, Optional
from tools.core.llm_query import LLMQuery


def load_best_answers(best_ans_file: str, logger) -> Dict[Tuple[str, str], str]:
    """
    모범답안 로드
    
    Args:
        best_ans_file: 모범답안 파일 경로
        logger: 로거 인스턴스
    
    Returns:
        {(file_id, tag): essay_answer} 형태의 딕셔너리
    """
    best_answers_dict = {}
    if os.path.exists(best_ans_file):
        logger.info(f"모범답안 로드 중: {best_ans_file}")
        with open(best_ans_file, 'r', encoding='utf-8') as f:
            best_answers = json.load(f)
        # file_id와 tag를 키로 하는 딕셔너리 생성
        for ba in best_answers:
            key = (ba.get('file_id'), ba.get('tag'))
            best_answers_dict[key] = ba.get('essay_answer', ba.get('answer', ''))
        logger.info(f"모범답안 {len(best_answers_dict)}개 로드 완료")
    else:
        logger.warning(f"모범답안 파일을 찾을 수 없습니다: {best_ans_file}")
    
    return best_answers_dict


def setup_llm_with_api_key(project_root_path: str, logger) -> LLMQuery:
    """
    API 키 설정 및 LLM 인스턴스 생성
    
    Args:
        project_root_path: 프로젝트 루트 경로
        logger: 로거 인스턴스
    
    Returns:
        LLMQuery 인스턴스
    """
    api_key = None
    try:
        config_path = os.path.join(project_root_path, 'llm_config.ini')
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            if config.has_option("OPENROUTER", "key_essay"):
                api_key = config.get("OPENROUTER", "key_essay")
                logger.info("key_essay를 사용하여 LLM 호출합니다.")
            elif config.has_option("OPENROUTER", "key"):
                api_key = config.get("OPENROUTER", "key")
                logger.info("key를 사용하여 LLM 호출합니다.")
    except Exception as e:
        logger.warning(f"API 키를 읽는 중 오류 발생: {e}")
    
    return LLMQuery(api_key=api_key) if api_key else LLMQuery()

