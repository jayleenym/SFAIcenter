#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험지 검증 및 업데이트 유틸리티
"""

import random
from typing import Dict, List, Any, Tuple
from collections import defaultdict


class ExamValidator:
    """시험지 검증 및 업데이트 클래스"""
    
    @staticmethod
    def check_exam_meets_requirements(exam_data: List[Dict], exam_name: str, 
                                      stats: Dict[str, Any]) -> Tuple[bool, Dict[str, Dict[str, int]]]:
        """
        기존 문제지가 exam_config 요구사항을 만족하는지 확인
        
        Args:
            exam_data: 기존 문제지 데이터
            exam_name: 시험 이름 (예: '금융일반')
            stats: exam_config에서 가져온 통계 정보
            
        Returns:
            (meets_requirements, actual_counts)
            - meets_requirements: 요구사항을 만족하는지 여부
            - actual_counts: {domain: {subdomain: count}} 형태의 실제 문제 수
        """
        if exam_name not in stats:
            return False, {}
        
        # 실제 문제 수 계산 (domain별, subdomain별)
        actual_counts = defaultdict(lambda: defaultdict(int))
        for question in exam_data:
            domain = question.get('domain', '')
            subdomain = question.get('subdomain', '')
            if domain and subdomain:
                actual_counts[domain][subdomain] += 1
        
        # 요구사항과 비교
        meets_requirements = True
        for domain in stats[exam_name].keys():
            if domain not in actual_counts:
                meets_requirements = False
                continue
            
            for subdomain, needed_count in stats[exam_name][domain]['exam_subdomain_distribution'].items():
                actual_count = actual_counts[domain][subdomain]
                if actual_count != needed_count:
                    meets_requirements = False
        
        return meets_requirements, dict(actual_counts)
    
    @staticmethod
    def update_existing_exam(existing_exam_data: List[Dict], exam_name: str,
                            stats: Dict[str, Any], all_data: List[Dict],
                            used_questions: set, logger) -> List[Dict]:
        """
        기존 문제지를 exam_config 요구사항에 맞게 업데이트
        - 부족한 문제 추가
        - 불필요한 문제 제거
        
        Args:
            existing_exam_data: 기존 문제지 데이터
            exam_name: 시험 이름
            stats: exam_config에서 가져온 통계 정보
            all_data: 전체 문제 데이터
            used_questions: 사용된 문제 추적용 set (업데이트됨)
            logger: 로거 인스턴스
            
        Returns:
            업데이트된 문제지 데이터
        """
        if exam_name not in stats:
            return existing_exam_data
        
        # 기존 문제를 domain/subdomain별로 분류
        existing_by_subdomain = defaultdict(list)
        existing_question_ids = set()
        for question in existing_exam_data:
            domain = question.get('domain', '')
            subdomain = question.get('subdomain', '')
            question_id = (question.get('file_id', ''), question.get('tag', ''))
            if domain and subdomain:
                existing_by_subdomain[(domain, subdomain)].append(question)
                existing_question_ids.add(question_id)
        
        # 업데이트된 문제지
        updated_exam_data = []
        
        # domain별로 처리
        for domain in stats[exam_name].keys():
            domain_data = [d for d in all_data if d.get('domain') == domain]
            
            # subdomain별로 처리
            for subdomain, needed_count in stats[exam_name][domain]['exam_subdomain_distribution'].items():
                # 기존 문제 중 해당 subdomain 문제들
                existing_subdomain_questions = existing_by_subdomain.get((domain, subdomain), [])
                existing_count = len(existing_subdomain_questions)
                
                if existing_count == needed_count:
                    # 정확히 필요한 만큼 있으면 그대로 사용
                    updated_exam_data.extend(existing_subdomain_questions)
                    for q in existing_subdomain_questions:
                        question_id = (q.get('file_id', ''), q.get('tag', ''))
                        used_questions.add(question_id)
                
                elif existing_count < needed_count:
                    # 부족한 경우: 기존 문제 유지 + 추가 문제 선택
                    updated_exam_data.extend(existing_subdomain_questions)
                    for q in existing_subdomain_questions:
                        question_id = (q.get('file_id', ''), q.get('tag', ''))
                        used_questions.add(question_id)
                    
                    # 추가로 필요한 문제 수
                    needed_additional = needed_count - existing_count
                    
                    # 사용 가능한 문제 중에서 선택 (기존에 사용되지 않은 것)
                    available_subdomain_data = [
                        d for d in domain_data 
                        if d.get('subdomain') == subdomain 
                        and (d.get('file_id', ''), d.get('tag', '')) not in existing_question_ids
                        and (d.get('file_id', ''), d.get('tag', '')) not in used_questions
                    ]
                    
                    random.shuffle(available_subdomain_data)
                    
                    if len(available_subdomain_data) >= needed_additional:
                        additional_questions = random.sample(available_subdomain_data, needed_additional)
                    else:
                        additional_questions = available_subdomain_data
                        logger.warning(
                            f"  - {subdomain}: 추가 데이터 부족 "
                            f"(기존: {existing_count}, 필요: {needed_count}, "
                            f"사용 가능: {len(available_subdomain_data)})"
                        )
                    
                    updated_exam_data.extend(additional_questions)
                    for q in additional_questions:
                        question_id = (q.get('file_id', ''), q.get('tag', ''))
                        used_questions.add(question_id)
                        existing_question_ids.add(question_id)  # 중복 선택 방지
                
                else:
                    # 초과하는 경우: 필요한 만큼만 선택
                    random.shuffle(existing_subdomain_questions)
                    selected_questions = existing_subdomain_questions[:needed_count]
                    updated_exam_data.extend(selected_questions)
                    for q in selected_questions:
                        question_id = (q.get('file_id', ''), q.get('tag', ''))
                        used_questions.add(question_id)
                    
                    logger.info(
                        f"  - {subdomain}: 초과 문제 제거 "
                        f"(기존: {existing_count}, 필요: {needed_count}, 제거: {existing_count - needed_count})"
                    )
        
        return updated_exam_data

