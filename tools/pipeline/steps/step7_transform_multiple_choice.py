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
import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from ..base import PipelineBase
from ..config import SFAICENTER_PATH

# AnswerTypeClassifier import
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, tools_dir)
try:
    from qna.processing.answer_type_classifier import AnswerTypeClassifier
except ImportError:
    AnswerTypeClassifier = None


class Step7TransformMultipleChoice(PipelineBase):
    """7단계: 객관식 문제 변형"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        
        if AnswerTypeClassifier is None:
            self.logger.warning("AnswerTypeClassifier를 import할 수 없습니다.")
        
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
                    results['transformations']['wrong_to_right'] = self._transform_wrong_to_right(
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
                    results['transformations']['right_to_wrong'] = self._transform_right_to_wrong(
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
                    results['transformations']['abcd'] = self._transform_abcd(
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
        """단계별 로그 파일 핸들러 설정"""
        log_dir = os.path.join(SFAICENTER_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'step7_{step_name}.log')
        
        try:
            # 파일 핸들러 생성 (append 모드, delay=True로 버퍼링 최적화)
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8', delay=False)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            # 로거에 핸들러 추가
            self.logger.addHandler(file_handler)
            
            # 핸들러 저장 (나중에 제거하기 위해)
            self._step_log_handlers[step_name] = file_handler
            
            self._safe_log_info(f"로그 파일 생성/추가: {log_file}")
        except Exception as e:
            self.logger.warning(f"로그 파일 핸들러 설정 실패: {e}")
    
    def _safe_log_info(self, message: str):
        """안전한 로깅 (타임아웃 예외 처리)"""
        try:
            self.logger.info(message)
        except (TimeoutError, OSError) as e:
            # 로깅 실패해도 프로그램은 계속 실행
            print(f"[로그 실패] {message} (에러: {e})")
    
    def _remove_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 제거"""
        if step_name in self._step_log_handlers:
            handler = self._step_log_handlers[step_name]
            try:
                self.logger.removeHandler(handler)
                handler.flush()  # 버퍼 비우기
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
            onedrive_path=self.onedrive_path
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
    
    def _sample_questions_by_answer_count(self, questions: List[Dict[str, Any]], 
                                         seed: int) -> Dict[int, List[Dict[str, Any]]]:
        """정답 개수별로 문제 샘플링 (옵션 개수에 따라 4지선다/5지선다로 분류 후 공평하게 배치)"""
        random.seed(seed)
        
        # 옵션 개수에 따라 분류
        options_4 = []
        options_5 = []
        option_others = []
        
        for q in questions:
            options_count = len(q.get('options', []))
            if options_count == 4:
                options_4.append(q)
            elif options_count == 5:
                options_5.append(q)
            else:
                option_others.append(q)
        
        self.logger.info(f"4지선다 문제 수: {len(options_4)}")
        self.logger.info(f"5지선다 문제 수: {len(options_5)}")
        if option_others:
            self.logger.warning(f"기타 옵션 개수 문제 수: {len(option_others)} (제외됨)")
        
        # 4지선다: 정답 개수 2, 3, 4로 3개 그룹으로 나눔
        ans_num_4 = {
            2: len(options_4) // 3,
            3: len(options_4) // 3,
            4: len(options_4) // 3
        }
        # 5지선다: 정답 개수 2, 3, 4, 5로 4개 그룹으로 나눔
        ans_num_5 = {
            2: len(options_5) // 4,
            3: len(options_5) // 4,
            4: len(options_5) // 4,
            5: len(options_5) // 4
        }
        
        # 나머지 문제를 공평하게 분배
        if len(options_4) % 3 != 0:
            remainder_4 = len(options_4) % 3
            for i in range(remainder_4):
                ans_num_4[3] += 1
        
        if len(options_5) % 4 != 0:
            remainder_5 = len(options_5) % 4
            for i in range(remainder_5):
                ans_num_5[4] += 1
        
        self.logger.info(f"4지선다 배치 계획: {ans_num_4}")
        self.logger.info(f"5지선다 배치 계획: {ans_num_5}")
        
        # 4지선다와 5지선다를 독립적으로 랜덤 샘플링
        remaining_4 = options_4.copy()
        remaining_5 = options_5.copy()
        sampling_result = {}
        
        for answer_count in range(2, 6):
            sampling_result[answer_count] = []
            
            # 4지선다에서 샘플링 (answer_count가 2, 3, 4일 때만)
            if answer_count in ans_num_4 and ans_num_4[answer_count] > 0:
                random.shuffle(remaining_4)
                sampled_4 = random.sample(remaining_4, ans_num_4[answer_count])
                sampling_result[answer_count].extend(sampled_4)
                remaining_4 = [x for x in remaining_4 if x not in sampled_4]
            
            # 5지선다에서 샘플링 (answer_count가 2, 3, 4, 5일 때)
            if answer_count in ans_num_5 and ans_num_5[answer_count] > 0:
                random.shuffle(remaining_5)
                sampled_5 = random.sample(remaining_5, ans_num_5[answer_count])
                sampling_result[answer_count].extend(sampled_5)
                remaining_5 = [x for x in remaining_5 if x not in sampled_5]
        
        # 검증: 모든 문제가 포함되었는지 확인
        total_sampled = sum(len(questions_list) for questions_list in sampling_result.values())
        total_valid = len(options_4) + len(options_5)
        
        if total_sampled != total_valid:
            self.logger.warning(
                f"샘플링 결과 검증 실패: 유효한 문제 수({total_valid}) != 샘플링된 문제 수({total_sampled}). "
                f"누락된 문제: {total_valid - total_sampled}개"
            )
            self.logger.warning(f"4지선다 남은 문제 수: {len(remaining_4)}")
            self.logger.warning(f"5지선다 남은 문제 수: {len(remaining_5)}")
        else:
            self.logger.info(f"샘플링 검증 성공: 모든 {total_valid}개 문제가 샘플링 결과에 포함되었습니다.")
        
        # 각 answer_count별 문제 수 로깅
        self.logger.info("각 answer_count별 문제 수:")
        for answer_count in range(2, 6):
            count = len(sampling_result.get(answer_count, []))
            if count > 0:
                self.logger.info(f"  answer_count={answer_count}: {count}개")
        
        return sampling_result
    
    def _transform_wrong_to_right(self, questions: List[Dict[str, Any]], 
                                   model: str, seed: int) -> Dict[str, Any]:
        """wrong -> right 변형"""
        sampling_result = self._sample_questions_by_answer_count(questions, seed)
        
        output_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw', 'pick_wrong')
        os.makedirs(output_dir, exist_ok=True)
        
        all_results = {}
        for answer_count, sampled_questions in sampling_result.items():
            if not sampled_questions:
                continue
            
            self.logger.info(f"  정답 {answer_count}개 그룹 처리 중... ({len(sampled_questions)}개 문제)")
            results = self._transform_batch(
                sampled_questions, answer_count, model, output_dir,
                self._create_wrong_to_right_prompt
            )
            all_results[answer_count] = results
        
        return all_results
    
    def _transform_right_to_wrong(self, questions: List[Dict[str, Any]], 
                                   model: str, seed: int) -> Dict[str, Any]:
        """right -> wrong 변형"""
        sampling_result = self._sample_questions_by_answer_count(questions, seed)
        
        output_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw', 'pick_right')
        os.makedirs(output_dir, exist_ok=True)
        
        all_results = {}
        for answer_count, sampled_questions in sampling_result.items():
            if not sampled_questions:
                continue
            
            self.logger.info(f"  정답 {answer_count}개 그룹 처리 중... ({len(sampled_questions)}개 문제)")
            results = self._transform_batch(
                sampled_questions, answer_count, model, output_dir,
                self._create_right_to_wrong_prompt
            )
            all_results[answer_count] = results
        
        return all_results
    
    def _get_processed_question_ids(self, result_file: str) -> set:
        """이미 처리된 question_id 목록을 반환"""
        processed_ids = set()
        if os.path.exists(result_file):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        for item in existing_data:
                            if isinstance(item, dict) and 'question_id' in item:
                                processed_ids.add(item['question_id'])
                    elif isinstance(existing_data, dict) and 'question_id' in existing_data:
                        processed_ids.add(existing_data['question_id'])
            except Exception as e:
                self.logger.warning(f"기존 결과 파일 읽기 실패 ({result_file}): {e}")
        return processed_ids
    
    def _transform_batch(self, questions: List[Dict[str, Any]], 
                        target_answer_count: int, model: str,
                        output_dir: str, prompt_creator: Callable) -> Dict[str, Any]:
        """배치 변형 처리 (공통 로직)"""
        # 이미 처리된 문제 확인
        result_file = os.path.join(output_dir, str(target_answer_count), 'result.json')
        processed_ids = self._get_processed_question_ids(result_file)
        
        if processed_ids:
            self.logger.info(f"    [{target_answer_count}개 그룹] 이미 처리된 문제 수: {len(processed_ids)}개")
        
        parsed_responses = []
        not_parsed_responses = []
        no_responses = []
        skipped = []
        
        for idx, p in enumerate(questions, 1):
            question_id = p.get('file_id', '') + '_' + p.get('tag', '')
            
            # 이미 처리된 문제인지 확인
            if question_id in processed_ids:
                skipped.append(question_id)
                if idx % 10 == 0 or idx == len(questions):
                    self._safe_log_info(f"    [{target_answer_count}개 그룹] {idx}/{len(questions)} - 문제 ID: {question_id} (이미 처리됨, 건너뜀)")
                continue
            
            # 로깅 빈도 줄이기: 10개마다 또는 마지막 문제일 때만 로그
            if idx % 10 == 0 or idx == len(questions):
                self._safe_log_info(f"    [{target_answer_count}개 그룹] {idx}/{len(questions)} - 문제 ID: {question_id}")
            
            # 프롬프트 생성
            system_prompt, user_prompt = prompt_creator(p, target_answer_count)
            
            # API 호출 및 저장
            result = self._call_api_and_save(
                system_prompt, user_prompt, model, p, question_id,
                output_dir, str(target_answer_count)
            )
            
            if result['success']:
                parsed_responses.append(result['response'])
                # 처리된 ID에 추가 (다음 반복에서 중복 체크용)
                processed_ids.add(question_id)
            elif result['parse_failed']:
                not_parsed_responses.append((p, result.get('raw_response')))
            else:
                no_responses.append(p)
        
        if skipped:
            self.logger.info(f"    [{target_answer_count}개 그룹] 건너뛴 문제 수: {len(skipped)}개")
        
        return {
            'total': len(questions),
            'success': len(parsed_responses),
            'parse_failed': len(not_parsed_responses),
            'api_failed': len(no_responses),
            'skipped': len(skipped)
        }
    
    def _call_api_and_save(self, system_prompt: str, user_prompt: str, 
                           model: str, question: Dict[str, Any],
                           question_id: str, output_dir: str,
                           subdir: str = '') -> Dict[str, Any]:
        """API 호출 및 결과 저장 (공통 로직)"""
        time.sleep(0.6)  # Rate limiting
        
        try:
            response = self.llm_query.query_openrouter(system_prompt, user_prompt, model_name=model)
            
            # 응답 파싱
            parsed_response = self._parse_response(response)
            
            if parsed_response is not None:
                # 성공: 결과 저장
                result_file = os.path.join(output_dir, subdir, 'result.json') if subdir else os.path.join(output_dir, 'result.json')
                self._save_result(parsed_response, result_file)
                
                return {
                    'success': True,
                    'response': parsed_response,
                    'raw_response': response
                }
            else:
                # 파싱 실패: 저장
                not_parsed_file = os.path.join(output_dir, subdir, 'not_parsed.json') if subdir else os.path.join(output_dir, 'not_parsed.json')
                self._save_failed_parsing(question, response, not_parsed_file)
                
                return {
                    'success': False,
                    'parse_failed': True,
                    'raw_response': response
                }
        
        except Exception as e:
            self.logger.error(f"    API 호출 실패: {str(e)}")
            return {
                'success': False,
                'parse_failed': False,
                'api_failed': True
            }
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """응답 파싱"""
        if response is None:
            return None
        
        try:
            parsed_response = self.llm_query.parse_api_response(response)
            
            if parsed_response is None:
                # JSON 객체 직접 파싱 시도
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx != -1 and end_idx > 0:
                    json_str = response[start_idx:end_idx]
                    parsed_response = json.loads(json_str)
            
            return parsed_response
        except Exception as e:
            self.logger.warning(f"    파싱 실패: {str(e)}")
            return None
    
    def _save_result(self, result: Dict[str, Any], file_path: str):
        """결과 저장 (중복 체크 포함)"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        existing_results = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_results = existing_data
                    else:
                        existing_results = [existing_data]
            except:
                existing_results = []
        
        # 중복 체크: question_id 기준으로 기존 항목 확인
        result_question_id = result.get('question_id')
        if result_question_id:
            # 기존에 같은 question_id가 있는지 확인
            existing_ids = {item.get('question_id') for item in existing_results if isinstance(item, dict) and 'question_id' in item}
            
            if result_question_id in existing_ids:
                # 중복 발견: 기존 항목을 새 항목으로 교체 (최신 결과 유지)
                existing_results = [item for item in existing_results 
                                  if not (isinstance(item, dict) and item.get('question_id') == result_question_id)]
                self.logger.warning(f"    중복된 question_id 발견: {result_question_id} (기존 항목 교체)")
        
        existing_results.append(result)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_results, f, ensure_ascii=False, indent=4)
    
    def _save_failed_parsing(self, question: Dict[str, Any], 
                            response: str, file_path: str):
        """파싱 실패 저장"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        existing_not_parsed = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_not_parsed = json.load(f)
            except:
                existing_not_parsed = []
        
        existing_not_parsed.append((question, response))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_not_parsed, f, ensure_ascii=False, indent=4)
    
    def _create_wrong_to_right_prompt(self, question: Dict[str, Any], 
                                     target_answer_count: int) -> Tuple[str, str]:
        """wrong -> right 변형 프롬프트 생성"""
        options_ct = len(question.get('options', []))
        question_id = question.get('file_id', '') + '_' + question.get('tag', '')
        
        system_prompt = f"""
당신은 25년 경력의 문제 출제 전문가입니다.

검증
- 목표 정답 수(= '옳은 것' 개수, {target_answer_count})가 2 이상 {options_ct} 이하인지 확인합니다. 범위를 벗어나면 오류를 보고합니다.
- 선택지 수({options_ct})와 순서는 반드시 유지합니다.

변형 규칙
- 문제 지문은 “옳은 것을 모두 고르시오”로 바꿉니다. 그 외 본문, 수식(LaTeX), 표, 선택지 문구(변형 대상 제외)는 원형을 최대한 보존합니다.
- 목표 오답 수 = '옳지 않은 것' 개수 = {options_ct - target_answer_count}.
  - 목표 오답 수 = 0: 원래 오답({question.get('answer', '')})을 최소 수정으로 ‘옳음’으로 뒤집습니다. 그 외 선택지는 변경하지 않습니다. 결과적으로 모든 선택지가 옳음입니다.
  - 목표 오답 수 = 1: 원래 오답을 그대로 유지합니다. 그 외 선택지는 변경하지 않습니다. 결과적으로 원래 오답 1개만 남습니다(단일선택형 재검증).
  - 목표 오답 수 ≥ 2: 원래 오답은 그대로 유지하고, 추가로 (목표 오답 수 - 1)개 만큼 원래 옳았던 선택지를 골라 최소 수정으로 ‘옳지 않음’으로 만듭니다.
- 최소 수정 원칙
  - 허용되는 변경 예: 수치/단위/부등호/최대↔최소/있다↔없다/반드시↔경우도 있다/조건의 범위·한정어 조정 등.
  - 제공된 해설의 논리 범위를 벗어나는 임의 창작 금지. 외부 사실 의존 금지.
  - 변형 대상이 아닌 선택지의 문구는 절대 수정하지 않습니다.
- 선택지 선정 가이드
  - 변형이 필요한 경우, 가장 적은 토큰 변경으로 참⇄거짓을 뒤집기 쉬운 선택지부터 우선 선택합니다.
  - 의미 일관성 유지: 변형으로 인해 다른 선택지와 모순되거나 문제 전체의 전제가 깨지지 않도록 합니다.

정답과 설명
- 정답(answer)은 변형 후 ‘옳은’ 선택지의 번호 목록입니다. 번호는 "①","②",... 형식의 문자열로, 오름차순으로 정렬합니다.
- explanation에는 모든 선택지를 순회하며 다음 형식으로 간단·명확히 기술합니다.
  - “① 옳다: 근거 …”
  - “③ 옳지 않다(원래 오답): 근거 …”
  - “⑤ 옳지 않다(변형): 변경 ‘높다→낮다’, 근거 …”
- 변형된 선택지는 반드시 어떤 단어/수치/기호를 어떻게 바꿨는지 구체적으로 한 토큰 수준으로 표기합니다.

출력 형식(JSON)
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", ...],  
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳다: … / ③ 옳지 않다(원래 오답): … / ⑤ 옳지 않다(변형): 변경 ‘…→…’, 근거 …"
}}

비고
- 목표 오답 수 계산식으로 일관되게 제어합니다.
  - 추가로 만들어야 할 오답 수 = {max(0, options_ct - target_answer_count - 1)}.
  - 단, {options_ct - target_answer_count} = 0이면 원래 오답을 ‘옳음’으로 뒤집고 추가 오답은 0입니다.
- 선택지 레이블(①, ②, …)과 원문 순서를 유지합니다.
- 최종적으로 옳음 개수 = {target_answer_count}, 오답(옳지 않음) 개수 = {options_ct - target_answer_count}임을 자기점검합니다.
"""
        
        user_prompt = f"""
========== 문제 ===========
문제번호: {question_id}
문제: {question.get('question', '')}
선택지: {question.get('options', [])}
답: {question.get('answer', '')}
해설: {question.get('explanation', '')}
"""
        
        return system_prompt, user_prompt
    
    def _create_right_to_wrong_prompt(self, question: Dict[str, Any], 
                                      target_answer_count: int) -> Tuple[str, str]:
        """right -> wrong 변형 프롬프트 생성"""
        options_ct = len(question.get('options', []))
        question_id = question.get('file_id', '') + '_' + question.get('tag', '')
        system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

