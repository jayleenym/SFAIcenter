#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4단계: Domain/Subdomain 분류
"""

import os
import sys
import logging
import shutil
from typing import Dict, Any
from ..base import PipelineBase
from ..config import PROJECT_ROOT_PATH, SFAICENTER_PATH

# qna processing 모듈 import (tools 폴더에서)
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(os.path.dirname(current_dir))  # steps -> pipeline -> tools
sys.path.insert(0, tools_dir)
try:
    from qna.processing.qna_subdomain_classifier import QnASubdomainClassifier
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
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, qna_type: str = 'multiple', model: str = 'x-ai/grok-4-fast') -> Dict[str, Any]:
        """
        4단계: domain/subdomain/classification_reason/is_calculation 빈칸 채우기
        - openrouter 사용해서 호출
        - 이때 분류실패/API호출실패 등 결과물은 따로 저장해서 한 번 더 처리
        - 만약 이미 {qtype}_subdomain_classified_ALL 파일이 있다면, 기존의 file_id와 tag를 비교하여 채워넣기
        """
        self.logger.info(f"=== 4단계: Domain/Subdomain 분류 (QnA Type: {qna_type}) ===")
        
        # 로깅 설정
        self._setup_step_logging('domain_subdomain')
        
        try:
            if QnASubdomainClassifier is None:
                self.logger.error("QnASubdomainClassifier를 import할 수 없습니다.")
                return {'success': False, 'error': 'QnASubdomainClassifier import 실패'}
            
            # qna_type을 파일명으로 변환 (Step 3에서 저장하는 파일명과 일치)
            file_name_map = {
                'multiple': 'multiple-choice',
                'short': 'short-answer',
                'essay': 'essay'
            }
            file_name = file_name_map.get(qna_type, qna_type)
            
            # 입력 파일 경로
            input_file = os.path.join(
                self.onedrive_path,
                f'evaluation/eval_data/1_filter_with_tags/{file_name}.json'
            )
            
            if not os.path.exists(input_file):
                self.logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
                return {'success': False, 'error': f'입력 파일 없음: {input_file}'}
            
            # 기존 분류 파일 확인
            existing_file = os.path.join(
                self.onedrive_path,
                f'evaluation/eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json'
            )
            
            # 전체 결과 파일 경로
            all_results_file = os.path.join(
                self.onedrive_path,
                f'evaluation/eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json'
            )
            
            # 기존 파일이 있으면 먼저 채워넣기
            existing_results_data = []
            if os.path.exists(existing_file) and load_json_file and create_lookup_dict and fill_multiple_choice_data:
                self.logger.info(f"기존 분류 파일 발견: {existing_file}")
                self.logger.info("기존 데이터로 빈칸 채우기 중...")
                
                try:
                    source_data = load_json_file(existing_file)
                    multiple_choice_data = load_json_file(input_file)
                    lookup_dict = create_lookup_dict(source_data)
                    updated_data, stats = fill_multiple_choice_data(multiple_choice_data, lookup_dict)
                    
                    # 업데이트된 데이터 저장
                    os.makedirs(os.path.dirname(all_results_file), exist_ok=True)
                    self.json_handler.save(updated_data, all_results_file)
                    
                    self.logger.info(f"기존 데이터로 채워넣기 완료: {stats}")
                    existing_results_data = updated_data
                except Exception as e:
                    self.logger.error(f"기존 데이터 채우기 오류: {e}")
            
            # 기존 파일이 있으면 백업
            if os.path.exists(all_results_file) and not existing_results_data:
                try:
                    existing_results_data = self.json_handler.load(all_results_file)
                    if not isinstance(existing_results_data, list):
                        existing_results_data = []
                    # 백업 파일 생성
                    backup_file = all_results_file + '.bak'
                    shutil.copy2(all_results_file, backup_file)
                    self.logger.info(f"기존 파일 백업: {len(existing_results_data)}개 항목 → {backup_file}")
                except Exception as e:
                    self.logger.warning(f"기존 파일 백업 실패: {e}")
            
            # 입력 데이터 로드
            input_data = self.json_handler.load(input_file)
            if not isinstance(input_data, list):
                input_data = []
            
            # 이미 분류된 항목 필터링 (기존 파일에서)
            already_classified_keys = set()
            if existing_results_data:
                for item in existing_results_data:
                    file_id = item.get('file_id', '')
                    tag = item.get('tag', '')
                    domain = item.get('domain', '').strip()
                    subdomain = item.get('subdomain', '').strip()
                    # 이미 분류되어 있고 실패 상태가 아닌 경우
                    if (domain and subdomain and 
                        domain not in ['', '분류실패', 'API호출실패', '파싱실패'] and
                        subdomain not in ['', '분류실패', 'API호출실패', '파싱실패']):
                        already_classified_keys.add((file_id, tag))
            
            # 분류가 필요한 항목만 필터링
            needs_classification = []
            for item in input_data:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                key = (file_id, tag)
                if key not in already_classified_keys:
                    needs_classification.append(item)
            
            self.logger.info(f"입력 데이터: {len(input_data)}개, 이미 분류됨: {len(already_classified_keys)}개, 분류 필요: {len(needs_classification)}개")
            
            # 분류가 필요한 항목이 없으면 종료
            if not needs_classification:
                self.logger.info("모든 항목이 이미 분류되어 있습니다. API 호출을 건너뜁니다.")
                if existing_results_data:
                    self.logger.info(f"기존 분류 파일 유지: {len(existing_results_data)}개 항목")
                    return {
                        'success': True,
                        'results': existing_results_data,
                        'message': '모든 항목이 이미 분류되어 있습니다.'
                    }
            
            # QnASubdomainClassifier로 분류 (필터링된 항목만)
            classifier = QnASubdomainClassifier(config_path=None, mode=qna_type, onedrive_path=self.onedrive_path)
            results = classifier.process_all_questions(
                questions=needs_classification,  # 필터링된 항목만 전달
                model=model,
                batch_size=10
            )
            
            # QnASubdomainClassifier._save_results()가 이미 병합을 수행하므로
            # 여기서는 최종 결과를 확인만 함
            if os.path.exists(all_results_file):
                try:
                    final_results_data = self.json_handler.load(all_results_file)
                    if isinstance(final_results_data, list):
                        self.logger.info(f"최종 결과 확인: {len(final_results_data)}개 항목 (QnASubdomainClassifier가 병합 완료)")
                    else:
                        self.logger.warning(f"최종 결과가 리스트 형식이 아닙니다: {type(final_results_data)}")
                except Exception as e:
                    self.logger.error(f"최종 결과 확인 오류: {e}")
            
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
                        retry_results = classifier.process_all_questions(
                            data_path=temp_failed_file,
                            model=model,
                            batch_size=10
                        )
                        
                        # 재처리 결과는 이미 저장되었으므로 직접 사용
                        retry_results_data = retry_results
                        
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
            
            # Lv2, Lv3_4만 처리한 경우 multiple_classification_Lv234.json으로도 저장
            if qna_type == 'multiple':
                lv2_path = os.path.join(self.onedrive_path, 'evaluation/workbook_data/Lv2')
                lv3_4_path = os.path.join(self.onedrive_path, 'evaluation/workbook_data/Lv3_4')
                if os.path.exists(lv2_path) or os.path.exists(lv3_4_path):
                    all_results_file = os.path.join(
                        self.onedrive_path,
                        f'evaluation/eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json'
                    )
                    if os.path.exists(all_results_file):
                        all_results_data = self.json_handler.load(all_results_file)
                        # multiple_classification_Lv234.json으로도 저장 (기존 파일이 있으면 병합)
                        output_file_lv234 = os.path.join(
                            self.onedrive_path,
                            'evaluation/eval_data/2_subdomain/multiple_classification_Lv234.json'
                        )
                        
                        # 기존 파일이 있으면 병합
                        existing_lv234_data = []
                        if os.path.exists(output_file_lv234):
                            try:
                                existing_lv234_data = self.json_handler.load(output_file_lv234)
                                if not isinstance(existing_lv234_data, list):
                                    existing_lv234_data = []
                                self.logger.info(f"기존 multiple_classification_Lv234.json 발견: {len(existing_lv234_data)}개 항목 로드")
                            except Exception as e:
                                self.logger.warning(f"기존 multiple_classification_Lv234.json 로드 실패: {e}")
                                existing_lv234_data = []
                        
                        if existing_lv234_data:
                            # 중복 제거: file_id와 tag 기준
                            existing_keys = set()
                            for item in existing_lv234_data:
                                file_id = item.get('file_id', '')
                                tag = item.get('tag', '')
                                existing_keys.add((file_id, tag))
                            
                            # 새 항목 중 중복이 아닌 것만 추가
                            merged_lv234_data = existing_lv234_data.copy()
                            new_count = 0
                            for item in all_results_data:
                                file_id = item.get('file_id', '')
                                tag = item.get('tag', '')
                                key = (file_id, tag)
                                if key not in existing_keys:
                                    merged_lv234_data.append(item)
                                    existing_keys.add(key)
                                    new_count += 1
                            
                            # 병합된 결과 저장
                            self.json_handler.save(merged_lv234_data, output_file_lv234)
                            self.logger.info(f"multiple_classification_Lv234.json 병합: 기존 {len(existing_lv234_data)}개 + 새 {new_count}개 = 총 {len(merged_lv234_data)}개")
                        else:
                            # 새로 저장
                            self.json_handler.save(all_results_data, output_file_lv234)
                            self.logger.info(f"multiple_classification_Lv234.json으로 저장: {len(all_results_data)}개 항목")
            
            self.logger.info("Domain/Subdomain 분류 완료")
            return {
                'success': True,
                'results': results
            }
        except Exception as e:
            self.logger.error(f"Domain/Subdomain 분류 오류: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
    
    def _setup_step_logging(self, step_name: str):
        """단계별 로그 파일 핸들러 설정"""
        log_dir = os.path.join(SFAICENTER_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'step4_{step_name}.log')
        
        # 파일 핸들러 생성 (append 모드)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # 로거에 핸들러 추가
        self.logger.addHandler(file_handler)
        self._step_log_handler = file_handler
        
        self.logger.info(f"로그 파일 생성/추가: {log_file}")
    
    def _remove_step_logging(self):
        """단계별 로그 파일 핸들러 제거"""
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
            self._step_log_handler.close()
            self._step_log_handler = None

