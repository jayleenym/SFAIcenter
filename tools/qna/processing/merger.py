#!/usr/bin/env python3
"""
Q&A 병합 모듈 (Merger)
- extracted_qna.json 파일들을 병합
- Domain별 병합 지원
"""

import os
import json
from typing import Dict, Any, List, Optional
from tools.core.utils import JSONHandler

class QnAMerger:
    """Q&A 병합 클래스"""
    
    def __init__(self, logger=None):
        self.logger = logger
        
    def merge_extracted_qna_files(self, input_dir: str, output_file: str = None) -> Dict[str, Any]:
        """
        지정된 경로의 모든 extracted_qna 파일들을 하나로 합치는 함수
        
        Args:
            input_dir: extracted_qna 파일들이 있는 디렉토리 경로
            output_file: 출력 파일 경로
            
        Returns:
            합쳐진 Q&A 데이터와 통계 정보
        """
        # 모든 extracted_qna 파일 찾기
        extracted_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('_extracted_qna.json') and file != 'merged_extracted_qna.json':
                    extracted_files.append(os.path.join(root, file))
        
        if not extracted_files:
            if self.logger:
                self.logger.warning(f"extracted_qna 파일을 찾을 수 없습니다: {input_dir}")
            return {'merged_data': [], 'statistics': {}}
        
        # 모든 Q&A 데이터를 합칠 리스트
        merged_qna_data = []
        file_stats = {}
        
        for file_path in extracted_files:
            try:
                qna_data = JSONHandler.load(file_path)
                
                if isinstance(qna_data, list):
                    merged_qna_data.extend(qna_data)
                    file_stats[os.path.basename(file_path)] = len(qna_data)
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"파일 읽기 오류 {file_path}: {e}")
        
        # 출력 파일 경로 설정
        if output_file is None:
            output_file = os.path.join(input_dir, 'merged_extracted_qna.json')
        
        # 저장
        JSONHandler.save(merged_qna_data, output_file)
        
        statistics = {
            'total_files_processed': len(extracted_files),
            'total_qna_count': len(merged_qna_data),
            'files_stats': file_stats,
            'output_file': output_file
        }
        
        if self.logger:
            self.logger.info(f"병합 완료: {output_file} (총 {len(merged_qna_data)}개)")
            
        return {
            'merged_data': merged_qna_data,
            'statistics': statistics
        }

    def merge_qna_by_domain(self, input_dir: str, output_dir: str = None) -> Dict[str, Any]:
        """
        Domain별로 extracted_qna 파일들을 분류하여 합치는 함수
        """
        extracted_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('_extracted_qna.json'):
                    extracted_files.append(os.path.join(root, file))
        
        if not extracted_files:
            return {}
        
        domain_data = {}
        
        for file_path in extracted_files:
            try:
                qna_data = JSONHandler.load(file_path)
                
                if isinstance(qna_data, list):
                    for qna_item in qna_data:
                        domain = qna_item.get('qna_domain', 'Unknown')
                        if domain not in domain_data:
                            domain_data[domain] = []
                        domain_data[domain].append(qna_item)
            except Exception:
                pass
        
        if output_dir is None:
            output_dir = os.path.join(input_dir, 'domain_merged')
            
        os.makedirs(output_dir, exist_ok=True)
        
        domain_results = {}
        for domain, qna_list in domain_data.items():
            output_file = os.path.join(output_dir, f"{domain}_merged_qna.json")
            JSONHandler.save(qna_list, output_file)
            
            domain_results[domain] = {
                'file_path': output_file,
                'count': len(qna_list)
            }
            
        return domain_results

