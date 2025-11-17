#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7단계: 객관식 문제 변형
- AnswerTypeClassifier로 문제를 right/wrong/abcd로 분류
- wrong -> right 변형 (옳지 않은 것 -> 옳은 것)
- right -> wrong 변형 (옳은 것 -> 옳지 않은 것)
- abcd 변형 (단일정답형 -> 복수정답형)
"""

import os
import sys
import json
import time
import random
from typing import List, Dict, Any, Optional, Tuple, Callable
from ..base import PipelineBase

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
    
    def execute(self, input_data_path: str = None, questions: List[Dict[str, Any]] = None,
                classify_model: str = 'openai/gpt-5', classify_batch_size: int = 10,
                transform_model: str = 'openai/o3', 
                transform_wrong_to_right: bool = True,
                transform_right_to_wrong: bool = True,
                transform_abcd: bool = True,
                seed: int = 42) -> Dict[str, Any]:
        """
        7단계: 객관식 문제 변형
        
        Args:
            input_data_path: 입력 데이터 파일 경로 (None이면 questions 사용)
            questions: 입력 문제 리스트 (None이면 input_data_path에서 로드)
            classify_model: 분류에 사용할 모델
            classify_batch_size: 분류 배치 크기
            transform_model: 변형에 사용할 모델
            transform_wrong_to_right: wrong -> right 변형 수행 여부
            transform_right_to_wrong: right -> wrong 변형 수행 여부
            transform_abcd: abcd 변형 수행 여부
            seed: 랜덤 시드
        
        Returns:
            실행 결과
        """
        self.logger.info("=== 7단계: 객관식 문제 변형 ===")
        
        if AnswerTypeClassifier is None:
            self.logger.error("AnswerTypeClassifier를 import할 수 없습니다.")
            return {'success': False, 'error': 'AnswerTypeClassifier import 실패'}
        
        if self.llm_query is None:
            self.logger.error("LLMQuery가 초기화되지 않았습니다.")
            return {'success': False, 'error': 'LLMQuery 초기화 실패'}
        
        # 데이터 로드
        questions = self._load_questions(input_data_path, questions)
        if not questions:
            self.logger.error("로드된 문제가 없습니다.")
            return {'success': False, 'error': '문제 데이터 없음'}
        
        self.logger.info(f"총 {len(questions)}개 문제 로드")
        
        # 1단계: AnswerTypeClassifier로 분류
        classified_questions = self._classify_questions(questions, classify_model, classify_batch_size)
        if not classified_questions:
            return {'success': False, 'error': '분류 실패'}
        
        # 2단계: 타입별 변형
        results = {
            'classified': len(classified_questions),
            'transformations': {}
        }
        
        # wrong -> right 변형
        if transform_wrong_to_right:
            wrong_questions = [q for q in classified_questions if q.get('answer_type') == 'wrong']
            if wrong_questions:
                self.logger.info("2단계-1: wrong -> right 변형 시작")
                results['transformations']['wrong_to_right'] = self._transform_wrong_to_right(
                    wrong_questions, transform_model, seed
                )
            else:
                self.logger.info("wrong 문제가 없어 변형을 건너뜁니다.")
        
        # right -> wrong 변형
        if transform_right_to_wrong:
            right_questions = [q for q in classified_questions if q.get('answer_type') == 'right']
            if right_questions:
                self.logger.info("2단계-2: right -> wrong 변형 시작")
                results['transformations']['right_to_wrong'] = self._transform_right_to_wrong(
                    right_questions, transform_model, seed
                )
            else:
                self.logger.info("right 문제가 없어 변형을 건너뜁니다.")
        
        # abcd 변형
        if transform_abcd:
            abcd_questions = [q for q in classified_questions if q.get('answer_type') == 'abcd']
            if abcd_questions:
                self.logger.info("2단계-3: abcd 변형 시작")
                results['transformations']['abcd'] = self._transform_abcd(
                    abcd_questions, transform_model
                )
            else:
                self.logger.info("abcd 문제가 없어 변형을 건너뜁니다.")
        
        self.logger.info("=== 7단계 완료 ===")
        results['success'] = True
        return results
    
    def _load_questions(self, input_data_path: str = None, 
                       questions: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """문제 데이터 로드"""
        if questions is not None:
            return questions
        
        if input_data_path is None:
            # 기본 경로에서 로드 시도
            default_path = os.path.join(
                self.onedrive_path,
                'evaluation/eval_data/4_multiple_exam'
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
        output_dir = os.path.join(self.onedrive_path, 'evaluation/eval_data/7_multiple_rw')
        os.makedirs(output_dir, exist_ok=True)
        
        classified_file = os.path.join(output_dir, 'answer_type_classified.json')
        self.json_handler.save(classified_questions, classified_file)
        self.logger.info(f"분류 결과 저장: {classified_file}")
        
        return classified_questions
    
    def _sample_questions_by_answer_count(self, questions: List[Dict[str, Any]], 
                                         seed: int) -> Dict[int, List[Dict[str, Any]]]:
        """정답 개수별로 문제 샘플링"""
        random.seed(seed)
        
        # 4지선다/5지선다 분류
        options_4 = [q for q in questions if len(q.get('options', [])) == 4]
        options_5 = [q for q in questions if len(q.get('options', [])) == 5]
        
        # 정답 개수별 샘플링 수 계산
        ans_num_4 = {
            2: len(options_4) // 3,
            3: len(options_4) // 3,
            4: len(options_4) // 3
        }
        ans_num_5 = {
            2: len(options_5) // 4,
            3: len(options_5) // 4,
            4: len(options_5) // 4,
            5: len(options_5) // 4
        }
        
        # 나머지 처리
        if len(options_4) % 3 != 0:
            for i in range(len(options_4) % 3):
                ans_num_4[3] += 1
        if len(options_5) % 4 != 0:
            ans_num_5[4] += 1
        
        # 샘플링
        remaining_4 = options_4.copy()
        remaining_5 = options_5.copy()
        sampling_result = {}
        
        for i in range(2, 6):
            result = []
            
            if i in ans_num_4:
                random.shuffle(remaining_4)
                sampled_4 = random.sample(remaining_4, ans_num_4[i])
                result.extend(sampled_4)
                remaining_4 = [x for x in remaining_4 if x not in sampled_4]
            
            if i in ans_num_5:
                random.shuffle(remaining_5)
                sampled_5 = random.sample(remaining_5, ans_num_5[i])
                result.extend(sampled_5)
                remaining_5 = [x for x in remaining_5 if x not in sampled_5]
            
            sampling_result[i] = result
        
        return sampling_result
    
    def _transform_wrong_to_right(self, questions: List[Dict[str, Any]], 
                                   model: str, seed: int) -> Dict[str, Any]:
        """wrong -> right 변형"""
        sampling_result = self._sample_questions_by_answer_count(questions, seed)
        
        output_dir = os.path.join(self.onedrive_path, 'evaluation/eval_data/7_multiple_rw/pick_wrong')
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
        
        output_dir = os.path.join(self.onedrive_path, 'evaluation/eval_data/7_multiple_rw/pick_right')
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
    
    def _transform_batch(self, questions: List[Dict[str, Any]], 
                        target_answer_count: int, model: str,
                        output_dir: str, prompt_creator: Callable) -> Dict[str, Any]:
        """배치 변형 처리 (공통 로직)"""
        parsed_responses = []
        not_parsed_responses = []
        no_responses = []
        
        for idx, p in enumerate(questions, 1):
            question_id = p.get('file_id', '') + '_' + p.get('tag', '')
            self.logger.info(f"    [{target_answer_count}개 그룹] {idx}/{len(questions)} - 문제 ID: {question_id}")
            
            # 프롬프트 생성
            system_prompt, user_prompt = prompt_creator(p, target_answer_count)
            
            # API 호출 및 저장
            result = self._call_api_and_save(
                system_prompt, user_prompt, model, p, question_id,
                output_dir, str(target_answer_count)
            )
            
            if result['success']:
                parsed_responses.append(result['response'])
            elif result['parse_failed']:
                not_parsed_responses.append((p, result.get('raw_response')))
            else:
                no_responses.append(p)
        
        return {
            'total': len(questions),
            'success': len(parsed_responses),
            'parse_failed': len(not_parsed_responses),
            'api_failed': len(no_responses)
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
        """결과 저장"""
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
        
        if options_ct - target_answer_count == 1:
            system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

변형 규칙
1) 주어진 답(원래의 '옳지 않은' 선택지)은 그대로 유지합니다.
3) 문제 지문을 '옳은 것을 모두 고르시오'로 명확히 바꿉니다. 그 외 문장과 LaTeX 수식이나 테이블 표현은 원형을 최대한 보존합니다.
4) 새로운 정답은 변형 후 '옳은' 선택지 전부입니다(총 선택지 수가 {options_ct}개라면 {target_answer_count}개).

출력 형식
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"],
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳다: 근거 ... / ③ 옳지 않다(원래 오답): 근거 ... / ⑤ 옳지 않다(변형): 변경 단어 '높다→낮다', 근거 ..."
}}"""
        elif options_ct - target_answer_count == 0:
            system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

