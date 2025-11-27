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
    
    def _reorder_fields(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """필드 순서를 지정된 순서로 재정렬"""
        field_order = [
            'file_id', 'tag', 'title', 'cat1_domain', 'cat2_sub', 'cat3_specific',
            'chapter', 'page', 'qna_type', 'domain', 'subdomain', 'is_calculation',
            'classification_reason', 'question', 'options', 'answer', 'explanation'
        ]
        
        ordered_data = []
        for item in data:
            ordered_item = {}
            # 지정된 순서대로 필드 추가
            for field in field_order:
                if field in item:
                    ordered_item[field] = item[field]
            # 순서에 없는 필드도 추가 (혹시 모를 추가 필드 대비)
            for key, value in item.items():
                if key not in ordered_item:
                    ordered_item[key] = value
            ordered_data.append(ordered_item)
        
        return ordered_data

    def fill_domain(self, qna_type: str, model: str, onedrive_path: str, debug: bool = False) -> Dict[str, Any]:
        """
        지정된 QnA 타입의 파일에 대해 Domain/Subdomain 채우기
        
        Args:
            qna_type: QnA 타입 ('multiple', 'short', 'essay')
            model: 사용할 LLM 모델
            onedrive_path: OneDrive 경로
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            
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
                    classification_reason = item.get('classification_reason', '')
                    
                    if (file_id and tag and 
                        domain and subdomain and
                        domain not in ['', '분류실패', 'API호출실패', '파싱실패', 'None'] and
                        subdomain not in ['', '분류실패', 'API호출실패', '파싱실패', 'None']):
                        key = (str(file_id), str(tag))
                        lookup_dict[key] = {
                            'domain': domain,
                            'subdomain': subdomain,
                            'is_calculation': is_calculation,
                            'classification_reason': classification_reason
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
                if existing_data.get('classification_reason'):
                    item['classification_reason'] = existing_data['classification_reason']
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
                    
        # 5. 필드 순서 정렬
        ordered_data = self._reorder_fields(input_data)
        
        # 6. 결과 저장
        output_file = os.path.join(
            onedrive_path,
            'evaluation', 'eval_data', '2_subdomain', 
            f'{output_file_name}_subdomain_classified_ALL.json'
        )
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # debug 모드일 때는 기존 파일과 병합
        if debug and os.path.exists(output_file):
            try:
                existing_data = self.json_handler.load(output_file)
                if isinstance(existing_data, list):
                    # file_id와 tag 기준으로 중복 제거
                    existing_dict = {}
                    for item in existing_data:
                        file_id = item.get('file_id', '')
                        tag = item.get('tag', '')
                        key = (str(file_id), str(tag))
                        existing_dict[key] = item
                    
                    # 새 데이터로 업데이트 (기존 데이터는 유지하되 새 데이터로 덮어쓰기)
                    for item in ordered_data:
                        file_id = item.get('file_id', '')
                        tag = item.get('tag', '')
                        key = (str(file_id), str(tag))
                        existing_dict[key] = item
                    
                    ordered_data = list(existing_dict.values())
                    self.logger.info(f"기존 파일과 병합: 총 {len(ordered_data)}개 항목")
            except Exception as e:
                self.logger.warning(f"기존 파일 병합 실패, 새로 생성: {e}")
        
        self.json_handler.save(ordered_data, output_file, backup=debug, logger=self.logger)
        
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
