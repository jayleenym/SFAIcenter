#!/usr/bin/env python3
"""
QnA 통계 분석 클래스
- workbook_data 하위의 extracted_qna.json 파일들을 분석하여
- qna_domain/qna_type별 통계를 확인
"""

import os
import glob
import re
import json
from collections import defaultdict
from typing import Dict, List, Any, Optional
import logging

from tools.core.utils import JSONHandler

class QnAStatisticsAnalyzer:
    """QnA 통계 분석 클래스"""
    
    # 유효한 Domain Type 정의
    VALID_DOMAINS = {
        '경제', '경영', '회계', '세무', '노무', '통계', 
        '내부통제', '영업', '디지털', '자산운용', '리스크관리', '보험계약', '보상처리'
    }
    
    def __init__(self, base_path: str, logger: Optional[logging.Logger] = None):
        """
        Args:
            base_path: 분석할 데이터가 있는 기본 경로 (workbook_data)
            logger: 로거 인스턴스
        """
        self.base_path = base_path
        self.logger = logger or logging.getLogger(__name__)
        
    def find_extracted_qna_files(self) -> List[str]:
        """workbook_data 하위의 모든 extracted_qna.json 파일을 찾습니다."""
        pattern = os.path.join(self.base_path, "**", "*extracted_qna.json")
        files = glob.glob(pattern, recursive=True)
        
        # merged로 시작하는 파일들과 백업 파일들 제외
        filtered_files = []
        for f in files:
            if (not f.endswith('.bak') and 
                not f.endswith('.backup') and 
                not os.path.basename(f).startswith('merged')):
                filtered_files.append(f)
        
        return filtered_files
        
    def is_valid_domain(self, domain: str) -> bool:
        """도메인이 유효한지 확인합니다."""
        return domain in self.VALID_DOMAINS
        
    def extract_ss_pattern_from_question(self, question_text: str) -> Optional[str]:
        """질문에서 SS0000_q_0000_0000 패턴을 추출합니다."""
        if not question_text:
            return None
        
        # SS0000_q_0000_0000 또는 SS00000_q_0000_0000 패턴 찾기
        pattern = r'SS\d+_q_\d+_\d+'
        matches = re.findall(pattern, question_text)
        return matches[0] if matches else None
        
    def analyze(self) -> Dict[str, Any]:
        """QnA 파일들을 분석하여 통계를 생성합니다."""
        files = self.find_extracted_qna_files()
        self.logger.info(f"분석할 파일 수: {len(files)}")
        
        stats = {
            'total_files': 0,
            'total_qna_items': 0,
            'valid_domain_items': 0,
            'invalid_domain_items': 0,
            'qna_domain_stats': defaultdict(int),
            'qna_type_stats': defaultdict(int),
            'domain_type_combination': defaultdict(lambda: defaultdict(int)),
            'file_stats': [],
            'domain_type_details': defaultdict(lambda: defaultdict(list)),
            'invalid_domain_details': defaultdict(list),
            'ss_pattern_details': defaultdict(list)
        }
        
        for file_path in files:
            self.logger.debug(f"Processing: {file_path}")
            try:
                data = JSONHandler.load(file_path)
            except Exception as e:
                self.logger.error(f"Error loading {file_path}: {e}")
                continue
            
            if data is None:
                continue
                
            stats['total_files'] += 1
            file_id = os.path.basename(file_path).replace('_extracted_qna.json', '')
            file_qna_count = 0
            file_valid_domain_count = 0
            file_invalid_domain_count = 0
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                    
                stats['total_qna_items'] += 1
                file_qna_count += 1
                
                qna_domain = item.get('qna_domain', '')
                qna_type = item.get('qna_type', 'Unknown')
                question_text = item.get('qna_data', {}).get('description', {}).get('question', '')
                
                # 빈 도메인을 ""로 명시
                if not qna_domain or qna_domain.strip() == '':
                    qna_domain = ''
                
                # 도메인 유효성 검사
                if self.is_valid_domain(qna_domain):
                    stats['valid_domain_items'] += 1
                    file_valid_domain_count += 1
                    
                    # 기본 통계
                    stats['qna_domain_stats'][qna_domain] += 1
                    stats['qna_type_stats'][qna_type] += 1
                    
                    # 도메인-타입 조합 통계
                    stats['domain_type_combination'][qna_domain][qna_type] += 1
                    
                    # 상세 정보 저장 (파일별)
                    stats['domain_type_details'][qna_domain][qna_type].append({
                        'file_id': file_id,
                        'title': item.get('title', ''),
                        'chapter': item.get('chapter', ''),
                        'page': item.get('page', ''),
                        'qna_reason': item.get('qna_reason', ''),
                        'question': question_text[:100] + '...' if len(question_text) > 100 else question_text
                    })
                else:
                    stats['invalid_domain_items'] += 1
                    file_invalid_domain_count += 1
                    
                    # SS 패턴 추출
                    ss_pattern = self.extract_ss_pattern_from_question(question_text)
                    
                    # 유효하지 않은 도메인 상세 정보 저장
                    stats['invalid_domain_details'][qna_domain].append({
                        'file_id': file_id,
                        'title': item.get('title', ''),
                        'chapter': item.get('chapter', ''),
                        'page': item.get('page', ''),
                        'qna_reason': item.get('qna_reason', ''),
                        'question': question_text[:100] + '...' if len(question_text) > 100 else question_text,
                        'ss_pattern': ss_pattern,
                        'original_domain': qna_domain,
                        'qna_type': qna_type
                    })
                    
                    # SS 패턴별 그룹화
                    if ss_pattern:
                        stats['ss_pattern_details'][ss_pattern].append({
                            'file_id': file_id,
                            'domain': qna_domain,
                            'type': qna_type,
                            'question': question_text[:100] + '...' if len(question_text) > 100 else question_text
                        })
            
            stats['file_stats'].append({
                'file_id': file_id,
                'file_path': file_path,
                'qna_count': file_qna_count,
                'valid_domain_count': file_valid_domain_count,
                'invalid_domain_count': file_invalid_domain_count
            })
        
        return stats

    def save_report(self, stats: Dict[str, Any], output_file: str):
        """
        상세 보고서를 마크다운 파일로 저장합니다.
        
        Note: 리포트 생성은 tools.stats.QnAReportGenerator로 위임됩니다.
        """
        from tools.stats import QnAReportGenerator
        QnAReportGenerator.save_report(stats, output_file)
        self.logger.info(f"상세 마크다운 보고서가 저장되었습니다: {output_file}")

