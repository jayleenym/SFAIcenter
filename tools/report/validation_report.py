#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QnA Validation 리포트 생성
- 중복 검사 결과
- 유효하지 않은 선택지 결과
"""

import os
from datetime import datetime
from typing import Dict, List, Any

from .markdown_writer import MarkdownWriter


class ValidationReportGenerator:
    """QnA Validation 리포트 생성 클래스"""
    
    @classmethod
    def generate_report(cls, validation_results: List[Dict[str, Any]]) -> str:
        """
        validation 결과를 마크다운 내용으로 생성합니다.
        
        Args:
            validation_results: validation 결과 리스트
            
        Returns:
            마크다운 문자열
        """
        lines = []
        lines.append("# QnA 추출 Validation Report")
        lines.append("")
        lines.append(f"생성일시: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        
        # 전체 요약
        total_files = len(validation_results)
        files_with_issues = sum(1 for r in validation_results if r.get('issues'))
        total_duplicates = sum(r.get('duplicates', {}).get('groups', 0) for r in validation_results)
        total_invalid = sum(r.get('invalid_options', {}).get('total', 0) for r in validation_results)
        total_qna = sum(r.get('duplicates', {}).get('total', 0) for r in validation_results)
        
        lines.extend(MarkdownWriter.create_section("요약", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["검사된 파일 수", f"{total_files}개"],
                ["총 QnA 수", f"{total_qna:,}개"],
                ["문제가 있는 파일 수", f"{files_with_issues}개"],
                ["총 중복 그룹 수", f"{total_duplicates}개"],
                ["총 유효하지 않은 선택지 수", f"{total_invalid}개"],
            ]
        ))
        lines.append("")
        
        if files_with_issues == 0:
            lines.append("✅ 모든 파일이 정상입니다!")
            lines.append("")
        else:
            lines.extend(MarkdownWriter.create_section("문제가 있는 파일", level=2))
            
            for result in validation_results:
                if result.get('issues'):
                    file_name = os.path.basename(result.get('file', 'unknown'))
                    lines.extend(MarkdownWriter.create_section(file_name, level=3))
                    
                    for issue in result['issues']:
                        lines.append(f"- ⚠️ {issue}")
                    lines.append("")
                    
                    # 상세 정보
                    details = []
                    if result.get('duplicates', {}).get('groups', 0) > 0:
                        details.append(f"중복 그룹: {result['duplicates']['groups']}개")
                    if result.get('invalid_options', {}).get('empty', 0) > 0:
                        details.append(f"빈 선택지: {result['invalid_options']['empty']}개")
                    if result.get('invalid_options', {}).get('invalid_format', 0) > 0:
                        details.append(f"잘못된 형식: {result['invalid_options']['invalid_format']}개")
                    
                    if details:
                        for detail in details:
                            lines.append(f"  - {detail}")
                        lines.append("")
                    
                    # 중복 그룹별 태그(q_0000_0000) 상세 정보
                    duplicate_details = result.get('duplicates', {}).get('details', [])
                    if duplicate_details:
                        lines.append("  **중복 그룹 상세:**")
                        lines.append("")
                        for group_idx, tags in enumerate(duplicate_details, 1):
                            tags_str = ", ".join(f"`{tag}`" for tag in tags)
                            lines.append(f"  - 그룹 {group_idx}: {tags_str}")
                        lines.append("")
        
        return '\n'.join(lines)
    
    @classmethod
    def save_report(cls, validation_results: List[Dict[str, Any]], output_path: str) -> None:
        """
        validation 결과를 마크다운 리포트로 저장합니다.
        
        Args:
            validation_results: validation 결과 리스트
            output_path: 리포트 저장 경로
        """
        content = cls.generate_report(validation_results)
        MarkdownWriter.save(content, output_path)