검증
- 목표 정답 수(= '옳지 않은 것' 개수, {target_answer_count})가 2 이상 {options_ct} 이하인지 확인합니다. 범위를 벗어나면 오류를 보고합니다.
- 선택지 수({options_ct})와 순서는 반드시 유지합니다.

변형 규칙
- 문제 지문은 “옳지 않은 것을 모두 고르시오”로 바꿉니다. 그 외 본문, 수식(LaTeX), 표, 선택지 문구(변형 대상 제외)는 원형을 최대한 보존합니다.
- 목표 오답 수 = '옳은 것' 개수 = {options_ct - target_answer_count}.
  - 목표 오답 수 = 0: 원래 오답({question.get('answer', '')})을 최소 수정으로 ‘옳지 않음’으로 뒤집습니다. 그 외 선택지는 변경하지 않습니다. 결과적으로 모든 선택지가 옳지 않음입니다.
  - 목표 오답 수 = 1: 원래 오답을 그대로 유지합니다. 그 외 선택지는 변경하지 않습니다. 결과적으로 원래 오답인 '옳은 것' 1개만 남습니다(단일선택형 재검증).
  - 목표 오답 수 ≥ 2: 원래 오답을 그대로 유지하고, 추가로 (목표 오답 수 - 1)개 만큼 원래 옳지 않았던 선택지를 골라 최소 수정으로 ‘옳음’으로 만듭니다.