변형 규칙
1) 주어진 답(원래의 '옳지 않은' 선택지)을 단어 1~2개 수준의 최소 변경으로 '옳은' 선택지로 만듭니다. (ex. 높다 -> 낮다, 한다 -> 하지 않는다)
2) 문제 지문을 '옳은 것을 모두 고르시오'로 명확히 바꿉니다. 그 외 문장과 LaTeX 수식이나 테이블 표현 원형을 최대한 보존합니다.
3) 새로운 정답은 변형 후 '옳은' 선택지 전부입니다(총 선택지 수가 {options_ct}개라면 {target_answer_count}개).
4) 해설에는 각 선택지의 옳고 그름과 간단한 근거를 명시하세요. 특히 새로 만든 정답 1개의 변경 포인트를 밝혀주세요.

출력 형식
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"],
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳다: 근거 ... / ③ 옳지 않다(원래 오답): 근거 ... / ⑤ 옳지 않다(변형): 변경 단어 '높다→낮다', 근거 ..."
}}

비고
- 원문 선택지 수가 5개가 아닐 경우에도 동일 원칙을 적용합니다(총 {options_ct-target_answer_count-1}개 추가 오답, 나머지 전부 정답).
- 사실과 상충하는 임의 창작을 피하고, 제공된 해설의 논리 범위 내에서만 최소 변경을 수행하세요."""
        else:
            system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

변형 규칙
1) 주어진 답(원래의 '옳지 않은' 선택지)은 그대로 유지합니다.
2) 나머지 선택지 중에서 정확히 {options_ct-target_answer_count-1}개를 골라, 단어 1~2개 수준의 최소 변경으로 '옳지 않은' 선택지로 만듭니다. (ex. 높다 -> 낮다, 한다 -> 하지 않는다)
3) 문제 지문을 '옳은 것을 모두 고르시오'로 명확히 바꿉니다. 그 외 문장과 LaTeX 수식이나 테이블 표현 원형을 최대한 보존합니다.
4) 새로운 정답은 변형 후 '옳은' 선택지 전부입니다(총 선택지 수가 {options_ct}개라면 {target_answer_count}개).
5) 해설에는 각 선택지의 옳고 그름과 간단한 근거를 명시하세요. 특히 새로 만든 오답 1개의 변경 포인트를 밝혀주세요.

출력 형식
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"],
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳다: 근거 ... / ③ 옳지 않다(원래 오답): 근거 ... / ⑤ 옳지 않다(변형): 변경 단어 '높다→낮다', 근거 ..."
}}

비고
- 원문 선택지 수가 5개가 아닐 경우에도 동일 원칙을 적용합니다(총 {options_ct-target_answer_count-1}개 추가 오답, 나머지 전부 정답).
- 사실과 상충하는 임의 창작을 피하고, 제공된 해설의 논리 범위 내에서만 최소 변경을 수행하세요."""
        
        user_prompt = f"""
========== 다음 ===========
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
        
        if options_ct - target_answer_count == 1:
            system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

변형 규칙
1) 주어진 답(원래의 '옳은' 선택지)은 그대로 유지합니다.
3) 문제 지문을 '옳지 않은 것을 모두 고르시오'로 명확히 바꿉니다. 그 외 문장과 LaTeX 수식이나 테이블 표현은 원형을 최대한 보존합니다.
4) 새로운 정답은 변형 후 '옳지 않은' 선택지 전부입니다(총 선택지 수가 {options_ct}개라면 {target_answer_count}개).

출력 형식
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳지 않은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"],
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳지 않다: 근거 ... / ③ 옳다(원래 답): 근거 ... / ⑤ 옳지 않다: 근거 ..."
}}"""
        elif options_ct - target_answer_count == 0:
            system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

