#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 추출 모듈
- 원본 JSON 파일에서 Q&A 추출하여 _extracted_qna.json 생성
- extraction/batch_extractor.py의 래퍼 (호환성 유지용)
"""

from typing import Dict, Any, List, Optional
from .extraction.batch_extractor import BatchExtractor

class QnAMaker(BatchExtractor):
    """
    Q&A 추출 클래스 (BatchExtractor 상속)
    기존 코드가 QnAMaker를 사용하므로 이름 유지
    """
    
    def process_cycle(self, cycle: Optional[int], levels: List[str], onedrive_path: str, debug: bool = False) -> Dict[str, Any]:
        """
        지정된 사이클과 레벨의 파일들에서 Q&A 추출
        
        Args:
            cycle: 사이클 번호 (None이면 모든 사이클)
            levels: 처리할 레벨 목록
            onedrive_path: OneDrive 경로
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            
        Returns:
            처리 결과 통계
        """
        return self.process_directory(cycle, levels, onedrive_path, debug=debug)
