#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1단계: Q&A 추출 및 Domain 분류 (통합)

처리 흐름:
1. ~_extracted_qna 파일들을 만들고 (qna/make_extracted_qna.py)
2. 필터링 조건에 따라 multiple/short-answer/essay/etc 로 구분하고 (qna/classify_qna_type.py)
3. 각각 2_subdomain에 저장해서 (qna/classify_qna_type.py)
4. domain/subdomain/is_calculation 을 채워서 (qna/fill_domain.py)
5. 2_subdomain 폴더에 ~_classified_ALL.json으로 저장 (qna/fill_domain.py)
"""

from typing import Dict, Any, Optional, List
from ..base import PipelineBase

# qna 모듈 import
from tools.qna.extraction.make_extracted_qna import QnAMaker
from tools.qna.processing.organize_qna_by_type import QnAOrganizer
from tools.qna.processing.fill_domain import DomainFiller

class Step1ExtractQnAWDomain(PipelineBase):
    """1단계: Q&A 추출 및 Domain 분류 (통합)"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, cycle: Optional[int] = None, levels: List[str] = None, model: str = 'x-ai/grok-4-fast', debug: bool = False) -> Dict[str, Any]:
        """
        1단계 실행: 추출 -> 분류 -> 도메인 채우기
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클)
            levels: 처리할 레벨 목록 (None이면 ['Lv2', 'Lv3_4', 'Lv5'])
            model: 도메인 분류에 사용할 LLM 모델
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
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
            extract_result = maker.process_cycle(cycle, levels, self.onedrive_path, debug=debug)
            self.logger.info(f"Q&A 추출 완료: {extract_result}")
            
            # 2-3. 타입별 분류 및 저장 (organize_qna_by_type.py)
            self.logger.info("--- 2-3. 타입별 분류 시작 ---")
            organizer = QnAOrganizer(self.file_manager, self.json_handler, self.logger)
            classify_result = organizer.classify_and_save(cycle, self.onedrive_path, debug=debug)
            self.logger.info(f"타입별 분류 완료: {classify_result}")
            
            # 4-5. Domain/Subdomain 채우기 (fill_domain.py)
            self.logger.info("--- 4-5. Domain/Subdomain 채우기 시작 ---")
            filler = DomainFiller(self.file_manager, self.json_handler, self.logger)
            
            fill_results = {}
            # 분류된 모든 타입에 대해 수행
            for qna_type in classify_result.get('classified_data', {}).keys():
                # etc는 제외할 수 있음 (필요에 따라)
                # if qna_type == 'etc':
                    # continue
                    
                self.logger.info(f"[{qna_type}] 처리 중...")
                result = filler.fill_domain(qna_type, model, self.onedrive_path, debug=debug)
                fill_results[qna_type] = result
                
                # 통계 파일 생성
                if result.get('success'):
                    try:
                        from qna.processing.qna_subdomain_classifier import QnASubdomainClassifier
                        classifier = QnASubdomainClassifier(
                            config_path=None,
                            mode=qna_type,
                            onedrive_path=self.onedrive_path,
                            logger=self.logger
                        )
                        classifier.save_statistics()
                        self.logger.info(f"[{qna_type}] 통계 파일 생성 완료")
                    except Exception as e:
                        self.logger.warning(f"[{qna_type}] 통계 파일 생성 실패: {e}")
            
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
