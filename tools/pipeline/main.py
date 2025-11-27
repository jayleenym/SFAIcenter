#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 파이프라인 - 전체 프로세스 실행
"""

from typing import List, Dict, Any, Optional
from .base import PipelineBase
from .steps import (
    Step1ExtractQnAWDomain,
    Step5CreateExam,
    Step6Evaluate,
    Step7TransformMultipleChoice,
    Step8CreateTransformedExam,
    Step9MultipleEssay
)


class Pipeline(PipelineBase):
    """메인 파이프라인 클래스"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        """
        Args:
            base_path: 기본 데이터 경로 (None이면 ONEDRIVE_PATH 사용)
            config_path: LLM 설정 파일 경로 (None이면 PROJECT_ROOT_PATH/llm_config.ini 사용)
            onedrive_path: OneDrive 경로 (None이면 전역 ONEDRIVE_PATH 사용)
            project_root_path: 프로젝트 루트 경로 (None이면 전역 PROJECT_ROOT_PATH 사용)
        """
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        
        # 각 단계 인스턴스 생성
        self.step1_domain = Step1ExtractQnAWDomain(base_path, config_path, onedrive_path, project_root_path)
        self.step5 = Step5CreateExam(base_path, config_path, onedrive_path, project_root_path)
        self.step6 = Step6Evaluate(base_path, config_path, onedrive_path, project_root_path)
        self.step7 = Step7TransformMultipleChoice(base_path, config_path, onedrive_path, project_root_path)
        self.step8 = Step8CreateTransformedExam(base_path, config_path, onedrive_path, project_root_path)
        self.step9 = Step9MultipleEssay(base_path, config_path, onedrive_path, project_root_path)
    
    def run_full_pipeline(self, cycle: int = None, steps: List[str] = None,
                         levels: List[str] = None,
                         qna_type: str = None, model: str = 'x-ai/grok-4-fast',
                         num_sets: int = 5, eval_models: List[str] = None,
                         eval_batch_size: int = 10, eval_use_ox_support: bool = True,
                         eval_use_server_mode: bool = False,
                         eval_exam_dir: str = None, eval_sets: List[int] = None,
                         eval_transformed: bool = False, eval_essay: bool = False,
                         transform_input_data_path: str = None, transform_questions: List[Dict[str, Any]] = None,
                         transform_classified_data_path: str = None,
                         transform_run_classify: bool = False,
                         transform_classify_model: str = 'openai/gpt-5', transform_classify_batch_size: int = 10,
                         transform_model: str = 'openai/o3', transform_wrong_to_right: bool = True,
                         transform_right_to_wrong: bool = True, transform_abcd: bool = True,
                         transform_seed: int = 42,
                         create_transformed_exam_sets: List[int] = None,
            essay_models: List[str] = None, essay_sets: List[int] = None,
            essay_use_server_mode: bool = False,
            essay_steps: List[int] = None) -> Dict[str, Any]:
        """
        전체 파이프라인 실행
        
        Args:
            cycle: 사이클 번호 (1, 2, 3) - 0, 1, 2, 3단계에서만 사용
            steps: 실행할 단계 리스트 (None이면 전체 실행)
                가능한 값: 'extract_qna_w_domain', 'create_exam', 'evaluate_exams', 'transform_multiple_choice', 'create_transformed_exam', 'evaluate_essay'
            qna_type: QnA 타입 (4단계에서 사용, None이면 모든 타입 처리: 'multiple', 'short', 'essay')
            model: 사용할 모델 (4단계에서 사용)
            num_sets: 시험 세트 개수 (5단계에서 사용)
            eval_models: 평가할 모델 목록 (6단계에서 사용)
            eval_batch_size: 평가 배치 크기 (6단계에서 사용)
            eval_use_ox_support: O, X 문제 지원 활성화 (6단계에서 사용)
            eval_use_server_mode: vLLM 서버 모드 사용 (6단계에서 사용)
            eval_exam_dir: 시험지 디렉토리 경로 (6단계에서 사용, None이면 기본 경로 사용)
            eval_sets: 평가할 세트 번호 리스트 (6단계에서 사용, None이면 모든 세트 평가)
            eval_transformed: 변형 시험지 평가 모드 (6단계에서 사용, 기본값: False)
            eval_essay: 서술형 문제 평가 모드 (6단계에서 사용, 기본값: False)
            transform_input_data_path: 변형 입력 데이터 파일 경로 (7단계에서 사용, run_classify가 True일 때)
            transform_questions: 변형 입력 문제 리스트 (7단계에서 사용, run_classify가 True일 때)
            transform_classified_data_path: 이미 분류된 데이터 파일 경로 (7단계에서 사용, run_classify가 False일 때 필수)
            transform_run_classify: 분류 단계 실행 여부 (7단계에서 사용, 기본값: False)
            transform_classify_model: 분류에 사용할 모델 (7단계에서 사용, run_classify가 True일 때만)
            transform_classify_batch_size: 분류 배치 크기 (7단계에서 사용, run_classify가 True일 때만)
            transform_model: 변형에 사용할 모델 (7단계에서 사용)
            transform_wrong_to_right: wrong -> right 변형 수행 여부 (7단계에서 사용)
            transform_right_to_wrong: right -> wrong 변형 수행 여부 (7단계에서 사용)
            transform_abcd: abcd 변형 수행 여부 (7단계에서 사용)
            transform_seed: 랜덤 시드 (7단계에서 사용)
            create_transformed_exam_sets: 변형 시험지 생성할 세트 번호 리스트 (8단계에서 사용, None이면 1~5 모두 처리)
            essay_models: 모델 답변 생성할 모델 목록 (9단계에서 사용, None이면 답변 생성 안 함)
            essay_sets: 처리할 세트 번호 리스트 (9단계에서 사용, models가 있을 때만 사용, None이면 1~5 모두 처리)
            essay_use_server_mode: vLLM 서버 모드 사용 (9단계에서 사용, models가 있을 때만 사용)
            essay_steps: 실행할 단계 리스트 (9단계에서 사용, 예: [0, 1, 2] 또는 [3] 등). None이면 모든 단계 실행 (0-4)
        
        Returns:
            실행 결과
        """
        if steps is None:
            steps = ['extract_qna_w_domain', 'create_exam', 'evaluate_exams', 'transform_multiple_choice', 'create_transformed_exam', 'evaluate_essay']
        
        results = {}
        
        try:
            if 'extract_qna_w_domain' in steps:
                # cycle이 None이어도 가능 (모든 사이클 자동 처리)
                results['extract_qna_w_domain'] = self.step1_domain.execute(cycle, levels=levels, model=model)
            
            if 'create_exam' in steps:
                results['create_exam'] = self.step5.execute(num_sets=num_sets)
            
            if 'evaluate_exams' in steps:
                results['evaluate_exams'] = self.step6.execute(
                    models=eval_models,
                    batch_size=eval_batch_size,
                    use_ox_support=eval_use_ox_support,
                    use_server_mode=eval_use_server_mode,
                    exam_dir=eval_exam_dir,
                    sets=eval_sets,
                    transformed=eval_transformed,
                    essay=eval_essay
                )
            
            if 'transform_multiple_choice' in steps:
                results['transform_multiple_choice'] = self.step7.execute(
                    classified_data_path=transform_classified_data_path,
                    input_data_path=transform_input_data_path,
                    questions=transform_questions,
                    run_classify=transform_run_classify,
                    classify_model=transform_classify_model,
                    classify_batch_size=transform_classify_batch_size,
                    transform_model=transform_model,
                    transform_wrong_to_right=transform_wrong_to_right,
                    transform_right_to_wrong=transform_right_to_wrong,
                    transform_abcd=transform_abcd,
                    seed=transform_seed
                )
            
            if 'create_transformed_exam' in steps:
                results['create_transformed_exam'] = self.step8.execute(
                    sets=create_transformed_exam_sets
                )
            
            if 'evaluate_essay' in steps:
                results['evaluate_essay'] = self.step9.execute(
                    models=essay_models,
                    sets=essay_sets,
                    use_server_mode=essay_use_server_mode,
                    steps=essay_steps
                )
            
            results['success'] = True
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
        
        return results

