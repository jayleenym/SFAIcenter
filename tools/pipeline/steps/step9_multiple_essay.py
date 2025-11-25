#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9단계: 객관식 문제를 서술형 문제로 변환
- 옳지 않은 문제 중 해설이 많은 문제 선별
- 키워드 추출 및 모범답안 생성
- 시험별로 분류
- 모델 답변 생성 (선택적)
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from ..base import PipelineBase

# transformed 모듈 import
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, tools_dir)

try:
    from transformed.create_essay_with_keywords import main as create_essay_main
    from transformed.classify_essay_by_exam import main as classify_essay_by_exam_main
    from transformed.multi_essay_answer import process_essay_questions, get_api_key
    from core.llm_query import LLMQuery
except ImportError as e:
    create_essay_main = None
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
                use_server_mode: bool = False) -> Dict[str, Any]:
        """
        9단계: 객관식 문제를 서술형 문제로 변환
        
        Args:
            models: 모델 답변 생성할 모델 목록 (None이면 답변 생성 안 함)
            sets: 처리할 세트 번호 리스트 (None이면 1~5 모두 처리, models가 있을 때만 사용)
            use_server_mode: vLLM 서버 모드 사용 (models가 있을 때만 사용)
        
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
            
            if create_essay_main is None:
                self.logger.error("transformed.create_essay_with_keywords 모듈을 import할 수 없습니다.")
                return {'success': False, 'error': '필수 모듈 import 실패'}
            
            # 경로 설정
            essay_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '9_multiple_to_essay'
            )
            output_file = os.path.join(essay_dir, 'best_ans.json')
            
            # create_essay_with_keywords.py의 main() 함수 호출
            self.logger.info("객관식 문제를 서술형 문제로 변환 중...")
            try:
                create_essay_main(
                    llm=self.llm_query,
                    onedrive_path=self.onedrive_path,
                    log_func=self.logger.info
                )
                
                # 결과 파일 확인
                if not os.path.exists(output_file):
                    self.logger.error(f"출력 파일이 생성되지 않았습니다: {output_file}")
                    return {'success': False, 'error': '출력 파일 생성 실패'}
                
                # 문제 개수 확인
                with open(output_file, 'r', encoding='utf-8') as f:
                    questions = json.load(f)
                self.logger.info(f"총 {len(questions)}개의 문제가 {output_file}에 저장되었습니다.")
            except Exception as e:
                self.logger.error(f"서술형 문제 변환 중 오류: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                return {'success': False, 'error': f'변환 오류: {str(e)}'}
            
            # 3단계: 시험별로 분류
            self.logger.info("3단계: 시험별로 분류 중...")
            try:
                if classify_essay_by_exam_main is None:
                    self.logger.error("classify_essay_by_exam 모듈을 import할 수 없습니다.")
                    return {'success': False, 'error': 'classify_essay_by_exam import 실패'}
                
                # classify_essay_by_exam.py의 main() 함수 실행
                # 이 함수는 ONEDRIVE_PATH를 직접 사용하므로 별도 설정 불필요
                classify_essay_by_exam_main()
                self.logger.info("시험별 분류 완료")
            except Exception as e:
                self.logger.error(f"시험별 분류 중 오류: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                return {'success': False, 'error': f'시험별 분류 오류: {str(e)}'}
            
            # 4단계: 모델 답변 생성 (models가 지정된 경우)
            if models:
                self.logger.info("4단계: 모델 답변 생성 중...")
                
                if process_essay_questions is None:
                    self.logger.error("transformed.multi_essay_answer 모듈을 import할 수 없습니다.")
                    return {'success': False, 'error': 'multi_essay_answer import 실패'}
                
                # 세트 번호 설정
                if sets is None:
                    sets = [1, 2, 3, 4, 5]
                else:
                    sets = [s for s in sets if 1 <= s <= 5]
                    if not sets:
                        self.logger.error("유효한 세트 번호가 없습니다. (1-5 사이의 숫자만 가능)")
                        return {'success': False, 'error': '유효하지 않은 세트 번호'}
                
                # 회차에 따른 폴더명 매핑
                round_folders = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th', '5': '5th'}
                
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
                        round_folder = round_folders[round_number]
                        
                        # 각 회차별 파일에서 데이터 로드
                        input_file = os.path.join(
                            essay_dir, 'questions', f'essay_questions_{round_folder}.json'
                        )
                        
                        if not os.path.exists(input_file):
                            self.logger.warning(f"파일을 찾을 수 없습니다: {input_file}")
                            continue
                        
                        self.logger.info(f"모델 {model_name} 세트 {round_folder} 답변 생성 중...")
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
                            self.logger.info(f"답변 생성 완료: 모델 {model_name}, 세트 {round_folder}")
                        except Exception as e:
                            self.logger.error(f"모델 {model_name} 세트 {round_folder} 답변 생성 중 오류: {e}")
                            import traceback
                            self.logger.error(traceback.format_exc())
                            continue
            
            self.logger.info("=== 9단계 완료 ===")
            
            # 문제 개수 확인
            total_questions = 0
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    questions = json.load(f)
                    total_questions = len(questions)
            
            return {
                'success': True,
                'total_questions': total_questions,
                'output_file': output_file
            }
            
        except Exception as e:
            self.logger.error(f"서술형 문제 변환 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': False, 'error': f'변환 오류: {str(e)}'}
        finally:
            self._remove_step_logging()

