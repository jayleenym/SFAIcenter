#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4단계: Domain/Subdomain 분류
"""

import os
import sys
from typing import Dict, Any
from ..base import PipelineBase
from ..config import PROJECT_ROOT_PATH

# evaluation 모듈 import (tools 폴더에서)
tools_dir = os.path.join(PROJECT_ROOT_PATH, 'tools')
sys.path.insert(0, tools_dir)
try:
    from evaluation.qna_subdomain_classifier import QnASubdomainClassifier
    from evaluation.fill_multiple_choice_data import (
        load_json_file, create_lookup_dict, fill_multiple_choice_data
    )
except ImportError:
    QnASubdomainClassifier = None
    load_json_file = None
    create_lookup_dict = None
    fill_multiple_choice_data = None


class Step4DomainSubdomain(PipelineBase):
    """4단계: Domain/Subdomain 분류"""
    
    def execute(self, qna_type: str = 'multiple', model: str = 'x-ai/grok-4-fast') -> Dict[str, Any]:
        """
        4단계: domain/subdomain/classification_reason/is_calculation 빈칸 채우기
        - openrouter 사용해서 호출
        - 이때 분류실패/API호출실패 등 결과물은 따로 저장해서 한 번 더 처리
        - 만약 이미 {qtype}_subdomain_classified_ALL 파일이 있다면, 기존의 file_id와 tag를 비교하여 채워넣기
        """
        self.logger.info(f"=== 4단계: Domain/Subdomain 분류 (QnA Type: {qna_type}) ===")
        
        if QnASubdomainClassifier is None:
            self.logger.error("QnASubdomainClassifier를 import할 수 없습니다.")
            return {'success': False, 'error': 'QnASubdomainClassifier import 실패'}
        
        # 입력 파일 경로
        input_file = os.path.join(
            self.onedrive_path,
            f'evaluation/eval_data/1_filter_with_tags/{qna_type}.json'
        )
        
        if not os.path.exists(input_file):
            self.logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
            return {'success': False, 'error': f'입력 파일 없음: {input_file}'}
        
        # 기존 분류 파일 확인
        existing_file = os.path.join(
            self.onedrive_path,
            f'evaluation/eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json'
        )
        
        # 기존 파일이 있으면 먼저 채워넣기
        if os.path.exists(existing_file) and load_json_file and create_lookup_dict and fill_multiple_choice_data:
            self.logger.info(f"기존 분류 파일 발견: {existing_file}")
            self.logger.info("기존 데이터로 빈칸 채우기 중...")
            
            try:
                source_data = load_json_file(existing_file)
                multiple_choice_data = load_json_file(input_file)
                lookup_dict = create_lookup_dict(source_data)
                updated_data, stats = fill_multiple_choice_data(multiple_choice_data, lookup_dict)
                
                # 업데이트된 데이터 저장
                output_file = os.path.join(
                    self.onedrive_path,
                    f'evaluation/eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json'
                )
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                self.json_handler.save(updated_data, output_file)
                
                self.logger.info(f"기존 데이터로 채워넣기 완료: {stats}")
            except Exception as e:
                self.logger.error(f"기존 데이터 채우기 오류: {e}")
        
        # QnASubdomainClassifier로 분류
        try:
            classifier = QnASubdomainClassifier(config_path=None, mode=qna_type)
            results = classifier.process_all_domains(
                data_path=input_file,
                model=model,
                batch_size=50
            )
            
            # 전체 결과 파일 로드
            all_results_file = os.path.join(
                self.onedrive_path,
                f'evaluation/eval_data/{qna_type}_with_subdomain/all_domains_subdomain_classified.json'
            )
            
            if os.path.exists(all_results_file):
                all_results_data = self.json_handler.load(all_results_file)
                
                # 실패한 항목들 찾기
                failed_items = []
                for item in all_results_data:
                    domain = item.get('domain', '')
                    subdomain = item.get('subdomain', '')
                    if (not domain or domain == '' or 
                        domain in ['분류실패', 'API호출실패', '파싱실패'] or
                        subdomain in ['분류실패', 'API호출실패', '파싱실패']):
                        failed_items.append(item)
                
                if failed_items:
                    self.logger.info(f"실패한 항목 발견: {len(failed_items)}개")
                    
                    # 실패한 항목들을 별도 파일로 저장
                    failed_file = os.path.join(
                        self.onedrive_path,
                        f'evaluation/eval_data/2_subdomain/{qna_type}_failed_items.json'
                    )
                    os.makedirs(os.path.dirname(failed_file), exist_ok=True)
                    self.json_handler.save(failed_items, failed_file)
                    self.logger.info(f"실패한 항목 저장: {failed_file}")
                    
                    # 실패한 항목들을 재처리
                    self.logger.info("실패한 항목 재처리 시작...")
                    try:
                        temp_failed_file = os.path.join(
                            self.onedrive_path,
                            f'evaluation/eval_data/2_subdomain/{qna_type}_failed_items_temp.json'
                        )
                        self.json_handler.save(failed_items, temp_failed_file)
                        
                        # 재처리 실행
                        retry_results = classifier.process_all_domains(
                            data_path=temp_failed_file,
                            model=model,
                            batch_size=50
                        )
                        
                        # 재처리 결과 로드 및 병합
                        retry_results_file = os.path.join(
                            self.onedrive_path,
                            f'evaluation/eval_data/{qna_type}_with_subdomain/all_domains_subdomain_classified.json'
                        )
                        
                        if os.path.exists(retry_results_file):
                            retry_results_data = self.json_handler.load(retry_results_file)
                            
                            # 재처리 결과를 원본 데이터에 병합
                            retry_dict = {}
                            for item in retry_results_data:
                                key = (item.get('file_id', ''), item.get('tag', ''))
                                retry_dict[key] = item
                            
                            updated_count = 0
                            for item in all_results_data:
                                key = (item.get('file_id', ''), item.get('tag', ''))
                                if key in retry_dict:
                                    retry_item = retry_dict[key]
                                    if (retry_item.get('domain', '') and 
                                        retry_item.get('domain', '') not in ['분류실패', 'API호출실패', '파싱실패'] and
                                        retry_item.get('subdomain', '') and 
                                        retry_item.get('subdomain', '') not in ['분류실패', 'API호출실패', '파싱실패']):
                                        item['domain'] = retry_item.get('domain', item.get('domain', ''))
                                        item['subdomain'] = retry_item.get('subdomain', item.get('subdomain', ''))
                                        item['classification_reason'] = retry_item.get('classification_reason', item.get('classification_reason', ''))
                                        item['is_calculation'] = retry_item.get('is_calculation', item.get('is_calculation', False))
                                        updated_count += 1
                            
                            self.logger.info(f"재처리 결과 병합: {updated_count}개 항목 업데이트")
                            
                            # 업데이트된 전체 결과 저장
                            final_output_file = os.path.join(
                                self.onedrive_path,
                                f'evaluation/eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json'
                            )
                            os.makedirs(os.path.dirname(final_output_file), exist_ok=True)
                            self.json_handler.save(all_results_data, final_output_file)
                            self.logger.info(f"업데이트된 전체 결과 저장: {final_output_file}")
                            
                            # 임시 파일 삭제
                            if os.path.exists(temp_failed_file):
                                os.remove(temp_failed_file)
                        
                    except Exception as e:
                        self.logger.error(f"실패한 항목 재처리 오류: {e}")
                else:
                    self.logger.info("실패한 항목이 없습니다.")
            
            self.logger.info("Domain/Subdomain 분류 완료")
            return {
                'success': True,
                'results': results
            }
        except Exception as e:
            self.logger.error(f"Domain/Subdomain 분류 오류: {e}")
            return {'success': False, 'error': str(e)}

