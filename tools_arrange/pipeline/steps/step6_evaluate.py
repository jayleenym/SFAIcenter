#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6단계: 시험지 평가
"""

import os
import sys
from typing import List, Dict, Any
from ..base import PipelineBase
from ..config import PROJECT_ROOT_PATH

# evaluation 모듈 import (tools_arrange 폴더에서)
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_arrange_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools_arrange
sys.path.insert(0, tools_arrange_dir)
try:
    from evaluation.multiple_eval_by_model import (
        run_eval_pipeline_improved,
        load_data_from_directory,
        save_results_to_excel,
        print_evaluation_summary
    )
except ImportError:
    # fallback: tools 폴더에서 시도
    tools_dir = os.path.join(PROJECT_ROOT_PATH, 'tools')
    sys.path.insert(0, tools_dir)
    try:
        from evaluation.multiple_eval_by_model import (
            run_eval_pipeline_improved,
            load_data_from_directory,
            save_results_to_excel,
            print_evaluation_summary
        )
    except ImportError:
        run_eval_pipeline_improved = None
        load_data_from_directory = None
        save_results_to_excel = None
        print_evaluation_summary = None


class Step6Evaluate(PipelineBase):
    """6단계: 시험지 평가"""
    
    def execute(self, models: List[str] = None, batch_size: int = 10, 
                use_ox_support: bool = True, use_server_mode: bool = False,
                reasoning: bool = False, exam_dir: str = None, sets: List[int] = None) -> Dict[str, Any]:
        """
        6단계: 시험지 평가
        - 만들어진 시험지(1st/2nd/3rd/4th/5th) 모델별 답변 평가
        - 10문제씩 배치화하여 호출
        
        Args:
            models: 평가할 모델 목록
            batch_size: 배치 크기
            use_ox_support: O, X 문제 지원 활성화
            use_server_mode: vLLM 서버 모드 사용
            reasoning: 추론 모델 여부
            exam_dir: 시험지 디렉토리 경로 (None이면 기본 경로 사용)
            sets: 평가할 세트 번호 리스트 (None이면 모든 세트 평가, 예: [1] 또는 [1, 2, 3])
        """
        self.logger.info(f"=== 6단계: 시험지 평가 (배치 크기: {batch_size}) ===")
        
        if run_eval_pipeline_improved is None or load_data_from_directory is None:
            self.logger.error("multiple_eval_by_model 모듈을 import할 수 없습니다.")
            return {'success': False, 'error': 'multiple_eval_by_model import 실패'}
        
        if models is None:
            models = [
                'anthropic/claude-sonnet-4.5',
                'google/gemini-2.5-flash',
                'openai/gpt-5',
                'google/gemini-2.5-pro',
                'google/gemma-3-27b-it:free'
            ]
        
        # 세트 이름 매핑
        set_names = {
            1: '1st',
            2: '2nd',
            3: '3rd',
            4: '4th',
            5: '5th'
        }
        
        # 시험지 디렉토리 (exam_dir가 지정되지 않으면 기본 경로 사용)
        if exam_dir is None:
            exam_dir = os.path.join(
                self.onedrive_path,
                'evaluation/eval_data/4_multiple_exam'
            )
        else:
            # 상대 경로인 경우 onedrive_path 기준으로 변환
            if not os.path.isabs(exam_dir):
                exam_dir = os.path.join(self.onedrive_path, exam_dir)
        
        if not os.path.exists(exam_dir):
            self.logger.error(f"시험지 디렉토리를 찾을 수 없습니다: {exam_dir}")
            return {'success': False, 'error': f'시험지 디렉토리 없음: {exam_dir}'}
        
        # 출력 디렉토리
        output_dir = os.path.join(
            self.onedrive_path,
            'evaluation/eval_data/6_exam_evaluation'
        )
        os.makedirs(output_dir, exist_ok=True)
        
        # 평가할 세트 번호 결정
        if sets is None:
            # 세트가 지정되지 않으면 모든 세트 평가
            sets_to_evaluate = list(range(1, 6))
        else:
            # 지정된 세트만 평가
            sets_to_evaluate = [s for s in sets if 1 <= s <= 5]
            if not sets_to_evaluate:
                self.logger.error("유효한 세트 번호가 없습니다. (1-5 사이의 숫자만 가능)")
                return {'success': False, 'error': '유효하지 않은 세트 번호'}
        
        self.logger.info(f"평가할 세트: {[set_names[s] for s in sets_to_evaluate]}")
        
        # 각 세트별로 평가
        all_results = {}
        
        for set_num in sets_to_evaluate:
            set_name = set_names[set_num]
            set_dir = os.path.join(exam_dir, set_name)
            
            if not os.path.exists(set_dir):
                self.logger.warning(f"세트 디렉토리를 찾을 수 없습니다: {set_dir}")
                continue
            
            self.logger.info(f"{'='*50}")
            self.logger.info(f"세트: {set_name}")
            self.logger.info(f"{'='*50}")
            
            # 세트 내 모든 시험 파일 찾기
            exam_files = []
            for file in os.listdir(set_dir):
                if file.endswith('_exam.json'):
                    exam_files.append(os.path.join(set_dir, file))
            
            if not exam_files:
                self.logger.warning(f"{set_name} 세트에 시험 파일이 없습니다.")
                continue
            
            self.logger.info(f"{set_name} 세트에서 {len(exam_files)}개의 시험 파일을 찾았습니다.")
            
            # 모든 시험 파일의 데이터를 합쳐서 한번에 평가
            try:
                # load_data_from_directory가 None인지 확인
                if load_data_from_directory is None:
                    self.logger.error("load_data_from_directory 함수를 import할 수 없습니다.")
                    continue
                
                # 모든 파일의 데이터를 합치기
                all_combined_data = []
                loaded_files = []
                
                for exam_file in exam_files:
                    exam_name = os.path.splitext(os.path.basename(exam_file))[0].replace('_exam', '')
                    self.logger.info(f"데이터 로딩 중: {exam_file}")
                    
                    file_data, is_mock_exam = load_data_from_directory(
                        exam_file,
                        apply_tag_replacement=False
                    )
                    
                    if file_data:
                        all_combined_data.extend(file_data)
                        loaded_files.append(exam_name)
                        self.logger.info(f"  - {exam_name}: {len(file_data)}개 문제 로드")
                    else:
                        self.logger.warning(f"  - {exam_name}: 데이터를 로드할 수 없습니다.")
                
                if not all_combined_data:
                    self.logger.warning(f"{set_name} 세트에서 로드된 데이터가 없습니다.")
                    continue
                
                self.logger.info(f"{'='*50}")
                self.logger.info(f"세트: {set_name} - 총 {len(all_combined_data)}개 문제 (파일: {', '.join(loaded_files)})")
                self.logger.info(f"{'='*50}")
                
                # 평가 실행
                self.logger.info(f"평가 실행 중... (모델: {models}, 배치 크기: {batch_size})")
                df_all, pred_long, pred_wide, acc = run_eval_pipeline_improved(
                    all_combined_data,
                    models,
                    sample_size=len(all_combined_data),
                    batch_size=batch_size,
                    seed=42,
                    mock_mode=False,
                    use_server_mode=use_server_mode,
                    reasoning=reasoning
                )
                
                # 결과 출력
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"평가 결과 요약 ({set_name} 세트 - 총 {len(all_combined_data)}개 문제)")
                self.logger.info(f"{'='*50}")
                if print_evaluation_summary:
                    print_evaluation_summary(acc, pred_long)
                
                # 결과 저장
                # 모델 이름들을 파일명에 사용할 수 있도록 변환 (특수문자 제거)
                model_names = [model.split("/")[-1].replace(':', '_') for model in models]
                models_str = '_'.join(model_names)
                # 파일명이 너무 길어지지 않도록 제한 (최대 200자)
                if len(models_str) > 200:
                    models_str = models_str[:200] + '_etc'
                output_filename = f"{set_name}_evaluation_{models_str}.xlsx"
                output_path = os.path.join(output_dir, output_filename)
                
                if save_results_to_excel:
                    save_results_to_excel(
                        df_all, pred_wide, acc, pred_long,
                        output_path, mock_mode=False
                    )
                    self.logger.info(f"결과 저장 완료: {output_path}")
                
                # 결과 저장
                result_key = f"{set_name}_combined"
                all_results[result_key] = {
                    'set_name': set_name,
                    'loaded_files': loaded_files,
                    'total_questions': len(all_combined_data),
                    'models': models,
                    'accuracy': acc.to_dict() if hasattr(acc, 'to_dict') else acc,
                    'output_file': output_path
                }
                
                self.logger.info(f"{set_name} 세트 평가 완료 (총 {len(all_combined_data)}개 문제)")
                
            except Exception as e:
                self.logger.error(f"시험 평가 오류 ({set_name} 세트): {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                continue
        
        self.logger.info("모든 시험지 평가 완료")
        return {
            'success': True,
            'results': all_results
        }

