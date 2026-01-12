#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2단계: 시험문제 만들기 (통합)

이 모듈은 시험문제 생성 파이프라인 단계를 구현합니다.

일반 시험지 생성 (transformed=False):
    - 금융일반/금융심화/금융실무1/금융실무2 총 4개의 시험문제 파일 생성
    - 각 과목당 1250문제씩 생성
    - is_table=false, is_calculation=false 인 문제만 대상
    - random_mode=False: exam_question_lists.json에서 문제 번호 로드 (기본값)
    - random_mode=True: exam_config.json 조건에 맞게 랜덤 선택

변형 시험지 생성 (transformed=True, --transformed 옵션 사용 시):
    - 4_multiple_exam의 각 세트(1st~5th) 시험지의 객관식들을 변형된 문제로 교체
    - 8_multiple_exam_+에 저장

관련 모듈:
    - tools.exam.exam_create.ExamMaker: 일반 시험지 생성
    - tools.exam.exam_plus_create.ExamPlusMaker: 변형 시험지 생성
    - tools.report.ExamReportGenerator: 시험 통계 리포트 생성
"""

from typing import Dict, Any, List
from ..base import PipelineBase
from tools.exam import ExamMaker, ExamPlusMaker


class Step2CreateExams(PipelineBase):
    """
    2단계: 시험문제 만들기 (통합)
    
    일반 시험지와 변형 시험지를 생성하는 파이프라인 단계입니다.
    
    Attributes:
        onedrive_path: OneDrive 데이터 경로
        logger: 로거 인스턴스
        json_handler: JSON 처리 핸들러
    """
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        """
        Step2CreateExams 초기화
        
        Args:
            base_path: 기본 경로
            config_path: 설정 파일 경로
            onedrive_path: OneDrive 경로
            project_root_path: 프로젝트 루트 경로
        """
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
            
        Returns:
            Dict[str, Any]: 생성 결과
                - success (bool): 성공 여부
                - results (Dict): 과목별 생성된 문제 수 (일반 시험지)
                - message (str): 결과 메시지 (변형 시험지)
                - error (str): 오류 메시지 (실패 시)
        """
        step_name = 'create_transformed_exam' if transformed else 'create_exam'
        step_num = 2
        
        self._setup_step_logging(step_name, step_num)
        
        try:
            if transformed:
                return self._create_transformed_exams(sets=sets, debug=debug)
            else:
                return self._create_regular_exams(seed=seed, debug=debug, random_mode=random_mode)
                
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
    
    def _create_regular_exams(self, seed: int, debug: bool, random_mode: bool) -> Dict[str, Any]:
        """
        일반 시험지 생성
        
        Args:
            seed: 랜덤 시드 값
            debug: 디버그 모드
            random_mode: 랜덤 모드
            
        Returns:
            생성 결과 딕셔너리
        """
        mode_str = "랜덤 모드" if random_mode else "저장된 리스트 사용 모드"
        self.logger.info(f"=== 2단계: 일반 시험지 만들기 (seed={seed}, {mode_str}) ===")
        
        maker = ExamMaker(self.onedrive_path, self.logger)
        return maker.create_exams(seed=seed, debug=debug, random_mode=random_mode)
    
    def _create_transformed_exams(self, sets: List[int], debug: bool) -> Dict[str, Any]:
        """
        변형 시험지 생성
        
        Args:
            sets: 처리할 세트 번호 리스트
            debug: 디버그 모드
            
        Returns:
            생성 결과 딕셔너리
        """
        self.logger.info(f"=== 2단계: 변형 시험지 만들기 (세트: {sets}) ===")
        
        maker = ExamPlusMaker(self.onedrive_path, self.json_handler, self.logger)
        return maker.create_transformed_exams(sets=sets, debug=debug)
