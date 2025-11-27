#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domain/Subdomain 채우기 모듈
- 1_filter_with_tags의 파일들을 읽어서 domain/subdomain/is_calculation 채우기
- 기존 분류 데이터 활용 또는 API 호출
"""

import os
import glob
import logging
import sys
from typing import Dict, Any, List

# tools 모듈 import를 위한 경로 설정 (필요한 경우)
# 이 파일이 tools/qna/ 에 위치하므로 상위 디렉토리 접근 가능해야 함
try:
    from .processing.qna_subdomain_classifier import QnASubdomainClassifier
except ImportError:
    QnASubdomainClassifier = None

class DomainFiller:
    """Domain/Subdomain 채우기 클래스"""
    
    def __init__(self, file_manager, json_handler, logger=None):
        self.file_manager = file_manager
        self.json_handler = json_handler
        self.logger = logger or logging.getLogger(__name__)

    def fill_domain(self, qna_type: str, model: str, onedrive_path: str) -> Dict[str, Any]:
        """
        지정된 QnA 타입의 파일에 대해 Domain/Subdomain 채우기
        
        Args:
            qna_type: QnA 타입 ('multiple', 'short', 'essay')
            model: 사용할 LLM 모델
            onedrive_path: OneDrive 경로
            
        Returns:
            처리 결과 통계
        """
        if QnASubdomainClassifier is None:
            self.logger.error("QnASubdomainClassifier를 import할 수 없습니다.")
            return {'success': False, 'error': 'QnASubdomainClassifier import 실패'}
        
        # 입력 파일명 매핑
        input_file_name_map = {
            'multiple': 'multiple-choice',
            'short': 'short-answer',
            'essay': 'essay'
        }
        input_file_name = input_file_name_map.get(qna_type, qna_type)
        output_file_name = qna_type
        
        # 1. {qna_type}.json 파일 읽기
        input_file = os.path.join(
            onedrive_path,
            'evaluation', 'eval_data', '1_filter_with_tags', f'{input_file_name}.json'
        )
        
        if not os.path.exists(input_file):
            self.logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
            return {'success': False, 'error': f'입력 파일 없음: {input_file}'}
        
        input_data = self.json_handler.load(input_file)
        if not isinstance(input_data, list):
            input_data = []
        
        self.logger.info(f"입력 파일 로드 ({len(input_data)}개): {input_file}")
        
        # 2. ~_classified_ALL.json 파일들에서 동일한 문제 확인
        subdomain_dir = os.path.join(
            onedrive_path,
            'evaluation', 'eval_data', '2_subdomain'
        )
        all_classified_files = glob.glob(
            os.path.join(subdomain_dir, '*_classified_ALL.json')
        )
        
        # 모든 기존 분류 파일에서 데이터 수집
        lookup_dict = {}
        for classified_file in all_classified_files:
            try:
                existing_data = self.json_handler.load(classified_file)
                if not isinstance(existing_data, list):
                    continue
                
                for item in existing_data:
                    file_id = item.get('file_id', '')
                    tag = item.get('tag', '')
                    domain = str(item.get('domain', '')).strip()
                    subdomain = str(item.get('subdomain', '')).strip()
                    is_calculation = str(item.get('is_calculation', '')).strip()
                    
                    if (file_id and tag and 
                        domain and subdomain and
                        domain not in ['', '분류실패', 'API호출실패', '파싱실패', 'None'] and
                        subdomain not in ['', '분류실패', 'API호출실패', '파싱실패', 'None']):
                        key = (str(file_id), str(tag))
                        lookup_dict[key] = {
                            'domain': domain,
                            'subdomain': subdomain,
                            'is_calculation': is_calculation
                        }
            except Exception:
                pass
        
        # 3. 데이터 채우기 (기존 데이터 활용)
        matched_count = 0
        unmatched_count = 0
        
        for item in input_data:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            key = (str(file_id), str(tag))
            
            if key in lookup_dict:
                existing_data = lookup_dict[key]
                item['domain'] = existing_data['domain']
                item['subdomain'] = existing_data['subdomain']
                item['is_calculation'] = existing_data['is_calculation']
                matched_count += 1
            else:
                if 'domain' not in item: item['domain'] = ''
                if 'subdomain' not in item: item['subdomain'] = ''
                if 'is_calculation' not in item: item['is_calculation'] = ''
                unmatched_count += 1
        
        # 4. 빈칸만 골라서 API 호출
        needs_classification = []
        for item in input_data:
            domain = str(item.get('domain', '')).strip()
            subdomain = str(item.get('subdomain', '')).strip()
            is_calculation = str(item.get('is_calculation', '')).strip()
            
            if not domain or not subdomain or not is_calculation:
                needs_classification.append(item)
        
        if needs_classification:
            self.logger.info(f"API 호출 필요 항목: {len(needs_classification)}개")
            
            classifier = QnASubdomainClassifier(
                config_path=None, 
                mode=qna_type, 
                onedrive_path=onedrive_path,
                logger=self.logger
            )
            
            updated_questions = classifier.process_all_questions(
                questions=needs_classification,
                model=model,
                batch_size=10
            )
            
            updated_dict = {}
            for item in updated_questions:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                key = (str(file_id), str(tag))
                updated_dict[key] = item
            
            for i, item in enumerate(input_data):
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                key = (str(file_id), str(tag))
                if key in updated_dict:
                    updated_item = updated_dict[key]
                    input_data[i]['domain'] = updated_item.get('domain', '')
                    input_data[i]['subdomain'] = updated_item.get('subdomain', '')
                    input_data[i]['is_calculation'] = updated_item.get('is_calculation', '')
                    if 'classification_reason' in updated_item:
                        input_data[i]['classification_reason'] = updated_item.get('classification_reason', '')
        
        # 5. 결과 저장
        output_file = os.path.join(
            onedrive_path,
            'evaluation', 'eval_data', '2_subdomain', 
            f'{output_file_name}_subdomain_classified_ALL.json'
        )
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        self.json_handler.save(input_data, output_file)
        
        stats = {
            'total': len(input_data),
            'matched': matched_count,
            'unmatched': unmatched_count,
            'api_called': len(needs_classification) if needs_classification else 0
        }
        
        self.logger.info(f"저장 완료: {output_file}")
        self.logger.info(f"통계: {stats}")
        
        return {
            'success': True,
            'stats': stats,
            'output_file': output_file
        }
