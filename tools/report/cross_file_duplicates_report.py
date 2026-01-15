#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일 간 중복(Cross-File Duplicates) 리포트 생성
- 여러 파일에 동일한 내용으로 존재하는 중복 문제 리포트
"""

from typing import Dict, List, Any

from .markdown_writer import MarkdownWriter


class CrossFileDuplicatesReportGenerator:
    """파일 간 중복 리포트 생성 클래스"""
    
    @classmethod
    def generate_report(cls, all_cross_file_duplicates: Dict[str, Dict[str, List[str]]]) -> str:
        """
        파일 간 중복 데이터를 마크다운 내용으로 생성합니다.
        
        Args:
            all_cross_file_duplicates: {qna_type: {content_key: [file_id_tag, ...]}}
            
        Returns:
            마크다운 문자열
        """
        lines = []
        lines.append("# Cross-File Duplicates Report")
        lines.append("")
        lines.append(f"생성일시: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        lines.append("파일 간 중복된 문제 목록입니다. 각 그룹에서 첫 번째 항목만 `multiple-choice.json` 등에 포함됩니다.")
        lines.append("")
        
        # 전체 통계
        total_groups = sum(len(dups) for dups in all_cross_file_duplicates.values())
        total_duplicates = sum(
            sum(len(items) - 1 for items in dups.values())
            for dups in all_cross_file_duplicates.values()
        )
        
        lines.extend(MarkdownWriter.create_section("요약", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["총 중복 그룹 수", f"{total_groups}개"],
                ["총 제거된 문제 수", f"{total_duplicates}개"],
            ]
        ))
        lines.append("")
        
        if total_groups == 0:
            lines.append("✅ 파일 간 중복이 없습니다!")
            lines.append("")
        else:
            # 타입별 상세
            for qna_type, cross_file_dups in all_cross_file_duplicates.items():
                if not cross_file_dups:
                    continue
                
                type_duplicates = sum(len(items) - 1 for items in cross_file_dups.values())
                    
                lines.extend(MarkdownWriter.create_section(qna_type, level=2))
                lines.append(f"중복 그룹: {len(cross_file_dups)}개, 제거된 문제: {type_duplicates}개")
                lines.append("")
                
                for idx, (content_key, item_keys) in enumerate(cross_file_dups.items(), 1):
                    # 첫 번째 항목은 포함됨 (✓), 나머지는 제외됨 (✗)
                    lines.extend(MarkdownWriter.create_section(f"그룹 {idx}", level=3))
                    lines.append(f"- ✓ `{item_keys[0]}` (포함됨)")
                    for removed_key in item_keys[1:]:
                        lines.append(f"- ✗ `{removed_key}` (제외됨)")
                    lines.append("")
                    
                    # 문제 내용 일부 표시 (content_key에서 추출)
                    question_preview = content_key.split('|')[0][:100]
                    if len(content_key.split('|')[0]) > 100:
                        question_preview += "..."
                    lines.append(f"> {question_preview}")
                    lines.append("")
        
        return '\n'.join(lines)
    
    @classmethod
    def save_report(cls, all_cross_file_duplicates: Dict[str, Dict[str, List[str]]], 
                    output_path: str) -> None:
        """
        파일 간 중복 데이터를 마크다운 리포트로 저장합니다.
        
        Args:
            all_cross_file_duplicates: {qna_type: {content_key: [file_id_tag, ...]}}
            output_path: 리포트 저장 경로
        """
        content = cls.generate_report(all_cross_file_duplicates)
        MarkdownWriter.save(content, output_path)

