#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
essay 패키지 공통 유틸리티

서술형 문제 변환 모듈에서 공통으로 사용하는 상수와 헬퍼 함수들을 제공합니다.
"""

import os
import json
from typing import Dict, Any, Optional, Callable, List

# 라운드 번호 → 폴더명 매핑
ROUND_NUMBER_TO_FOLDER = {
    '1': '1st',
    '2': '2nd', 
    '3': '3rd',
    '4': '4th',
    '5': '5th'
}


def validate_round_number(round_number: str, log_func: Callable = print) -> Optional[str]:
    """
    round_number 검증 및 폴더명 반환
    
    Args:
        round_number: 라운드 번호 ('1', '2', ...)
        log_func: 로그 출력 함수
        
    Returns:
        폴더명 ('1st', '2nd', ...) 또는 None (검증 실패 시)
    """
    if not round_number:
        log_func("오류: round_number가 필요합니다.")
        return None
    return ROUND_NUMBER_TO_FOLDER.get(str(round_number), '1st')


def get_essay_dir(onedrive_path: str) -> str:
    """essay 디렉토리 경로 반환"""
    return os.path.join(onedrive_path, 'evaluation', 'eval_data', '9_multiple_to_essay')


def load_questions(input_file: str, log_func: Callable = print, step_name: str = "") -> Optional[List[Dict[str, Any]]]:
    """
    입력 파일에서 질문 데이터 로드
    
    Args:
        input_file: 입력 JSON 파일 경로
        log_func: 로그 출력 함수
        step_name: 단계 이름 (로그용)
        
    Returns:
        문제 리스트 또는 None (파일 없음 시)
    """
    if not os.path.exists(input_file):
        log_func(f"오류: 입력 파일이 존재하지 않습니다: {input_file}")
        return None
    
    log_func(f"{step_name} 입력 파일 읽기: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    log_func(f"총 {len(questions)}개의 문제 처리 시작")
    return questions


def save_questions(questions: List[Dict[str, Any]], output_file: str, log_func: Callable = print, step_name: str = "") -> None:
    """
    질문 데이터를 파일에 저장
    
    Args:
        questions: 저장할 문제 리스트
        output_file: 출력 JSON 파일 경로
        log_func: 로그 출력 함수
        step_name: 단계 이름 (로그용)
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    log_func(f"{step_name} 저장: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    log_func(f"{step_name} 완료! 총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")


def clean_question_data(question: Dict[str, Any]) -> None:
    """
    질문 데이터의 특수 문자 정리 (in-place 수정)
    
    Args:
        question: 정리할 문제 딕셔너리
    """
    if 'question' in question:
        question['question'] = question['question'].replace("\\'", "'")
    if 'options' in question:
        question['options'] = [opt.replace("\\'", "'") for opt in question['options']]
    if 'explanation' in question:
        question['explanation'] = question['explanation'].replace("\\'", "'")


def init_common(llm=None, onedrive_path: Optional[str] = None, 
                log_func: Optional[Callable] = None, logger=None):
    """
    공통 초기화 함수
    
    Args:
        llm: LLMQuery 인스턴스 (None이면 새로 생성)
        onedrive_path: OneDrive 경로 (None이면 기본값 사용)
        log_func: 로그 함수 (None이면 logger.info 또는 print 사용)
        logger: 로거 인스턴스
        
    Returns:
        (llm, onedrive_path, log_func) 튜플
    """
    # 지연 import로 순환 참조 방지
    if onedrive_path is None:
        from tools import ONEDRIVE_PATH
        onedrive_path = ONEDRIVE_PATH
    
    if llm is None:
        from tools.core.llm_query import LLMQuery
        llm = LLMQuery()
    
    if log_func is None:
        log_func = logger.info if logger else print
    
    return llm, onedrive_path, log_func

