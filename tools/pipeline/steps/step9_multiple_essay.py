#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9단계: 객관식 문제를 서술형 문제로 변환

처리 흐름:
1. 해설이 많은 문제 선별
2. 시험별로 분류
3. 서술형 문제로 변환
4. 키워드 추출
5. 모범답안 생성
6. 모델 답변 생성 (선택적)
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from ..base import PipelineBase

# transformed 모듈 import
try:
    from tools.transformed.essay_filter_full_explanation import filter_full_explanation
    from tools.transformed.essay_change_question_to_essay import change_question_to_essay
    from tools.transformed.essay_extract_keywords import extract_keywords
    from tools.transformed.essay_create_best_answers import create_best_answers
    from tools.transformed.essay_classify_by_exam import main as classify_essay_by_exam_main
    from tools.transformed.essay_create_model_answers import process_essay_questions, get_api_key
    from tools.core.llm_query import LLMQuery
except ImportError as e:
    # 디버깅을 위해 에러 로깅
    import traceback
    logger = logging.getLogger(__name__)
    logger.error(f"Import error: {e}")
    logger.error(traceback.format_exc())
    filter_full_explanation = None
    change_question_to_essay = None
    extract_keywords = None
    create_best_answers = None
    classify_essay_by_exam_main = None
    process_essay_questions = None
    get_api_key = None
    LLMQuery = None


