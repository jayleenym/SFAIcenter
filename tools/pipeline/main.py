#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 파이프라인 - 전체 프로세스 실행

이 모듈은 전체 파이프라인을 오케스트레이션하는 Pipeline 클래스를 제공합니다.

사용 예시:
    # 기본 사용
    from tools.pipeline import Pipeline
    pipeline = Pipeline()
    
    # 특정 단계만 실행
    result = pipeline.run_full_pipeline(steps=['extract_qna_w_domain', 'create_exam'])
    
    # 평가 실행
    result = pipeline.run_full_pipeline(
        steps=['evaluate_exams'],
        eval_models=['openai/gpt-5', 'google/gemini-2.5-pro'],
        eval_sets=[1, 2]
    )

실행 가능한 단계:
    - extract_qna_w_domain: Q&A 추출 및 도메인 분류 (Step1)
    - create_exam: 일반 시험지 생성 (Step2)
    - transform_questions: 객관식 문제 변형 (Step3)
    - evaluate_exams: 시험지 평가 (Step6)
    - create_transformed_exam: 변형 시험지 생성 (Step2)
    - evaluate_essay: 서술형 변환 및 평가 (Step9)
"""

from typing import List, Dict, Any, Optional, Type
from .base import PipelineBase
from .steps import (
    Step1ExtractQnAWDomain,
    Step2CreateExams,
    Step3TransformQuestions,
    Step6Evaluate,
    Step9MultipleEssay
)


class Pipeline(PipelineBase):
    """
    메인 파이프라인 클래스
    
    전체 파이프라인을 오케스트레이션하며, 각 단계를 lazy initialization으로 관리합니다.
    
    Attributes:
        STEP_CLASSES: 단계명 → 클래스 매핑
    """
    
    # 단계명 → (클래스, 내부 속성명) 매핑
    STEP_CLASSES: Dict[str, tuple] = {
        'step1': (Step1ExtractQnAWDomain, '_step1'),
        'step2': (Step2CreateExams, '_step2'),
        'step3': (Step3TransformQuestions, '_step3'),
        'step6': (Step6Evaluate, '_step6'),
        'step9': (Step9MultipleEssay, '_step9'),
    }
    
    def __init__(
        self, 
        base_path: Optional[str] = None, 
        config_path: Optional[str] = None, 
        onedrive_path: Optional[str] = None, 
        project_root_path: Optional[str] = None
    ):
        """
        Args:
            base_path: 기본 데이터 경로 (None이면 ONEDRIVE_PATH 사용)
            config_path: LLM 설정 파일 경로 (None이면 PROJECT_ROOT_PATH/llm_config.ini 사용)
            onedrive_path: OneDrive 경로 (None이면 전역 ONEDRIVE_PATH 사용)
            project_root_path: 프로젝트 루트 경로 (None이면 전역 PROJECT_ROOT_PATH 사용)
        """
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        
        # 초기화 파라미터 저장 (lazy init용)
        self._init_params = (base_path, config_path, onedrive_path, project_root_path)
        
        # 각 단계 인스턴스 (lazy initialization)
        self._step1: Optional[Step1ExtractQnAWDomain] = None
        self._step2: Optional[Step2CreateExams] = None
        self._step3: Optional[Step3TransformQuestions] = None
        self._step6: Optional[Step6Evaluate] = None
        self._step9: Optional[Step9MultipleEssay] = None
    
    def _get_step(self, step_name: str) -> PipelineBase:
        """
        필요할 때만 step 인스턴스 생성 (lazy initialization)
        
        Args:
            step_name: 단계 이름 ('step1', 'step2', 'step3', 'step6', 'step9')
            
        Returns:
            해당 단계의 인스턴스
            
        Raises:
            ValueError: 알 수 없는 step_name인 경우
        """
        if step_name not in self.STEP_CLASSES:
            raise ValueError(f"알 수 없는 단계: {step_name}. 가능한 값: {list(self.STEP_CLASSES.keys())}")
        
        step_class, attr_name = self.STEP_CLASSES[step_name]
        
        # 인스턴스가 없으면 생성
        if getattr(self, attr_name) is None:
            setattr(self, attr_name, step_class(*self._init_params))
        
        return getattr(self, attr_name)
    
    def run_full_pipeline(self, cycle: int = None, steps: List[str] = None,
                         levels: List[str] = None, model: str = 'x-ai/grok-4-fast',
                         eval_models: List[str] = None,
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
            essay_steps: List[int] = None,
            debug: bool = False, random_mode: bool = False) -> Dict[str, Any]:
        """
        전체 파이프라인 실행
        
        Args:
            cycle: 사이클 번호 (1, 2, 3) - 1단계에서 사용
            steps: 실행할 단계 리스트 (None이면 전체 실행)
                가능한 값: 'extract_qna_w_domain', 'create_exam', 'create_transformed_exam', 'evaluate_exams', 'transform_questions', 'evaluate_essay'
            levels: 처리할 레벨 목록 (1단계에서 사용, None이면 ['Lv2', 'Lv3_4', 'Lv5'])
            model: 도메인 분류에 사용할 LLM 모델 (1단계에서 사용)
            random_mode: 랜덤 모드 (2단계에서 사용, True면 새로 뽑기, False면 저장된 문제 번호 리스트 사용)
            eval_models: 평가할 모델 목록 (6단계에서 사용)
            eval_batch_size: 평가 배치 크기 (6단계에서 사용)
            eval_use_ox_support: O, X 문제 지원 활성화 (6단계에서 사용)
            eval_use_server_mode: vLLM 서버 모드 사용 (6단계에서 사용)
            eval_exam_dir: 시험지 디렉토리 경로 (6단계에서 사용, None이면 기본 경로 사용)
            eval_sets: 평가할 세트 번호 리스트 (6단계에서 사용, None이면 모든 세트 평가)
            eval_transformed: 변형 시험지 평가 모드 (6단계에서 사용, 기본값: False)
            eval_essay: 서술형 문제 평가 모드 (6단계에서 사용, 기본값: False)
            transform_input_data_path: 변형 입력 데이터 파일 경로 (3단계에서 사용, run_classify가 True일 때)
            transform_questions: 변형 입력 문제 리스트 (3단계에서 사용, run_classify가 True일 때)
            transform_classified_data_path: 이미 분류된 데이터 파일 경로 (3단계에서 사용, run_classify가 False일 때 필수)
            transform_run_classify: 분류 단계 실행 여부 (3단계에서 사용, 기본값: False)
            transform_classify_model: 분류에 사용할 모델 (3단계에서 사용, run_classify가 True일 때만)
            transform_classify_batch_size: 분류 배치 크기 (3단계에서 사용, run_classify가 True일 때만)
            transform_model: 변형에 사용할 모델 (3단계에서 사용)
            transform_wrong_to_right: wrong -> right 변형 수행 여부 (3단계에서 사용)
            transform_right_to_wrong: right -> wrong 변형 수행 여부 (3단계에서 사용)
            transform_abcd: abcd 변형 수행 여부 (3단계에서 사용)
            transform_seed: 랜덤 시드 (3단계에서 사용)
            create_transformed_exam_sets: 변형 시험지 생성할 세트 번호 리스트 (2단계에서 사용, None이면 1~5 모두 처리)
            essay_models: 모델 답변 생성할 모델 목록 (9단계에서 사용, None이면 답변 생성 안 함)
            essay_sets: 처리할 세트 번호 리스트 (9단계에서 사용, models가 있을 때만 사용, None이면 1~5 모두 처리)
            essay_use_server_mode: vLLM 서버 모드 사용 (9단계에서 사용, models가 있을 때만 사용)
            essay_steps: 실행할 단계 리스트 (9단계에서 사용, 예: [0, 1, 2] 또는 [3] 등). None이면 모든 단계 실행 (0-4)
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
        
        Returns:
            실행 결과
        """
        if steps is None:
            steps = ['extract_qna_w_domain', 'create_exam', 'evaluate_exams', 'transform_questions', 'create_transformed_exam', 'evaluate_essay']
        
        results = {}
        
        try:
            if 'extract_qna_w_domain' in steps:
                # cycle이 None이어도 가능 (모든 사이클 자동 처리)
                results['extract_qna_w_domain'] = self._get_step('step1').execute(cycle, levels=levels, model=model, debug=debug)
            
            if 'create_exam' in steps:
                results['create_exam'] = self._get_step('step2').execute(seed=transform_seed, transformed=False, debug=debug, random_mode=random_mode)
            
            if 'evaluate_exams' in steps:
                results['evaluate_exams'] = self._get_step('step6').execute(
                    models=eval_models,
                    batch_size=eval_batch_size,
                    use_ox_support=eval_use_ox_support,
                    use_server_mode=eval_use_server_mode,
                    exam_dir=eval_exam_dir,
                    sets=eval_sets,
                    transformed=eval_transformed,
                    essay=eval_essay
                )
            
            if 'transform_questions' in steps:
                results['transform_questions'] = self._get_step('step3').execute(
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
                results['create_transformed_exam'] = self._get_step('step2').execute(
                    sets=create_transformed_exam_sets,
                    transformed=True,
                    debug=debug
                )
            
            if 'evaluate_essay' in steps:
                results['evaluate_essay'] = self._get_step('step9').execute(
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

