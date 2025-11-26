#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4단계: Domain/Subdomain 채우기 (Fill Domain)
- {qna_type}.json 파일 읽기 (multiple-choice, short-answer, essay 등)
- ~_classified_ALL.json 파일들에서 동일한 문제 확인
- 있으면 domain, subdomain, is_calculation 추가
- 없으면 빈 문자열("")로 채우기
- 빈칸만 골라서 API 호출 후 파싱 결과 채워넣기
- {qna_type}_subdomain_classified_ALL.json으로 저장
"""

import os
import sys
import glob
from typing import Dict, Any
from ..base import PipelineBase

# qna processing 모듈 import (tools 폴더에서)
current_dir = os.path.dirname(os.path.abspath(__file__))
# tools 모듈 import를 위한 경로 설정
_temp_tools_dir = os.path.dirname(os.path.dirname(current_dir))  # steps -> pipeline -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)
try:
    from qna.processing.qna_subdomain_classifier import QnASubdomainClassifier
except ImportError:
    QnASubdomainClassifier = None


class Step4FillDomain(PipelineBase):
    """4단계: Domain/Subdomain 채우기"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, qna_type: str = 'multiple', model: str = 'x-ai/grok-4-fast') -> Dict[str, Any]:
        """
        4단계: domain/subdomain/is_calculation 빈칸 채우기
        
        Args:
            qna_type: QnA 타입 (기본값: 'multiple')
            model: 사용할 LLM 모델 (기본값: 'x-ai/grok-4-fast')
            
        Returns:
            처리 결과 딕셔너리
        """
        self.logger.info(f"=== 4단계: Domain/Subdomain 채우기 (QnA Type: {qna_type}) ===")
        
        # 로깅 설정
        self._setup_step_logging('fill_domain', 4)
        
        try:
            if QnASubdomainClassifier is None:
                self.logger.error("QnASubdomainClassifier를 import할 수 없습니다.")
                return {'success': False, 'error': 'QnASubdomainClassifier import 실패'}
            
            # qna_type을 파일명으로 변환
            # 입력 파일명 매핑
            input_file_name_map = {
                'multiple': 'multiple-choice',
                'short': 'short-answer',
                'essay': 'essay'
            }
            input_file_name = input_file_name_map.get(qna_type, qna_type)
            
            # 출력 파일명은 qna_type 그대로 사용 (multiple_subdomain_classified_ALL.json)
            output_file_name = qna_type
            
            # 1. {qna_type}.json 파일 읽기
            input_file = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '1_filter_with_tags', f'{input_file_name}.json'
            )
            
            if not os.path.exists(input_file):
                self.logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
                return {'success': False, 'error': f'입력 파일 없음: {input_file}'}
            
            self.logger.info(f"1. {input_file_name}.json 파일 읽기: {input_file}")
            input_data = self.json_handler.load(input_file)
            if not isinstance(input_data, list):
                input_data = []
            
            self.logger.info(f"   총 {len(input_data)}개 항목 로드")
            
            # 2. ~_classified_ALL.json 파일들에서 동일한 문제 확인
            subdomain_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '2_subdomain'
            )
            all_classified_files = glob.glob(
                os.path.join(subdomain_dir, '*_classified_ALL.json')
            )
            
            self.logger.info(f"2. ~_classified_ALL.json 파일들 확인: {len(all_classified_files)}개 파일")
            for f in all_classified_files:
                self.logger.info(f"   - {os.path.basename(f)}")
            
            # 모든 기존 분류 파일에서 데이터 수집
            lookup_dict = {}  # (file_id, tag) -> {domain, subdomain, is_calculation}
            
            for classified_file in all_classified_files:
                try:
                    existing_data = self.json_handler.load(classified_file)
                    if not isinstance(existing_data, list):
                        existing_data = []
                    
                    for item in existing_data:
                        file_id = item.get('file_id', '')
                        tag = item.get('tag', '')
                        # 문자열로 변환 후 strip (boolean이나 다른 타입일 수 있음)
                        domain = str(item.get('domain', '')).strip()
                        subdomain = str(item.get('subdomain', '')).strip()
                        is_calculation = str(item.get('is_calculation', '')).strip()
                        
                        # 유효한 분류 데이터만 사용
                        if (file_id and tag and 
                            domain and subdomain and
                            domain not in ['', '분류실패', 'API호출실패', '파싱실패', 'None'] and
                            subdomain not in ['', '분류실패', 'API호출실패', '파싱실패', 'None']):
                            key = (str(file_id), str(tag))
                            # 가장 최신 데이터를 유지 (나중에 로드된 파일이 우선)
                            lookup_dict[key] = {
                                'domain': domain,
                                'subdomain': subdomain,
                                'is_calculation': is_calculation
                            }
                except Exception as e:
                    self.logger.warning(f"기존 분류 파일 로드 실패 ({classified_file}): {e}")
            
            self.logger.info(f"   기존 분류 데이터: {len(lookup_dict)}개 항목 발견")
            
            # 3. 있으면 domain, subdomain, is_calculation 추가
            # 4. 없으면 빈 문자열("")로 채우기
            matched_count = 0
            unmatched_count = 0
            
            for item in input_data:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                key = (str(file_id), str(tag))
                
                if key in lookup_dict:
                    # 기존 분류 데이터로 채우기
                    existing_data = lookup_dict[key]
                    item['domain'] = existing_data['domain']
                    item['subdomain'] = existing_data['subdomain']
                    item['is_calculation'] = existing_data['is_calculation']
                    matched_count += 1
                else:
                    # 빈 문자열로 채우기
                    if 'domain' not in item:
                        item['domain'] = ''
                    if 'subdomain' not in item:
                        item['subdomain'] = ''
                    if 'is_calculation' not in item:
                        item['is_calculation'] = ''
                    unmatched_count += 1
            
            self.logger.info(f"3-4. 데이터 채우기 완료: 매칭 {matched_count}개, 빈칸 {unmatched_count}개")
            
            # 5. 빈칸만 골라서 API 호출 후 파싱 결과 채워넣기
            needs_classification = []
            for item in input_data:
                # 문자열로 변환 후 strip (boolean이나 다른 타입일 수 있음)
                domain = str(item.get('domain', '')).strip()
                subdomain = str(item.get('subdomain', '')).strip()
                is_calculation = str(item.get('is_calculation', '')).strip()
                
                # 빈칸이 하나라도 있으면 분류 필요
                if not domain or not subdomain or not is_calculation:
                    needs_classification.append(item)
            
            self.logger.info(f"5. 빈칸 항목: {len(needs_classification)}개")
            
            if needs_classification:
                # QnASubdomainClassifier로 분류
                # mode는 qna_type을 사용 (유효한 모드: 'multiple', 'short', 'essay')
                classifier = QnASubdomainClassifier(
                    config_path=None, 
                    mode=qna_type, 
                    onedrive_path=self.onedrive_path,
                    logger=self.logger  # step 로거 전달
                )
                
                self.logger.info(f"   API 호출 시작 (모델: {model})...")
                updated_questions = classifier.process_all_questions(
                    questions=needs_classification,
                    model=model,
                    batch_size=10
                )
                
                # API 호출 결과를 input_data에 반영
                # updated_questions를 딕셔너리로 변환하여 빠른 조회
                updated_dict = {}
                for item in updated_questions:
                    file_id = item.get('file_id', '')
                    tag = item.get('tag', '')
                    key = (str(file_id), str(tag))
                    updated_dict[key] = item
                
                # input_data에서 해당 항목들을 업데이트
                for i, item in enumerate(input_data):
                    file_id = item.get('file_id', '')
                    tag = item.get('tag', '')
                    key = (str(file_id), str(tag))
                    if key in updated_dict:
                        # domain, subdomain, is_calculation 업데이트
                        updated_item = updated_dict[key]
                        input_data[i]['domain'] = updated_item.get('domain', '')
                        input_data[i]['subdomain'] = updated_item.get('subdomain', '')
                        input_data[i]['is_calculation'] = updated_item.get('is_calculation', '')
                        # classification_reason도 업데이트 (있는 경우)
                        if 'classification_reason' in updated_item:
                            input_data[i]['classification_reason'] = updated_item.get('classification_reason', '')
                
                self.logger.info(f"   API 호출 완료: {len(needs_classification)}개 항목 처리")
            else:
                self.logger.info("   빈칸이 없어 API 호출을 건너뜁니다.")
            
            # 6. {qna_type}_subdomain_classified_ALL.json으로 저장
            # 모든 항목 저장 (matched + API 호출로 새로 분류된 항목)
            output_file = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '2_subdomain', 
                f'{output_file_name}_subdomain_classified_ALL.json'
            )
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            self.logger.info(f"6. 결과 저장: {output_file}")
            self.logger.info(f"   저장 항목: 총 {len(input_data)}개 (matched: {matched_count}개 + 새로 분류: {len(needs_classification) if needs_classification else 0}개)")
            self.json_handler.save(input_data, output_file)
            self.logger.info(f"   저장 완료: {len(input_data)}개 항목")
            
            # 통계 정보
            stats = {
                'total': len(input_data),
                'matched': matched_count,
                'unmatched': unmatched_count,
                'api_called': len(needs_classification) if needs_classification else 0
            }
            
            self.logger.info("=== Domain/Subdomain 채우기 완료 ===")
            self.logger.info(f"통계: {stats}")
            
            return {
                'success': True,
                'results': input_data,
                'stats': stats,
                'output_file': output_file
            }
            
        except Exception as e:
            self.logger.error(f"Domain/Subdomain 채우기 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
    
