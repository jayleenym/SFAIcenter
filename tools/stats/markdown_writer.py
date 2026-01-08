#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 마크다운 생성 유틸리티
- 테이블 생성
- 섹션 생성
- 파일 저장
"""

import os
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional


class MarkdownWriter:
    """마크다운 생성 유틸리티 클래스"""
    
    @staticmethod
    def create_table(headers: List[str], rows: List[List[str]], 
                     alignments: Optional[List[str]] = None) -> List[str]:
        """
        마크다운 테이블 생성
        
        Args:
            headers: 헤더 리스트
            rows: 행 데이터 리스트
            alignments: 정렬 방식 ('left', 'center', 'right')
            
        Returns:
            마크다운 라인 리스트
        """
        lines = []
        
        # 헤더 행
        lines.append("| " + " | ".join(headers) + " |")
        
        # 구분선
        if alignments:
            separators = []
            for align in alignments:
                if align == 'center':
                    separators.append(':------:')
                elif align == 'right':
                    separators.append('------:')
                else:
                    separators.append('------')
            lines.append("|" + "|".join(separators) + "|")
        else:
            lines.append("|" + "|".join(['------'] * len(headers)) + "|")
        
        # 데이터 행
        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        
        return lines
    
    @staticmethod
    def create_section(title: str, level: int = 2) -> List[str]:
        """
        섹션 헤더 생성
        
        Args:
            title: 섹션 제목
            level: 헤더 레벨 (1-6)
            
        Returns:
            마크다운 라인 리스트
        """
        return [f"{'#' * level} {title}", ""]
    
    @staticmethod
    def save(content: str, output_path: str):
        """
        마크다운 내용을 파일로 저장
        
        Args:
            content: 마크다운 내용
            output_path: 저장 경로
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def get_timestamp() -> str:
        """현재 시간 문자열 반환"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def get_domain_stats(data: List[Dict]) -> Dict[str, int]:
        """
        Domain별 통계 계산
        
        Args:
            data: 문제 데이터 리스트
            
        Returns:
            Domain별 문제 수 딕셔너리
        """
        stats = {}
        for item in data:
            domain = item.get('domain', '알 수 없음')
            stats[domain] = stats.get(domain, 0) + 1
        return stats
    
    @staticmethod
    def get_subdomain_stats(data: List[Dict]) -> Dict[str, int]:
        """
        Subdomain별 통계 계산
        
        Args:
            data: 문제 데이터 리스트
            
        Returns:
            "Domain > Subdomain" 형식의 키를 가진 문제 수 딕셔너리
        """
        stats = {}
        for item in data:
            domain = item.get('domain', '알 수 없음')
            subdomain = item.get('subdomain', '알 수 없음')
            key = f"{domain} > {subdomain}"
            stats[key] = stats.get(key, 0) + 1
        return stats
    
    @classmethod
    def generate_domain_table(cls, data: List[Dict], include_ratio: bool = True) -> List[str]:
        """
        Domain별 분포 테이블 생성
        
        Args:
            data: 문제 데이터 리스트
            include_ratio: 비율 포함 여부
            
        Returns:
            마크다운 라인 리스트
        """
        domain_stats = cls.get_domain_stats(data)
        total = len(data)
        
        if include_ratio:
            headers = ["Domain", "문제 수", "비율"]
            rows = []
            for domain, count in sorted(domain_stats.items(), key=lambda x: -x[1]):
                ratio = count / total * 100 if total > 0 else 0
                rows.append([domain, f"{count:,}", f"{ratio:.1f}%"])
        else:
            headers = ["Domain", "문제 수"]
            rows = []
            for domain, count in sorted(domain_stats.items(), key=lambda x: -x[1]):
                rows.append([domain, f"{count:,}"])
        
        return cls.create_table(headers, rows)