- 최소 수정 원칙
  - 허용되는 변경 예: 수치/단위/부등호/최대↔최소/있다↔없다/반드시↔경우도 있다/조건의 범위·한정어 조정 등.
  - 제공된 해설의 논리 범위를 벗어나는 임의 창작 금지. 외부 사실 의존 금지.
  - 변형 대상이 아닌 선택지의 문구는 절대 수정하지 않습니다.
- 선택지 선정 가이드
  - 변형이 필요한 경우, 가장 적은 토큰 변경으로 참⇄거짓을 뒤집기 쉬운 선택지부터 우선 선택합니다.
  - 의미 일관성 유지: 변형으로 인해 다른 선택지와 모순되거나 문제 전체의 전제가 깨지지 않도록 합니다.

정답과 설명
- 정답(answer)은 변형 후 ‘옳지 않은’ 선택지의 번호 목록입니다. 번호는 "①","②",... 형식의 문자열로, 오름차순으로 정렬합니다.
- explanation에는 모든 선택지를 순회하며 다음 형식으로 간단·명확히 기술합니다.
  - “① 옳다(원래 오답): 근거 …”
  - “③ 옳지 않다: 근거 …”
  - “⑤ 옳다(변형): 변경 ‘높다→낮다’, 근거 …”
- 변형된 선택지는 반드시 어떤 단어/수치/기호를 어떻게 바꿨는지 구체적으로 한 토큰 수준으로 표기합니다.

