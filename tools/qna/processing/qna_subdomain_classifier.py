#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 도메인/서브도메인 분류기
- 모든 도메인을 포함한 단일 프롬프트로 도메인+서브도메인을 한 번에 분류
- 10문제 단위로 API 호출 (기본값)
- JSON 응답 파싱하여 domain, subdomain, is_calculation 업데이트
- --mode 옵션으로 multiple/short/essay 구분
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
log_file = os.path.join(log_dir, 'qna_subdomain_classifier.log')

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

class QnASubdomainClassifier:
    def __init__(self, config_path: str = None, mode: str = 'multiple', onedrive_path: str = None):
        """Q&A 도메인/서브도메인 분류기 초기화"""
        # LLMQuery 초기화
        self.llm_query = LLMQuery(config_path=config_path)
        
        # mode 검증
        valid_modes = ['multiple', 'short', 'essay', 'multiple-fail', 'multiple-re', 'short-fail']
        if mode not in valid_modes:
            logger.warning(f"mode '{mode}'가 표준 모드가 아닙니다. 계속 진행합니다.")
        
        self.mode = mode
        
        # OneDrive 경로 설정
        if onedrive_path is None:
            onedrive_path = os.path.join(os.path.expanduser("~"), "Library/CloudStorage/OneDrive-개인/데이터L/selectstar")
        
        self.onedrive_path = onedrive_path
        
        # 도메인-서브도메인 매핑 로드
        self.domain_subdomain = self.load_domain_subdomain()
        
        # 시스템 프롬프트 생성 (모든 도메인 포함)
        self.system_prompt = self.create_system_prompt()
        
        # 결과 저장 디렉토리
        self.output_dir = os.path.join(self.onedrive_path, 'evaluation/eval_data/2_subdomain')
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"출력 디렉토리: {self.output_dir}")
        
    def load_domain_subdomain(self) -> Dict[str, List[str]]:
        """도메인-서브도메인 매핑 로드"""
        domain_subdomain_path = os.path.join(self.onedrive_path, 'evaluation/eval_data/domain_subdomain.json')
        
        if not os.path.exists(domain_subdomain_path):
            # 프로젝트 내 경로도 시도 (전역 project_root 사용)
            eval_dir = os.path.join(project_root, 'evaluation_yejin')
            if not os.path.exists(eval_dir):
                eval_dir = os.path.join(project_root, 'evaluation')
            domain_subdomain_path = os.path.join(eval_dir, 'eval_data', 'domain_subdomain.json')
        
        if not os.path.exists(domain_subdomain_path):
            raise FileNotFoundError(f"도메인-서브도메인 매핑 파일을 찾을 수 없습니다: {domain_subdomain_path}")
        
        with open(domain_subdomain_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_multiple_choice_data(self, data_path: str) -> List[Dict[str, Any]]:
        """문제 데이터 로드"""
        logger.info(f"데이터 로딩 중: {data_path}")
        
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    
    def create_system_prompt(self) -> str:
        """모든 도메인을 포함한 시스템 프롬프트 생성"""
        prompt_domain = ''
        
        for domain in self.domain_subdomain.keys():
            subdomain_list = self.domain_subdomain[domain]
            prompt_domain += f'{domain}\n'
            for i, subdomain_item in enumerate(subdomain_list):
                subdomain_name = subdomain_item.split('(')[0].strip()
                subdomain_ex = subdomain_item.split('(')[1].split(')')[0].strip()
                prompt_domain += f'{i+1}. {subdomain_name}\n   - {subdomain_ex}\n'
        
        system_prompt = f"""
당신은 금융 시험 문제를 세부 주제별로 정확히 분류하는 전문가입니다.  
당신의 임무는 이 문제를 아래의 세부 분류체계 중 하나로 정확히 분류하고, 계산이 필요한 문제인지 판단하는 것입니다.

### 세부 분류체계
{prompt_domain}

분류 기준:
- 문제의 핵심 개념, 등장 용어, 계산 대상, 제시된 사례를 기준으로 판단합니다.
- 특정 학문적 이론이나 모형이 등장한다면 그 이론이 속한 학문 영역으로 분류합니다.
- 판단이 애매할 경우, **'가장 관련성이 높은 영역 하나만** 선택해야 합니다.

출력은 아래 JSON 형태로 작성합니다. 각 문제마다 하나의 객체를 생성하세요.
문제 ID는 "file_id_tag" 형태로 제공됩니다.

[
{{
  "qna_id": "file_id_tag",
  "domain": "도메인명",
  "subdomain": "서브도메인명",
  "reason": "간단한 이유 (문제의 핵심키워드와 근거 중심으로)",
  "is_calculation": "계산 여부 (True/False)"
}},
{{
  "qna_id": "file_id_tag",
  "domain": "도메인명",
  "subdomain": "서브도메인명", 
  "reason": "간단한 이유 (문제의 핵심키워드와 근거 중심으로)",
  "is_calculation": "계산 여부 (True/False)"
}}
]
"""
        return system_prompt
    
    def create_user_prompt(self, questions: List[Dict[str, Any]]) -> str:
        """사용자 프롬프트 생성"""
        user_prompt = ''
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['tag']}"
            
            # 옵션이 있는 경우 (multiple choice)
            if qna.get('options'):
                options_text = '\n'.join(qna['options']) if isinstance(qna['options'], list) else qna['options']
                single_prompt = f"""
문제 ID: {unique_id}
책 제목: {qna['title']}
챕터: {qna['chapter']}
질문: {qna['question']}
선지: {options_text}
답변: {qna['answer']}
해설: {qna['explanation']}
===================="""
            else:
                # 옵션이 없는 경우 (short answer, essay)
                single_prompt = f"""
문제 ID: {unique_id}
책 제목: {qna['title']}
챕터: {qna['chapter']}
질문: {qna['question']}
답변: {qna['answer']}
해설: {qna['explanation']}
===================="""
            user_prompt += single_prompt
        
        return user_prompt
    
    def call_api(self, system_prompt: str, user_prompt: str, model: str = "x-ai/grok-4-fast") -> str:
        """API 호출 (llm_query 모듈 사용)"""
        try:
            response = self.llm_query.query_openrouter(system_prompt, user_prompt, model)
            return response
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            return None
    
    def parse_api_response(self, response: str) -> List[Dict[str, Any]]:
        """API 응답 파싱 (llm_query 모듈 사용)"""
        parsed_data = self.llm_query.parse_api_response(response)
        
        if parsed_data is None:
            logger.error("JSON 배열을 찾을 수 없거나 파싱에 실패했습니다.")
            logger.error(f"응답 내용: {response[:500]}...")
            return None
        
        return parsed_data
    
    def update_qna_subdomain(self, questions: List[Dict[str, Any]], 
                           classifications: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Q&A 데이터에 도메인/서브도메인 분류 결과 업데이트"""
        # file_id + tag 조합을 키로 하는 딕셔너리 생성
        classification_dict = {item['qna_id']: item for item in classifications}
        
        updated_questions = []
        failed_questions = []  # 분류 실패한 문제들 수집
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['tag']}"
            if unique_id in classification_dict:
                qna['domain'] = classification_dict[unique_id]['domain']
                qna['subdomain'] = classification_dict[unique_id]['subdomain']
                qna['classification_reason'] = classification_dict[unique_id]['reason']
                qna['is_calculation'] = classification_dict[unique_id]['is_calculation']
            else:
                logger.warning(f"분류 결과를 찾을 수 없음: {unique_id}")
                qna['domain'] = "분류실패"
                qna['subdomain'] = "분류실패"
                qna['classification_reason'] = "API 응답에서 해당 문제를 찾을 수 없음"
                qna['is_calculation'] = "분류실패"
                failed_questions.append(qna)
            
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
                # 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "API호출실패"
                    qna['subdomain'] = "API호출실패"
                    qna['classification_reason'] = "API 호출에 실패했습니다"
                    qna['is_calculation'] = "API호출실패"
                all_updated_questions.extend(batch)
                continue
            
            if response is None:
                logger.error(f"배치 {batch_num} API 호출 실패")
                fail_response.append(None)
                # 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "API호출실패"
                    qna['subdomain'] = "API호출실패"
                    qna['classification_reason'] = "API 호출에 실패했습니다"
                    qna['is_calculation'] = "API호출실패"
                all_updated_questions.extend(batch)
                continue
            
            # 응답 파싱
            try:
                classifications = self.parse_api_response(response)
            except Exception as e:
                logger.error(f"배치 {batch_num} 응답 파싱 실패: {e}")
                fail_response.append(response)
                # 파싱 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
                    qna['is_calculation'] = "파싱실패"
                all_updated_questions.extend(batch)
                continue
            
            if classifications is None:
                logger.error(f"배치 {batch_num} 응답 파싱 실패")
                fail_response.append(response)
                # 파싱 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
                    qna['is_calculation'] = "파싱실패"
                all_updated_questions.extend(batch)
                continue
            
            # Q&A 데이터 업데이트
            try:
                updated_batch, fail_batch = self.update_qna_subdomain(batch, classifications)
                all_updated_questions.extend(updated_batch)
                fail_question.extend(fail_batch)
            except Exception as e:
                logger.error(f"배치 {batch_num} 업데이트 실패: {e}")
                fail_response.append(response)
            
            # API 호출 간격 조절
            time.sleep(1.2)
            
            # 중간 결과 저장
            if batch_num:  # 중간 저장
                self._save_results(all_updated_questions, fail_response, fail_question)
        
        # 전체 문제수 검증
        if len(all_updated_questions) != len(questions):
            logger.warning(f"문제수 불일치: 원본 {len(questions)}개, 처리된 {len(all_updated_questions)}개")
        
        logger.info(f"처리 완료 - {len(all_updated_questions)}개 문제")
        return all_updated_questions, fail_response, fail_question
    
    def _save_results(self, questions: List[Dict[str, Any]], 
                     fail_response: List, fail_question: List[Dict[str, Any]]):
        """결과 저장"""
        if self.mode == 'multiple-fail':
            filename = f"{self.mode}_response.json"
        else:
            filename = f"{self.mode}_subdomain_classified_ALL.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        if self.mode == 'multiple-fail' or self.mode == 'multiple-re':
            with open(os.path.join(self.output_dir, f"{self.mode}_fail_response.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_response, f, ensure_ascii=False, indent=2)
            with open(os.path.join(self.output_dir, f"{self.mode}_fail_q.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_question, f, ensure_ascii=False, indent=2)
        else:
            with open(os.path.join(self.output_dir, f"{self.mode}_subdomain_classified_ALL_fail_response.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_response, f, ensure_ascii=False, indent=2)
            with open(os.path.join(self.output_dir, f"{self.mode}_subdomain_classified_ALL_fail_q.json"), 'w', encoding='utf-8') as f:
                json.dump(fail_question, f, ensure_ascii=False, indent=2)
    
    def process_all_questions(self, data_path: str = None, questions: List[Dict[str, Any]] = None,
                              model: str = "x-ai/grok-4-fast", batch_size: int = 10) -> List[Dict[str, Any]]:
        """모든 문제 처리 (도메인+서브도메인 한 번에 분류)"""
        # 데이터 로드
        if questions is None:
            if data_path is None:
                # 기본 경로 설정
                if self.mode == 'short-fail':
                    data_path = os.path.join(self.onedrive_path, 'evaluation/eval_data/2_subdomain/short_subdomain_classified_ALL_fail_response.json')
                elif self.mode == 'multiple-fail':
                    data_path = os.path.join(self.onedrive_path, 'evaluation/eval_data/2_subdomain/multiple_re_run.json')
                elif self.mode == 'multiple-re':
                    data_path = os.path.join(self.onedrive_path, 'evaluation/eval_data/2_subdomain/multiple.json')
                else:
                    data_path = os.path.join(self.onedrive_path, f'evaluation/eval_data/1_filter/{self.mode}.json')
            
            questions = self.load_multiple_choice_data(data_path)
        
        logger.info(f"총 문제 수: {len(questions)}")
        
        # 문제 처리
        updated_questions, fail_response, fail_question = self.process_questions(questions, batch_size, model)
        
        # 최종 결과 저장
        self._save_results(updated_questions, fail_response, fail_question)
        
        return updated_questions
    


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Q&A 도메인/서브도메인 분류기')
    parser.add_argument('--data_path', type=str, 
                       default=None,
                       help='데이터 경로 (파일)')
    parser.add_argument('--model', type=str, default='x-ai/grok-4-fast',
                       help='사용할 모델')
    parser.add_argument('--batch_size', type=int, default=10,
                       help='배치 크기 (기본값: 10)')
    parser.add_argument('--config', type=str, default=None,
                       help='설정 파일 경로')
    parser.add_argument('--mode', type=str, default='multiple',
                       help='처리할 문제 유형 (multiple/short/essay/multiple-fail/multiple-re/short-fail)')
    parser.add_argument('--onedrive_path', type=str, default=None,
                       help='OneDrive 경로')
    
    args = parser.parse_args()
    
    # 분류기 초기화
    classifier = QnASubdomainClassifier(
        config_path=args.config, 
        mode=args.mode,
        onedrive_path=args.onedrive_path
    )
    
    # 처리 실행
    try:
        logger.info(f"모드: {args.mode}, 모델: {args.model}, 배치 크기: {args.batch_size}")
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

