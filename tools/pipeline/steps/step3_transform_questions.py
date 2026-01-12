#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계: 객관식 문제 변형

이 모듈은 객관식 문제 변형 파이프라인 단계를 구현합니다.

변형 유형:
    - AnswerTypeClassifier로 문제를 right/wrong/abcd로 분류
    - wrong → right 변형 (옳지 않은 것 → 옳은 것을 모두 고르시오)
    - right → wrong 변형 (옳은 것 → 옳지 않은 것을 모두 고르시오)
    - abcd 변형 (단일정답형 → 복수정답형)

입력:
    - 분류된 데이터: {onedrive_path}/evaluation/eval_data/7_multiple_rw/answer_type_classified.json
    - 또는 직접 분류 수행 (run_classify=True)

출력:
    - pick_wrong/: wrong → right 변형 결과
    - pick_right/: right → wrong 변형 결과
    - pick_abcd/: abcd 변형 결과

관련 모듈:
    - tools.transformed.multiple.QuestionTransformerOrchestrator: 변형 오케스트레이터
    - tools.transformed.multiple.AnswerTypeClassifier: 문제 분류
    - tools.transformed.multiple.MultipleChoiceTransformer: 변형 수행
"""

from typing import Dict, Any, List
from ..base import PipelineBase
from tools.transformed.multiple import QuestionTransformerOrchestrator


class Step3TransformQuestions(PipelineBase):
    """
    3단계: 객관식 문제 변형
    
    AnswerTypeClassifier로 문제를 분류하고, 각 유형에 맞게 변형합니다.
    
    Attributes:
        onedrive_path: OneDrive 데이터 경로
        project_root_path: 프로젝트 루트 경로
        json_handler: JSON 처리 핸들러
        logger: 로거 인스턴스
        llm_query: LLM API 쿼리 인스턴스
    """
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        """
        Step3TransformQuestions 초기화
        
        Args:
            base_path: 기본 경로
            config_path: 설정 파일 경로
            onedrive_path: OneDrive 경로
            project_root_path: 프로젝트 루트 경로
        """
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
        
    def execute(self, classified_data_path: str = None,
                input_data_path: str = None, questions: List[Dict[str, Any]] = None,
                run_classify: bool = False,
                classify_model: str = 'openai/gpt-5', classify_batch_size: int = 10,
                transform_model: str = 'openai/o3', 
                transform_wrong_to_right: bool = True,
                transform_right_to_wrong: bool = True,
                transform_abcd: bool = True,
                seed: int = 42) -> Dict[str, Any]:
        """
        객관식 문제 변형 실행
        
        Args:
            classified_data_path: 이미 분류된 데이터 파일 경로
            input_data_path: 분류할 입력 데이터 경로 (run_classify=True 시)
            questions: 직접 전달할 문제 리스트
            run_classify: 분류 단계 실행 여부
            classify_model: 분류에 사용할 LLM 모델
            classify_batch_size: 분류 배치 크기
            transform_model: 변형에 사용할 LLM 모델
            transform_wrong_to_right: wrong → right 변형 수행 여부
            transform_right_to_wrong: right → wrong 변형 수행 여부
            transform_abcd: abcd 변형 수행 여부
            seed: 랜덤 시드
            
        Returns:
            Dict[str, Any]: 변형 결과
                - success (bool): 성공 여부
                - classified (int): 분류된 문제 수
                - transformations (dict): 각 변형 타입별 결과
                - error (str): 오류 메시지 (실패 시)
        """
        self._setup_step_logging('transform_questions', 3)
        
        try:
            orchestrator = QuestionTransformerOrchestrator(
                self.onedrive_path, self.project_root_path, self.json_handler, self.logger, self.llm_query
            )
            return orchestrator.transform_questions(
                classified_data_path=classified_data_path,
                input_data_path=input_data_path,
                questions=questions,
                run_classify=run_classify,
                classify_model=classify_model,
                classify_batch_size=classify_batch_size,
                transform_model=transform_model,
                transform_wrong_to_right=transform_wrong_to_right,
                transform_right_to_wrong=transform_right_to_wrong,
                transform_abcd=transform_abcd,
                seed=seed
            )
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