출력 형식(JSON)
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳지 않은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", ...],  
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳다(원래 오답): … / ③ 옳지 않다: … / ⑤ 옳다(변형): 변경 ‘…→…’, 근거 …"
}}

비고
- 목표 오답 수 계산식으로 일관되게 제어합니다.
  - 추가로 만들어야 할 오답 수 = {max(0, options_ct - target_answer_count - 1)}.
  - 단, {options_ct - target_answer_count} = 0이면 원래 오답을 ‘옳지 않음’으로 뒤집고 추가 오답은 0입니다.
- 선택지 레이블(①, ②, …)과 원문 순서를 유지합니다.
- 최종적으로 옳지 않음 개수 = {target_answer_count}, 오답(옳음) 개수 = {options_ct - target_answer_count}임을 자기점검합니다.
"""
        
        
        user_prompt = f"""
========== 문제 ===========
문제번호: {question_id}
문제: {question.get('question', '')}
선택지: {question.get('options', [])}
답: {question.get('answer', '')}
해설: {question.get('explanation', '')}
"""
        
        return system_prompt, user_prompt
    
    def _transform_abcd(self, questions: List[Dict[str, Any]], 
                        model: str) -> Dict[str, Any]:
        """abcd 변형 (단일정답형 -> 복수정답형)"""
        output_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw', 'pick_abcd')
        os.makedirs(output_dir, exist_ok=True)
        
        system_prompt = """당신은 25년 경력의 문제 출제 전문가입니다.