변형 규칙
1) 주어진 답(원래의 '옳은' 선택지)을 단어 1~2개 수준의 최소 변경으로 '옳지 않은' 선택지로 만듭니다. (ex. 높다 -> 낮다, 한다 -> 하지 않는다)
2) 문제 지문을 '옳지 않은 것을 모두 고르시오'로 명확히 바꿉니다. 그 외 문장과 LaTeX 수식이나 테이블 표현 원형을 최대한 보존합니다.
3) 새로운 정답은 변형 후 '옳지 않은' 선택지 전부입니다(총 선택지 수가 {options_ct}개라면 {target_answer_count}개).
4) 해설에는 각 선택지의 옳고 그름과 간단한 근거를 명시하세요. 특히 새로 만든 정답 1개의 변경 포인트를 밝혀주세요.

출력 형식
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳지 않은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"],
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳지 않다: 근거 ... / ③ 옳지 않다: 근거 ... / ⑤ 옳지 않다(원래 답): 변경 단어 '높다→낮다', 근거 ..."
}}

비고
- 원문 선택지 수가 5개가 아닐 경우에도 동일 원칙을 적용합니다(총 {options_ct-target_answer_count-1}개 추가 오답, 나머지 전부 정답).
- 사실과 상충하는 임의 창작을 피하고, 제공된 해설의 논리 범위 내에서만 최소 변경을 수행하세요."""
        else:
            system_prompt = f"""당신은 25년 경력의 문제 출제 전문가입니다.

