#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 도메인/서브도메인 분류기
- API 호출을 통한 domain/subdomain/is_calculation 분류만 담당
- 파일 저장, 기존 데이터 활용 등은 fill_domain.py에서 처리
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
# tools 모듈 import를 위한 경로 설정
_temp_tools_dir = os.path.dirname(os.path.dirname(current_dir))  # processing -> qna -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
project_root = os.path.dirname(tools_dir)  # tools -> project_root

# llm_query 모듈 import
sys.path.insert(0, tools_dir)

# 중앙화된 로깅 유틸리티 사용
from tools.core.logger import setup_logger

# 독립 실행 시 파일명 기반 로그 파일명 생성
_log_file = None
if __name__ == "__main__":
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    _log_file = f'{script_name}.log'
else:
    _log_file = 'qna_subdomain_classifier.log'

logger = setup_logger(
    name=__name__,
    log_file=_log_file,
    use_console=True,
    use_file=True
)
from tools.core.llm_query import LLMQuery
from tools.core.exam_config import ExamConfig


class QnASubdomainClassifier:
    """Q&A 도메인/서브도메인 분류기 (API 호출만 담당)"""
    
    def __init__(self, config_path: str = None, onedrive_path: str = None, logger=None):
        """Q&A 도메인/서브도메인 분류기 초기화
        
        Args:
            config_path: 설정 파일 경로
            onedrive_path: OneDrive 경로
            logger: 사용할 로거 (None이면 자체 로거 사용)
        """
        self.logger = logger if logger is not None else globals().get('logger', logging.getLogger(__name__))
        
        # LLMQuery 초기화
        self.llm_query = LLMQuery(config_path=config_path)
        
        # OneDrive 경로 설정
        if onedrive_path is None:
            import platform
            system = platform.system()
            home_dir = os.path.expanduser("~")
            if system == "Windows":
                onedrive_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
            else:
                onedrive_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
        
        self.onedrive_path = onedrive_path
        
        # 도메인-서브도메인 매핑 로드
        self.domain_subdomain = self._load_domain_subdomain()
        
        # 시스템 프롬프트 생성
        self.system_prompt = self._create_system_prompt()
        
    def _load_domain_subdomain(self) -> Dict[str, List[str]]:
        """도메인-서브도메인 매핑 로드"""
        try:
            exam_config = ExamConfig(onedrive_path=self.onedrive_path)
            domain_subdomain = exam_config.get_domain_subdomain()
            self.logger.info("exam_config.json에서 도메인-서브도메인 매핑 로드 완료")
            return domain_subdomain
        except FileNotFoundError:
            self.logger.warning("exam_config.json을 찾을 수 없습니다.")
            raise
        except Exception as e:
            self.logger.error(f"도메인-서브도메인 매핑 로드 실패: {e}")
            raise
    
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
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
    
    def _create_user_prompt(self, questions: List[Dict[str, Any]]) -> str:
        """사용자 프롬프트 생성"""
        user_prompt = ''
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['tag']}"
            
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
    
    def _call_api(self, user_prompt: str, model: str = "x-ai/grok-4-fast") -> str:
        """API 호출"""
        try:
            response = self.llm_query.query_openrouter(self.system_prompt, user_prompt, model)
            return response
        except Exception as e:
            self.logger.error(f"API 호출 실패: {e}")
            return None
    
    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """API 응답 파싱"""
        parsed_data = self.llm_query.parse_api_response(response)
        
        if parsed_data is None:
            self.logger.error("JSON 배열을 찾을 수 없거나 파싱에 실패했습니다.")
            return None
        
        return parsed_data
    
    def _update_questions(self, questions: List[Dict[str, Any]], 
                          classifications: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """분류 결과를 문제에 적용"""
        classification_dict = {item['qna_id']: item for item in classifications}
        
        updated_questions = []
        failed_questions = []
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['tag']}"
            if unique_id in classification_dict:
                qna['domain'] = classification_dict[unique_id]['domain']
                qna['subdomain'] = classification_dict[unique_id]['subdomain']
                qna['classification_reason'] = classification_dict[unique_id]['reason']
                qna['is_calculation'] = classification_dict[unique_id]['is_calculation']
            else:
                self.logger.warning(f"분류 결과를 찾을 수 없음: {unique_id}")
                qna['domain'] = "분류실패"
                qna['subdomain'] = "분류실패"
                qna['classification_reason'] = "API 응답에서 해당 문제를 찾을 수 없음"
                qna['is_calculation'] = "분류실패"
                failed_questions.append(qna)
            
            updated_questions.append(qna)
        
        return updated_questions, failed_questions

    def classify_questions(self, questions: List[Dict[str, Any]], 
                          batch_size: int = 10, 
                          model: str = "x-ai/grok-4-fast") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        문제들을 배치 단위로 API 호출하여 분류
        
        Args:
            questions: 분류할 문제 리스트
            batch_size: 배치 크기
            model: 사용할 모델
            
        Returns:
            (updated_questions, failed_questions): 분류된 문제와 실패한 문제
        """
        if not questions:
            self.logger.info("분류할 문제가 없습니다.")
            return [], []
        
        self.logger.info(f"API 분류 시작 - 총 {len(questions)}개 문제")
        
        all_updated = []
        all_failed = []
        
        for i in tqdm(range(0, len(questions), batch_size), desc="API 분류 중"):
            batch = questions[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            self.logger.info(f"배치 {batch_num} 처리 중... ({len(batch)}개 문제)")
            
            # 프롬프트 생성 및 API 호출
            user_prompt = self._create_user_prompt(batch)
            
            try:
                response = self._call_api(user_prompt, model)
            except Exception as e:
                self.logger.error(f"배치 {batch_num} API 호출 실패: {e}")
                for qna in batch:
                    qna['domain'] = "API호출실패"
                    qna['subdomain'] = "API호출실패"
                    qna['classification_reason'] = "API 호출에 실패했습니다"
                    qna['is_calculation'] = "API호출실패"
                    all_failed.append(qna)
                all_updated.extend(batch)
                continue
            
            if response is None:
                self.logger.error(f"배치 {batch_num} API 호출 실패")
                for qna in batch:
                    qna['domain'] = "API호출실패"
                    qna['subdomain'] = "API호출실패"
                    qna['classification_reason'] = "API 호출에 실패했습니다"
                    qna['is_calculation'] = "API호출실패"
                    all_failed.append(qna)
                all_updated.extend(batch)
                continue
            
            # 응답 파싱
            try:
                classifications = self._parse_response(response)
            except Exception as e:
                self.logger.error(f"배치 {batch_num} 응답 파싱 실패: {e}")
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
                    qna['is_calculation'] = "파싱실패"
                    all_failed.append(qna)
                all_updated.extend(batch)
                continue
            
            if classifications is None:
                self.logger.error(f"배치 {batch_num} 응답 파싱 실패")
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
                    qna['is_calculation'] = "파싱실패"
                    all_failed.append(qna)
                all_updated.extend(batch)
                continue
            
            # 분류 결과 적용
            try:
                updated_batch, fail_batch = self._update_questions(batch, classifications)
                all_updated.extend(updated_batch)
                all_failed.extend(fail_batch)
            except Exception as e:
                self.logger.error(f"배치 {batch_num} 업데이트 실패: {e}")
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = f"업데이트 실패: {e}"
                    qna['is_calculation'] = "파싱실패"
                    all_failed.append(qna)
                all_updated.extend(batch)
            
            # API 호출 간격 조절
            time.sleep(1.2)
        
        self.logger.info(f"API 분류 완료 - 성공: {len(all_updated) - len(all_failed)}개, 실패: {len(all_failed)}개")
        
        return all_updated, all_failed


def main():
    """테스트용 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Q&A 도메인/서브도메인 분류기')
    parser.add_argument('--data_path', type=str, required=True, help='데이터 경로')
    parser.add_argument('--model', type=str, default='x-ai/grok-4-fast', help='사용할 모델')
    parser.add_argument('--batch_size', type=int, default=10, help='배치 크기')
    parser.add_argument('--onedrive_path', type=str, default=None, help='OneDrive 경로')
    
    args = parser.parse_args()
    
    # 데이터 로드
    with open(args.data_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    # 분류기 초기화
    classifier = QnASubdomainClassifier(onedrive_path=args.onedrive_path)
    
    # 분류 실행
    updated, failed = classifier.classify_questions(
        questions=questions,
        model=args.model,
        batch_size=args.batch_size
    )
    
    logger.info(f"완료! 성공: {len(updated) - len(failed)}개, 실패: {len(failed)}개")


if __name__ == "__main__":
    main()
