#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 시험문제 만들기 (통합)

- 일반 시험지 생성 (transformed=False)
  - 금융일반/금융심화/금융실무1/금융실무2 총 4개의 시험문제 파일 생성
  - 각 과목당 1250문제씩 생성
  - is_table=false, is_calculation=false 인 문제만 대상
  - random_mode=False: exam_question_lists.json에서 문제 번호 로드 (기본값)
  - random_mode=True: exam_config.json 조건에 맞게 랜덤 선택
- 변형 시험지 생성 (transformed=True, --transformed 옵션 사용 시)
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
        
    def execute(self, seed: int = 42, transformed: bool = False, sets: List[int] = None, 
                debug: bool = False, random_mode: bool = False) -> Dict[str, Any]:
        """
        시험문제 생성 실행
        
        Args:
            seed: 랜덤 시드 값 (기본값: 42, 랜덤 모드에서만 사용)
            transformed: 변형 시험지 생성 여부 (기본값: False)
            sets: 변형 시험지 생성 시 처리할 세트 번호 리스트 (None이면 1~5 모두 처리)
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            random_mode: 랜덤 모드 (True: 새로 뽑기, False: 저장된 문제 번호 리스트 사용, 기본값: False)
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
                self.logger.info(f"=== 2단계: 일반 시험지 만들기 (seed={seed}, {mode_str}) ===")
                maker = ExamMaker(self.onedrive_path, self.logger)
                return maker.create_exams(seed=seed, debug=debug, random_mode=random_mode)
                
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
