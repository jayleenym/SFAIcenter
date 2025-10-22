#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 서브도메인 분류기
- 50문제 단위로 API 호출
- JSON 응답 파싱하여 qna_subdomain 업데이트
- 도메인별 문제들을 JSON 파일로 저장
"""

import os
import json
import time
import logging
import glob
from typing import List, Dict, Any, Tuple
from tqdm import tqdm
import configparser
from openai import OpenAI

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/qna_subdomain_classifier.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QnASubdomainClassifier:
    def __init__(self, config_path: str = './llm_config.ini'):
        """Q&A 서브도메인 분류기 초기화"""
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')
        
        # OpenAI 클라이언트 초기화
        self.client = OpenAI(
            api_key=self.config["OPENROUTER"]["key"], 
            base_url=self.config["OPENROUTER"]["url"]
        )
        
        # 도메인-서브도메인 매핑 로드
        self.domain_subdomain = self.load_domain_subdomain()
        
        # 결과 저장 디렉토리
        self.output_dir = 'evaluation/eval_data/multiple_with_subdomain'
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_domain_subdomain(self) -> Dict[str, List[str]]:
        """도메인-서브도메인 매핑 로드"""
        with open('evaluation/eval_data/domain_subdomain.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_multiple_choice_data(self, data_path: str) -> List[Dict[str, Any]]:
        """객관식 문제 데이터 로드"""
        logger.info(f"데이터 로딩 중: {data_path}")
        
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    
    def create_system_prompt(self, domain: str) -> str:
        """도메인별 시스템 프롬프트 생성"""
        subdomain_list = self.domain_subdomain[domain]
        
        prompt_domain = ''
        domain_list = []
        
        for i, subdomain_item in enumerate(subdomain_list):
            subdomain_name = subdomain_item.split('(')[0].strip()
            domain_list.append(subdomain_name)
            subdomain_ex = subdomain_item.split('(')[1].split(')')[0].strip()
            prompt_domain += f'{i+1}. {subdomain_name}\n   - {subdomain_ex}\n'
        
        system_prompt = f"""
당신은 금융·{domain} 시험 문제를 세부 주제별로 정확히 분류하는 전문가입니다.  
주어진 문제는 이미 '{domain}' 영역으로 1차 분류된 것입니다.  
당신의 임무는 이 문제를 아래의 세부 분류체계 중 하나로 정확히 분류하는 것입니다.

### 세부 분류체계
{prompt_domain}

분류 기준:
- 문제의 핵심 개념, 등장 용어, 계산 대상, 제시된 사례를 기준으로 판단합니다.
- 특정 학문적 이론이나 모형이 등장한다면 그 이론이 속한 학문 영역으로 분류합니다.
- 판단이 애매할 경우, **'가장 관련성이 높은 영역 하나만** 선택해야 합니다.

출력은 아래 JSON 형태로 작성합니다. 각 문제마다 하나의 객체를 생성하세요.
문제 ID는 "file_id_qna_id" 형태로 제공됩니다.

[
{{
  "qna_id": "file_id_qna_id",
  "category_detail": "선택된_서브도메인명",
  "reason": "간단한 이유 (문제의 핵심 키워드와 근거 중심으로)"
}},
{{
  "qna_id": "file_id_qna_id",
  "category_detail": "선택된_서브도메인명", 
  "reason": "간단한 이유 (문제의 핵심 키워드와 근거 중심으로)"
}}
]
"""
        return system_prompt
    
    def create_user_prompt(self, questions: List[Dict[str, Any]]) -> str:
        """사용자 프롬프트 생성"""
        user_prompt = ''
        
        for qna in questions:
            options_text = '\n'.join(qna['qna_options'])
            unique_id = f"{qna['file_id']}_{qna['qna_id']}"
            single_prompt = f"""
