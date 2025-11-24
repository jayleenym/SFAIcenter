#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7단계: 객관식 문제 변형
- AnswerTypeClassifier로 문제를 right/wrong/abcd로 분류 (선택적)
- 이미 분류된 파일을 입력으로 받을 수 있음
- wrong -> right 변형 (옳지 않은 것 -> 옳은 것)
- right -> wrong 변형 (옳은 것 -> 옳지 않은 것)
- abcd 변형 (단일정답형 -> 복수정답형)
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from ..base import PipelineBase
from core.logger import setup_step_logger

# AnswerTypeClassifier 및 변형 모듈 import
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, tools_dir)

try:
    from qna.processing.answer_type_classifier import AnswerTypeClassifier
    from transformed.transform_multiple_choice import MultipleChoiceTransformer
except ImportError:
    AnswerTypeClassifier = None
    MultipleChoiceTransformer = None


class Step7TransformMultipleChoice(PipelineBase):
    """7단계: 객관식 문제 변형"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        
        if AnswerTypeClassifier is None:
            self.logger.warning("AnswerTypeClassifier를 import할 수 없습니다.")
        if MultipleChoiceTransformer is None:
            self.logger.warning("MultipleChoiceTransformer를 import할 수 없습니다.")
        
        # 단계별 로그 핸들러 저장용
        self._step_log_handlers = {}
    
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
        7단계: 객관식 문제 변형
        
        Args:
            classified_data_path: 이미 분류된 데이터 파일 경로 (run_classify가 False일 때 필수)
            input_data_path: 입력 데이터 파일 경로 (run_classify가 True일 때 사용)
            questions: 입력 문제 리스트 (run_classify가 True일 때 사용)
            run_classify: 분류 단계 실행 여부 (기본값: False, True일 때만 분류 수행)
            classify_model: 분류에 사용할 모델 (run_classify가 True일 때만 사용)
            classify_batch_size: 분류 배치 크기 (run_classify가 True일 때만 사용)
            transform_model: 변형에 사용할 모델
            transform_wrong_to_right: wrong -> right 변형 수행 여부
            transform_right_to_wrong: right -> wrong 변형 수행 여부
            transform_abcd: abcd 변형 수행 여부
            seed: 랜덤 시드
        
        Returns:
            실행 결과
        """
        self.logger.info("=== 7단계: 객관식 문제 변형 ===")
        
        if self.llm_query is None:
            self.logger.error("LLMQuery가 초기화되지 않았습니다.")
            return {'success': False, 'error': 'LLMQuery 초기화 실패'}
        
        if MultipleChoiceTransformer is None:
            self.logger.error("MultipleChoiceTransformer를 import할 수 없습니다.")
            return {'success': False, 'error': 'MultipleChoiceTransformer import 실패'}
        
        # 분류된 데이터 로드 또는 분류 수행
        if run_classify:
            # 분류 수행
            if AnswerTypeClassifier is None:
                self.logger.error("AnswerTypeClassifier를 import할 수 없습니다.")
                return {'success': False, 'error': 'AnswerTypeClassifier import 실패'}
            
            # 원본 문제 데이터 로드
            questions = self._load_questions(input_data_path, questions)
            if not questions:
                self.logger.error("로드된 문제가 없습니다.")
                return {'success': False, 'error': '문제 데이터 없음'}
            
            self.logger.info(f"총 {len(questions)}개 문제 로드")
            
            # 분류 수행
            classified_questions = self._classify_questions(questions, classify_model, classify_batch_size)
            if not classified_questions:
                return {'success': False, 'error': '분류 실패'}
        else:
            # 이미 분류된 파일 사용
            if not classified_data_path:
                # 기본 경로에서 answer_type_classified.json 읽기
                default_classified_path = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '7_multiple_rw', 'answer_type_classified.json'
                )
                if os.path.exists(default_classified_path):
                    classified_data_path = default_classified_path
                    self.logger.info(f"기본 경로에서 분류된 데이터 파일 사용: {classified_data_path}")
                else:
                    self.logger.error(f"기본 경로에 분류된 데이터 파일이 없습니다: {default_classified_path}")
                    return {'success': False, 'error': f'분류된 데이터 파일을 찾을 수 없습니다. 기본 경로: {default_classified_path}'}
            else:
                self.logger.info(f"지정된 분류된 데이터 파일 로드: {classified_data_path}")
            
            classified_questions = self._load_classified_questions(classified_data_path)
            if not classified_questions:
                return {'success': False, 'error': '분류된 데이터 로드 실패'}
        
        self.logger.info(f"총 {len(classified_questions)}개 분류된 문제 사용")
        
        # 변형기 초기화
        transformer = MultipleChoiceTransformer(
            llm_query=self.llm_query,
            onedrive_path=self.onedrive_path,
            logger=self.logger
        )
        
        # 타입별 변형
        results = {
            'classified': len(classified_questions),
            'transformations': {}
        }
        
        # wrong -> right 변형
        if transform_wrong_to_right:
            wrong_questions = [q for q in classified_questions if q.get('answer_type') == 'wrong']
            wrong_questions = self._remove_duplicates(wrong_questions, 'wrong')
            if wrong_questions:
                self.logger.info("2단계-1: wrong -> right 변형 시작")
                self._setup_step_logging('wrong_to_right')
                try:
                    results['transformations']['wrong_to_right'] = transformer.transform_wrong_to_right(
                        wrong_questions, transform_model, seed
                    )
                finally:
                    self._remove_step_logging('wrong_to_right')
            else:
                self.logger.info("wrong 문제가 없어 변형을 건너뜁니다.")
        
        # right -> wrong 변형
        if transform_right_to_wrong:
            right_questions = [q for q in classified_questions if q.get('answer_type') == 'right']
            right_questions = self._remove_duplicates(right_questions, 'right')
            if right_questions:
                self.logger.info("2단계-2: right -> wrong 변형 시작")
                self._setup_step_logging('right_to_wrong')
                try:
                    results['transformations']['right_to_wrong'] = transformer.transform_right_to_wrong(
                        right_questions, transform_model, seed
                    )
                finally:
                    self._remove_step_logging('right_to_wrong')
            else:
                self.logger.info("right 문제가 없어 변형을 건너뜁니다.")
        
        # abcd 변형
        if transform_abcd:
            abcd_questions = [q for q in classified_questions if q.get('answer_type') == 'abcd']
            abcd_questions = self._remove_duplicates(abcd_questions, 'abcd')
            if abcd_questions:
                self.logger.info("2단계-3: abcd 변형 시작")
                self._setup_step_logging('abcd')
                try:
                    results['transformations']['abcd'] = transformer.transform_abcd(
                        abcd_questions, transform_model
                    )
                finally:
                    self._remove_step_logging('abcd')
            else:
                self.logger.info("abcd 문제가 없어 변형을 건너뜁니다.")
        
        self.logger.info("=== 7단계 완료 ===")
        results['success'] = True
        return results
    
    def _setup_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 설정 (step7은 여러 개의 로그 핸들러 사용)"""
        try:
            step_logger, file_handler = setup_step_logger(
                step_name=step_name,
                step_number=7
            )
            self.logger.addHandler(file_handler)
            
            if not hasattr(self, '_step_log_handlers'):
                self._step_log_handlers = {}
            self._step_log_handlers[step_name] = file_handler
        except Exception as e:
            self.logger.warning(f"로그 파일 핸들러 설정 실패: {e}")
    
    def _safe_log_info(self, message: str):
        """안전한 로깅 (타임아웃 예외 처리)"""
        try:
            self.logger.info(message)
        except (TimeoutError, OSError) as e:
            print(f"[로그 실패] {message} (에러: {e})")
    
    def _remove_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 제거"""
        if step_name in self._step_log_handlers:
            handler = self._step_log_handlers[step_name]
            try:
                self.logger.removeHandler(handler)
                handler.flush()
                handler.close()
            except Exception as e:
                self.logger.warning(f"로그 핸들러 제거 중 오류: {e}")
            finally:
                del self._step_log_handlers[step_name]
                self._safe_log_info(f"로그 파일 핸들러 제거: step7_{step_name}.log")
    
    def _load_questions(self, input_data_path: str = None, 
                       questions: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """문제 데이터 로드"""
        if questions is not None:
            return questions
        
        if input_data_path is None:
            # 기본 경로에서 로드 시도
            default_path = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '4_multiple_exam'
            )
            # 1st~5th 디렉토리에서 모든 파일 로드
            questions = []
            for exam_dir in ['1st', '2nd', '3rd', '4th', '5th']:
                exam_path = os.path.join(default_path, exam_dir)
                if os.path.exists(exam_path):
                    for file in os.listdir(exam_path):
                        if file.endswith('.json'):
                            file_path = os.path.join(exam_path, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    questions.extend(json.load(f))
                            except Exception as e:
                                self.logger.warning(f"파일 로드 실패 ({file_path}): {e}")
            return questions
        else:
            # input_data_path에서 로드
            if not os.path.isabs(input_data_path):
                input_data_path = os.path.join(self.onedrive_path, input_data_path)
            
            with open(input_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _load_classified_questions(self, classified_data_path: str) -> List[Dict[str, Any]]:
        """분류된 문제 데이터 로드"""
        # 절대 경로가 아니면 onedrive_path 기준으로 처리
        if not os.path.isabs(classified_data_path):
            classified_data_path = os.path.join(self.onedrive_path, classified_data_path)
        
        if not os.path.exists(classified_data_path):
            self.logger.error(f"분류된 데이터 파일이 존재하지 않습니다: {classified_data_path}")
            return []
        
        try:
            with open(classified_data_path, 'r', encoding='utf-8') as f:
                classified_questions = json.load(f)
            
            # 분류 결과 통계
            answer_type_counts = {}
            for item in classified_questions:
                answer_type = item.get('answer_type', 'unknown')
                answer_type_counts[answer_type] = answer_type_counts.get(answer_type, 0) + 1
            
            self.logger.info("분류된 데이터 통계:")
            for answer_type, count in sorted(answer_type_counts.items()):
                self.logger.info(f"  {answer_type}: {count}")
            
            return classified_questions
        except Exception as e:
            self.logger.error(f"분류된 데이터 파일 로드 실패 ({classified_data_path}): {e}")
            return []
    
    def _classify_questions(self, questions: List[Dict[str, Any]], 
                          model: str, batch_size: int) -> List[Dict[str, Any]]:
        """문제 분류"""
        self.logger.info("1단계: 문제 분류 중...")
        classifier = AnswerTypeClassifier(
            config_path=os.path.join(self.project_root_path, 'llm_config.ini') if self.llm_query else None,
            onedrive_path=self.onedrive_path,
            logger=self.logger  # step 로거 전달
        )
        
        classified_questions = classifier.process_all_questions(
            questions=questions,
            model=model,
            batch_size=batch_size
        )
        
        # 분류 결과 통계
        answer_type_counts = {}
        for item in classified_questions:
            answer_type = item.get('answer_type', 'unknown')
            answer_type_counts[answer_type] = answer_type_counts.get(answer_type, 0) + 1
        
        self.logger.info("분류 결과:")
        for answer_type, count in sorted(answer_type_counts.items()):
            self.logger.info(f"  {answer_type}: {count}")
        
        # 분류 결과 저장
        output_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw')
        os.makedirs(output_dir, exist_ok=True)
        
        classified_file = os.path.join(output_dir, 'answer_type_classified.json')
        self.json_handler.save(classified_questions, classified_file)
        self.logger.info(f"분류 결과 저장: {classified_file}")
        
        return classified_questions
    
    def _remove_duplicates(self, questions: List[Dict[str, Any]], 
                          question_type: str) -> List[Dict[str, Any]]:
        """입력 데이터에서 중복 제거 (question_id 기준: file_id + tag 조합)"""
        if not questions:
            return questions
        
        seen_ids = set()
        unique_questions = []
        duplicate_count = 0
        
        for q in questions:
            question_id = q.get('file_id', '') + '_' + q.get('tag', '')
            if question_id in seen_ids:
                duplicate_count += 1
                self.logger.warning(f"중복된 question_id 발견 (입력 데이터, {question_type}): {question_id}")
            else:
                seen_ids.add(question_id)
                unique_questions.append(q)
        
        if duplicate_count > 0:
            self.logger.warning(f"입력 데이터에서 {duplicate_count}개의 중복 항목 제거됨 ({question_type})")
            self.logger.info(f"중복 제거 후 {question_type} 문제 수: {len(unique_questions)} (원본: {len(questions)})")
        
        return unique_questions
