#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5단계: 시험문제 만들기
- 1st/2nd/3rd/4th/5th 총 5세트의 시험문제를 만듬
- exam_config.json 파일 참고하여 갯수 지정
"""

import os
import json
import random
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from ..base import PipelineBase
from core.exam_config import ExamConfig
from exam.exam_validator import ExamValidator


class Step5CreateExam(PipelineBase):
    """5단계: 시험문제 만들기"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, num_sets: int = 5, seed: int = 42) -> Dict[str, Any]:
        """
        5단계: 시험문제 만들기
        - 1st/2nd/3rd/4th/5th 총 5세트의 시험문제를 만듬
        - exam_config.json 파일 참고하여 갯수 지정
        
        Args:
            num_sets: 생성할 시험 세트 개수 (기본값: 5)
            seed: 랜덤 시드 값 (기본값: 42, 동일한 결과를 위해 고정)
        """
        # 랜덤 시드 설정 (재현 가능한 결과를 위해)
        random.seed(seed)
        self.logger.info(f"=== 5단계: 시험문제 만들기 ({num_sets}세트, seed={seed}) ===")
        
        # 로깅 설정
        self._setup_step_logging('create_exam', 5)
        
        try:
            # 세트 이름 매핑
            set_names = {
                1: '1st',
                2: '2nd',
                3: '3rd',
                4: '4th',
                5: '5th'
            }
            
            # exam_config.json에서 통계 정보 로드
            try:
                exam_config = ExamConfig(onedrive_path=self.onedrive_path)
                stats = exam_config.get_exam_statistics()
                self.logger.info("exam_config.json에서 통계 정보 로드 완료")
            except Exception as e:
                self.logger.error(f"exam_config.json 파일 로드 실패: {e}")
                return {'success': False, 'error': f'설정 파일 로드 실패: {e}'}
            
            # 전체 데이터 파일
            all_data_file = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '2_subdomain', 'multiple_subdomain_classified_ALL.json'
            )
            
            if not os.path.exists(all_data_file):
                self.logger.error(f"전체 데이터 파일을 찾을 수 없습니다: {all_data_file}")
                return {'success': False, 'error': f'데이터 파일 없음: {all_data_file}'}
            
            # 전체 데이터 로드
            with open(all_data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            self.logger.info(f"전체 데이터 로딩 완료: {len(all_data)}개 문제")
            
            # 사용된 문제 추적
            used_questions = set()
            
            # 출력 디렉토리
            exam_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '4_multiple_exam'
            )
            os.makedirs(exam_dir, exist_ok=True)
            
            # 4개의 과목별로 처리
            for exam_name in stats.keys():
                self.logger.info(f"{'='*50}")
                self.logger.info(f"과목: {exam_name}")
                
                total_exam_questions = 0
                for domain in stats[exam_name].keys():
                    total_exam_questions += stats[exam_name][domain]['exam_questions']
                
                # 먼저 기존 문제지 확인 및 처리
                sets_to_create = []  # 새로 생성이 필요한 세트 번호
                sets_to_update = []  # 업데이트가 필요한 세트 번호 (기존 파일 존재, 요구사항 미만족)
                existing_exams_data = {}  # 업데이트가 필요한 기존 문제지 데이터
                
                for set_num in range(num_sets):
                    set_dir = os.path.join(exam_dir, set_names[set_num+1])
                    os.makedirs(set_dir, exist_ok=True)
                    output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
                    
                    if os.path.exists(output_file):
                        self.logger.info(f"  ====> {set_names[set_num+1]}세트: 기존 문제지 발견")
                        
                        # 기존 문제지 로드
                        with open(output_file, 'r', encoding='utf-8') as f:
                            existing_exam_data = json.load(f)
                        
                        # 요구사항 만족 여부 확인
                        meets_requirements, actual_counts = ExamValidator.check_exam_meets_requirements(
                            existing_exam_data, exam_name, stats
                        )
                        
                        if meets_requirements:
                            # 요구사항을 만족하면 그대로 유지
                            self.logger.info(
                                f"  ====> {set_names[set_num+1]}세트: 요구사항 만족, 변경 없음 "
                                f"({len(existing_exam_data)}개 문제)"
                            )
                            # 사용된 문제 추적에 추가
                            for question in existing_exam_data:
                                question_id = (question.get('file_id', ''), question.get('tag', ''))
                                used_questions.add(question_id)
                        else:
                            # 요구사항을 만족하지 않으면 업데이트 필요
                            self.logger.info(
                                f"  ====> {set_names[set_num+1]}세트: 요구사항 미만족, 업데이트 필요"
                            )
                            sets_to_update.append(set_num)
                            existing_exams_data[set_num] = existing_exam_data
                    else:
                        # 기존 문제지가 없으면 새로 생성 필요
                        sets_to_create.append(set_num)
                
                # 새로 생성이 필요한 세트만 처리
                if sets_to_create:
                    exam_data_sets = [[] for _ in range(num_sets)]
                    
                    # domain별로 처리
                    for domain in stats[exam_name].keys():
                        self.logger.info(f"{'-'*50}")
                        self.logger.info(f"도메인: {domain}")
                        
                        domain_data = [d for d in all_data if d.get('domain') == domain]
                        
                        # subdomain 별로 문제 추출
                        for subdomain, needed_count in stats[exam_name][domain]['exam_subdomain_distribution'].items():
                            # 사용 가능한 문제 필터링 (이미 사용된 문제 제외)
                            subdomain_data = [
                                d for d in domain_data 
                                if d.get('subdomain') == subdomain
                                and (d.get('file_id', ''), d.get('tag', '')) not in used_questions
                            ]
                            random.shuffle(subdomain_data)
                            
                            try:
                                remaining_data = subdomain_data.copy()
                                samples = []
                                
                                for set_num in sets_to_create:
                                    if len(remaining_data) >= needed_count:
                                        sample = random.sample(remaining_data, needed_count)
                                        remaining_data = [d for d in remaining_data if d not in sample]
                                        samples.append((set_num, sample))
                                    else:
                                        sample = remaining_data[:needed_count] if remaining_data else []
                                        remaining_data = remaining_data[needed_count:] if len(remaining_data) > needed_count else []
                                        samples.append((set_num, sample))
                                        self.logger.warning(
                                            f"  - {subdomain}: 데이터 부족 "
                                            f"(사용 가능: {len(subdomain_data)}, 필요: {needed_count * len(sets_to_create)})"
                                        )
                                
                                for set_num, sample in samples:
                                    for item in sample:
                                        question_id = (item.get('file_id', ''), item.get('tag', ''))
                                        used_questions.add(question_id)
                                    exam_data_sets[set_num].extend(sample)
                                
                                self.logger.info(
                                    f"  - {subdomain}: {needed_count} x {len(sets_to_create)}세트 "
                                    f"(총 {len(subdomain_data)}개 중 {needed_count * len(sets_to_create)}개 사용)"
                                )
                                
                            except ValueError as e:
                                self.logger.error(f"  - {subdomain}: 샘플링 오류 - {e}")
                    
                    # 새로 생성할 세트 저장
                    for set_num in sets_to_create:
                        set_dir = os.path.join(exam_dir, set_names[set_num+1])
                        output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
                        
                        percentage_total = (len(exam_data_sets[set_num])/total_exam_questions*100) if total_exam_questions > 0 else 0
                        self.logger.info(
                            f"  ====> {set_names[set_num+1]}세트: 새로 생성 "
                            f"{len(exam_data_sets[set_num])}/{total_exam_questions} ({percentage_total:.2f}%)"
                        )
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(exam_data_sets[set_num], f, ensure_ascii=False, indent=4)
                        
                        self.logger.info(f"  ====> 저장 완료: {output_file}")
                
                # 업데이트가 필요한 세트 처리
                if sets_to_update:
                    for set_num in sets_to_update:
                        set_dir = os.path.join(exam_dir, set_names[set_num+1])
                        output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
                        
                        existing_exam_data = existing_exams_data[set_num]
                        updated_exam_data = ExamValidator.update_existing_exam(
                            existing_exam_data, exam_name, stats, all_data, used_questions, self.logger
                        )
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(updated_exam_data, f, ensure_ascii=False, indent=4)
                        
                        percentage_total = (len(updated_exam_data)/total_exam_questions*100) if total_exam_questions > 0 else 0
                        self.logger.info(
                            f"  ====> {set_names[set_num+1]}세트: 업데이트 완료 "
                            f"({len(existing_exam_data)}개 → {len(updated_exam_data)}개, "
                            f"{len(updated_exam_data)}/{total_exam_questions} ({percentage_total:.2f}%))"
                        )
                
                if not sets_to_create and not sets_to_update:
                    self.logger.info(f"  모든 세트가 요구사항을 만족하여 변경 없음")
            
            # 사용되지 않은 나머지 문제 필터링
            self.logger.info(f"\n{'='*50}")
            self.logger.info("사용되지 않은 나머지 문제 필터링 시작...")
            remaining_data = []
            for item in all_data:
                question_id = (item.get('file_id', ''), item.get('tag', ''))
                if question_id not in used_questions:
                    remaining_data.append(item)
            
            # 나머지 문제 저장
            self.logger.info(f"사용되지 않은 나머지 문제: {len(remaining_data)}개")
            remaining_file = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '4_multiple_exam', 'multiple_remaining.json'
            )
            os.makedirs(os.path.dirname(remaining_file), exist_ok=True)
            with open(remaining_file, 'w', encoding='utf-8') as f:
                json.dump(remaining_data, f, ensure_ascii=False, indent=4)
            
            self.logger.info(f"나머지 문제 저장 완료: {remaining_file}")
            self.logger.info(
                f"전체: {len(all_data)}개, 사용: {len(used_questions)}개, 남음: {len(remaining_data)}개"
            )
            
            return {
                'success': True,
                'total_questions': len(all_data),
                'used_questions': len(used_questions),
                'remaining_questions': len(remaining_data)
            }
        finally:
            self._remove_step_logging()
