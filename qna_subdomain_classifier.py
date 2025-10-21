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
from typing import List, Dict, Any, Tuple
from tqdm import tqdm
import configparser
from openai import OpenAI

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qna_classification.log', encoding='utf-8'),
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
        self.output_dir = 'evaluation/eval_data/subdomain_results'
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_domain_subdomain(self) -> Dict[str, List[str]]:
        """도메인-서브도메인 매핑 로드"""
        with open('evaluation/eval_data/domain_subdomain.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_multiple_choice_data(self, data_path: str) -> List[Dict[str, Any]]:
        """객관식 문제 데이터 로드"""
        logger.info(f"데이터 로딩 중: {data_path}")
        
        if os.path.isfile(data_path):
            # 단일 파일인 경우
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 디렉토리인 경우 모든 JSON 파일 로드
            json_files = []
            for root, _, files in os.walk(data_path):
                for f in files:
                    if f.endswith(".json") and 'merged' not in f:
                        json_files.append(os.path.join(root, f))
            
            all_data = []
            for file_path in tqdm(json_files, desc="파일 로딩"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            all_data.extend(data)
                        else:
                            all_data.append(data)
                except Exception as e:
                    logger.error(f"파일 로딩 실패: {file_path} - {e}")
            
            return all_data
    
    def process_qna_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """원시 Q&A 데이터를 처리하여 표준화된 형태로 변환"""
        from tools.evaluation.llm_evaluation_system import replace_tags_in_qna_data
        
        processed_data = []
        
        for item in tqdm(raw_data, desc="데이터 처리"):
            try:
                if not item.get('qna_data') or not item.get('qna_data', {}).get('description', {}).get('answer'):
                    continue
                
                qna_data = replace_tags_in_qna_data(
                    item.get('qna_data'), 
                    item.get('additional_tag_data')
                )
                
                # 객관식 문제만 처리 (선지가 2개 이상)
                if (qna_data.get('description', {}).get('options') is not None and 
                    len(qna_data.get('description', {}).get('options', [])) > 2):
                    
                    processed_qna = {
                        'file_id': item.get('file_id'),
                        'title': item.get('title'),
                        'chapter': item.get('chapter'),
                        'qna_id': qna_data.get('tag'),
                        'qna_domain': item.get('qna_domain'),
                        'qna_subdomain': "",
                        'qna_reason': item.get('qna_reason'),
                        'qna_question': qna_data.get('description', {}).get('question'),
                        'qna_answer': qna_data.get('description', {}).get('answer'),
                        'qna_options': qna_data.get('description', {}).get('options'),
                        'qna_explanation': qna_data.get('description', {}).get('explanation')
                    }
                    processed_data.append(processed_qna)
                    
            except Exception as e:
                logger.error(f"데이터 처리 실패: {item.get('file_id', 'unknown')} - {e}")
                continue
        
        logger.info(f"처리된 객관식 문제 수: {len(processed_data)}")
        return processed_data
    
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

[
{{
  "qna_id": "문제ID",
  "category_detail": "선택된_서브도메인명",
  "reason": "간단한 이유 (문제의 핵심 키워드와 근거 중심으로)"
}},
{{
  "qna_id": "문제ID",
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
            single_prompt = f"""
문제 ID: {qna['qna_id']}
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
                           classifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Q&A 데이터에 서브도메인 분류 결과 업데이트"""
        # qna_id를 키로 하는 딕셔너리 생성
        classification_dict = {item['qna_id']: item for item in classifications}
        
        updated_questions = []
        for qna in questions:
            qna_id = qna['qna_id']
            if qna_id in classification_dict:
                qna['qna_subdomain'] = classification_dict[qna_id]['category_detail']
                qna['qna_subdomain_reason'] = classification_dict[qna_id]['reason']
            else:
                logger.warning(f"분류 결과를 찾을 수 없음: {qna_id}")
                qna['qna_subdomain'] = "분류실패"
                qna['qna_subdomain_reason'] = "API 응답에서 해당 문제를 찾을 수 없음"
            
            updated_questions.append(qna)
        
        return updated_questions
    
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
                # 파싱 실패한 경우 기본값으로 설정
                for qna in batch:
                    qna['qna_subdomain'] = "파싱실패"
                    qna['qna_subdomain_reason'] = "API 응답 파싱에 실패했습니다"
                all_updated_questions.extend(batch)
                continue
            
            # Q&A 데이터 업데이트
            updated_batch = self.update_qna_subdomain(batch, classifications)
            all_updated_questions.extend(updated_batch)
            
            # API 호출 간격 조절
            time.sleep(1)
            
            # 중간 결과 저장
            if batch_num % 5 == 0:  # 5배치마다 중간 저장
                self.save_domain_results(domain, all_updated_questions, f"_batch_{batch_num}")
        
        logger.info(f"{domain} 도메인 처리 완료 - {len(all_updated_questions)}개 문제")
        return all_updated_questions
    
    def save_domain_results(self, domain: str, questions: List[Dict[str, Any]], suffix: str = ""):
        """도메인별 결과 저장"""
        filename = f"{domain}_subdomain_classified{suffix}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{domain} 결과 저장 완료: {filepath}")
    
    def process_all_domains(self, data_path: str, model: str = "x-ai/grok-4-fast", 
                          batch_size: int = 50):
        """모든 도메인 처리"""
        # 데이터 로드 및 처리
        raw_data = self.load_multiple_choice_data(data_path)
        processed_data = self.process_qna_data(raw_data)
        
        # 도메인별로 그룹화
        domain_groups = {}
        for qna in processed_data:
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
                
            except Exception as e:
                logger.error(f"{domain} 도메인 처리 중 오류: {e}")
                continue
        
        # 전체 결과 저장
        self.save_all_results(all_results)
        
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
        
        # 통계 정보 저장
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
                       default='/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/data/FIN_workbook',
                       help='데이터 경로 (파일 또는 디렉토리)')
    parser.add_argument('--model', type=str, default='x-ai/grok-4-fast',
                       help='사용할 모델')
    parser.add_argument('--batch_size', type=int, default=50,
                       help='배치 크기')
    parser.add_argument('--config', type=str, default='./llm_config.ini',
                       help='설정 파일 경로')
    
    args = parser.parse_args()
    
    # 분류기 초기화
    classifier = QnASubdomainClassifier(args.config)
    
    # 처리 실행
    try:
        results = classifier.process_all_domains(
            data_path=args.data_path,
            model=args.model,
            batch_size=args.batch_size
        )
        
        logger.info("모든 도메인 처리 완료!")
        
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
