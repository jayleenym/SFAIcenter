#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5단계: 시험문제 만들기
"""

import os
import json
import random
from typing import Dict, Any
from ..base import PipelineBase
# base.py에서 이미 sys.path에 tools_dir이 추가되어 있음
from core.exam_config import ExamConfig


class Step5CreateExam(PipelineBase):
    """5단계: 시험문제 만들기"""
    
    def execute(self, num_sets: int = 5) -> Dict[str, Any]:
        """
        5단계: 시험문제 만들기
        - 1st/2nd/3rd/4th/5th 총 5세트의 시험문제를 만듬
        - exam_config.json 파일 참고하여 갯수 지정
        """
        self.logger.info(f"=== 5단계: 시험문제 만들기 ({num_sets}세트) ===")
        
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
            'evaluation/eval_data/2_subdomain/multiple_subdomain_classified_ALL.json'
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
            'evaluation/eval_data/4_multiple_exam'
        )
        os.makedirs(exam_dir, exist_ok=True)
        
        # 4개의 과목별로 처리
        for exam_name in stats.keys():
            self.logger.info(f"{'='*50}")
            self.logger.info(f"과목: {exam_name}")
            
            exam_data_sets = [[] for _ in range(num_sets)]
            total_exam_questions = 0
            
            # domain별로 처리
            for domain in stats[exam_name].keys():
                self.logger.info(f"{'-'*50}")
                self.logger.info(f"도메인: {domain}")
                
                domain_exam_questions = stats[exam_name][domain]['exam_questions']
                total_exam_questions += domain_exam_questions
                
                domain_data = [d for d in all_data if d.get('domain') == domain]
                
                # subdomain 별로 문제 추출
                for subdomain, needed_count in stats[exam_name][domain]['exam_subdomain_distribution'].items():
                    subdomain_data = [d for d in domain_data if d.get('subdomain') == subdomain]
                    random.shuffle(subdomain_data)
                    
                    try:
                        remaining_data = subdomain_data.copy()
                        samples = []
                        
                        for set_num in range(num_sets):
                            if len(remaining_data) >= needed_count:
                                sample = random.sample(remaining_data, needed_count)
                                remaining_data = [d for d in remaining_data if d not in sample]
                                samples.append(sample)
                            else:
                                sample = remaining_data[:needed_count] if remaining_data else []
                                remaining_data = remaining_data[needed_count:] if len(remaining_data) > needed_count else []
                                samples.append(sample)
                                self.logger.warning(
                                    f"  - {subdomain}: 데이터 부족 "
                                    f"({len(subdomain_data)}/{needed_count * num_sets})"
                                )
                        
                        for set_num, sample in enumerate(samples):
                            for item in sample:
                                question_id = (item.get('file_id', ''), item.get('tag', ''))
                                used_questions.add(question_id)
                            exam_data_sets[set_num].extend(sample)
                        
                        self.logger.info(
                            f"  - {subdomain}: {needed_count} x {num_sets}세트 "
                            f"(총 {len(subdomain_data)}개 중 {needed_count * num_sets}개 사용)"
                        )
                        
                    except ValueError as e:
                        self.logger.error(f"  - {subdomain}: 샘플링 오류 - {e}")
            
            # num_sets개 세트로 저장
            for set_num in range(num_sets):
                percentage_total = (len(exam_data_sets[set_num])/total_exam_questions*100) if total_exam_questions > 0 else 0
                self.logger.info(
                    f"  ====> {set_names[set_num+1]}세트: "
                    f"{len(exam_data_sets[set_num])}/{total_exam_questions} ({percentage_total:.2f}%)"
                )
                
                set_dir = os.path.join(exam_dir, set_names[set_num+1])
                os.makedirs(set_dir, exist_ok=True)
                output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(exam_data_sets[set_num], f, ensure_ascii=False, indent=4)
                
                self.logger.info(f"  ====> 저장 완료: {output_file}")
        
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
            'evaluation/eval_data/2_subdomain/multiple_remaining.json'
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

