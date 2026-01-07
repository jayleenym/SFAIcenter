#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domain/Subdomain 채우기 모듈
- 2_subdomain의 파일들을 읽어서 domain/subdomain/is_calculation 채우기
- 기존 분류 데이터 활용 또는 API 호출
"""

import os
import logging
import sys
from typing import Dict, Any, List

# tools 모듈 import를 위한 경로 설정 (필요한 경우)
# 이 파일이 tools/qna/processing/ 에 위치하므로 상위 디렉토리 접근 가능해야 함
try:
    from .qna_subdomain_classifier import QnASubdomainClassifier
    from .questions_info_manager import QuestionsInfoManager
except ImportError:
    QnASubdomainClassifier = None
    QuestionsInfoManager = None

class DomainFiller:
    """Domain/Subdomain 채우기 클래스"""
    
    def __init__(self, file_manager, json_handler, logger=None):
        self.file_manager = file_manager
        self.json_handler = json_handler
        self.logger = logger or logging.getLogger(__name__)
    
    def _reorder_fields(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """필드 순서를 지정된 순서로 재정렬하고 is_table 필드 추가"""
        field_order = [
            'file_id', 'tag', 'title', 'cat1_domain', 'cat2_sub', 'cat3_specific',
            'chapter', 'page', 'qna_type', 'domain', 'subdomain', 'is_calculation',
            'is_table', 'classification_reason', 'question', 'options', 'answer', 'explanation'
        ]
        
        ordered_data = []
        for item in data:
            # is_table 필드 설정: question에 {tb_ 패턴이 있으면 True
            question = item.get('question', '')
            item['is_table'] = '{tb_' in question
            
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
    
    def _delete_original_file(self, qna_type: str, onedrive_path: str):
        """원본 파일 삭제 (classified_ALL 파일 생성 후)"""
        # mode에 따른 파일명 매핑
        qna_type_file_map = {
            'multiple-choice': 'multiple-choice.json',
            'short-answer': 'short-answer.json',
            'essay': 'essay.json',
            'etc': 'etc.json'
        }
        
        if qna_type not in qna_type_file_map:
            return
        
        subdomain_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '2_subdomain')
        original_file = os.path.join(subdomain_dir, qna_type_file_map[qna_type])
        
        if os.path.exists(original_file):
            try:
                os.remove(original_file)
                self.logger.info(f"✓ 원본 파일 삭제 완료: {qna_type_file_map[qna_type]}")
            except Exception as e:
                self.logger.error(f"원본 파일 삭제 실패: {original_file} - {e}")

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
            'evaluation', 'eval_data', '2_subdomain', f'{input_file_name}.json'
        )
        
        if not os.path.exists(input_file):
            self.logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
            return {'success': False, 'error': f'입력 파일 없음: {input_file}'}
        
        input_data = self.json_handler.load(input_file)
        if not isinstance(input_data, list):
            input_data = []
        
        self.logger.info(f"입력 파일 로드 ({len(input_data)}개): {input_file}")
        
        # 2. questions_info.json에서 기존 분류 정보 로드
        if QuestionsInfoManager is None:
            self.logger.error("QuestionsInfoManager를 import할 수 없습니다.")
            lookup_dict = {}
        else:
            info_manager = QuestionsInfoManager(onedrive_path, self.logger)
            lookup_dict = info_manager.load()
        
        # 3. 데이터 채우기 (기존 데이터 활용)
        matched_count = 0
        unmatched_count = 0
        
        for item in input_data:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            key = (str(file_id), str(tag))
            
            if key in lookup_dict:
                existing_data = lookup_dict[key]
                item['domain'] = existing_data.get('domain', '')
                item['subdomain'] = existing_data.get('subdomain', '')
                item['is_calculation'] = existing_data.get('is_calculation', '')
                if existing_data.get('is_table') is not None:
                    item['is_table'] = existing_data['is_table']
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
                onedrive_path=onedrive_path,
                logger=self.logger
            )
            
            # 1차 분류
            updated_questions, failed_questions = classifier.classify_questions(
                questions=needs_classification,
                model=model,
                batch_size=10
            )
            
            # 실패한 항목 재시도
            if failed_questions:
                self.logger.info(f"실패한 항목 {len(failed_questions)}개 재시도...")
                retry_updated, retry_failed = classifier.classify_questions(
                    questions=failed_questions,
                    model=model,
                    batch_size=10
                )
                # 재시도 결과 병합
                updated_dict_retry = {(item.get('file_id', ''), item.get('tag', '')): item for item in retry_updated}
                for i, item in enumerate(updated_questions):
                    key = (item.get('file_id', ''), item.get('tag', ''))
                    if key in updated_dict_retry:
                        updated_questions[i] = updated_dict_retry[key]
            
            # 결과를 input_data에 반영
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
            f'{output_file_name}_DST.json'
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
        
        # 원본 파일 삭제 (classified_ALL 파일 생성 완료 후)
        self._delete_original_file(input_file_name, onedrive_path)
        
        # questions_info.json 업데이트
        if QuestionsInfoManager is not None:
            info_manager = QuestionsInfoManager(onedrive_path, self.logger)
            updated_count = info_manager.update(ordered_data)
            self.logger.info(f"questions_info.json 업데이트: {updated_count}개 항목")
        
        stats = {
            'total': len(input_data),
            'matched': matched_count,
            'unmatched': unmatched_count,
            'api_called': len(needs_classification) if needs_classification else 0
        }
        
        self.logger.info(f"저장 완료: {output_file}")
        self.logger.info(f"통계: {stats}")
        
        # 통계 파일 저장
        self._save_statistics(ordered_data, qna_type, onedrive_path)
        
        return {
            'success': True,
            'stats': stats,
            'output_file': output_file
        }
    
    def _save_statistics(self, data: List[Dict[str, Any]], qna_type: str, onedrive_path: str):
        """통계 정보를 마크다운 파일로 저장"""
        from datetime import datetime
        
        # 도메인별로 그룹화
        domain_groups = {}
        for item in data:
            domain = item.get('domain', '미분류')
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(item)
        
        # 통계 계산
        stats = {}
        for domain, questions in domain_groups.items():
            subdomain_counts = {}
            for qna in questions:
                subdomain = qna.get('subdomain', '미분류')
                subdomain_counts[subdomain] = subdomain_counts.get(subdomain, 0) + 1
            
            stats[domain] = {
                'total_questions': len(questions),
                'subdomain_distribution': subdomain_counts
            }
        
        # 표시 이름
        mode_display_name = {
            'multiple-choice': 'Multiple Choice',
            'short-answer': 'Short Answer',
            'essay': 'Essay',
            'etc': 'Etc',
        }.get(qna_type, qna_type.title())
        
        # 파일 저장
        subdomain_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '2_subdomain')
        stats_filepath = os.path.join(subdomain_dir, f"STATS_{qna_type}_DST.md")
        
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
        
        self.logger.info(f"통계 파일 저장 완료: {stats_filepath}")
