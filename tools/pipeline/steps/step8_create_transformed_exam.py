#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8단계: 변형 문제를 포함한 시험지 생성
- 4_multiple_exam의 각 세트(1st~5th) 시험지의 객관식들을 pick_right, pick_wrong, pick_abcd result.json 파일에서 찾아서
- 각각 금융일반/금융심화/금융실무1/금융실무2_exam_transformed.json 파일로 만들어서 8_multiple_exam_+에 저장

변형 규칙:
1. 기존 시험지의 question, options, answer를 변형된 문제의 것으로 교체
2. 기존 시험지의 explanation을 original_explanation으로 키 이름 변경
3. 변형된 문제의 explanation을 explanation 키에 넣기
"""

import os
import sys
from typing import Dict, List, Any
from ..base import PipelineBase

# statistics 및 transformed 모듈 import
current_dir = os.path.dirname(os.path.abspath(__file__))
# tools 모듈 import를 위한 경로 설정
_temp_tools_dir = os.path.dirname(os.path.dirname(current_dir))  # steps -> pipeline -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)

from statistics import StatisticsSaver
from tools.transformed.multiple_load_transformed_questions import load_transformed_questions
from tools.transformed.multiple_create_transformed_exam import create_transformed_exam


class Step8CreateTransformedExam(PipelineBase):
    """8단계: 변형 문제를 포함한 시험지 생성"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, sets: List[int] = None) -> Dict[str, Any]:
        """
        8단계: 변형 문제를 포함한 시험지 생성
        
        Args:
            sets: 처리할 세트 번호 리스트 (None이면 1~5 모두 처리)
        """
        if sets is None:
            sets = [1, 2, 3, 4, 5]
        
        self.logger.info(f"=== 8단계: 변형 문제를 포함한 시험지 생성 (세트: {sets}) ===")
        
        # 로깅 설정
        self._setup_step_logging('create_transformed_exam', 8)
        
        try:
            # 세트 이름 매핑
            set_names = {
                1: '1st',
                2: '2nd',
                3: '3rd',
                4: '4th',
                5: '5th'
            }
            
            # 변형된 문제들 로드
            self.logger.info("1. 변형된 문제 로드 중...")
            transformed_questions = load_transformed_questions(
                self.onedrive_path, self.json_handler, self.logger
            )
            
            total_transformed = (
                len(transformed_questions['pick_abcd']) +
                len(transformed_questions['pick_right']) +
                len(transformed_questions['pick_wrong'])
            )
            self.logger.info(f"총 변형된 문제 수:")
            self.logger.info(f"  - pick_abcd: {len(transformed_questions['pick_abcd'])}개")
            self.logger.info(f"  - pick_right: {len(transformed_questions['pick_right'])}개")
            self.logger.info(f"  - pick_wrong: {len(transformed_questions['pick_wrong'])}개")
            self.logger.info(f"  - 총계: {total_transformed}개")
            
            # 시험지 파일 목록
            exam_files = {
                '금융일반': '금융일반_exam.json',
                '금융심화': '금융심화_exam.json',
                '금융실무1': '금융실무1_exam.json',
                '금융실무2': '금융실무2_exam.json'
            }
            
            # 각 세트별로 처리
            for set_num in sets:
                set_name = set_names.get(set_num, f"{set_num}th")
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"세트 {set_name} 처리 중...")
                self.logger.info(f"{'='*60}")
                
                # 원본 시험지 디렉토리
                original_exam_dir = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '4_multiple_exam', set_name
                )
                
                # 출력 디렉토리 (세트별 디렉토리: 1st, 2nd, 3rd, 4th, 5th)
                output_dir = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '8_multiple_exam_+', set_name
                )
                os.makedirs(output_dir, exist_ok=True)
                self.logger.info(f"  출력 디렉토리: {output_dir}")
                
                # 세트별 통계 수집용
                set_statistics = {}
                
                # 각 시험지 처리
                for exam_name, exam_filename in exam_files.items():
                    original_exam_path = os.path.join(original_exam_dir, exam_filename)
                    
                    if not os.path.exists(original_exam_path):
                        self.logger.warning(f"  ⚠️  원본 시험지를 찾을 수 없습니다: {original_exam_path}")
                        continue
                    
                    self.logger.info(f"\n  [{exam_name}] 처리 중...")
                    
                    # 원본 시험지 로드
                    original_exam = self.json_handler.load(original_exam_path)
                    if not isinstance(original_exam, list):
                        original_exam = []
                    self.logger.info(f"    원본 문제 수: {len(original_exam)}개")
                    
                    # 변형된 시험지 생성
                    transformed_exam, missing_questions, transform_stats = create_transformed_exam(
                        original_exam, transformed_questions
                    )
                    self.logger.info(f"    변형된 시험지 문제 수: {len(transformed_exam)}개")
                    
                    # 변형된 문제 개수 확인
                    transformed_count = 0
                    for q in transformed_exam:
                        file_id = q.get('file_id', '')
                        tag = q.get('tag', '')
                        if file_id and tag:
                            question_id = f"{file_id}_{tag}"
                            if (question_id in transformed_questions['pick_abcd'] or
                                question_id in transformed_questions['pick_right'] or
                                question_id in transformed_questions['pick_wrong']):
                                transformed_count += 1
                    
                    self.logger.info(f"    변형된 문제 수: {transformed_count}개")
                    self.logger.info(f"    변형되지 않은 문제 수: {len(missing_questions)}개")
                    
                    # 변형된 시험지 저장 (세트별 디렉토리에 저장)
                    output_filename = f"{exam_name}_exam_transformed.json"
                    output_path = os.path.join(output_dir, output_filename)
                    self.json_handler.save(transformed_exam, output_path)
                    self.logger.info(f"    ✅ 저장 완료: {output_path} (세트: {set_name})")
                    
                    # 누락된 문제들 저장 (세트별 디렉토리에 저장)
                    if missing_questions:
                        missing_filename = f"{exam_name}_missing.json"
                        missing_path = os.path.join(output_dir, missing_filename)
                        self.json_handler.save(missing_questions, missing_path)
                        self.logger.info(f"    ✅ 누락된 문제 저장 완료: {missing_path} (세트: {set_name})")
                    
                    # 통계를 메모리에 저장 (세트별 집계용)
                    set_statistics[exam_name] = transform_stats
                    StatisticsSaver.log_statistics(transform_stats, exam_name, self.logger)
                
                # 세트별 통계 집계 및 마크다운 생성
                self.logger.info(f"\n  세트 {set_name} 통계 집계 중...")
                set_stats = StatisticsSaver.aggregate_set_statistics(set_statistics)
                markdown_path = os.path.join(output_dir, f"STATS_{set_name}.md")
                StatisticsSaver.save_statistics_markdown(set_stats, set_name, markdown_path)
                self.logger.info(f"    ✅ 세트 통계 마크다운 저장 완료: {markdown_path}")
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info("완료!")
            self.logger.info(f"{'='*60}")
            
            # 로그 핸들러 제거
            self._remove_step_logging()
            
            return {'success': True, 'message': '변형 문제를 포함한 시험지 생성 완료'}
            
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            # 오류 발생 시에도 로그 핸들러 제거
            self._remove_step_logging()
            return {'success': False, 'error': str(e)}
