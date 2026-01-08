#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험지 검증 및 업데이트 유틸리티
"""

import re
import random
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict


# 원문자 번호 상수
CIRCLED_NUMBERS = {'①', '②', '③', '④', '⑤'}
CIRCLED_NUMBERS_PATTERN = re.compile(r'[①②③④⑤]')


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
    
    @staticmethod
    def validate_multiple_choice_format(exam_data: List[Dict]) -> Dict[str, List[Dict[str, Any]]]:
        """
        multiple-choice 문제의 형식을 검증
        
        검증 조건:
        1. options의 각 항목이 ①②③④⑤ 중 하나로 시작해야 함
        2. answer에 ①②③④⑤ 중 하나의 번호만 포함되어야 함
        
        Args:
            exam_data: 문제 데이터 리스트
            
        Returns:
            {
                'invalid_options': [...],  # options 형식이 잘못된 문제들
                'invalid_answer': [...],   # answer 형식이 잘못된 문제들
                'all_invalid': [...]       # 모든 유효하지 않은 문제들 (중복 제거)
            }
            각 항목은 {'file_id': str, 'tag': str, 'reason': str, 'details': Any} 형태
        """
        invalid_options = []
        invalid_answer = []
        all_invalid_ids: Set[Tuple[str, str]] = set()
        
        for question in exam_data:
            # multiple-choice 문제만 검증
            qna_type = question.get('qna_type', '')
            if qna_type != 'multiple-choice':
                continue
            
            file_id = question.get('file_id', '')
            tag = question.get('tag', '')
            options = question.get('options', [])
            answer = question.get('answer', '')
            
            # 1. options 검증: 각 항목이 ①②③④⑤ 중 하나로 시작해야 함
            options_invalid = False
            invalid_option_details = []
            
            for idx, option in enumerate(options):
                if not option or not isinstance(option, str):
                    options_invalid = True
                    invalid_option_details.append({
                        'index': idx,
                        'option': option,
                        'reason': '빈 옵션 또는 문자열이 아님'
                    })
                    continue
                
                # 옵션 앞의 공백 제거 후 첫 문자 확인
                stripped_option = option.strip()
                if not stripped_option:
                    options_invalid = True
                    invalid_option_details.append({
                        'index': idx,
                        'option': option,
                        'reason': '공백만 있는 옵션'
                    })
                    continue
                
                first_char = stripped_option[0]
                if first_char not in CIRCLED_NUMBERS:
                    options_invalid = True
                    invalid_option_details.append({
                        'index': idx,
                        'option': option[:50] + '...' if len(option) > 50 else option,
                        'first_char': first_char,
                        'reason': f'①②③④⑤로 시작하지 않음 (시작 문자: "{first_char}")'
                    })
            
            if options_invalid:
                invalid_options.append({
                    'file_id': file_id,
                    'tag': tag,
                    'reason': 'options 형식 오류',
                    'details': invalid_option_details
                })
                all_invalid_ids.add((file_id, tag))
            
            # 2. answer 검증: ①②③④⑤ 중 하나의 번호만 포함되어야 함
            answer_invalid = False
            answer_reason = ''
            
            if not answer or not isinstance(answer, str):
                answer_invalid = True
                answer_reason = '빈 답변 또는 문자열이 아님'
            else:
                # answer에서 원문자 번호 찾기
                found_numbers = CIRCLED_NUMBERS_PATTERN.findall(answer)
                
                if len(found_numbers) == 0:
                    answer_invalid = True
                    answer_reason = f'①②③④⑤ 번호가 없음 (answer: "{answer}")'
                elif len(found_numbers) > 1:
                    # 중복 번호 체크 (같은 번호가 여러 번 나온 경우는 허용할 수도 있음)
                    unique_numbers = set(found_numbers)
                    if len(unique_numbers) > 1:
                        answer_invalid = True
                        answer_reason = f'여러 개의 다른 번호가 포함됨 (발견: {found_numbers}, answer: "{answer}")'
            
            if answer_invalid:
                invalid_answer.append({
                    'file_id': file_id,
                    'tag': tag,
                    'reason': 'answer 형식 오류',
                    'details': answer_reason
                })
                all_invalid_ids.add((file_id, tag))
        
        # all_invalid: 중복 제거된 전체 invalid 문제 목록
        all_invalid = []
        seen_ids = set()
        for item in invalid_options + invalid_answer:
            key = (item['file_id'], item['tag'])
            if key not in seen_ids:
                seen_ids.add(key)
                all_invalid.append({
                    'file_id': item['file_id'],
                    'tag': item['tag']
                })
        
        return {
            'invalid_options': invalid_options,
            'invalid_answer': invalid_answer,
            'all_invalid': all_invalid,
            'summary': {
                'total_multiple_choice': sum(1 for q in exam_data if q.get('qna_type') == 'multiple-choice'),
                'invalid_options_count': len(invalid_options),
                'invalid_answer_count': len(invalid_answer),
                'total_invalid_count': len(all_invalid)
            }
        }
    
    @staticmethod
    def print_validation_report(validation_result: Dict[str, Any], verbose: bool = True) -> str:
        """
        검증 결과를 보기 좋게 출력
        
        Args:
            validation_result: validate_multiple_choice_format의 반환값
            verbose: 상세 정보 출력 여부
            
        Returns:
            포맷된 리포트 문자열
        """
        summary = validation_result['summary']
        lines = []
        
        lines.append("=" * 60)
        lines.append("Multiple Choice 문제 형식 검증 결과")
        lines.append("=" * 60)
        lines.append(f"전체 multiple-choice 문제 수: {summary['total_multiple_choice']}")
        lines.append(f"options 형식 오류: {summary['invalid_options_count']}개")
        lines.append(f"answer 형식 오류: {summary['invalid_answer_count']}개")
        lines.append(f"총 오류 문제 수 (중복 제거): {summary['total_invalid_count']}개")
        lines.append("-" * 60)
        
        if verbose and validation_result['invalid_options']:
            lines.append("\n[Options 형식 오류 목록]")
            for item in validation_result['invalid_options']:
                lines.append(f"\n  file_id: {item['file_id']}, tag: {item['tag']}")
                for detail in item['details']:
                    lines.append(f"    - {detail['reason']}")
                    if 'option' in detail:
                        lines.append(f"      옵션 내용: {detail['option']}")
        
        if verbose and validation_result['invalid_answer']:
            lines.append("\n[Answer 형식 오류 목록]")
            for item in validation_result['invalid_answer']:
                lines.append(f"\n  file_id: {item['file_id']}, tag: {item['tag']}")
                lines.append(f"    - {item['details']}")
        
        lines.append("\n" + "=" * 60)
        lines.append("[수정 필요 문제 목록 (file_id, tag)]")
        lines.append("-" * 60)
        for item in validation_result['all_invalid']:
            lines.append(f"  {item['file_id']}, {item['tag']}")
        
        return "\n".join(lines)