작업 목표
- '모두 고르시오' 유형에서 보기(ㄱ/ㄴ/ㄷ/ㄹ, 가/나/다/라, A/B/C/D 등)를 선택지로 전환하고, 기존 정답을 그대로 매핑하여 정답 번호를 산출합니다.
- 원문 문장, 수식(LaTeX), 표는 가능한 한 그대로 보존합니다.

변형 규칙
1) 보기 라벨 식별: 문제 본문에 제시된 보기(예: ㄱ, ㄴ, ㄷ, ㄹ 또는 가, 나, 다, 라 등)를 원문 순서대로 식별합니다. 보기의 내용(문장)은 question 필드에 그대로 남깁니다.
2) 선택지 구성: options에는 라벨만을 표시합니다. 예: ① ㄱ, ② ㄴ, ③ ㄷ, ④ ㄹ. 보기 수에 맞춰 ①부터 순차적으로 생성합니다(개수 가변).
3) 정답 매핑: 기존 정답의 라벨(예: ㄱ, ㄷ)을 해당 번호(예: ①, ③)로 변환하여 answer 배열에 문자열로 담습니다. 정답이 없으면 [], 전부 정답이면 모든 번호를 포함합니다.
4) 해설: 각 번호(①, ②, …)마다 "옳다/옳지 않다"를 명시하고, 제공된 해설을 근거로 1문장 이상 요약 근거를 제시합니다. 예: "① 옳다(원래 답 중 하나): … / ② 옳지 않다: …"
5) 보존 원칙: 원문의 기타 문장, 수식(LaTeX), 표, 줄바꿈을 가능한 한 그대로 유지합니다. 내용 변형, 임의 추론은 금지합니다.
6) 출력 형식: 오직 유효한 JSON만 출력합니다. 코드블록, 추가 설명, 주석 금지.

