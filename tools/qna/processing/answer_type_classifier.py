#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A Answer Type 분류기
- 선택형 문제를 right/wrong/abcd로 분류
- 10문제 단위로 API 호출 (기본값)
- answer_type 키를 추가하여 업데이트
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict, Any, Tuple
from tqdm import tqdm

# 프로젝트 루트 경로 찾기 (로깅과 import에 사용)
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # processing -> qna -> tools
project_root = os.path.dirname(tools_dir)  # tools -> project_root

# 로깅 설정
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'multiple_answer_classify.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# llm_query 모듈 import
sys.path.insert(0, tools_dir)
from core.llm_query import LLMQuery


class AnswerTypeClassifier:
    """Q&A Answer Type 분류기 (right/wrong/abcd)"""
    
    def __init__(self, config_path: str = None, onedrive_path: str = None):
        """Answer Type 분류기 초기화"""
        # LLMQuery 초기화
        self.llm_query = LLMQuery(config_path=config_path)
        
        # OneDrive 경로 설정
        if onedrive_path is None:
            onedrive_path = os.path.join(os.path.expanduser("~"), "Library/CloudStorage/OneDrive-개인/데이터L/selectstar")
        
        self.onedrive_path = onedrive_path
        
        # 시스템 프롬프트 생성
        self.system_prompt = self.create_system_prompt()
        
        # 결과 저장 디렉토리
        self.output_dir = os.path.join(self.onedrive_path, 'evaluation/eval_data/7_multiple_rw')
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"출력 디렉토리: {self.output_dir}")
    
    def create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        system_prompt = """다음 지시문을 사용해 문제 유형을 분류하시오.

목표
- 입력된 선택형 문제를 아래 3가지 중 하나로 분류하여 한 단어로만 출력
  - right: 옳은 것(맞는 것/적절한 것/참인 것)을 고르게 하거나, 단순히 정답을 묻는 일반형 문제
  - wrong: 옳지 않은 것(틀린 것/부적절한 것/거짓/해당하지 않는 것)을 고르게 하는 문제
  - abcd: 보기(ㄱ/ㄴ/ㄷ/ㄹ 등)에서 해당되는 것들을 모두 골라 조합(예: "ㄱ, ㄷ")을 선택하는 문제

입력
- 문제 레코드(예: question, options, title, chapter 등). answer, explanation, pick 필드는 분류에 사용하지 말 것.

판정 규칙(우선순위 적용)
1) abcd 판정(최우선)
   - 다음 중 하나라도 만족하면 abcd:
     - 본문에 <보기>나 항목 기호(ㄱ, ㄴ, ㄷ, ㄹ / I, II, III / A, B, C)가 나오고, 보기 조합을 고르는 형태
     - 선택지에 "ㄱ, ㄴ", "ㄴ, ㄷ, ㄹ" 등 항목 조합이 존재
     - 질문 문구에 "모두 고르면", "모두 고르시오", "해당하는 것을 모두" 등 '모두 선택'을 요구
   - 참고: '옳은 것만을 모두', '옳지 않은 것만을 모두'처럼 옳고 그름과 무관하게 '모두 고르기'면 abcd로 분류

2) wrong 판정(차선)
   - 질문이 "옳지 않은/틀린/부적절한/거짓/해당하지 않는/아닌/가장 옳지 않은/가장 덜 적절한/거리가 먼/반대되는 것" 등을 "고르라/선택하라/찾으라"고 요구하면 wrong
   - 핵심 부정 키워드 예:
     - 옳지 않은, 틀린, 잘못된, 부적절한, 부당한, 거짓, 오류, 해당하지 않는, 아닌 것, 옳지 못한, 가장 옳지 않은, 가장 덜 적절한, 거리가 먼

3) right 판정(기본값)
   - 위 두 조건에 해당하지 않으면 모두 right
   - 다음과 같은 경우는 right:
     - "옳은/맞는/바른/올바른/적절한/참인/가장 적절한 것은?" 등 긍정 선택
     - 계산/개수/값/정답 자체를 묻는 질문(예: "몇 개인가?", "값은?", "어느 것인가?")
     - "가장 옳은 것은?", "가장 타당한 것은?" 등 최상급 긍정 선택

판단 팁
- 부정어가 보기 설명에만 등장하고 선택 지시에는 등장하지 않으면(예: 보기 내부 문장에 '~이 아니다'), 선택 지시문을 기준으로 판정
- "옳지 않은 것을 모두"처럼 abcd 패턴과 부정이 동시에 있으면 abcd로 분류
- 숫자만 고르는 "몇 개인가?" 유형은 abcd가 아니면 right
- 빈칸에 알맞은 답을 고르는 문제는 right

출력 형식
- 다음 중 하나만 소문자로 출력: right, wrong, abcd
- 그 외 설명, 공백, 따옴표, 기호 출력 금지"""
        return system_prompt
    
    def load_questions(self, data_path: str) -> List[Dict[str, Any]]:
        """문제 데이터 로드"""
        logger.info(f"데이터 로딩 중: {data_path}")
        
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    
    def create_user_prompt(self, questions: List[Dict[str, Any]]) -> str:
        """사용자 프롬프트 생성"""
        user_prompt = ''
        
        for qna in questions:
            unique_id = f"{qna.get('file_id', '')}_{qna.get('tag', '')}"
            
            # answer, explanation, pick 필드를 제외한 문제 정보만 사용
            options_text = ', '.join(qna.get('options', [])) if isinstance(qna.get('options'), list) else qna.get('options', '')
            
            single_prompt = f"""문제 ID: {unique_id}
책 제목: {qna.get('title', '')}
챕터: {qna.get('chapter', '')}
질문: {qna.get('question', '')}
선택지: {options_text}
===================="""
            user_prompt += single_prompt
        
        return user_prompt
    
    def call_api(self, system_prompt: str, user_prompt: str, model: str = "google/gemini-2.5-flash") -> str:
        """API 호출 (llm_query 모듈 사용)"""
        try:
            response = self.llm_query.query_openrouter(system_prompt, user_prompt, model)
            return response
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            return None
    
    def parse_response(self, response: str, batch_size: int) -> List[str]:
        """API 응답 파싱 (각 문제당 하나의 답변 추출)"""
        if response is None:
            return None
        
        # 응답을 줄 단위로 분리
        lines = [line.strip().lower() for line in response.split('\n') if line.strip()]
        
        # 유효한 값만 추출
        answer_types = []
        for line in lines:
            # right, wrong, abcd 중 하나가 포함되어 있는지 확인
            if 'right' in line and 'wrong' not in line and 'abcd' not in line:
                answer_types.append('right')
            elif 'wrong' in line:
                answer_types.append('wrong')
            elif 'abcd' in line:
                answer_types.append('abcd')
            else:
                # 유효한 값을 찾지 못한 경우 None 추가
                answer_types.append(None)
        
        # 배치 크기만큼 채우기 (부족하면 None으로 채움)
        while len(answer_types) < batch_size:
            answer_types.append(None)
        
        return answer_types[:batch_size]
    
    def update_answer_type(self, questions: List[Dict[str, Any]], 
                          answer_types: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Q&A 데이터에 answer_type 분류 결과 업데이트"""
        updated_questions = []
        failed_questions = []
        
        for i, qna in enumerate(questions):
            if i < len(answer_types) and answer_types[i] is not None:
                qna['answer_type'] = answer_types[i]
                updated_questions.append(qna)
            else:
                qna['answer_type'] = ''  # 실패한 경우 빈 문자열
                failed_questions.append({
                    'file_id': qna.get('file_id', ''),
                    'tag': qna.get('tag', ''),
                    'question': qna.get('question', '')[:100],
                    'reason': '응답 파싱 실패' if i < len(answer_types) else '응답 개수 부족'
                })
                updated_questions.append(qna)
        
        return updated_questions, failed_questions
    
    def process_questions(self, questions: List[Dict[str, Any]], 
                         batch_size: int = 10, model: str = "x-ai/grok-4-fast") -> Tuple[List[Dict[str, Any]], List, List[Dict[str, Any]]]:
        """문제들을 배치 단위로 처리"""
        logger.info(f"처리 시작 - 총 {len(questions)}개 문제")
        
        all_updated_questions = []
        fail_response = []
        fail_question = []
        
        # 배치 단위로 처리
        for i in tqdm(range(0, len(questions), batch_size), desc="처리 중"):
            batch = questions[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"배치 {batch_num} 처리 중... ({len(batch)}개 문제)")
            
            # 사용자 프롬프트 생성
            user_prompt = self.create_user_prompt(batch)
            
            # API 호출
            try:
                response = self.call_api(self.system_prompt, user_prompt, model)
            except Exception as e:
                logger.error(f"배치 {batch_num} API 호출 실패: {e}")
                fail_response.append(None)
                # 실패한 경우 기본값으로 설정 (빈 문자열)
                for qna in batch:
                    qna['answer_type'] = ""
                all_updated_questions.extend(batch)
                continue
            
            if response is None:
                logger.error(f"배치 {batch_num} API 호출 실패")
                fail_response.append(None)
                # 실패한 경우 기본값으로 설정 (빈 문자열)
                for qna in batch:
                    qna['answer_type'] = ""
                all_updated_questions.extend(batch)
                continue
            
            # 응답 파싱
            try:
                answer_types = self.parse_response(response, len(batch))
            except Exception as e:
                logger.error(f"배치 {batch_num} 응답 파싱 실패: {e}")
                fail_response.append(response)
                # 파싱 실패한 경우 기본값으로 설정 (빈 문자열)
                for qna in batch:
                    qna['answer_type'] = ""
                all_updated_questions.extend(batch)
                continue
            
            if answer_types is None:
                logger.error(f"배치 {batch_num} 응답 파싱 실패")
                fail_response.append(response)
                # 파싱 실패한 경우 기본값으로 설정 (빈 문자열)
                for qna in batch:
                    qna['answer_type'] = ""
                all_updated_questions.extend(batch)
                continue
            
            # Q&A 데이터 업데이트
            try:
                updated_batch, fail_batch = self.update_answer_type(batch, answer_types)
                all_updated_questions.extend(updated_batch)
                fail_question.extend(fail_batch)
            except Exception as e:
                logger.error(f"배치 {batch_num} 업데이트 실패: {e}")
                fail_response.append(response)
            
            # API 호출 간격 조절
            time.sleep(1.2)
            
            # 중간 결과 저장 (매 10배치마다)
            if batch_num % 10 == 0:
                self._save_results(all_updated_questions, fail_response, fail_question, suffix='_intermediate')
        
        # 전체 문제수 검증
        if len(all_updated_questions) != len(questions):
            logger.warning(f"문제수 불일치: 원본 {len(questions)}개, 처리된 {len(all_updated_questions)}개")
        
        logger.info(f"처리 완료 - {len(all_updated_questions)}개 문제")
        return all_updated_questions, fail_response, fail_question
    
    def _save_results(self, questions: List[Dict[str, Any]], 
                     fail_response: List, fail_question: List[Dict[str, Any]], 
                     suffix: str = ''):
        """결과 저장"""
        filename = f"answer_type_classified{suffix}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        if fail_response or fail_question:
            with open(os.path.join(self.output_dir, f"answer_type_classified{suffix}_fail_response.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_response, f, ensure_ascii=False, indent=2)
            with open(os.path.join(self.output_dir, f"answer_type_classified{suffix}_fail_q.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_question, f, ensure_ascii=False, indent=2)
    
    def _cleanup_files(self, fail_response: List, fail_question: List[Dict[str, Any]]):
        """처리 완료 후 중간 파일 및 빈 fail 파일 정리"""
        # intermediate 파일 삭제
        intermediate_file = os.path.join(self.output_dir, "answer_type_classified_intermediate.json")
        if os.path.exists(intermediate_file):
            try:
                os.remove(intermediate_file)
                logger.info("중간 결과 파일 삭제 완료: answer_type_classified_intermediate.json")
            except Exception as e:
                logger.warning(f"중간 결과 파일 삭제 실패: {e}")
        
        # intermediate fail_response 파일 삭제
        intermediate_fail_response = os.path.join(self.output_dir, "answer_type_classified_intermediate_fail_response.json")
        if os.path.exists(intermediate_fail_response):
            try:
                os.remove(intermediate_fail_response)
                logger.info("중간 fail_response 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"중간 fail_response 파일 삭제 실패: {e}")
        
        # intermediate fail_q 파일 삭제
        intermediate_fail_q = os.path.join(self.output_dir, "answer_type_classified_intermediate_fail_q.json")
        if os.path.exists(intermediate_fail_q):
            try:
                os.remove(intermediate_fail_q)
                logger.info("중간 fail_q 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"중간 fail_q 파일 삭제 실패: {e}")
        
        # 최종 fail_response 파일이 비어있으면 삭제
        final_fail_response = os.path.join(self.output_dir, "answer_type_classified_fail_response.json")
        if not fail_response and os.path.exists(final_fail_response):
            try:
                os.remove(final_fail_response)
                logger.info("빈 fail_response 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"fail_response 파일 삭제 실패: {e}")
        
        # 최종 fail_q 파일이 비어있으면 삭제
        final_fail_q = os.path.join(self.output_dir, "answer_type_classified_fail_q.json")
        if not fail_question and os.path.exists(final_fail_q):
            try:
                os.remove(final_fail_q)
                logger.info("빈 fail_q 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"fail_q 파일 삭제 실패: {e}")
    
    def process_all_questions(self, data_path: str = None, questions: List[Dict[str, Any]] = None,
                              model: str = "x-ai/grok-4-fast", batch_size: int = 10) -> List[Dict[str, Any]]:
        """모든 문제 처리 (answer_type 분류)"""
        # 데이터 로드
        if questions is None:
            if data_path is None:
                raise ValueError("data_path 또는 questions를 제공해야 합니다.")
            questions = self.load_questions(data_path)
        
        logger.info(f"총 문제 수: {len(questions)}")
        
        # 문제 처리
        updated_questions, fail_response, fail_question = self.process_questions(questions, batch_size, model)
        
        # 최종 결과 저장
        self._save_results(updated_questions, fail_response, fail_question)
        
        # 통계 출력
        answer_type_counts = {}
        for item in updated_questions:
            answer_type = item.get('answer_type', 'unknown')
            answer_type_counts[answer_type] = answer_type_counts.get(answer_type, 0) + 1
        
        logger.info("분류 결과 통계:")
        for answer_type, count in sorted(answer_type_counts.items()):
            logger.info(f"  {answer_type}: {count}")
        
        # 처리 완료 후 파일 정리
        self._cleanup_files(fail_response, fail_question)
        
        return updated_questions


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Q&A Answer Type 분류기')
    parser.add_argument('--data_path', type=str, 
                       default=None,
                       help='데이터 경로 (파일)')
    parser.add_argument('--model', type=str, default='x-ai/grok-4-fast',
                       help='사용할 모델')
    parser.add_argument('--batch_size', type=int, default=10,
                       help='배치 크기 (기본값: 10)')
    parser.add_argument('--config', type=str, default=None,
                       help='설정 파일 경로')
    parser.add_argument('--onedrive_path', type=str, default=None,
                       help='OneDrive 경로')
    
    args = parser.parse_args()
    
    # 분류기 초기화
    classifier = AnswerTypeClassifier(
        config_path=args.config,
        onedrive_path=args.onedrive_path
    )
    
    # 처리 실행
    try:
        logger.info(f"모델: {args.model}, 배치 크기: {args.batch_size}")
        results = classifier.process_all_questions(
            data_path=args.data_path,
            model=str(args.model).strip(),
            batch_size=args.batch_size
        )
        logger.info("처리 완료!")
        
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()