문제 ID: {unique_id}
책 제목: {qna['title']}
챕터: {qna['chapter']}
질문 분류: {qna['qna_domain']}
질문: {qna['qna_question']}
선지: {options_text}
답변: {qna['qna_answer']}
해설: {qna['qna_explanation']}
===================="""
            user_prompt += single_prompt
        
        return user_prompt
    
    def call_api(self, system_prompt: str, user_prompt: str, model: str = "x-ai/grok-4-fast") -> str:
        """API 호출"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                temperature=float(self.config["PARAMS"]["temperature"]),
                frequency_penalty=float(self.config["PARAMS"]["frequency_penalty"]),
                presence_penalty=float(self.config["PARAMS"]["presence_penalty"]),
                top_p=float(self.config["PARAMS"]["top_p"]),
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": user_prompt}
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            return None
    
    def parse_api_response(self, response: str) -> List[Dict[str, Any]]:
        """API 응답 파싱"""
        try:
            # JSON 응답에서 배열 부분만 추출
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.error("JSON 배열을 찾을 수 없습니다.")
                return []
            
            json_str = response[start_idx:end_idx]
            parsed_data = json.loads(json_str)
            
            if not isinstance(parsed_data, list):
                logger.error("응답이 배열 형태가 아닙니다.")
                return []
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.error(f"응답 내용: {response[:500]}...")
            return []
        except Exception as e:
            logger.error(f"응답 파싱 중 오류: {e}")
            return []
    
    def update_qna_subdomain(self, questions: List[Dict[str, Any]], 
                           classifications: List[Dict[str, Any]], 
                           domain: str = None, batch_num: int = None) -> List[Dict[str, Any]]:
        """Q&A 데이터에 서브도메인 분류 결과 업데이트"""
        # file_id + qna_id 조합을 키로 하는 딕셔너리 생성
        classification_dict = {item['qna_id']: item for item in classifications}
        
        updated_questions = []
        failed_questions = []  # 분류 실패한 문제들 수집
        
        for qna in questions:
            unique_id = f"{qna['file_id']}_{qna['qna_id']}"
            if unique_id in classification_dict:
                qna['qna_subdomain'] = classification_dict[unique_id]['category_detail']
                qna['qna_subdomain_reason'] = classification_dict[unique_id]['reason']
            else:
                logger.warning(f"분류 결과를 찾을 수 없음: {unique_id}")
                qna['qna_subdomain'] = "분류실패"
                qna['qna_subdomain_reason'] = "API 응답에서 해당 문제를 찾을 수 없음"
                failed_questions.append(qna)
            
            updated_questions.append(qna)
        
        # 분류 실패한 문제들이 있고, 도메인과 배치 번호가 제공된 경우 파일에 저장
        if failed_questions and domain and batch_num is not None:
            self.save_failure_response(domain, batch_num, "분류실패", 
                                     error_message=f"{len(failed_questions)}개 문제 분류 실패", 
                                     batch=failed_questions)
        
        return updated_questions
    
    def save_failure_response(self, domain: str, batch_num: int, failure_type: str, 
                            response: str = None, batch: List[Dict[str, Any]] = None, 
                            error_message: str = None):
        """실패 시 응답 결과를 별도 파일에 저장"""
        failure_data = {
            "domain": domain,
            "batch_num": batch_num,
            "failure_type": failure_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if batch:
            failure_data.update({
                "batch_size": len(batch),
                "qna_ids": [f"{qna['file_id']}_{qna['qna_id']}" for qna in batch]
            })
        
        if response:
            failure_data["api_response"] = response
        
        if error_message:
            failure_data["error_message"] = error_message
        
        failure_filename = f"{domain}_{failure_type}.json"
        failure_filepath = os.path.join(self.output_dir, failure_filename)
        
        # 기존 파일이 있으면 로드하고 새 데이터 추가
        if os.path.exists(failure_filepath):
            with open(failure_filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        existing_data.append(failure_data)
        
        with open(failure_filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{failure_type} 응답 저장: {failure_filepath}")

    def save_parsing_failure_response(self, domain: str, batch_num: int, response: str, batch: List[Dict[str, Any]]):
        """파싱 실패 시 응답 결과를 별도 파일에 저장 (기존 호환성 유지)"""
        self.save_failure_response(domain, batch_num, "파싱실패", response, batch)

    def process_domain_batch(self, domain: str, questions: List[Dict[str, Any]], 
                           batch_size: int = 50, model: str = "x-ai/grok-4-fast") -> List[Dict[str, Any]]:
        """도메인별 문제들을 배치 단위로 처리"""
        logger.info(f"{domain} 도메인 처리 시작 - 총 {len(questions)}개 문제")
        
        system_prompt = self.create_system_prompt(domain)
        all_updated_questions = []
        
        # 배치 단위로 처리
        for i in tqdm(range(0, len(questions), batch_size), desc=f"{domain} 처리"):
            batch = questions[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"{domain} 배치 {batch_num} 처리 중... ({len(batch)}개 문제)")
            
            # 사용자 프롬프트 생성
            user_prompt = self.create_user_prompt(batch)
            
            # API 호출
            response = self.call_api(system_prompt, user_prompt, model)
            
            if response is None:
                logger.error(f"{domain} 배치 {batch_num} API 호출 실패")
                # API 호출 실패를 파일에 저장
                self.save_failure_response(domain, batch_num, "API호출실패", 
                                         error_message="API 호출에 실패했습니다", batch=batch)
                
                # 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['qna_subdomain'] = "API호출실패"
                    qna['qna_subdomain_reason'] = "API 호출에 실패했습니다"
                all_updated_questions.extend(batch)
                continue
            
            # 응답 파싱
            classifications = self.parse_api_response(response)
            
            if not classifications:
                logger.error(f"{domain} 배치 {batch_num} 응답 파싱 실패")
                # 파싱 실패한 경우 응답 결과를 별도 파일에 저장
                self.save_parsing_failure_response(domain, batch_num, response, batch)
                
                # 파싱 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['qna_subdomain'] = "파싱실패"
                    qna['qna_subdomain_reason'] = "API 응답 파싱에 실패했습니다"
                all_updated_questions.extend(batch)
                continue
            
            # Q&A 데이터 업데이트
            updated_batch = self.update_qna_subdomain(batch, classifications, domain, batch_num)
            all_updated_questions.extend(updated_batch)
            
            # API 호출 간격 조절
            time.sleep(1)
            
            # 중간 결과 저장
            if batch_num % 5 == 0:  # 5배치마다 중간 저장
                self.save_domain_results(domain, all_updated_questions, f"_batch_{batch_num}")
        
        # 전체 문제수 검증
        if len(all_updated_questions) != len(questions):
            logger.warning(f"{domain} 도메인 문제수 불일치: 원본 {len(questions)}개, 처리된 {len(all_updated_questions)}개")
        
        logger.info(f"{domain} 도메인 처리 완료 - {len(all_updated_questions)}개 문제")
        return all_updated_questions
    
    def save_domain_results(self, domain: str, questions: List[Dict[str, Any]], suffix: str = ""):
        """도메인별 결과 저장"""
        filename = f"{domain}_subdomain_classified{suffix}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{domain} 결과 저장 완료: {filepath}")
    
    def cleanup_temp_files(self, domain: str):
        """도메인별 임시 파일들 정리"""
        pattern = os.path.join(self.output_dir, f"{domain}_subdomain_classified_batch_*.json")
        temp_files = glob.glob(pattern)
        
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
                logger.info(f"임시 파일 삭제: {temp_file}")
            except OSError as e:
                logger.warning(f"임시 파일 삭제 실패: {temp_file} - {e}")
    
    def process_single_domain(self, domain: str, data_path: str, model: str = "x-ai/grok-4-fast", 
                            batch_size: int = 50):
        """특정 도메인만 처리"""
        logger.info(f"'{domain}' 도메인 처리 시작")
        
        # 데이터 로드 및 처리
        raw_data = self.load_multiple_choice_data(data_path)
        # processed_data = self.process_qna_data(raw_data)
        logger.info(f"원시 문제 수: {len(raw_data)}")
        
        # 해당 도메인의 문제만 필터링
        domain_questions = [qna for qna in raw_data if qna['qna_domain'] == domain]
        logger.info(f"해당 도메인의 문제 수: {len(domain_questions)}")
        if not domain_questions:
            logger.warning(f"'{domain}' 도메인의 문제를 찾을 수 없습니다.")
            return {}
        
        if domain not in self.domain_subdomain:
            logger.error(f"도메인 '{domain}'에 대한 서브도메인 매핑이 없습니다.")
            return {}
        
        logger.info(f"{domain} 도메인 문제 수: {len(domain_questions)}")
        
        try:
            updated_questions = self.process_domain_batch(
                domain, domain_questions, batch_size, model
            )
            
            # 결과 저장
            self.save_domain_results(domain, updated_questions)
            
            # 임시 파일들 정리
            self.cleanup_temp_files(domain)
            
            logger.info(f"'{domain}' 도메인 처리 완료!")
            return {domain: updated_questions}
            
        except Exception as e:
            logger.error(f"{domain} 도메인 처리 중 오류: {e}")
            return {}

    def process_all_domains(self, data_path: str, model: str = "x-ai/grok-4-fast", 
                          batch_size: int = 50):
        """모든 도메인 처리"""
        # 데이터 로드 및 처리
        raw_data = self.load_multiple_choice_data(data_path)
        # processed_data = self.process_qna_data(raw_data)
        
        # 도메인별로 그룹화
        domain_groups = {}
        for qna in raw_data:
            domain = qna['qna_domain']
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(qna)
        
        logger.info(f"도메인별 문제 수: {[(k, len(v)) for k, v in domain_groups.items()]}")
        
        # 각 도메인별로 처리
        all_results = {}
        for domain, questions in domain_groups.items():
            if domain not in self.domain_subdomain:
                logger.warning(f"도메인 '{domain}'에 대한 서브도메인 매핑이 없습니다. 건너뜁니다.")
                continue
            
            try:
                updated_questions = self.process_domain_batch(
                    domain, questions, batch_size, model
                )
                all_results[domain] = updated_questions
                
                # 최종 결과 저장
                self.save_domain_results(domain, updated_questions)
                
                # 임시 파일들 정리
                self.cleanup_temp_files(domain)
                
            except Exception as e:
                logger.error(f"{domain} 도메인 처리 중 오류: {e}")
                continue
        
        # 전체 결과 저장
        self.save_all_results(all_results)
        self.save_statistics(all_results)
        
        return all_results
    
    def save_all_results(self, all_results: Dict[str, List[Dict[str, Any]]]):
        """전체 결과 저장"""
        # 통합 결과 저장
        all_questions = []
        for domain, questions in all_results.items():
            all_questions.extend(questions)
        
        all_filepath = os.path.join(self.output_dir, "all_domains_subdomain_classified.json")
        with open(all_filepath, 'w', encoding='utf-8') as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=2)
        
        logger.info(f"전체 결과 저장 완료: {all_filepath}")
        
    def save_statistics(self, all_results: Dict[str, List[Dict[str, Any]]] = None):
        # 통계 정보 저장
        if all_results is None:
            all_results = {}
            for filename in os.listdir(self.output_dir):
                if filename.endswith('_subdomain_classified.json'):
                    domain = filename.replace('_subdomain_classified.json', '')
                    with open(os.path.join(self.output_dir, filename), 'r', encoding='utf-8') as f:
                        all_results[domain] = json.load(f)
        else:
            pass
        
        stats = {}
        for domain, questions in all_results.items():
            subdomain_counts = {}
            for qna in questions:
                subdomain = qna.get('qna_subdomain', '미분류')
                subdomain_counts[subdomain] = subdomain_counts.get(subdomain, 0) + 1
            
            stats[domain] = {
                'total_questions': len(questions),
                'subdomain_distribution': subdomain_counts
            }
            
        stats_filepath = os.path.join(self.output_dir, "classification_statistics.json")
        with open(stats_filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"통계 정보 저장 완료: {stats_filepath}")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Q&A 서브도메인 분류기')
    parser.add_argument('--data_path', type=str, 
                       default='/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/evaluation/eval_data',
                       help='데이터 경로 (파일 또는 디렉토리)')
    parser.add_argument('--model', type=str, default='x-ai/grok-4-fast',
                       help='사용할 모델')
    parser.add_argument('--batch_size', type=int, default=50,
                       help='배치 크기')
    parser.add_argument('--config', type=str, default='./llm_config.ini',
                       help='설정 파일 경로')
    parser.add_argument('--domain', type=str, default=None,
                       help='처리할 특정 도메인 (지정하지 않으면 모든 도메인 처리)')
    
    args = parser.parse_args()
    
    # 분류기 초기화
    classifier = QnASubdomainClassifier(args.config)
    
    # 처리 실행
    try:
        if args.domain:
            # 특정 도메인만 처리
            logger.info(f"'{args.domain}' 도메인만 처리합니다.")
            results = classifier.process_single_domain(
                domain=str(args.domain).strip(),
                data_path=str(args.data_path).strip(),
                model=str(args.model).strip(),
                batch_size=args.batch_size
            )
            logger.info(f"'{args.domain}' 도메인 처리 완료!")
        else:
            # 모든 도메인 처리
            logger.info("모든 도메인을 처리합니다.")
            results = classifier.process_all_domains(
                data_path=str(args.data_path).strip(),
                model=str(args.model).strip(),
                batch_size=args.batch_size
            )
            logger.info("모든 도메인 처리 완료!")
        
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