변형 규칙
1) 주어진 답(원래의 '옳은' 선택지)은 그대로 유지합니다.
2) 나머지 선택지 중에서 정확히 {options_ct-target_answer_count-1}개를 골라, 단어 1~2개 수준의 최소 변경으로 '옳지 않은' 선택지로 만듭니다. (ex. 높다 -> 낮다, 한다 -> 하지 않는다)
3) 문제 지문을 '옳지 않은 것을 모두 고르시오'로 명확히 바꿉니다. 그 외 문장과 LaTeX 수식이나 테이블 표현 원형을 최대한 보존합니다.
4) 새로운 정답은 변형 후 '옳지 않은' 선택지 전부입니다(총 선택지 수가 {options_ct}개라면 {target_answer_count}개).
5) 해설에는 각 선택지의 옳고 그름과 간단한 근거를 명시하세요. 특히 새로 만든 오답 1개의 변경 포인트를 밝혀주세요.

출력 형식
{{
  "question_id": "문제번호",
  "question": "변형된 문제(옳지 않은 것을 모두 고르시오)",
  "options": ["① 선택지1", "② 선택지2", "③ 선택지3", "④ 선택지4", "⑤ 선택지5"],
  "answer": ["정답번호1", "정답번호2", ...], 
  "explanation": "① 옳지 않다: 근거 ... / ③ 옳다(원래 답): 근거 ... / ⑤ 옳지 않다(변형): 변경 단어 '높다→낮다', 근거 ..."
}}

비고
- 원문 선택지 수가 5개가 아닐 경우에도 동일 원칙을 적용합니다(총 {options_ct-target_answer_count-1}개 추가 오답, 나머지 전부 정답).
- 사실과 상충하는 임의 창작을 피하고, 제공된 해설의 논리 범위 내에서만 최소 변경을 수행하세요."""
        
        user_prompt = f"""
========== 다음 ===========
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
        output_dir = os.path.join(self.onedrive_path, 'evaluation/eval_data/7_multiple_rw/pick_abcd')
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
        
        parsed_responses = []
        not_parsed_responses = []
        no_responses = []
        
        for idx, p in enumerate(questions, 1):
            question_id = p.get('file_id', '') + '_' + p.get('tag', '')
            self.logger.info(f"  {idx}/{len(questions)} - 문제 ID: {question_id}")
            
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
            elif result.get('parse_failed'):
                not_parsed_responses.append((p, result.get('raw_response')))
            else:
                no_responses.append(p)
        
        return {
            'total': len(questions),
            'success': len(parsed_responses),
            'parse_failed': len(not_parsed_responses),
            'api_failed': len(no_responses)
        }