출력 형식
{
  "question_id": "문제번호",
  "question": "문제 원문(보기 문장 포함, LaTeX/표/줄바꿈 보존)",
  "options": ["① ㄱ", "② ㄴ", "③ ㄷ", "④ ㄹ"],
  "answer": ["①","③"],
  "explanation": "① 옳다(원래 답 중 하나): 근거 … / ② 옳지 않다: 근거 … / ③ 옳다(원래 답 중 하나): 근거 … / ④ 옳지 않다: 근거 …"
}

추가 권고
- 라벨이 가/나/다/라 등인 경우에도 options는 ① 가, ② 나처럼 그대로 표기합니다.
- 보기 수가 9개를 초과할 경우, ①~⑨ 이후에는 ⑩, ⑪… 또는 일반 숫자 10), 11)로 일관되게 표기하는 규칙을 사전에 정해 두세요.
- 원문에 보기가 명시적 라벨 없이 줄글로만 제시되면 변환을 중단하고 에러를 출력하도록 별도 규칙을 두는 것이 안전합니다."""
        
        # 이미 처리된 문제 확인
        result_file = os.path.join(output_dir, 'result.json')
        processed_ids = self._get_processed_question_ids(result_file)
        
        if processed_ids:
            self.logger.info(f"  이미 처리된 문제 수: {len(processed_ids)}개")
        
        parsed_responses = []
        not_parsed_responses = []
        no_responses = []
        skipped = []
        
        for idx, p in enumerate(questions, 1):
            question_id = p.get('file_id', '') + '_' + p.get('tag', '')
            
            # 이미 처리된 문제인지 확인
            if question_id in processed_ids:
                skipped.append(question_id)
                if idx % 10 == 0 or idx == len(questions):
                    self._safe_log_info(f"  {idx}/{len(questions)} - 문제 ID: {question_id} (이미 처리됨, 건너뜀)")
                continue
            
            # 로깅 빈도 줄이기: 10개마다 또는 마지막 문제일 때만 로그
            if idx % 10 == 0 or idx == len(questions):
                self._safe_log_info(f"  {idx}/{len(questions)} - 문제 ID: {question_id}")
            
            user_prompt = f"""
========== 다음 ===========
문제번호: {question_id}
문제: {p.get('question', '')}
선택지: {p.get('options', [])}
답: {p.get('answer', '')}
해설: {p.get('explanation', '')}
"""
            
            # API 호출 및 저장
            result = self._call_api_and_save(
                system_prompt, user_prompt, model, p, question_id,
                output_dir, ''
            )
            
            if result['success']:
                parsed_responses.append(result['response'])
                # 처리된 ID에 추가 (다음 반복에서 중복 체크용)
                processed_ids.add(question_id)
            elif result.get('parse_failed'):
                not_parsed_responses.append((p, result.get('raw_response')))
            else:
                no_responses.append(p)
        
        if skipped:
            self.logger.info(f"  건너뛴 문제 수: {len(skipped)}개")
        
        return {
            'total': len(questions),
            'success': len(parsed_responses),
            'parse_failed': len(not_parsed_responses),
            'api_failed': len(no_responses),
            'skipped': len(skipped)
        }