#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6단계: 시험지 평가
"""

import os
import sys
import configparser
import logging
from typing import List, Dict, Any
from ..base import PipelineBase
from ..config import PROJECT_ROOT_PATH, SFAICENTER_PATH
from core.logger import setup_step_logger

# evaluation 모듈 import (tools 폴더에서)
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, tools_dir)
try:
    from evaluation.multiple_eval_by_model import (
        run_eval_pipeline,
        load_data_from_directory,
        save_results_to_excel,
        print_evaluation_summary
    )
except ImportError:
    # fallback: 이미 tools_dir에 추가되어 있으므로 None으로 설정
    run_eval_pipeline = None
    load_data_from_directory = None
    save_results_to_excel = None
    print_evaluation_summary = None


class Step6Evaluate(PipelineBase):
    """6단계: 시험지 평가"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, models: List[str] = None, batch_size: int = 10, 
                use_ox_support: bool = True, use_server_mode: bool = False,
                exam_dir: str = None, sets: List[int] = None, 
                transformed: bool = False) -> Dict[str, Any]:
        """
        6단계: 시험지 평가
        - 만들어진 시험지(1st/2nd/3rd/4th/5th) 모델별 답변 평가
        - 10문제씩 배치화하여 호출
        
        Args:
            models: 평가할 모델 목록
            batch_size: 배치 크기
            use_ox_support: O, X 문제 지원 활성화
            use_server_mode: vLLM 서버 모드 사용
            exam_dir: 시험지 디렉토리 경로 (None이면 기본 경로 사용)
            sets: 평가할 세트 번호 리스트 (None이면 모든 세트 평가, 예: [1] 또는 [1, 2, 3])
            transformed: 변형 시험지 평가 모드 (True면 8_multiple_exam_+ 사용, False면 4_multiple_exam 사용)
        """
        self.logger.info(f"=== 6단계: 시험지 평가 (배치 크기: {batch_size}) ===")
        
        # 로깅 설정
        self._setup_step_logging('evaluate')
        
        try:
            if run_eval_pipeline is None or load_data_from_directory is None:
                self.logger.error("multiple_eval_by_model 모듈을 import할 수 없습니다.")
                return {'success': False, 'error': 'multiple_eval_by_model import 실패'}
            
            # llm_config.ini에서 key_evaluate 읽기 (OpenRouter 사용 시 필수)
            api_key = None
            if not use_server_mode:  # OpenRouter API 모드일 때만 key_evaluate 필수
                try:
                    config_path = os.path.join(self.project_root_path, 'llm_config.ini')
                    if not os.path.exists(config_path):
                        self.logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
                        return {'success': False, 'error': f'설정 파일 없음: {config_path}'}
                    
                    config = configparser.ConfigParser()
                    config.read(config_path, encoding='utf-8')
                    
                    if not config.has_option("OPENROUTER", "key_evaluate"):
                        self.logger.error("key_evaluate가 설정 파일에 없습니다. step6_evaluate에서는 key_evaluate가 필수입니다.")
                        return {'success': False, 'error': 'key_evaluate가 설정 파일에 없습니다.'}
                    
                    api_key = config.get("OPENROUTER", "key_evaluate")
                    self.logger.info("key_evaluate를 사용하여 LLM 호출합니다.")
                except Exception as e:
                    self.logger.error(f"key_evaluate를 읽는 중 오류 발생: {e}")
                    return {'success': False, 'error': f'key_evaluate 읽기 실패: {str(e)}'}
            
            if models is None:
                models = [
                    # SOTA 상위버전 모델
                    'openai/gpt-5',
                    'google/gemini-2.5-pro',
                    'anthropic/claude-sonnet-4.5',
                    
                    # SOTA 하위버전 모델
                    'openai/gpt-4.1',
                    'anthropic/claude-3.7-sonnet',
                    'google/gemini-2.5-flash',                
                    
                    # 센터 바닐라모델
                    'google/gemma-3-27b-it:free',

                    # 대형 모델
                    'meta-llama/llama-4-maverick:free'
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
                if transformed:
                    exam_dir = os.path.join(
                        self.onedrive_path,
                        'evaluation', 'eval_data', '8_multiple_exam_+'
                    )
                else:
                    exam_dir = os.path.join(
                        self.onedrive_path,
                        'evaluation', 'eval_data', '4_multiple_exam'
                    )
            else:
                # 상대 경로인 경우 onedrive_path 기준으로 변환
                if not os.path.isabs(exam_dir):
                    exam_dir = os.path.join(self.onedrive_path, exam_dir)
            
            if not os.path.exists(exam_dir):
                self.logger.error(f"시험지 디렉토리/파일을 찾을 수 없습니다: {exam_dir}")
                return {'success': False, 'error': f'시험지 디렉토리/파일 없음: {exam_dir}'}
            
            # 출력 디렉토리 설정
            if transformed:
                # 변형 모드: 8_multiple_exam_+ 밑에 exam_+_result 폴더
                output_dir = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '8_multiple_exam_+', 'exam_+_result'
                )
            else:
                # 기본 모드: 4_multiple_exam 밑에 exam_result 폴더
                output_dir = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '4_multiple_exam', 'exam_result'
                )
            os.makedirs(output_dir, exist_ok=True)
            
            # exam_dir가 단일 JSON 파일인지 확인
            if os.path.isfile(exam_dir) and exam_dir.endswith('.json'):
                # 단일 파일 평가 모드
                self.logger.info(f"단일 JSON 파일 평가 모드: {exam_dir}")
                
                try:
                    if load_data_from_directory is None:
                        self.logger.error("load_data_from_directory 함수를 import할 수 없습니다.")
                        return {'success': False, 'error': 'load_data_from_directory import 실패'}
                    
                    # 파일 데이터 로드
                    exam_name = os.path.splitext(os.path.basename(exam_dir))[0]
                    self.logger.info(f"데이터 로딩 중: {exam_dir}")
                    
                    file_data = load_data_from_directory(
                        exam_dir,
                        apply_tag_replacement=False
                    )
                    
                    if not file_data:
                        self.logger.error(f"데이터를 로드할 수 없습니다: {exam_dir}")
                        return {'success': False, 'error': f'데이터 로드 실패: {exam_dir}'}
                    
                    self.logger.info(f"{'='*50}")
                    self.logger.info(f"파일: {exam_name} - 총 {len(file_data)}개 문제")
                    self.logger.info(f"{'='*50}")
                    
                    # 평가 실행
                    self.logger.info(f"평가 실행 중... (모델: {models}, 배치 크기: {batch_size}, 변형 모드: {transformed})")
                    df_all, pred_long, pred_wide, acc = run_eval_pipeline(
                        file_data,
                        models,
                        sample_size=len(file_data),
                        batch_size=batch_size,
                        seed=42,
                        use_server_mode=use_server_mode,
                        use_ox_support=use_ox_support,
                        api_key=api_key,
                        output_base_dir=output_dir,
                        transformed=transformed
                    )
                    
                    # 결과 출력
                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"평가 결과 요약 ({exam_name} - 총 {len(file_data)}개 문제)")
                    self.logger.info(f"{'='*50}")
                    if print_evaluation_summary:
                        print_evaluation_summary(acc, pred_long)
                    
                    # 파일명에서 세트 정보 추출 (1st, 2nd, 3rd, 4th, 5th)
                    detected_set = None
                    exam_name_lower = exam_name.lower()
                    for set_num, set_name in set_names.items():
                        if set_name.lower() in exam_name_lower:
                            detected_set = set_name
                            break
                    
                    # 결과 저장 경로 설정
                    # 모델 이름들을 파일명에 사용할 수 있도록 변환
                    model_names = [model.split("/")[-1].replace(':', '_') for model in models]
                    models_str = '_'.join(model_names)
                    if len(models_str) > 200:
                        models_str = models_str[:200] + '_etc'
                    
                    if transformed:
                        # 변형 모드: 기본 모드와 같은 파일명 형식에 _transformed 추가
                        if detected_set:
                            output_filename = f"{detected_set}_evaluation_{models_str}_transformed.xlsx"
                        else:
                            output_filename = f"{exam_name}_evaluation_{models_str}_transformed.xlsx"
                        output_path = os.path.join(output_dir, output_filename)
                    else:
                        # 기본 모드: 세트별 디렉토리에 저장
                        if detected_set:
                            set_output_dir = os.path.join(output_dir, detected_set)
                            os.makedirs(set_output_dir, exist_ok=True)
                        else:
                            set_output_dir = output_dir
                        
                        output_filename = f"{exam_name}_evaluation_{models_str}.xlsx"
                        output_path = os.path.join(set_output_dir, output_filename)
                    
                    if save_results_to_excel:
                        save_results_to_excel(
                            df_all, pred_wide, acc, pred_long,
                            output_path
                        )
                        self.logger.info(f"결과 저장 완료: {output_path}")
                    
                    self.logger.info(f"평가 완료 (총 {len(file_data)}개 문제)")
                    return {
                        'success': True,
                        'results': {
                            'single_file': {
                                'file_name': exam_name,
                                'file_path': exam_dir,
                                'total_questions': len(file_data),
                                'models': models,
                                'accuracy': acc.to_dict() if hasattr(acc, 'to_dict') else acc,
                                'output_file': output_path
                            }
                        }
                    }
                
                except Exception as e:
                    self.logger.error(f"시험 평가 오류: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return {'success': False, 'error': f'평가 오류: {str(e)}'}
            
            # 디렉토리 모드 (기존 로직)
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
                self.logger.info(f"세트 디렉토리: {set_dir}")
                self.logger.info(f"{'='*50}")
                
                # 세트 내 모든 시험 파일 찾기
                exam_files = []
                try:
                    files_in_dir = os.listdir(set_dir)
                    self.logger.info(f"디렉토리 내 파일 목록: {files_in_dir}")
                    for file in files_in_dir:
                        if file.endswith('_exam.json'):
                            exam_files.append(os.path.join(set_dir, file))
                        if transformed and file.endswith('_exam_transformed.json'):
                            exam_files.append(os.path.join(set_dir, file))
                except Exception as e:
                    self.logger.error(f"디렉토리 읽기 오류 ({set_dir}): {e}")
                    continue
                
                if not exam_files:
                    self.logger.warning(f"{set_name} 세트에 시험 파일(~_exam.json 또는 ~_exam_transformed.json)이 없습니다. (디렉토리: {set_dir})")
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
                        
                        file_data = load_data_from_directory(
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
                    self.logger.info(f"평가 실행 중... (모델: {models}, 배치 크기: {batch_size}, 변형 모드: {transformed})")
                    df_all, pred_long, pred_wide, acc = run_eval_pipeline(
                        all_combined_data,
                        models,
                        sample_size=len(all_combined_data),
                        batch_size=batch_size,
                        seed=42,
                        use_server_mode=use_server_mode,
                        use_ox_support=use_ox_support,
                        api_key=api_key,
                        output_base_dir=output_dir,
                        transformed=transformed
                    )
                    
                    # 결과 출력
                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"평가 결과 요약 ({set_name} 세트 - 총 {len(all_combined_data)}개 문제)")
                    self.logger.info(f"{'='*50}")
                    if print_evaluation_summary:
                        print_evaluation_summary(acc, pred_long)
                    
                    # 결과 저장 경로 설정
                    # 모델 이름들을 파일명에 사용할 수 있도록 변환 (특수문자 제거)
                    model_names = [model.split("/")[-1].replace(':', '_') for model in models]
                    models_str = '_'.join(model_names)
                    # 파일명이 너무 길어지지 않도록 제한 (최대 200자)
                    if len(models_str) > 200:
                        models_str = models_str[:200] + '_etc'
                    
                    if transformed:
                        # 변형 모드: 기본 모드와 같은 파일명 형식에 _transformed 추가
                        output_filename = f"{set_name}_evaluation_{models_str}_transformed.xlsx"
                        output_path = os.path.join(output_dir, output_filename)
                    else:
                        # 기본 모드: 세트별 디렉토리에 저장
                        # 세트별 출력 디렉토리 생성 (예: exam_result/1st, exam_result/2nd)
                        set_output_dir = os.path.join(output_dir, set_name)
                        os.makedirs(set_output_dir, exist_ok=True)
                        
                        output_filename = f"{set_name}_evaluation_{models_str}.xlsx"
                        output_path = os.path.join(set_output_dir, output_filename)
                    
                    if save_results_to_excel:
                        save_results_to_excel(
                            df_all, pred_wide, acc, pred_long,
                            output_path
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
        except Exception as e:
            self.logger.error(f"시험 평가 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': False, 'error': f'평가 오류: {str(e)}'}
        finally:
            self._remove_step_logging()
    
    def _setup_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 설정"""
        step_logger, file_handler = setup_step_logger(
            step_name=step_name,
            step_number=6
        )
        # 기존 로거에 핸들러 추가
        self.logger.addHandler(file_handler)
        self._step_log_handler = file_handler
    
    def _remove_step_logging(self):
        """단계별 로그 파일 핸들러 제거"""
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
            self._step_log_handler.close()
            self._step_log_handler = None

