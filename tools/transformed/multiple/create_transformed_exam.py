#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
변형된 시험지 생성 유틸리티
- 원본 시험지의 각 문제에 대해 변형된 문제를 찾아서 새로운 시험지 생성
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict


def create_transformed_exam(original_exam: List[Dict[str, Any]], 
                           transformed_questions: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    원본 시험지의 각 문제에 대해 변형된 문제를 찾아서 새로운 시험지 생성
    - 기존 시험지의 question, options, answer를 변형된 문제의 것으로 교체
    - 기존 시험지의 explanation을 original_explanation으로 키 이름 변경
    - 변형된 문제의 explanation을 explanation 키에 넣기
    
    Args:
        original_exam: 원본 시험지 데이터
        transformed_questions: 변형된 문제 딕셔너리
    
    Returns:
        tuple: (변형된 시험지, 변형되지 않은 문제 리스트, 통계 정보)
    """
    def create_question_id(file_id: str, tag: str) -> str:
        """question_id 생성 (file_id_tag 형식)"""
        return f"{file_id}_{tag}"
    
    new_exam = []
    missing_questions = []  # 변형되지 않은 문제들
    
    # 통계 수집용
    stats = {
        'total_questions': len(original_exam),
        'transformed_count': 0,
        'not_transformed_count': 0,
        'pick_abcd': 0,
        'pick_right_2': 0,
        'pick_right_3': 0,
        'pick_right_4': 0,
        'pick_right_5': 0,
        'pick_wrong_2': 0,
        'pick_wrong_3': 0,
        'pick_wrong_4': 0,
        'pick_wrong_5': 0,
        'breakdown': {
            'pick_abcd': [],
            'pick_right_2': [],
            'pick_right_3': [],
            'pick_right_4': [],
            'pick_right_5': [],
            'pick_wrong_2': [],
            'pick_wrong_3': [],
            'pick_wrong_4': [],
            'pick_wrong_5': []
        }
    }
    
    for original_q in original_exam:
        file_id = original_q.get('file_id', '')
        tag = original_q.get('tag', '')
        
        if not file_id or not tag:
            # file_id나 tag가 없으면 원본 그대로 추가하고 누락으로 표시
            new_exam.append(original_q)
            missing_questions.append(original_q)
            stats['not_transformed_count'] += 1
            continue
        
        question_id = create_question_id(file_id, tag)
        
        # 변형된 문제 찾기 (우선순위: pick_abcd > pick_right > pick_wrong)
        transformed_q = None
        transform_type = None
        set_num = None
        
        if question_id in transformed_questions['pick_abcd']:
            transformed_q = transformed_questions['pick_abcd'][question_id]
            transform_type = 'pick_abcd'
            set_num = transformed_q.get('_set_num')
        elif question_id in transformed_questions['pick_right']:
            transformed_q = transformed_questions['pick_right'][question_id]
            transform_type = 'pick_right'
            set_num = transformed_q.get('_set_num')
        elif question_id in transformed_questions['pick_wrong']:
            transformed_q = transformed_questions['pick_wrong'][question_id]
            transform_type = 'pick_wrong'
            set_num = transformed_q.get('_set_num')
        
        # 새로운 문제 객체 생성 (원본의 모든 필드를 복사)
        new_q = original_q.copy()
        
        if transformed_q:
            # 변형된 문제가 있으면 question, options, answer 교체
            new_q['question'] = transformed_q.get('question', original_q.get('question', ''))
            new_q['options'] = transformed_q.get('options', original_q.get('options', []))
            new_q['answer'] = transformed_q.get('answer', original_q.get('answer', ''))
            
            # explanation 처리
            # 기존 시험지의 explanation을 original_explanation으로
            original_explanation = original_q.get('explanation', '')
            if original_explanation:
                new_q['original_explanation'] = original_explanation
            
            # 변형된 문제의 explanation을 explanation으로
            transformed_explanation = transformed_q.get('explanation', '')
            if transformed_explanation:
                new_q['explanation'] = transformed_explanation
            elif 'explanation' in new_q:
                # 변형된 문제에 explanation이 없으면 원본 유지
                pass
            
            # 통계 업데이트
            stats['transformed_count'] += 1
            stat_key = None
            if transform_type == 'pick_abcd':
                stats['pick_abcd'] += 1
                stat_key = 'pick_abcd'
            elif transform_type == 'pick_right' and set_num:
                stats[f'pick_right_{set_num}'] += 1
                stat_key = f'pick_right_{set_num}'
            elif transform_type == 'pick_wrong' and set_num:
                stats[f'pick_wrong_{set_num}'] += 1
                stat_key = f'pick_wrong_{set_num}'
            
            # breakdown에 question_id 추가
            if stat_key and stat_key in stats['breakdown']:
                stats['breakdown'][stat_key].append(question_id)
        else:
            # 변형된 문제가 없으면 원본 그대로 (explanation은 그대로 유지)
            missing_questions.append(original_q)
            stats['not_transformed_count'] += 1
        
        new_exam.append(new_q)
    
    return new_exam, missing_questions, stats

