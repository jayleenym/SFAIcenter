#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계: 객관식 문제 변형
- AnswerTypeClassifier로 문제를 right/wrong/abcd로 분류
- wrong -> right 변형 (옳지 않은 것 -> 옳은 것)
- right -> wrong 변형 (옳은 것 -> 옳지 않은 것)
- abcd 변형 (단일정답형 -> 복수정답형)
"""

from typing import Dict, Any, List
from ..base import PipelineBase
from tools.transformed.question_transformer import QuestionTransformerOrchestrator

class Step3TransformQuestions(PipelineBase):
    """3단계: 객관식 문제 변형"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
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
