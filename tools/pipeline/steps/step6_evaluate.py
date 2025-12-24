#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6단계: 시험지 평가

- 객관식 문제 평가 (일반/변형)
- 서술형 문제 평가
"""

import os
import json
import configparser
from typing import List, Dict, Any
from ..base import PipelineBase

# evaluation 모듈 import
try:
    from tools.evaluation.multiple_eval_by_model import (
        run_eval_pipeline,
        load_data_from_directory,
        save_results_to_excel,
        save_combined_results_to_excel,
        print_evaluation_summary,
    )
    from tools.evaluation.evaluate_essay_model import (
        evaluate_single_model,
        calculate_statistics,
    )
    from tools.evaluation.essay_utils import load_best_answers, setup_llm_with_api_key
except ImportError:
    run_eval_pipeline = None
    load_data_from_directory = None
    save_results_to_excel = None
    save_combined_results_to_excel = None
    print_evaluation_summary = None
    evaluate_single_model = None
    calculate_statistics = None
    load_best_answers = None
    setup_llm_with_api_key = None


class Step6Evaluate(PipelineBase):
    """6단계: 시험지 평가"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, models: List[str] = None, batch_size: int = 10, 
                use_ox_support: bool = True, use_server_mode: bool = False,
                exam_dir: str = None, sets: List[int] = None, 
                transformed: bool = False, essay: bool = False) -> Dict[str, Any]:
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
            essay: 서술형 문제 평가 모드 (True면 9_multiple_to_essay 평가 수행)
        """
        self.logger.info(f"=== 6단계: 시험지 평가 (배치 크기: {batch_size}) ===")
        
        # 로깅 설정
        self._setup_step_logging('evaluate', 6)
        
        try:
            if run_eval_pipeline is None or load_data_from_directory is None:
                self.logger.error("multiple_eval_by_model 모듈을 import할 수 없습니다.")
                return {'success': False, 'error': 'multiple_eval_by_model import 실패'}
            
            # llm_config.ini에서 key_evaluate 읽기 (OpenRouter 사용 시 필수)
            api_key = None
            if not use_server_mode:  # OpenRouter API 모드일 때만 key_evaluate 필수
                try:
                    # self.config_path 사용 (--config_path로 지정한 경로 또는 기본값)
                    config_path = self.config_path
                    if not config_path:
                        config_path = os.path.join(self.project_root_path, 'llm_config.ini')
                    
                    if not os.path.exists(config_path):
                        self.logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
                        return {'success': False, 'error': f'설정 파일 없음: {config_path}'}
                    
                    self.logger.info(f"설정 파일 사용: {config_path}")
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
            if use_server_mode:
                # 서버 모드: exam_dir 밑에 결과 폴더
                result_folder = 'exam_+_result' if transformed else 'exam_result'
                if os.path.isfile(exam_dir):
                    # 단일 파일인 경우 부모 디렉토리 사용
                    output_dir = os.path.join(os.path.dirname(exam_dir), result_folder)
                else:
                    output_dir = os.path.join(exam_dir, result_folder)
            elif transformed:
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
                    # subject 추출: 파일명에서 _exam, _transformed 등을 제거
                    subject_name = exam_name.replace('_exam', '').replace('_transformed', '')
                    self.logger.info(f"데이터 로딩 중: {exam_dir}")
                    
                    file_data = load_data_from_directory(
                        exam_dir,
                        apply_tag_replacement=False
                    )
                    
                    if not file_data:
                        self.logger.error(f"데이터를 로드할 수 없습니다: {exam_dir}")
                        return {'success': False, 'error': f'데이터 로드 실패: {exam_dir}'}
                    
                    # 각 item에 subject 추가 (비어있거나 없는 경우)
                    for item in file_data:
                        if not item.get('subject'):
                            item['subject'] = subject_name
                    
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
                transformed_files = []
                normal_files = []
                actual_transformed = transformed  # 기본값은 파라미터로 전달된 값
                try:
                    files_in_dir = os.listdir(set_dir)
                    self.logger.info(f"디렉토리 내 파일 목록: {files_in_dir}")
                    for file in files_in_dir:
                        if file.endswith('_exam_transformed.json'):
                            transformed_files.append(os.path.join(set_dir, file))
                        elif file.endswith('_exam.json'):
                            normal_files.append(os.path.join(set_dir, file))
                    
                    # 파일명에 따라 transformed 모드 자동 감지
                    # _exam_transformed.json 파일이 있으면 transformed 모드로 평가
                    if transformed_files:
                        exam_files = transformed_files
                        # 파일명 기반으로 transformed 모드 자동 설정
                        actual_transformed = True
                        self.logger.info(f"{set_name} 세트: _exam_transformed.json 파일 발견, transformed 모드로 평가합니다.")
                    elif normal_files:
                        exam_files = normal_files
                        actual_transformed = False
                        self.logger.info(f"{set_name} 세트: _exam.json 파일 발견, 기본 모드로 평가합니다.")
                    else:
                        exam_files = []
                except Exception as e:
                    self.logger.error(f"디렉토리 읽기 오류 ({set_dir}): {e}")
                    continue
                
                if not exam_files:
                    self.logger.warning(f"{set_name} 세트에 시험 파일(~_exam.json 또는 ~_exam_transformed.json)이 없습니다. (디렉토리: {set_dir})")
                    continue
                
                self.logger.info(f"{set_name} 세트에서 {len(exam_files)}개의 시험 파일을 찾았습니다.")
                
                # 세트별 통합 평가 수행 (4개 파일을 하나로 합쳐서 평가)
                try:
                    # load_data_from_directory가 None인지 확인
                    if load_data_from_directory is None:
                        self.logger.error("load_data_from_directory 함수를 import할 수 없습니다.")
                        continue
                    
                    # 모델 이름들을 파일명에 사용할 수 있도록 변환 (특수문자 제거)
                    model_names = [model.split("/")[-1].replace(':', '_') for model in models]
                    models_str = '_'.join(model_names)
                    # 파일명이 너무 길어지지 않도록 제한 (최대 200자)
                    if len(models_str) > 200:
                        models_str = models_str[:200] + '_etc'
                    
                    # 모든 시험 파일 데이터를 통합
                    all_exam_data = []
                    for exam_file in exam_files:
                        exam_name = os.path.splitext(os.path.basename(exam_file))[0].replace('_exam', '').replace('_transformed', '')
                        self.logger.info(f"데이터 로딩 중: {exam_file}")
                        
                        file_data = load_data_from_directory(
                            exam_file,
                            apply_tag_replacement=False
                        )
                        
                        if not file_data:
                            self.logger.warning(f"  - {exam_name}: 데이터를 로드할 수 없습니다.")
                            continue
                        
                        # 각 item에 subject 추가 (비어있거나 없는 경우)
                        for item in file_data:
                            if not item.get('subject'):
                                item['subject'] = exam_name
                        
                        self.logger.info(f"  - {exam_name}: {len(file_data)}개 문제 로드")
                        all_exam_data.extend(file_data)
                    
                    if not all_exam_data:
                        self.logger.warning(f"{set_name} 세트에서 로드할 문제가 없습니다.")
                        continue
                    
                    self.logger.info(f"{'='*50}")
                    self.logger.info(f"세트 {set_name} 통합 평가 시작: 총 {len(all_exam_data)}개 문제")
                    self.logger.info(f"{'='*50}")
                    
                    # 통합 평가 실행
                    self.logger.info(f"평가 실행 중... (모델: {models}, 배치 크기: {batch_size}, 변형 모드: {actual_transformed})")
                    df_all, pred_long, pred_wide, acc = run_eval_pipeline(
                        all_exam_data,
                        models,
                        sample_size=len(all_exam_data),
                        batch_size=batch_size,
                        seed=42,
                        use_server_mode=use_server_mode,
                        use_ox_support=use_ox_support,
                        api_key=api_key,
                        output_base_dir=output_dir,
                        transformed=actual_transformed
                    )
                    
                    # 결과 출력
                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"평가 결과 요약 (세트: {set_name}, 총 {len(all_exam_data)}개 문제)")
                    self.logger.info(f"{'='*50}")
                    if print_evaluation_summary:
                        print_evaluation_summary(acc, pred_long)
                    
                    # 결과 저장 경로 설정
                    if actual_transformed:
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
                    
                    # 통합 결과 저장 (subject/domain/subdomain별 정확도 포함)
                    if save_combined_results_to_excel:
                        save_combined_results_to_excel(
                            df_all, pred_wide, acc, pred_long,
                            models, output_path, actual_transformed
                        )
                        self.logger.info(f"통합 결과 저장 완료: {output_path}")
                    elif save_results_to_excel:
                        # fallback: 기본 저장
                        save_results_to_excel(
                            df_all, pred_wide, acc, pred_long,
                            output_path
                        )
                        self.logger.info(f"결과 저장 완료: {output_path}")
                    
                    # 결과 저장
                    all_results[set_name] = {
                        'set_name': set_name,
                        'total_questions': len(all_exam_data),
                        'models': models,
                        'accuracy': acc.to_dict() if hasattr(acc, 'to_dict') else acc,
                        'output_file': output_path
                    }
                    
                    self.logger.info(f"세트 {set_name} 평가 완료 (총 {len(all_exam_data)}개 문제)")
                
                except Exception as e:
                    self.logger.error(f"시험 평가 오류 ({set_name} 세트): {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    continue
            
            self.logger.info("모든 시험지 평가 완료")
            
            # essay=True일 때 서술형 문제 평가 수행
            if essay:
                self.logger.info("\n" + "="*60)
                self.logger.info("서술형 문제 평가 시작")
                self.logger.info("="*60)
                
                if evaluate_single_model is None:
                    self.logger.warning("evaluate_essay_model 모듈을 import할 수 없어 서술형 평가를 건너뜁니다.")
                else:
                    try:
                        # 서술형 문제 평가 경로 설정
                        essay_base_dir = os.path.join(
                            self.onedrive_path,
                            'evaluation', 'eval_data', '9_multiple_to_essay'
                        )
                        
                        if not os.path.exists(essay_base_dir):
                            self.logger.warning(f"서술형 문제 디렉토리를 찾을 수 없습니다: {essay_base_dir}")
                        else:
                            # 모범답안 로드
                            best_ans_file = os.path.join(essay_base_dir, 'best_ans.json')
                            best_answers_dict = {}
                            if load_best_answers:
                                best_answers_dict = load_best_answers(best_ans_file, self.logger)
                            else:
                                # 직접 로드
                                if os.path.exists(best_ans_file):
                                    with open(best_ans_file, 'r', encoding='utf-8') as f:
                                        best_answers = json.load(f)
                                    for ba in best_answers:
                                        key = (ba.get('file_id'), ba.get('tag'))
                                        best_answers_dict[key] = ba.get('essay_answer', ba.get('answer', ''))
                            
                            # LLM 인스턴스 생성
                            if setup_llm_with_api_key:
                                llm = setup_llm_with_api_key(self.project_root_path, self.logger)
                            else:
                                llm = self.llm_query
                            
                            # 평가할 세트 설정 (객관식 평가와 동일한 sets 파라미터 사용)
                            sets_to_evaluate = sets if sets else [1, 2, 3, 4, 5]
                            
                            # 출력 디렉토리
                            essay_output_dir = os.path.join(essay_base_dir, 'evaluation_results')
                            os.makedirs(essay_output_dir, exist_ok=True)
                            
                            # 세트 이름 매핑
                            set_names = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th'}
                            
                            # 각 모델과 세트 조합에 대해 평가 수행
                            for set_num in sets_to_evaluate:
                                set_name = set_names[set_num]
                                
                                # 각 세트별 문제 파일 경로 (questions/essay_questions_{set_name}.json)
                                question_file = os.path.join(
                                    essay_base_dir, 'questions', f'essay_questions_{set_name}.json'
                                )
                                
                                if not os.path.exists(question_file):
                                    self.logger.warning(f"서술형 문제 파일을 찾을 수 없습니다: {question_file}")
                                    continue
                                
                                for model_name in models:
                                    try:
                                        self.logger.info(f"서술형 평가: 모델 {model_name}, 세트 {set_num} ({set_name})")
                                        
                                        # 평가 수행
                                        evaluation_results, detailed_results, stats = evaluate_single_model(
                                            model_name, question_file, 
                                            keyword_check_model='google/gemini-2.5-flash',
                                            scoring_model='google/gemini-3-pro-preview',
                                            set_num=set_num,
                                            best_answers_dict=best_answers_dict
                                        )
                                        
                                        if evaluation_results is None:
                                            self.logger.warning(f"모델 {model_name} 세트 {set_num} 평가 결과가 없습니다.")
                                            continue
                                        
                                        # 파일명 생성
                                        model_safe_name = model_name.replace("/", "_")
                                        set_suffix = f"_set{set_num}"
                                        
                                        # 상세 결과 저장
                                        detailed_output_file = os.path.join(
                                            essay_output_dir, 
                                            f'{model_safe_name}{set_suffix}_detailed_results.json'
                                        )
                                        with open(detailed_output_file, 'w', encoding='utf-8') as f:
                                            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
                                        self.logger.info(f"상세 결과 저장: {detailed_output_file}")
                                        
                                        # 통계 저장
                                        stats_output_file = os.path.join(
                                            essay_output_dir,
                                            f'{model_safe_name}{set_suffix}_statistics.json'
                                        )
                                        stats_for_save = dict(stats)
                                        if 'keyword_avg_scores' in stats_for_save:
                                            stats_for_save['keyword_avg_scores'] = dict(stats['keyword_avg_scores'])
                                        with open(stats_output_file, 'w', encoding='utf-8') as f:
                                            json.dump(stats_for_save, f, ensure_ascii=False, indent=2)
                                        self.logger.info(f"통계 저장: {stats_output_file}")
                                        
                                    except Exception as e:
                                        self.logger.error(f"서술형 평가 오류 (모델: {model_name}, 세트: {set_num}): {e}")
                                        import traceback
                                        self.logger.error(traceback.format_exc())
                                        continue
                            
                            self.logger.info("서술형 문제 평가 완료")
                    except Exception as e:
                        self.logger.error(f"서술형 평가 중 오류: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
            
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
    

