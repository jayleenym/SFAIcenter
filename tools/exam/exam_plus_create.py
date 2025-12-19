#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
변형 문제 포함 시험지 생성 모듈
- 4_multiple_exam의 각 세트(1st~5th) 시험지의 객관식들을 변형된 문제로 교체
- 8_multiple_exam_+에 저장
"""

import os
import sys
from typing import Dict, List, Any
from stats_utils import StatisticsSaver
from tools.transformed.multiple_load_transformed_questions import load_transformed_questions
from tools.transformed.multiple_create_transformed_exam import create_transformed_exam

class ExamPlusMaker:
    """변형 문제 포함 시험지 생성 클래스"""
    
    def __init__(self, onedrive_path: str, json_handler: Any, logger: Any):
        self.onedrive_path = onedrive_path
        self.json_handler = json_handler
        self.logger = logger
        
    def create_transformed_exams(self, sets: List[int] = None, debug: bool = False) -> Dict[str, Any]:
        """
        변형 문제 포함 시험지 생성 실행
        
        Args:
            sets: 처리할 세트 번호 리스트 (None이면 1~5 모두 처리)
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
        """
        if sets is None:
            sets = [1, 2, 3, 4, 5]
            
        self.logger.info(f"=== 변형 문제를 포함한 시험지 생성 (세트: {sets}, debug={debug}) ===")
        
        try:
            set_names = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th'}
            
            # 변형된 문제들 로드
            self.logger.info("1. 변형된 문제 로드 중...")
            transformed_questions = load_transformed_questions(
                self.onedrive_path, self.json_handler, self.logger
            )
            
            total_transformed = sum(len(transformed_questions[k]) for k in ['pick_abcd', 'pick_right', 'pick_wrong'])
            self.logger.info(f"총 변형된 문제 수: {total_transformed}개")
            
            exam_files = {
                '금융일반': '금융일반_exam.json',
                '금융심화': '금융심화_exam.json',
                '금융실무1': '금융실무1_exam.json',
                '금융실무2': '금융실무2_exam.json'
            }
            
            for set_num in sets:
                self._process_set(set_num, set_names, exam_files, transformed_questions, debug)
            
            return {'success': True, 'message': '변형 문제를 포함한 시험지 생성 완료'}
            
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _process_set(self, set_num: int, set_names: Dict, exam_files: Dict, transformed_questions: Dict, debug: bool = False):
        """세트별 처리"""
        set_name = set_names.get(set_num, f"{set_num}th")
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"세트 {set_name} 처리 중...")
        
        original_exam_dir = os.path.join(
            self.onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam', set_name
        )
        
        output_dir = os.path.join(
            self.onedrive_path, 'evaluation', 'eval_data', '8_multiple_exam_+', set_name
        )
        os.makedirs(output_dir, exist_ok=True)
        
        set_statistics = {}
        
        for exam_name, exam_filename in exam_files.items():
            original_exam_path = os.path.join(original_exam_dir, exam_filename)
            
            if not os.path.exists(original_exam_path):
                self.logger.warning(f"  ⚠️  원본 시험지를 찾을 수 없습니다: {original_exam_path}")
                continue
            
            self.logger.info(f"\n  [{exam_name}] 처리 중...")
            
            original_exam = self.json_handler.load(original_exam_path)
            if not isinstance(original_exam, list):
                original_exam = []
            
            transformed_exam, missing_questions, transform_stats = create_transformed_exam(
                original_exam, transformed_questions
            )
            
            output_filename = f"{exam_name}_exam_transformed.json"
            output_path = os.path.join(output_dir, output_filename)
            
            # debug 모드일 때는 기존 파일 백업
            if debug and os.path.exists(output_path):
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{output_path}.backup_{timestamp}"
                try:
                    import shutil
                    shutil.copy2(output_path, backup_path)
                    self.logger.info(f"    📁 기존 파일 백업: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"    ⚠️  백업 실패: {e}")
            
            self.json_handler.save(transformed_exam, output_path, backup=debug, logger=self.logger)
            self.logger.info(f"    ✅ 저장 완료: {output_path}")
            
            if missing_questions:
                missing_filename = f"{exam_name}_missing.json"
                missing_path = os.path.join(output_dir, missing_filename)
                self.json_handler.save(missing_questions, missing_path)
            
            set_statistics[exam_name] = transform_stats
            StatisticsSaver.log_statistics(transform_stats, exam_name, self.logger)
        
        set_stats = StatisticsSaver.aggregate_set_statistics(set_statistics)
        markdown_path = os.path.join(output_dir, f"STATS_{set_name}.md")
        StatisticsSaver.save_statistics_markdown(set_stats, set_name, markdown_path)
