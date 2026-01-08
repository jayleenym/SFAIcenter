#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험 통계 리포트 생성
- 시험 통계 마크다운 생성 (STATS_exam.md)
- Remaining 문제 README 생성
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from .markdown_writer import MarkdownWriter


class ExamReportGenerator:
    """시험 관련 리포트 생성 클래스"""
    
    # MarkdownWriter의 유틸리티 메서드를 클래스 메서드로 노출 (하위 호환성)
    get_domain_stats = staticmethod(MarkdownWriter.get_domain_stats)
    get_subdomain_stats = staticmethod(MarkdownWriter.get_subdomain_stats)
    save_markdown = staticmethod(MarkdownWriter.save)
    
    @classmethod
    def generate_remaining_readme(cls, table_data: List[Dict], 
                                   calculation_data: List[Dict], 
                                   others_data: List[Dict]) -> str:
        """
        remaining 폴더용 README.md 내용 생성
        
        Args:
            table_data: 표 해석형 문제 리스트
            calculation_data: 계산형 문제 리스트
            others_data: 일반 객관식 문제 리스트
            
        Returns:
            README.md 내용 문자열
        """
        lines = []
        lines.append("# 남은 문제 데이터 (Remaining Questions)")
        lines.append("")
        lines.append(f"생성일시: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        lines.append("## 개요")
        lines.append("")
        lines.append("이 폴더에는 시험 문제 선정 후 남은 문제들이 포함되어 있습니다.")
        lines.append("추후 문제 보충이나 교체 시 활용할 수 있습니다.")
        lines.append("")
        
        # 파일 구성 요약
        total_count = len(table_data) + len(calculation_data) + len(others_data)
        lines.append("## 파일 구성")
        lines.append("")
        lines.extend(MarkdownWriter.create_table(
            ["파일명", "문제 수", "설명"],
            [
                ["multiple_calculation.json", f"{len(calculation_data):,}", "계산형 문제 (is_calculation=true)"],
                ["multiple_table.json", f"{len(table_data):,}", "표 해석형 문제 (is_table=true)"],
                ["multiple_others.json", f"{len(others_data):,}", "일반 객관식 문제"],
                ["**합계**", f"**{total_count:,}**", ""],
            ]
        ))
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 계산형 문제 통계
        if calculation_data:
            lines.extend(cls._generate_domain_section(
                "multiple_calculation.json (계산형 문제)",
                calculation_data
            ))
        
        # 표 해석형 문제 통계
        if table_data:
            lines.extend(cls._generate_domain_section(
                "multiple_table.json (표 해석형 문제)",
                table_data
            ))
        
        # 일반 객관식 문제 통계 (+ Subdomain 상세)
        if others_data:
            lines.extend(cls._generate_domain_section(
                "multiple_others.json (일반 객관식 문제)",
                others_data,
                include_subdomain=True,
                subdomain_limit=20
            ))
        
        # 활용 방법
        lines.append("## 활용 방법")
        lines.append("")
        lines.append("1. **문제 교체**: 검수 과정에서 부적합 판정된 문제를 이 풀에서 교체")
        lines.append("2. **부족 영역 보충**: 목표 수량에 미달하는 subdomain에서 추가 선정")
        lines.append("3. **시험 확장**: 향후 시험 문제 추가 시 활용")
        lines.append("")
        
        return '\n'.join(lines)
    
    @classmethod
    def _generate_domain_section(cls, title: str, data: List[Dict], 
                                  include_subdomain: bool = False,
                                  subdomain_limit: int = 20) -> List[str]:
        """
        Domain별 분포 섹션 생성
        """
        lines = []
        lines.extend(MarkdownWriter.create_section(title, level=2))
        lines.append(f"총 {len(data):,}문제")
        lines.append("")
        lines.extend(MarkdownWriter.create_section("Domain별 분포", level=3))
        lines.extend(MarkdownWriter.generate_domain_table(data, include_ratio=True))
        lines.append("")
        
        # Subdomain 상세 분포
        if include_subdomain:
            lines.extend(MarkdownWriter.create_section(f"Subdomain별 상세 분포 (상위 {subdomain_limit}개)", level=3))
            
            subdomain_stats = MarkdownWriter.get_subdomain_stats(data)
            rows = []
            for key, count in sorted(subdomain_stats.items(), key=lambda x: -x[1])[:subdomain_limit]:
                parts = key.split(' > ')
                domain = parts[0]
                subdomain = parts[1] if len(parts) > 1 else '알 수 없음'
                rows.append([domain, subdomain, f"{count:,}"])
            
            lines.extend(MarkdownWriter.create_table(
                ["Domain", "Subdomain", "문제 수"],
                rows
            ))
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return lines
    
    @classmethod
    def generate_exam_statistics(cls, exams_config: Dict[str, Any], 
                                  results: Dict[str, int],
                                  exam_data_loader: Callable[[str], Optional[List[Dict]]],
                                  default_questions: int = 1250) -> str:
        """
        시험 통계 마크다운 내용 생성
        
        Args:
            exams_config: exam_config.json에서 로드한 설정
            results: 각 과목별 생성된 문제 수
            exam_data_loader: exam_data를 로드하는 콜백 함수 (exam_name -> List[Dict])
            default_questions: 기본 문제 수
            
        Returns:
            STATS_exam.md 내용 문자열
        """
        lines = []
        lines.append("# 시험문제 통계")
        lines.append("")
        lines.append(f"생성일시: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        
        # 전체 요약
        total_questions = sum(results.values())
        total_target = 0
        lines.extend(MarkdownWriter.create_section("전체 요약", level=2))
        
        summary_rows = []
        for exam_name, exam_info in exams_config.items():
            count = results.get(exam_name, 0)
            target = exam_info.get('exam_questions', default_questions)
            total_target += target
            rate = f"{count/target*100:.1f}%" if target > 0 else "N/A"
            summary_rows.append([exam_name, str(count), str(target), rate])
        
        summary_rows.append([
            "**합계**", 
            f"**{total_questions}**", 
            f"**{total_target}**", 
            f"**{total_questions/total_target*100:.1f}%**"
        ])
        
        lines.extend(MarkdownWriter.create_table(
            ["과목", "문제 수", "목표", "달성률"],
            summary_rows
        ))
        lines.append("")
        
        # 과목별 상세 통계
        for exam_name, exam_info in exams_config.items():
            exam_data = exam_data_loader(exam_name)
            if exam_data is None:
                continue
            
            lines.extend(MarkdownWriter.create_section(exam_name, level=2))
            lines.append(f"총 문제 수: {len(exam_data)}개")
            lines.append("")
            
            # Domain별 통계 수집
            domain_stats = MarkdownWriter.get_domain_stats(exam_data)
            subdomain_stats = {}
            for item in exam_data:
                domain = item.get('domain', '알 수 없음')
                subdomain = item.get('subdomain', '알 수 없음')
                key = f"{domain}/{subdomain}"
                subdomain_stats[key] = subdomain_stats.get(key, 0) + 1
            
            # domain_details가 있는 경우 상세 통계 표시
            domain_details = exam_info.get('domain_details', {})
            if domain_details:
                lines.extend(MarkdownWriter.create_section("Domain/Subdomain별 문제 분포", level=3))
                
                detail_rows = []
                for domain_name, domain_info in domain_details.items():
                    subdomains = domain_info.get('subdomains', {})
                    for subdomain_name, subdomain_info in subdomains.items():
                        target_count = subdomain_info.get('count', 0)
                        key = f"{domain_name}/{subdomain_name}"
                        actual_count = subdomain_stats.get(key, 0)
                        
                        if actual_count >= target_count:
                            status = "✅"
                        elif actual_count > 0:
                            status = "⚠️ 부족"
                        else:
                            status = "❌ 없음"
                        
                        detail_rows.append([domain_name, subdomain_name, str(actual_count), str(target_count), status])
                
                lines.extend(MarkdownWriter.create_table(
                    ["Domain", "Subdomain", "실제", "목표", "상태"],
                    detail_rows
                ))
                lines.append("")
            
            # Domain별 소계
            if domain_stats:
                lines.extend(MarkdownWriter.create_section("Domain별 소계", level=3))
                
                subtotal_rows = []
                for domain_name, count in sorted(domain_stats.items(), key=lambda x: -x[1]):
                    subtotal_rows.append([domain_name, str(count)])
                
                lines.extend(MarkdownWriter.create_table(
                    ["Domain", "문제 수"],
                    subtotal_rows
                ))
                lines.append("")
        
        return '\n'.join(lines)

