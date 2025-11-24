#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 데이터 포맷화 유틸리티
"""

from typing import Dict, Any


def format_qna_item(qna_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Q&A 항목을 표준 형식으로 포맷화
    
    Args:
        qna_item: 원본 Q&A 항목
    
    Returns:
        포맷화된 Q&A 항목
    """
    return {
        'file_id': qna_item.get('file_id'),
        'tag': qna_item.get('qna_data', {}).get('tag', ''),
        'title': qna_item.get('title'),
        'cat1_domain': qna_item.get('cat1_domain'),
        'cat2_sub': qna_item.get('cat2_sub'),
        'cat3_specific': qna_item.get('cat3_specific'),
        'chapter': qna_item.get('chapter'),
        'page': qna_item.get('page'),
        'qna_type': qna_item.get('qna_type', 'etc'),
        'question': qna_item.get('qna_data', {}).get('description', {}).get('question', ''),
        'options': qna_item.get('qna_data', {}).get('description', {}).get('options', []),
        'answer': qna_item.get('qna_data', {}).get('description', {}).get('answer', ''),
        'explanation': qna_item.get('qna_data', {}).get('description', {}).get('explanation', '')
    }


def should_include_qna_item(qna_item: Dict[str, Any], qna_type: str) -> bool:
    """
    Q&A 항목이 필터링 조건을 만족하는지 확인
    
    Args:
        qna_item: Q&A 항목 (포맷화된 항목 또는 원본 항목)
        qna_type: Q&A 타입
    
    Returns:
        포함 여부
    """
    # 포맷화된 항목인지 확인
    if 'qna_data' in qna_item:
        # 원본 형식
        qna_data_desc = qna_item.get('qna_data', {}).get('description', {})
        options = qna_data_desc.get('options', [])
        answer = qna_data_desc.get('answer', '')
    else:
        # 포맷화된 형식
        options = qna_item.get('options', [])
        answer = qna_item.get('answer', '')
    
    # 각 타입별 필터링 조건 확인
    if qna_type == "multiple-choice":
        # 객관식: OX 문제 제외, 선지가 3개 이상인 경우
        return (options is not None) and (len(options) > 2)
    elif qna_type == "short-answer":
        # 단답형: 답변이 있고, 답변이 삭제되지 않은 경우
        return (answer is not None) and (answer != "삭제")
    elif qna_type == "essay":
        # 서술형: 답변이 있는 경우
        return answer is not None
    elif qna_type == "etc":
        # etc 타입은 모두 포함
        return True
    
    return False

