#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 정리 리포트 생성
- 빈 페이지 삭제 전후 통계를 마크다운으로 저장
"""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from .markdown_writer import MarkdownWriter

if TYPE_CHECKING:
    from tools.data_processing.json_cleaner import CleanupResult, DirectoryCleanupResult, PageStats


class CleanupReportGenerator:
    """JSON 정리 리포트 생성 클래스"""
    
    @classmethod
    def generate_file_report(
        cls, 
        result: "CleanupResult",
        output_path: Optional[Path] = None
    ) -> Path:
        """
        개별 파일 정리 결과 MD 리포트 생성
        
        Args:
            result: 정리 결과
            output_path: 저장 경로 (None이면 원본 파일 옆에 생성)
            
        Returns:
            생성된 MD 파일 경로
        """
        if result.file_path is None:
            return None
        
        if output_path is None:
            output_path = result.file_path.with_suffix('.cleanup_report.md')
        
        lines = []
        
        # 타이틀
        lines.append("# JSON 정리 리포트")
        lines.append("")
        lines.append(f"**생성일시**: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 파일 정보
        lines.extend(MarkdownWriter.create_section("파일 정보", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["파일명", f"`{result.file_path.name}`"],
                ["파일 경로", f"`{result.file_path}`"],
            ]
        ))
        lines.append("")
        
        # 삭제 전 통계
        lines.extend(MarkdownWriter.create_section("삭제 전 통계", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "페이지 수"],
            [
                ["전체 페이지", f"{result.before_stats.total_pages:,}"],
                ["Lv3 페이지", f"{result.before_stats.lv3_pages:,}"],
                ["Lv4 페이지", f"{result.before_stats.lv4_pages:,}"],
            ],
            alignments=['left', 'right']
        ))
        lines.append("")
        lines.append("> **Lv4 페이지**: `type`이 `image`, `table`, `formula`, `etc`인 태그가 포함된 페이지")
        lines.append("")
        
        # 삭제 후 통계
        lines.extend(MarkdownWriter.create_section("삭제 후 통계", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "페이지 수"],
            [
                ["전체 페이지", f"{result.after_stats.total_pages:,}"],
                ["Lv3 페이지", f"{result.after_stats.lv3_pages:,}"],
                ["Lv4 페이지", f"{result.after_stats.lv4_pages:,}"],
            ],
            alignments=['left', 'right']
        ))
        lines.append("")
        
        # 정리 요약
        lines.extend(MarkdownWriter.create_section("정리 요약", level=2))
        removal_rate = (
            result.removed_count / result.original_count * 100 
            if result.original_count > 0 else 0
        )
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["삭제된 빈 페이지 수", f"{result.removed_count:,}"],
                ["삭제 비율", f"{removal_rate:.1f}%"],
            ],
            alignments=['left', 'right']
        ))
        lines.append("")
        
        content = "\n".join(lines)
        MarkdownWriter.save(content, str(output_path))
        
        return output_path
    
    @classmethod
    def generate_directory_report(
        cls,
        directory: Path,
        result: "DirectoryCleanupResult",
        output_path: Optional[Path] = None
    ) -> Path:
        """
        디렉토리 정리 결과 MD 리포트 생성
        
        Args:
            directory: 정리한 디렉토리 경로
            result: 디렉토리 정리 결과
            output_path: 저장 경로 (None이면 디렉토리 내에 생성)
            
        Returns:
            생성된 MD 파일 경로
        """
        directory = Path(directory)
        
        if output_path is None:
            output_path = directory / f"{directory.name}_cleanup_report.md"
        
        before_stats = result.total_before_stats
        after_stats = result.total_after_stats
        
        lines = []
        
        # 타이틀
        lines.append("# JSON 정리 리포트 (디렉토리)")
        lines.append("")
        lines.append(f"**생성일시**: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 디렉토리 정보
        lines.extend(MarkdownWriter.create_section("디렉토리 정보", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["디렉토리명", f"`{directory.name}`"],
                ["디렉토리 경로", f"`{directory}`"],
                ["처리된 파일 수", f"{result.processed_files:,}개"],
            ]
        ))
        lines.append("")
        
        # 삭제 전 전체 통계
        lines.extend(MarkdownWriter.create_section("삭제 전 전체 통계", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "페이지 수"],
            [
                ["전체 페이지", f"{before_stats.total_pages:,}"],
                ["Lv3 페이지", f"{before_stats.lv3_pages:,}"],
                ["Lv4 페이지", f"{before_stats.lv4_pages:,}"],
            ],
            alignments=['left', 'right']
        ))
        lines.append("")
        lines.append("> **Lv4 페이지**: `type`이 `image`, `table`, `formula`, `etc`인 태그가 포함된 페이지")
        lines.append("")
        
        # 삭제 후 전체 통계
        lines.extend(MarkdownWriter.create_section("삭제 후 전체 통계", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "페이지 수"],
            [
                ["전체 페이지", f"{after_stats.total_pages:,}"],
                ["Lv3 페이지", f"{after_stats.lv3_pages:,}"],
                ["Lv4 페이지", f"{after_stats.lv4_pages:,}"],
            ],
            alignments=['left', 'right']
        ))
        lines.append("")
        
        # 정리 요약
        lines.extend(MarkdownWriter.create_section("정리 요약", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["삭제된 총 빈 페이지 수", f"{result.total_removed:,}"],
                ["삭제 비율", f"{result.removal_rate:.1f}%"],
            ],
            alignments=['left', 'right']
        ))
        lines.append("")
        
        # 파일별 상세 정보
        lines.extend(MarkdownWriter.create_section("파일별 상세 정보", level=2))
        
        headers = [
            "파일명", 
            "삭제 전 전체", 
            "삭제 전 Lv4", 
            "삭제 후 Lv4", 
            "삭제 후 Lv3", 
            "삭제 후 전체"
        ]
        rows = []
        
        for file_result in result.file_results:
            if file_result.file_path:
                rows.append([
                    f"`{file_result.file_path.name}`",
                    f"{file_result.before_stats.total_pages:,}",
                    f"{file_result.before_stats.lv4_pages:,}",
                    f"{file_result.after_stats.lv4_pages:,}",
                    f"{file_result.after_stats.lv3_pages:,}",
                    f"{file_result.after_stats.total_pages:,}",
                ])
        
        lines.extend(MarkdownWriter.create_table(
            headers, 
            rows,
            alignments=['left', 'right', 'right', 'right', 'right', 'right']
        ))
        lines.append("")
        
        content = "\n".join(lines)
        MarkdownWriter.save(content, str(output_path))
        
        return output_path

