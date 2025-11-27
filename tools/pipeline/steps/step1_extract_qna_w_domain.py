#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1단계: Q&A 추출 및 Domain 분류 (통합)
- 기존 step2, step3, step4를 통합
1. ~_extracted_qna 파일들을 만들고 (qna/make_extracted_qna.py)
2. 거기에서 필터링 조건에 따라 multiple/short-answer/essay/etc 로 구분하고 (qna/classify_qna_type.py)
3. 각각 1_filter_with_tags에 저장해서 (qna/classify_qna_type.py)
4. domain/subdomain/is_calculation 을 채워서 (qna/fill_domain.py)
5. 2_subdomain 폴더에 저장할거야. (qna/fill_domain.py)
"""

import os
import sys
from typing import Dict, Any, Optional, List
from ..base import PipelineBase

# tools 모듈 import를 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(os.path.dirname(current_dir))  # pipeline/steps -> pipeline -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)

# 새로 만든 모듈들 import
from qna.make_extracted_qna import QnAMaker
from qna.classify_qna_type import QnAClassifier
from qna.fill_domain import DomainFiller

class Step1ExtractQnAWDomain(PipelineBase):
    """1단계: Q&A 추출 및 Domain 분류 (통합)"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: Optional[int] = None, levels: List[str] = None, model: str = 'x-ai/grok-4-fast') -> Dict[str, Any]:
        """
        1단계 실행: 추출 -> 분류 -> 도메인 채우기
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클)
            levels: 처리할 레벨 목록 (None이면 ['Lv2', 'Lv3_4', 'Lv5'])
            model: 도메인 분류에 사용할 LLM 모델
        """
        if cycle is None:
            self.logger.info("=== 1단계: Q&A 추출 및 Domain 분류 (모든 사이클) ===")
        else:
            self.logger.info(f"=== 1단계: Q&A 추출 및 Domain 분류 (Cycle {cycle}) ===")
            
        self._setup_step_logging('extract_qna_w_domain', 1)
        
        try:
            if levels is None:
                levels = ['Lv2', 'Lv3_4', 'Lv5']
                
            # 1. Q&A 추출 (make_extracted_qna.py)
            self.logger.info("--- 1. Q&A 추출 시작 ---")
            maker = QnAMaker(self.file_manager, self.json_handler, self.logger)
            extract_result = maker.process_cycle(cycle, levels, self.onedrive_path)
            self.logger.info(f"Q&A 추출 완료: {extract_result}")
            
            # 2-3. 타입별 분류 및 저장 (classify_qna_type.py)
            self.logger.info("--- 2-3. 타입별 분류 시작 ---")
            classifier = QnAClassifier(self.file_manager, self.json_handler, self.logger)
            classify_result = classifier.classify_and_save(cycle, self.onedrive_path)
            self.logger.info(f"타입별 분류 완료: {classify_result}")
            
            # 4-5. Domain/Subdomain 채우기 (fill_domain.py)
            self.logger.info("--- 4-5. Domain/Subdomain 채우기 시작 ---")
            filler = DomainFiller(self.file_manager, self.json_handler, self.logger)
            
            fill_results = {}
            # 분류된 모든 타입에 대해 수행
            for qna_type in classify_result.get('classified_data', {}).keys():
                # etc는 제외할 수 있음 (필요에 따라)
                if qna_type == 'etc':
                    continue
                    
                self.logger.info(f"[{qna_type}] 처리 중...")
                result = filler.fill_domain(qna_type, model, self.onedrive_path)
                fill_results[qna_type] = result
            
            self.logger.info("Domain/Subdomain 채우기 완료")
            
            return {
                'success': True,
                'extract_result': extract_result,
                'classify_result': classify_result,
                'fill_results': {k: v.get('stats', {}) for k, v in fill_results.items()}
            }
            
        except Exception as e:
            self.logger.error(f"1단계 실행 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
        finally:
            self._remove_step_logging()