class Step9MultipleEssay(PipelineBase):
    """9단계: 객관식 문제를 서술형 문제로 변환"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, models: List[str] = None, sets: List[int] = None,
                use_server_mode: bool = False, steps: List[int] = None) -> Dict[str, Any]:
        """
        9단계: 객관식 문제를 서술형 문제로 변환
        
        Args:
            models: 모델 답변 생성할 모델 목록 (None이면 답변 생성 안 함)
            sets: 처리할 세트 번호 리스트 (None이면 1~5 모두 처리, models가 있을 때만 사용)
            use_server_mode: vLLM 서버 모드 사용 (models가 있을 때만 사용)
            steps: 실행할 단계 리스트 (예: [1, 2] 또는 [3, 4, 5] 등). None이면 모든 단계(1-5) 실행
                1단계: 해설이 많은 문제 선별
                2단계: 시험별로 분류
                3단계: 서술형 문제로 변환
                4단계: 키워드 추출
                5단계: 모범답안 생성
        
        Returns:
            dict: 실행 결과
        """
        self.logger.info("=== 9단계: 객관식 문제를 서술형 문제로 변환 ===")
        
        # 로깅 설정
        self._setup_step_logging('multiple_essay', 9)
        
        try:
            if self.llm_query is None:
                self.logger.error("LLMQuery가 초기화되지 않았습니다.")
                return {'success': False, 'error': 'LLMQuery 초기화 실패'}
            
            if filter_full_explanation is None:
                self.logger.error("transformed.essay_filter_full_explanation 모듈을 import할 수 없습니다.")
                return {'success': False, 'error': '필수 모듈 import 실패'}
            
            # 경로 설정
            essay_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '9_multiple_to_essay'
            )
            
            # 실행할 단계 결정 (None이면 모든 단계 실행)
            if steps is None:
                steps = [1, 2, 3, 4, 5]
            else:
                steps = [s for s in steps if 1 <= s <= 5]
                if not steps:
                    self.logger.error("유효한 단계가 없습니다. (1-5 사이의 숫자만 가능)")
                    return {'success': False, 'error': '유효하지 않은 단계 번호'}
            
            self.logger.info(f"실행할 단계: {steps}")
            
            # 회차에 따른 폴더명 매핑
            round_number_to_folder = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th', '5': '5th'}
            
            # sets가 있으면 해당 회차만 처리, 없으면 모든 회차 처리
            if sets is not None:
                valid_sets = [s for s in sets if 1 <= s <= 5]
                if not valid_sets:
                    self.logger.error("유효한 세트 번호가 없습니다. (1-5 사이의 숫자만 가능)")
                    return {'success': False, 'error': '유효하지 않은 세트 번호'}
                round_numbers = [str(s) for s in sorted(valid_sets)]
                # 4단계에서 사용할 수 있도록 sets 업데이트
                sets = valid_sets
                self.logger.info(f"처리할 회차: {round_numbers}")
            else:
                round_numbers = ['1', '2', '3', '4', '5']
            
            total_questions = 0
            output_files = []
            
            # 1단계: 해설이 많은 문제 선별
            if 1 in steps:
                self.logger.info("1단계: 해설이 많은 문제 선별 중...")
                if filter_full_explanation is None:
                    self.logger.error("filter_full_explanation 함수를 import할 수 없습니다.")
                    return {'success': False, 'error': 'filter_full_explanation import 실패'}
                
                try:
                    count = filter_full_explanation(
                        llm=self.llm_query,
                        onedrive_path=self.onedrive_path,
                        log_func=self.logger.info
                    )
                    self.logger.info(f"1단계 완료: 총 {count}개의 문제 선별")
                except Exception as e:
                    self.logger.error(f"1단계 오류: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return {'success': False, 'error': f'1단계 오류: {str(e)}'}
            
            # 2단계: 시험별로 분류
            if 2 in steps:
                self.logger.info("2단계: 시험별로 분류 중...")
                try:
                    if classify_essay_by_exam_main is None:
                        self.logger.error("essay_classify_by_exam 모듈을 import할 수 없습니다.")
                        return {'success': False, 'error': 'essay_classify_by_exam import 실패'}
                    
                    # classify_essay_by_exam_main은 모든 회차를 한 번에 처리하므로
                    # sets가 있어도 전체를 처리하고, 이후 단계에서 sets에 해당하는 회차만 사용
                    classify_essay_by_exam_main()
                    self.logger.info("2단계 완료: 시험별 분류")
                except Exception as e:
                    self.logger.error(f"2단계 오류: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return {'success': False, 'error': f'2단계 오류: {str(e)}'}
            
            # 3단계: 서술형 문제로 변환
            if 3 in steps:
                self.logger.info("3단계: 서술형 문제로 변환 중...")
                if change_question_to_essay is None:
                    self.logger.error("essay_change_question_to_essay 함수를 import할 수 없습니다.")
                    return {'success': False, 'error': 'essay_change_question_to_essay import 실패'}
                
                step3_total = 0
                for round_number in round_numbers:
                    round_folder = round_number_to_folder[round_number]
                    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}.json')
                    
                    if not os.path.exists(input_file):
                        self.logger.warning(f"입력 파일을 찾을 수 없습니다: {input_file}, 건너뜁니다.")
                        continue
                    
                    self.logger.info(f"{round_number} 회차 3단계 처리 중...")
                    try:
                        count = change_question_to_essay(
                            llm=self.llm_query,
                            onedrive_path=self.onedrive_path,
                            log_func=self.logger.info,
                            round_number=round_number
                        )
                        step3_total += count
                    except Exception as e:
                        self.logger.error(f"{round_number} 회차 3단계 오류: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                        continue
                
                self.logger.info(f"3단계 완료: 총 {step3_total}개의 문제 처리")
            
            # 4단계: 키워드 추출
            if 4 in steps:
                self.logger.info("4단계: 키워드 추출 중...")
                if extract_keywords is None:
                    self.logger.error("essay_extract_keywords 함수를 import할 수 없습니다.")
                    return {'success': False, 'error': 'essay_extract_keywords import 실패'}
                
                step4_total = 0
                for round_number in round_numbers:
                    round_folder = round_number_to_folder[round_number]
                    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_{round_folder}_서술형문제로변환.json')
                    
                    if not os.path.exists(input_file):
                        self.logger.warning(f"입력 파일을 찾을 수 없습니다: {input_file}, 건너뜁니다.")
                        continue
                    
                    self.logger.info(f"{round_number} 회차 4단계 처리 중...")
                    try:
                        count = extract_keywords(
                            llm=self.llm_query,
                            onedrive_path=self.onedrive_path,
                            log_func=self.logger.info,
                            round_number=round_number
                        )
                        step4_total += count
                    except Exception as e:
                        self.logger.error(f"{round_number} 회차 4단계 오류: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                        continue
                
                self.logger.info(f"4단계 완료: 총 {step4_total}개의 문제 처리")
            
            # 5단계: 모범답안 생성
            if 5 in steps:
                self.logger.info("5단계: 모범답안 생성 중...")
                if create_best_answers is None:
                    self.logger.error("essay_create_best_answers 함수를 import할 수 없습니다.")
                    return {'success': False, 'error': 'essay_create_best_answers import 실패'}
                
                step5_total = 0
                for round_number in round_numbers:
                    round_folder = round_number_to_folder[round_number]
                    input_file = os.path.join(essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json')
                    output_file = os.path.join(essay_dir, 'answers', f'best_ans_{round_folder}.json')
                    
                    if not os.path.exists(input_file):
                        self.logger.warning(f"입력 파일을 찾을 수 없습니다: {input_file}, 건너뜁니다.")
                        continue
                    
                    self.logger.info(f"{round_number} 회차 5단계 처리 중...")
                    try:
                        count = create_best_answers(
                            llm=self.llm_query,
                            onedrive_path=self.onedrive_path,
                            log_func=self.logger.info,
                            round_number=round_number
                        )
                        step5_total += count
                        output_files.append(output_file)
                    except Exception as e:
                        self.logger.error(f"{round_number} 회차 5단계 오류: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                        continue
                
                total_questions = step5_total
                self.logger.info(f"5단계 완료: 총 {step5_total}개의 문제 처리")
            
            # 모델 답변 생성 (선택적, steps와 별개)
            if models:
                self.logger.info("모델 답변 생성 중...")
                
                if process_essay_questions is None:
                    self.logger.error("transformed.multi_essay_answer 모듈을 import할 수 없습니다.")
                    return {'success': False, 'error': 'multi_essay_answer import 실패'}
                
                # 세트 번호 설정 (이미 위에서 설정됨)
                if sets is None:
                    sets = [1, 2, 3, 4, 5]
                
                # API 키 읽기 (서버 모드가 아닐 때만 필요)
                api_key = None
                if not use_server_mode:
                    if get_api_key:
                        api_key = get_api_key()
                    else:
                        # 직접 config 읽기
                        import configparser
                        config_path = os.path.join(self.project_root_path, 'llm_config.ini')
                        if os.path.exists(config_path):
                            config = configparser.ConfigParser()
                            config.read(config_path, encoding='utf-8')
                            if config.has_option("OPENROUTER", "key_evaluate"):
                                api_key = config.get("OPENROUTER", "key_evaluate")
                            elif config.has_option("OPENROUTER", "key_essay"):
                                api_key = config.get("OPENROUTER", "key_essay")
                            elif config.has_option("OPENROUTER", "key"):
                                api_key = config.get("OPENROUTER", "key")
                
                # 각 모델과 세트 조합에 대해 답변 생성
                for model_name in models:
                    for set_num in sets:
                        round_number = str(set_num)
                        round_folder = round_number_to_folder.get(round_number, '1st')
                        
                        # 각 회차별 파일에서 데이터 로드 (4단계 출력 파일 사용)
                        input_file = os.path.join(
                            essay_dir, 'questions', f'essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json'
                        )
                        
                        if not os.path.exists(input_file):
                            self.logger.warning(f"파일을 찾을 수 없습니다: {input_file}")
                            continue
                        
                        self.logger.info(f"모델 {model_name} 세트 {round_number} 답변 생성 중...")
                        with open(input_file, 'r', encoding='utf-8') as f:
                            full_explanation = json.load(f)
                        
                        # seed 고정하여 랜덤으로 150문제 추출 (각 회차마다 독립적으로)
                        import random
                        random.seed(42)
                        selected_questions = random.sample(full_explanation, min(150, len(full_explanation)))
                        self.logger.info(f"선택된 문제 수: {len(selected_questions)}개 (전체: {len(full_explanation)}개)")
                        
                        try:
                            process_essay_questions(
                                model_name, round_number, round_folder, 
                                selected_questions, api_key, use_server_mode
                            )
                            self.logger.info(f"답변 생성 완료: 모델 {model_name}, 세트 {round_number}")
                        except Exception as e:
                            self.logger.error(f"모델 {model_name} 세트 {round_number} 답변 생성 중 오류: {e}")
                            import traceback
                            self.logger.error(traceback.format_exc())
                            continue
            
            self.logger.info("=== 9단계 완료 ===")
            
            return {
                'success': True,
                'total_questions': total_questions,
                'output_files': output_files
            }
            
        except Exception as e:
            self.logger.error(f"서술형 문제 변환 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': False, 'error': f'변환 오류: {str(e)}'}
        finally:
            self._remove_step_logging()


