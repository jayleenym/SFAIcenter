#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 데이터 포맷화 유틸리티
"""

import re
from typing import Dict, Any


def format_qna_item(qna_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Q&A 항목을 표준 형식으로 포맷화
    
    Args:
        qna_item: 원본 Q&A 항목
    
    Returns:
        포맷화된 Q&A 항목
    """
    formatted = {
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
    
    # additional_tag_data 포함 (태그 대치를 위해 나중에 필요)
    if 'additional_tag_data' in qna_item:
        formatted['additional_tag_data'] = qna_item.get('additional_tag_data', [])
    
    return formatted


def should_include_qna_item(qna_item: Dict[str, Any], qna_type: str, qna_data: Dict[str, Any] = None) -> bool:
    """
    Q&A 항목이 필터링 조건을 만족하는지 확인
    
    Args:
        qna_item: Q&A 항목 (포맷화된 항목 또는 원본 항목)
        qna_type: Q&A 타입
        qna_data: 태그 치환된 qna_data (선택적, 제공되면 우선 사용)
    
    Returns:
        포함 여부
    """
    # qna_data가 직접 제공된 경우 우선 사용 (태그 치환된 경우)
    if qna_data is not None:
        qna_data_desc = qna_data.get('description', {})
        question = qna_data_desc.get('question', '')
        options = qna_data_desc.get('options', [])
        answer = qna_data_desc.get('answer', '')
        explanation = qna_data_desc.get('explanation', '')
    # 포맷화된 항목인지 확인
    elif 'qna_data' in qna_item:
        # 원본 형식
        qna_data_desc = qna_item.get('qna_data', {}).get('description', {})
        question = qna_data_desc.get('question', '')
        options = qna_data_desc.get('options', [])
        answer = qna_data_desc.get('answer', '')
        explanation = qna_data_desc.get('explanation', '')
    else:
        # 포맷화된 형식
        question = qna_item.get('question', '')
        options = qna_item.get('options', [])
        answer = qna_item.get('answer', '')
        explanation = qna_item.get('explanation', '')
    
    # img 또는 etc 태그가 있는지 확인 (문제/선지에서 제외)
    img_pattern = r'\{img_\d{4}_\d{4}\}'
    etc_pattern = r'\{etc_\d{4}_\d{4}\}'
    
    # question에서 체크
    if question and (re.search(img_pattern, str(question)) or re.search(etc_pattern, str(question))):
        return False
    
    # options에서 체크
    if options:
        if isinstance(options, list):
            for option in options:
                if option and (re.search(img_pattern, str(option)) or re.search(etc_pattern, str(option))):
                    return False
        else:
            if re.search(img_pattern, str(options)) or re.search(etc_pattern, str(options)):
                return False
    
    # answer와 explanation은 체크하지 않음 (문제/선지만 체크)
    
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

