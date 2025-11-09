#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계: Q&A 타입별 분류
"""

import os
from typing import Dict, Any
from ..base import PipelineBase
from qna.qna_processor import QnATypeClassifier


class Step3Classify(PipelineBase):
    """3단계: Q&A 타입별 분류"""
    
    def execute(self, cycle: int) -> Dict[str, Any]:
        """
        3단계: qna_type별 분류
        - multiple/short/essay/etc로 분류 및 필터링
        """
        self.logger.info(f"=== 3단계: Q&A 타입별 분류 (Cycle {cycle}) ===")
        
        extracted_dir = os.path.join(
            self.onedrive_path,
            f'evaluation/workbook_data/{self.file_manager.cycle_path[cycle]}'
        )
        
        output_dir = os.path.join(
            self.onedrive_path,
            f'evaluation/eval_data/1_filter_with_tags'
        )
        os.makedirs(output_dir, exist_ok=True)
        
        # 모든 extracted_qna 파일 찾기
        extracted_files = []
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.endswith('_extracted_qna.json'):
                    extracted_files.append(os.path.join(root, file))
        
        self.logger.info(f"총 {len(extracted_files)}개의 extracted_qna 파일을 찾았습니다.")
        
        # 타입별로 분류
        type_classifier = QnATypeClassifier()
        classified_data = {
            'multiple-choice': [],
            'short-answer': [],
            'essay': [],
            'etc': []
        }
        
        for extracted_file in extracted_files:
            try:
                qna_data = self.json_handler.load(extracted_file)
                
                for qna_item in qna_data:
                    qna_type = qna_item.get('qna_type', 'etc')
                    
                    # 포맷화된 데이터 생성
                    formatted_item = {
                        'file_id': qna_item.get('file_id'),
                        'tag': qna_item.get('qna_data', {}).get('tag', ''),
                        'title': qna_item.get('title'),
                        'cat1_domain': qna_item.get('cat1_domain'),
                        'cat2_sub': qna_item.get('cat2_sub'),
                        'cat3_specific': qna_item.get('cat3_specific'),
                        'chapter': qna_item.get('chapter'),
                        'page': qna_item.get('page'),
                        'qna_type': qna_type,
                        'question': qna_item.get('qna_data', {}).get('description', {}).get('question', ''),
                        'options': qna_item.get('qna_data', {}).get('description', {}).get('options', []),
                        'answer': qna_item.get('qna_data', {}).get('description', {}).get('answer', ''),
                        'explanation': qna_item.get('qna_data', {}).get('description', {}).get('explanation', '')
                    }
                    
                    if qna_type in classified_data:
                        classified_data[qna_type].append(formatted_item)
                    else:
                        classified_data['etc'].append(formatted_item)
                        
            except Exception as e:
                self.logger.error(f"파일 처리 오류 ({extracted_file}): {e}")
        
        # 타입별로 저장
        for qna_type, items in classified_data.items():
            if items:
                output_file = os.path.join(output_dir, f'{qna_type}.json')
                self.json_handler.save(items, output_file)
                self.logger.info(f"{qna_type}: {len(items)}개 저장")
        
        self.logger.info("Q&A 타입별 분류 완료")
        return {
            'success': True,
            'classified_data': {k: len(v) for k, v in classified_data.items()}
        }

