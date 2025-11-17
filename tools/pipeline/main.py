#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 파이프라인 - 전체 프로세스 실행
"""

from typing import List, Dict, Any, Optional
from .base import PipelineBase
from .steps import (
    Step0Preprocessing,
    Step1ExtractBasic,
    Step2ExtractFull,
    Step3Classify,
    Step4DomainSubdomain,
    Step5CreateExam,
    Step6Evaluate,
    Step7TransformMultipleChoice
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
        self.step0 = Step0Preprocessing(base_path, config_path, onedrive_path, project_root_path)
        self.step1 = Step1ExtractBasic(base_path, config_path, onedrive_path, project_root_path)
        self.step2 = Step2ExtractFull(base_path, config_path, onedrive_path, project_root_path)
        self.step3 = Step3Classify(base_path, config_path, onedrive_path, project_root_path)
        self.step4 = Step4DomainSubdomain(base_path, config_path, onedrive_path, project_root_path)
        self.step5 = Step5CreateExam(base_path, config_path, onedrive_path, project_root_path)
        self.step6 = Step6Evaluate(base_path, config_path, onedrive_path, project_root_path)
        self.step7 = Step7TransformMultipleChoice(base_path, config_path, onedrive_path, project_root_path)
    
    def run_full_pipeline(self, cycle: int = None, steps: List[str] = None,
                         qna_type: str = 'multiple', model: str = 'x-ai/grok-4-fast',
                         num_sets: int = 5, eval_models: List[str] = None,
                         eval_batch_size: int = 10, eval_use_ox_support: bool = True,
                         eval_use_server_mode: bool = False,
                         eval_exam_dir: str = None, eval_sets: List[int] = None,
                         transform_input_data_path: str = None, transform_questions: List[Dict[str, Any]] = None,
                         transform_classify_model: str = 'openai/gpt-5', transform_classify_batch_size: int = 10,
                         transform_model: str = 'openai/o3', transform_wrong_to_right: bool = True,
                         transform_right_to_wrong: bool = True, transform_abcd: bool = True,
                         transform_seed: int = 42) -> Dict[str, Any]:
        """
        전체 파이프라인 실행
        
        Args:
            cycle: 사이클 번호 (1, 2, 3) - 0, 1, 2, 3단계에서만 사용
            steps: 실행할 단계 리스트 (None이면 전체 실행)
                가능한 값: 'preprocess', 'extract_basic', 'extract_full', 'classify', 'fill_domain', 'create_exam', 'evaluate_exams', 'transform_multiple_choice'
            qna_type: QnA 타입 (4단계에서 사용)
            model: 사용할 모델 (4단계에서 사용)
            num_sets: 시험 세트 개수 (5단계에서 사용)
            eval_models: 평가할 모델 목록 (6단계에서 사용)
            eval_batch_size: 평가 배치 크기 (6단계에서 사용)
            eval_use_ox_support: O, X 문제 지원 활성화 (6단계에서 사용)
            eval_use_server_mode: vLLM 서버 모드 사용 (6단계에서 사용)
            eval_exam_dir: 시험지 디렉토리 경로 (6단계에서 사용, None이면 기본 경로 사용)
            eval_sets: 평가할 세트 번호 리스트 (6단계에서 사용, None이면 모든 세트 평가)
            transform_input_data_path: 변형 입력 데이터 파일 경로 (7단계에서 사용)
            transform_questions: 변형 입력 문제 리스트 (7단계에서 사용)
            transform_classify_model: 분류에 사용할 모델 (7단계에서 사용)
            transform_classify_batch_size: 분류 배치 크기 (7단계에서 사용)
            transform_model: 변형에 사용할 모델 (7단계에서 사용)
            transform_wrong_to_right: wrong -> right 변형 수행 여부 (7단계에서 사용)
            transform_right_to_wrong: right -> wrong 변형 수행 여부 (7단계에서 사용)
            transform_abcd: abcd 변형 수행 여부 (7단계에서 사용)
            transform_seed: 랜덤 시드 (7단계에서 사용)
        
        Returns:
            실행 결과
        """
        if steps is None:
            steps = ['preprocess', 'extract_basic', 'extract_full', 'classify', 'fill_domain', 'create_exam', 'evaluate_exams', 'transform_multiple_choice']
        
        self.logger.info(f"=== 전체 파이프라인 시작 ===")
        self.logger.info(f"실행 단계: {', '.join(steps)}")
        
        results = {}
        
        try:
            if 'preprocess' in steps:
                if cycle is None:
                    self.logger.error("preprocess 단계는 cycle이 필요합니다.")
                    results['preprocess'] = {'success': False, 'error': 'cycle 필요'}
                else:
                    results['preprocess'] = self.step0.execute(cycle)
            
            if 'extract_basic' in steps:
                if cycle is None:
                    self.logger.error("extract_basic 단계는 cycle이 필요합니다.")
                    results['extract_basic'] = {'success': False, 'error': 'cycle 필요'}
                else:
                    results['extract_basic'] = self.step1.execute(cycle)
            
            if 'extract_full' in steps:
                if cycle is None:
                    self.logger.error("extract_full 단계는 cycle이 필요합니다.")
                    results['extract_full'] = {'success': False, 'error': 'cycle 필요'}
                else:
                    results['extract_full'] = self.step2.execute(cycle)
            
            if 'classify' in steps:
                if cycle is None:
                    self.logger.error("classify 단계는 cycle이 필요합니다.")
                    results['classify'] = {'success': False, 'error': 'cycle 필요'}
                else:
                    results['classify'] = self.step3.execute(cycle)
            
            if 'fill_domain' in steps:
                results['fill_domain'] = self.step4.execute(qna_type=qna_type, model=model)
            
            if 'create_exam' in steps:
                results['create_exam'] = self.step5.execute(num_sets=num_sets)
            
            if 'evaluate_exams' in steps:
                results['evaluate_exams'] = self.step6.execute(
                    models=eval_models,
                    batch_size=eval_batch_size,
                    use_ox_support=eval_use_ox_support,
                    use_server_mode=eval_use_server_mode,
                    exam_dir=eval_exam_dir,
                    sets=eval_sets
                )
            
            if 'transform_multiple_choice' in steps:
                results['transform_multiple_choice'] = self.step7.execute(
                    input_data_path=transform_input_data_path,
                    questions=transform_questions,
                    classify_model=transform_classify_model,
                    classify_batch_size=transform_classify_batch_size,
                    transform_model=transform_model,
                    transform_wrong_to_right=transform_wrong_to_right,
                    transform_right_to_wrong=transform_right_to_wrong,
                    transform_abcd=transform_abcd,
                    seed=transform_seed
                )
            
            self.logger.info("=== 전체 파이프라인 완료 ===")
            results['success'] = True
            
        except Exception as e:
            self.logger.error(f"파이프라인 실행 오류: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results

