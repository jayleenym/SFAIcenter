#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 시험문제 만들기 (통합)

- 일반 시험지 생성 (기존 Step 5)
- 변형 시험지 생성 (기존 Step 8, --transformed 옵션 사용 시)
"""

from typing import Dict, Any, List
from ..base import PipelineBase
from tools.exam.exam_create import ExamMaker
from tools.exam.exam_plus_create import ExamPlusMaker

class Step2CreateExams(PipelineBase):
    """2단계: 시험문제 만들기 (통합)"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
        
    def execute(self, num_sets: int = 5, seed: int = 42, transformed: bool = False, sets: List[int] = None, debug: bool = False, random_mode: bool = False) -> Dict[str, Any]:
        """
        시험문제 생성 실행
        
        Args:
            num_sets: 생성할 시험 세트 개수 (기본값: 5)
            seed: 랜덤 시드 값 (기본값: 42)
            transformed: 변형 시험지 생성 여부 (기본값: False)
            sets: 변형 시험지 생성 시 처리할 세트 번호 리스트 (None이면 1~5 모두 처리)
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            random_mode: 랜덤 모드 (True면 새로 뽑기, False면 저장된 문제 번호 리스트 사용, 기본값: False)
        """
        step_name = 'create_transformed_exam' if transformed else 'create_exam'
        step_num = 2
        
        self._setup_step_logging(step_name, step_num)
        
        try:
            if transformed:
                self.logger.info(f"=== 2단계: 변형 시험지 만들기 (세트: {sets}) ===")
                maker = ExamPlusMaker(self.onedrive_path, self.json_handler, self.logger)
                return maker.create_transformed_exams(sets=sets, debug=debug)
            else:
                mode_str = "랜덤 모드" if random_mode else "저장된 리스트 사용 모드"
                self.logger.info(f"=== 2단계: 일반 시험지 만들기 ({num_sets}세트, seed={seed}, {mode_str}) ===")
                maker = ExamMaker(self.onedrive_path, self.logger)
                return maker.create_exams(num_sets=num_sets, seed=seed, debug=debug, random_mode=random_mode)
                
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
