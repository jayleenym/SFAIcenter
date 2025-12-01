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
from datetime import datetime
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
from core.logger import setup_logger

# 독립 실행 시 파일명 기반 로그 파일명 생성
_log_file = None
if __name__ == "__main__":
    # 독립 실행 시: 파일명.log
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    _log_file = f'{script_name}.log'
else:
    # 모듈로 import 시: 기존 이름 유지
    _log_file = 'qna_subdomain_classifier.log'

logger = setup_logger(
    name=__name__,
    log_file=_log_file,
    use_console=True,
    use_file=True
)
from core.llm_query import LLMQuery
from core.exam_config import ExamConfig

class QnASubdomainClassifier:
    def __init__(self, config_path: str = None, mode: str = 'multiple', onedrive_path: str = None, logger=None):
        """Q&A 도메인/서브도메인 분류기 초기화
        
        Args:
            config_path: 설정 파일 경로
            mode: 처리할 문제 유형 (multiple/short/essay 등)
            onedrive_path: OneDrive 경로
            logger: 사용할 로거 (None이면 자체 로거 사용)
        """
        # 로거 설정 (step에서 호출될 때는 step 로거 사용)
        self.logger = logger if logger is not None else globals().get('logger', logging.getLogger(__name__))
        
        # LLMQuery 초기화
        self.llm_query = LLMQuery(config_path=config_path)
        
        # mode 검증
        valid_modes = ['multiple', 'short', 'essay', 'multiple-choice', 'short-answer', 
                      'multiple-fail', 'multiple-re', 'short-fail']
        if mode not in valid_modes:
            self.logger.warning(f"mode '{mode}'가 표준 모드가 아닙니다. 계속 진행합니다.")
        
        self.mode = mode
        
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
        self.domain_subdomain = self.load_domain_subdomain()
        
        # 시스템 프롬프트 생성 (모든 도메인 포함)
        self.system_prompt = self.create_system_prompt()
        
        # 결과 저장 디렉토리
        self.output_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '2_subdomain')
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"출력 디렉토리: {self.output_dir}")
        
    def load_domain_subdomain(self) -> Dict[str, List[str]]:
        """도메인-서브도메인 매핑 로드 (exam_config.json 사용)"""
        try:
            exam_config = ExamConfig(onedrive_path=self.onedrive_path)
            domain_subdomain = exam_config.get_domain_subdomain()
            self.logger.info("exam_config.json에서 도메인-서브도메인 매핑 로드 완료")
            return domain_subdomain
        except FileNotFoundError:
            # fallback: 기존 방식으로 시도 (하위 호환성)
            self.logger.warning("exam_config.json을 찾을 수 없어 기존 domain_subdomain.json을 시도합니다.")
            domain_subdomain_path = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '_old', 'domain_subdomain.json')
            
            if not os.path.exists(domain_subdomain_path):
                raise FileNotFoundError(f"도메인-서브도메인 매핑 파일을 찾을 수 없습니다: {domain_subdomain_path}")
            
            with open(domain_subdomain_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"도메인-서브도메인 매핑 로드 실패: {e}")
            raise
    
    def load_multiple_choice_data(self, data_path: str) -> List[Dict[str, Any]]:
        """문제 데이터 로드"""
        self.logger.info(f"데이터 로딩 중: {data_path}")
        
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
            self.logger.error(f"API 호출 실패: {e}")
            return None
    
    def parse_api_response(self, response: str) -> List[Dict[str, Any]]:
        """API 응답 파싱 (llm_query 모듈 사용)"""
        parsed_data = self.llm_query.parse_api_response(response)
        
        if parsed_data is None:
            self.logger.error("JSON 배열을 찾을 수 없거나 파싱에 실패했습니다.")
            self.logger.error(f"응답 내용: {response[:500]}...")
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
                self.logger.warning(f"분류 결과를 찾을 수 없음: {unique_id}")
                qna['domain'] = "분류실패"
                qna['subdomain'] = "분류실패"
                qna['classification_reason'] = "API 응답에서 해당 문제를 찾을 수 없음"
                qna['is_calculation'] = "분류실패"
                failed_questions.append(qna)
            
            updated_questions.append(qna)
        
        return updated_questions, failed_questions
    

    def process_questions(self, questions: List[Dict[str, Any]], 
                         batch_size: int = 10, model: str = "x-ai/grok-4-fast", 
                         is_retry: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """문제들을 배치 단위로 처리 (이미 분류된 항목은 건너뜀)
        
        Args:
            questions: 처리할 문제 리스트
            batch_size: 배치 크기
            model: 사용할 모델
            is_retry: 재시도 모드인지 여부
            
        Returns:
            (all_updated_questions, failed_questions): 
                - all_updated_questions: 모든 처리된 문제 (성공+실패 포함)
                - failed_questions: 실패한 문제 리스트
        """
        if is_retry:
            self.logger.info(f"재시도 처리 시작 - 총 {len(questions)}개 문제")
        else:
            self.logger.info(f"처리 시작 - 총 {len(questions)}개 문제")
        
        # 기존 파일에서 이미 분류된 항목 키 추출 (재시도 모드가 아닐 때만)
        existing_keys = set()
        if not is_retry:
            existing_file_path = self._get_output_filepath()
            if os.path.exists(existing_file_path):
                try:
                    with open(existing_file_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, list):
                            for item in existing_data:
                                file_id = item.get('file_id', '')
                                tag = item.get('tag', '')
                                domain = item.get('domain', '').strip()
                                subdomain = item.get('subdomain', '').strip()
                                # 이미 분류되어 있고 실패 상태가 아닌 경우
                                if (domain and subdomain and 
                                    domain not in ['', '분류실패', 'API호출실패', '파싱실패'] and
                                    subdomain not in ['', '분류실패', 'API호출실패', '파싱실패']):
                                    existing_keys.add((file_id, tag))
                            self.logger.info(f"기존 파일에서 이미 분류된 항목: {len(existing_keys)}개")
                except Exception as e:
                    self.logger.warning(f"기존 파일 로드 실패: {e}")
        
        # 새로운 항목만 필터링 (기존 파일에 없는 항목)
        needs_classification = []
        for qna in questions:
            file_id = qna.get('file_id', '')
            tag = qna.get('tag', '')
            key = (file_id, tag)
            if key not in existing_keys:
                needs_classification.append(qna)
        
        if not is_retry:
            self.logger.info(f"입력: {len(questions)}개, 이미 분류됨: {len(existing_keys)}개, 분류 필요: {len(needs_classification)}개")
        
        all_updated_questions = []
        failed_questions = []
        
        # 분류가 필요한 항목만 배치 단위로 처리
        if not needs_classification:
            if is_retry:
                self.logger.info("재시도할 항목이 없습니다.")
            else:
                self.logger.info("모든 항목이 이미 분류되어 있습니다. API 호출을 건너뜁니다.")
            return all_updated_questions, failed_questions
        
        for i in tqdm(range(0, len(needs_classification), batch_size), desc="처리 중"):
            batch = needs_classification[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            self.logger.info(f"배치 {batch_num} 처리 중... ({len(batch)}개 문제)")
            
            # 사용자 프롬프트 생성
            user_prompt = self.create_user_prompt(batch)
            
            # API 호출
            try:
                response = self.call_api(self.system_prompt, user_prompt, model)
            except Exception as e:
                self.logger.error(f"배치 {batch_num} API 호출 실패: {e}")
                # 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "API호출실패"
                    qna['subdomain'] = "API호출실패"
                    qna['classification_reason'] = "API 호출에 실패했습니다"
                    qna['is_calculation'] = "API호출실패"
                    failed_questions.append(qna)
                all_updated_questions.extend(batch)
                continue
            
            if response is None:
                logger.error(f"배치 {batch_num} API 호출 실패")
                # 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "API호출실패"
                    qna['subdomain'] = "API호출실패"
                    qna['classification_reason'] = "API 호출에 실패했습니다"
                    qna['is_calculation'] = "API호출실패"
                    failed_questions.append(qna)
                all_updated_questions.extend(batch)
                continue
            
            # 응답 파싱
            try:
                classifications = self.parse_api_response(response)
            except Exception as e:
                self.logger.error(f"배치 {batch_num} 응답 파싱 실패: {e}")
                # 파싱 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
                    qna['is_calculation'] = "파싱실패"
                    failed_questions.append(qna)
                all_updated_questions.extend(batch)
                continue
            
            if classifications is None:
                logger.error(f"배치 {batch_num} 응답 파싱 실패")
                # 파싱 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = "API 응답 파싱에 실패했습니다"
                    qna['is_calculation'] = "파싱실패"
                    failed_questions.append(qna)
                all_updated_questions.extend(batch)
                continue
            
            # Q&A 데이터 업데이트
            try:
                updated_batch, fail_batch = self.update_qna_subdomain(batch, classifications)
                all_updated_questions.extend(updated_batch)
                failed_questions.extend(fail_batch)  # 분류 실패한 항목도 추가
            except Exception as e:
                self.logger.error(f"배치 {batch_num} 업데이트 실패: {e}")
                # 예외 발생 시 전체 배치를 실패로 처리
                for qna in batch:
                    qna['domain'] = "파싱실패"
                    qna['subdomain'] = "파싱실패"
                    qna['classification_reason'] = f"업데이트 실패: {e}"
                    qna['is_calculation'] = "파싱실패"
                    failed_questions.append(qna)
                all_updated_questions.extend(batch)
            
            # API 호출 간격 조절
            time.sleep(1.2)
            
            # 중간 결과 저장 (재시도 모드가 아닐 때만)
            if batch_num and not is_retry:
                self._append_results(all_updated_questions, [], [])
        
        # 전체 문제수 검증
        total_processed = len(all_updated_questions)
        if total_processed != len(questions):
            self.logger.warning(f"문제수 불일치: 원본 {len(questions)}개, 처리된 {total_processed}개")
        
        if is_retry:
            self.logger.info(f"재시도 처리 완료 - 성공: {len(all_updated_questions) - len(failed_questions)}개, 실패: {len(failed_questions)}개")
        else:
            self.logger.info(f"처리 완료 - 새로 분류: {len(needs_classification)}개, 실패: {len(failed_questions)}개")
        
        return all_updated_questions, failed_questions
    
    def _normalize_item_format(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """항목 형식을 표준 형식으로 정규화 (불필요한 필드 제거)"""
        # 표준 필드만 유지 (지정된 순서대로)
        normalized = {
            'file_id': item.get('file_id', ''),
            'tag': item.get('tag', ''),
            'title': item.get('title', ''),
            'cat1_domain': item.get('cat1_domain', ''),
            'cat2_sub': item.get('cat2_sub', ''),
            'cat3_specific': item.get('cat3_specific', ''),
            'chapter': item.get('chapter', ''),
            'page': item.get('page', ''),
            'qna_type': item.get('qna_type', ''),
            'domain': item.get('domain', ''),
            'subdomain': item.get('subdomain', ''),
            'is_calculation': item.get('is_calculation', False),
            'classification_reason': item.get('classification_reason', ''),
            'question': item.get('question', ''),
            'options': item.get('options', []),
            'answer': item.get('answer', ''),
            'explanation': item.get('explanation', '')
        }
        return normalized
    
    def _get_output_filepath(self) -> str:
        """출력 파일 경로 반환"""
        if self.mode == 'multiple-fail':
            filename = f"{self.mode}_response.json"
        else:
            filename = f"{self.mode}_subdomain_classified_ALL.json"
        return os.path.join(self.output_dir, filename)
    
    def _delete_qna_type_file(self):
        """~_classified_ALL.json 파일이 생성되면 {qna_type}.json 파일 삭제"""
        # mode에 따른 파일명 매핑
        qna_type_file_map = {
            'multiple': 'multiple-choice.json',
            'multiple-choice': 'multiple-choice.json',
            'short': 'short-answer.json',
            'short-answer': 'short-answer.json',
            'essay': 'essay.json',
            'etc': 'etc.json'
        }
        
        # multiple-fail, multiple-re, short-fail 등의 특수 모드는 건너뛰기
        if self.mode not in qna_type_file_map:
            return
        
        # ~_classified_ALL.json 파일이 존재하는지 확인
        all_file_path = self._get_output_filepath()
        if not os.path.exists(all_file_path):
            return
        
        # {qna_type}.json 파일 경로
        qna_type_file = os.path.join(self.output_dir, qna_type_file_map[self.mode])
        
        # 파일이 존재하면 삭제
        if os.path.exists(qna_type_file):
            try:
                os.remove(qna_type_file)
                self.logger.info(f"{qna_type_file_map[self.mode]} 파일 삭제 완료 (~_classified_ALL.json 파일 생성됨)")
            except Exception as e:
                self.logger.warning(f"{qna_type_file_map[self.mode]} 파일 삭제 실패: {e}")
    
    def _append_results(self, new_questions: List[Dict[str, Any]], 
                       fail_response: List, fail_question: List[Dict[str, Any]]):
        """새로운 결과를 기존 파일에 추가 (중복 체크)"""
        filepath = self._get_output_filepath()
        
        # 기존 파일 로드
        existing_questions = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_questions = existing_data
            except Exception as e:
                self.logger.warning(f"기존 파일 로드 실패: {e}")
                existing_questions = []
        
        # 중복 제거: file_id와 tag 기준
        existing_keys = set()
        for item in existing_questions:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            existing_keys.add((file_id, tag))
        
        # 새 항목 중 중복이 아닌 것만 추가 (형식 정규화)
        new_count = 0
        for item in new_questions:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            key = (file_id, tag)
            if key not in existing_keys:
                # 형식 정규화 후 추가
                normalized_item = self._normalize_item_format(item)
                existing_questions.append(normalized_item)
                existing_keys.add(key)
                new_count += 1
        
        # 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_questions, f, ensure_ascii=False, indent=2)
        
        if new_count > 0:
            self.logger.info(f"새 항목 {new_count}개 추가 (기존 {len(existing_questions) - new_count}개 + 새 {new_count}개 = 총 {len(existing_questions)}개)")
    
    def _save_results(self, questions: List[Dict[str, Any]], 
                     fail_response: List, fail_question: List[Dict[str, Any]]):
        """최종 결과 저장 (처리 완료 후 호출)"""
        filepath = self._get_output_filepath()
        
        # 기존 파일 로드
        existing_questions = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_questions = existing_data
            except Exception as e:
                self.logger.warning(f"기존 파일 로드 실패: {e}")
                existing_questions = []
        
        # 중복 제거: file_id와 tag 기준
        existing_keys = set()
        for item in existing_questions:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            existing_keys.add((file_id, tag))
        
        # 새 항목 중 중복이 아닌 것만 추가 (형식 정규화)
        new_count = 0
        for item in questions:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            key = (file_id, tag)
            if key not in existing_keys:
                # 형식 정규화 후 추가
                normalized_item = self._normalize_item_format(item)
                existing_questions.append(normalized_item)
                existing_keys.add(key)
                new_count += 1
        
        # 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_questions, f, ensure_ascii=False, indent=2)
        
        if new_count > 0:
            self.logger.info(f"최종 저장: 새 항목 {new_count}개 추가 (기존 {len(existing_questions) - new_count}개 + 새 {new_count}개 = 총 {len(existing_questions)}개)")
        else:
            self.logger.info(f"최종 저장: 기존 {len(existing_questions)}개 유지 (새 항목 없음)")
        
        # ~_classified_ALL.json 파일이 생성되면 {qna_type}.json 파일 삭제
        self._delete_qna_type_file()
    
    def process_all_questions(self, data_path: str = None, questions: List[Dict[str, Any]] = None,
                              model: str = "x-ai/grok-4-fast", batch_size: int = 10) -> List[Dict[str, Any]]:
        """모든 문제 처리 (도메인+서브도메인 한 번에 분류, 실패 항목 재시도)"""
        # 데이터 로드
        if questions is None:
            if data_path is None:
                # 기본 경로 설정
                if self.mode == 'short-fail':
                    data_path = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '2_subdomain', 'short_subdomain_classified_ALL_fail_response.json')
                elif self.mode == 'multiple-fail':
                    data_path = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '2_subdomain', 'multiple_re_run.json')
                elif self.mode == 'multiple-re':
                    data_path = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '2_subdomain', 'multiple.json')
                else:
                    data_path = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '1_filter', f'{self.mode}.json')
            
            questions = self.load_multiple_choice_data(data_path)
        
        self.logger.info(f"총 문제 수: {len(questions)}")
        
        # 1차 처리
        updated_questions, failed_questions = self.process_questions(questions, batch_size, model, is_retry=False)
        
        # 실패한 항목이 있으면 재시도
        if failed_questions:
            self.logger.info(f"실패한 항목 {len(failed_questions)}개 재시도 시작...")
            retry_updated, retry_failed = self.process_questions(failed_questions, batch_size, model, is_retry=True)
            
            # 재시도 결과를 원본 결과에 반영
            # 재시도 성공한 항목은 업데이트, 실패한 항목은 그대로 유지
            retry_success_keys = set()
            for item in retry_updated:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                domain = item.get('domain', '').strip()
                subdomain = item.get('subdomain', '').strip()
                # 재시도에서 성공한 항목 (실패 상태가 아닌 경우)
                if (domain and subdomain and 
                    domain not in ['API호출실패', '파싱실패', '분류실패', ''] and
                    subdomain not in ['API호출실패', '파싱실패', '분류실패', '']):
                    retry_success_keys.add((file_id, tag))
            
            # 원본 결과에서 재시도 성공한 항목 업데이트
            updated_dict = {(item.get('file_id', ''), item.get('tag', '')): item for item in retry_updated}
            for i, item in enumerate(updated_questions):
                key = (item.get('file_id', ''), item.get('tag', ''))
                if key in updated_dict:
                    updated_questions[i] = updated_dict[key]
            
            # 2번 실패한 항목만 추출
            twice_failed = [item for item in retry_failed]
            
            if twice_failed:
                failed_filepath = os.path.join(self.output_dir, f"{self.mode}_failed.json")
                self.logger.warning(f"2번 실패한 항목 {len(twice_failed)}개를 {failed_filepath}에 저장합니다.")
                with open(failed_filepath, 'w', encoding='utf-8') as f:
                    json.dump(twice_failed, f, ensure_ascii=False, indent=2)
                self.logger.info(f"2번 실패한 항목 저장 완료: {failed_filepath}")
        else:
            self.logger.info("실패한 항목이 없어 재시도를 건너뜁니다.")
        
        # 최종 결과 저장 (모든 항목 포함: 성공 + 실패)
        self._save_results(updated_questions, [], [])
        
        return updated_questions
    
    def save_statistics(self, all_results: Dict[str, List[Dict[str, Any]]] = None):
        """통계 정보 저장"""
        # 통계 정보 저장
        if all_results is None:
            # 먼저 {mode}_subdomain_classified_ALL.json 파일을 찾아서 읽기 (원본 모드 사용)
            all_file = self._get_output_filepath()
            if os.path.exists(all_file):
                with open(all_file, 'r', encoding='utf-8') as f:
                    all_questions = json.load(f)
                # 도메인별로 그룹화
                all_results = {}
                for qna in all_questions:
                    domain = qna.get('domain', '미분류')
                    if domain not in all_results:
                        all_results[domain] = []
                    all_results[domain].append(qna)
            else:
                # fallback: 도메인별 파일 찾기 (하위 호환성)
                all_results = {}
                for filename in os.listdir(self.output_dir):
                    if filename.endswith('_subdomain_classified.json') and not filename.endswith('_ALL.json'):
                        domain = filename.replace('_subdomain_classified.json', '')
                        with open(os.path.join(self.output_dir, filename), 'r', encoding='utf-8') as f:
                            all_results[domain] = json.load(f)
        else:
            # all_results가 리스트 형태인 경우 처리
            if isinstance(all_results, list):
                # 도메인별로 그룹화
                domain_groups = {}
                for qna in all_results:
                    domain = qna.get('domain', '미분류')
                    if domain not in domain_groups:
                        domain_groups[domain] = []
                    domain_groups[domain].append(qna)
                all_results = domain_groups
        
        stats = {}
        for domain, questions in all_results.items():
            subdomain_counts = {}
            for qna in questions:
                # subdomain 키를 우선 사용, 없으면 qna_subdomain 사용
                subdomain = qna.get('subdomain', '미분류')
                subdomain_counts[subdomain] = subdomain_counts.get(subdomain, 0) + 1
            
            stats[domain] = {
                'total_questions': len(questions),
                'subdomain_distribution': subdomain_counts
            }
            
        # mode에 따라 파일명과 제목 설정
        mode_display_name = {
            'multiple': 'Multiple Choice',
            'multiple-choice': 'Multiple Choice',
            'short': 'Short Answer',
            'short-answer': 'Short Answer',
            'essay': 'Essay',
            'multiple-fail': 'Multiple Choice (Fail)',
            'multiple-re': 'Multiple Choice (Re-run)',
            'short-fail': 'Short Answer (Fail)'
        }.get(self.mode, self.mode.title())
        
        stats_filepath = os.path.join(self.output_dir, f"STATS_{self.mode}_subdomain.md")
        with open(stats_filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {mode_display_name} Subdomain 통계\n\n")
            f.write(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            for domain, domain_stats in sorted(stats.items()):
                f.write(f"## {domain}\n\n")
                f.write(f"- **전체 문제 수**: {domain_stats['total_questions']:,}개\n\n")
                f.write("### 서브도메인별 분포\n\n")
                f.write("| 서브도메인 | 문제 수 | 비율 |\n")
                f.write("|-----------|--------|------|\n")
                
                total = domain_stats['total_questions']
                subdomain_dist = sorted(domain_stats['subdomain_distribution'].items(), 
                                       key=lambda x: x[1], reverse=True)
                for subdomain, count in subdomain_dist:
                    percentage = (count / total * 100) if total > 0 else 0
                    f.write(f"| {subdomain} | {count:,}개 | {percentage:.2f}% |\n")
                f.write("\n")
        
        self.logger.info(f"통계 정보 저장 완료: {stats_filepath}")


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

