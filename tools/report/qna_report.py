#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QnA 통계 리포트 생성
- QnA 분석 결과를 마크다운으로 저장
"""

import os
from collections import Counter
from datetime import datetime
from typing import Dict, Any, List

from .markdown_writer import MarkdownWriter


class QnAReportGenerator:
    """QnA 통계 리포트 생성 클래스"""
    
    @classmethod
    def save_report(cls, stats: Dict[str, Any], output_file: str):
        """
        상세 보고서를 마크다운 파일로 저장
        
        Args:
            stats: QnAStatisticsAnalyzer.analyze()의 결과
            output_file: 출력 파일 경로
        """
        lines = []
        lines.append("# QnA 통계 분석 상세")
        lines.append("")
        lines.append(f"**생성일시**: {MarkdownWriter.get_timestamp()}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 1. 전체 통계
        lines.extend(MarkdownWriter.create_section("1. 전체 통계", level=2))
        lines.extend(MarkdownWriter.create_table(
            ["항목", "값"],
            [
                ["처리된 파일 수", f"{stats['total_files']:,}개"],
                ["총 QnA 항목 수", f"{stats['total_qna_items']:,}개"],
                ["유효한 도메인 항목", f"{stats['valid_domain_items']:,}개"],
                ["유효하지 않은 도메인 항목", f"{stats['invalid_domain_items']:,}개"],
            ]
        ))
        lines.append("")
        
        # 2. 유효한 도메인별 통계
        lines.extend(MarkdownWriter.create_section("2. 유효한 QnA Domain별 통계", level=2))
        domain_rows = []
        domain_stats = sorted(stats['qna_domain_stats'].items(), key=lambda x: x[1], reverse=True)
        for domain, count in domain_stats:
            percentage = (count / stats['valid_domain_items']) * 100 if stats['valid_domain_items'] > 0 else 0
            domain_rows.append([domain, f"{count:,}개", f"{percentage:.1f}%"])
        lines.extend(MarkdownWriter.create_table(["도메인", "개수", "비율"], domain_rows))
        lines.append("")
        
        # 3. QnA Type별 통계
        lines.extend(MarkdownWriter.create_section("3. QnA Type별 통계", level=2))
        type_rows = []
        type_stats = sorted(stats['qna_type_stats'].items(), key=lambda x: x[1], reverse=True)
        for qna_type, count in type_stats:
            percentage = (count / stats['valid_domain_items']) * 100 if stats['valid_domain_items'] > 0 else 0
            type_rows.append([qna_type, f"{count:,}개", f"{percentage:.1f}%"])
        lines.extend(MarkdownWriter.create_table(["타입", "개수", "비율"], type_rows))
        lines.append("")
        
        # 4. Domain-Type 조합별 통계
        lines.extend(MarkdownWriter.create_section("4. Domain-Type 조합별 통계", level=2))
        for domain in sorted(stats['domain_type_combination'].keys()):
            lines.extend(MarkdownWriter.create_section(domain, level=3))
            combo_rows = []
            type_combinations = sorted(
                stats['domain_type_combination'][domain].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for qna_type, count in type_combinations:
                percentage = (count / stats['qna_domain_stats'][domain]) * 100
                combo_rows.append([qna_type, f"{count:,}개", f"{percentage:.1f}%"])
            lines.extend(MarkdownWriter.create_table(["타입", "개수", "비율"], combo_rows))
            lines.append("")
        
        # 5. 유효하지 않은 도메인 통계
        if stats['invalid_domain_items'] > 0:
            lines.extend(MarkdownWriter.create_section("5. 유효하지 않은 도메인 통계", level=2))
            invalid_rows = []
            invalid_domain_stats = Counter()
            for domain, items in stats['invalid_domain_details'].items():
                invalid_domain_stats[domain] = len(items)
            for domain, count in invalid_domain_stats.most_common():
                percentage = (count / stats['invalid_domain_items']) * 100
                invalid_rows.append([domain, f"{count:,}개", f"{percentage:.1f}%"])
            lines.extend(MarkdownWriter.create_table(["도메인", "개수", "비율"], invalid_rows))
            lines.append("")
            
            # 6. SS 패턴별 분석
            if stats['ss_pattern_details']:
                lines.extend(MarkdownWriter.create_section("6. SS 패턴별 분석 (유효하지 않은 도메인)", level=2))
                for ss_pattern, items in sorted(stats['ss_pattern_details'].items()):
                    lines.extend(MarkdownWriter.create_section(f"{ss_pattern} - {len(items)}개", level=3))
                    for item in items[:5]:
                        lines.append(f"- **파일**: {item['file_id']}, **도메인**: {item['domain']}, **타입**: {item['type']}")
                        lines.append(f"  - 질문: {item['question']}")
                    if len(items) > 5:
                        lines.append(f"\n... 외 {len(items) - 5}개")
                    lines.append("")
        
        # 7. 파일별 통계
        lines.extend(MarkdownWriter.create_section("7. 파일별 통계", level=2))
        file_rows = []
        for file_stat in sorted(stats['file_stats'], key=lambda x: x['file_id']):
            file_rows.append([
                file_stat['file_id'],
                str(file_stat['qna_count']),
                str(file_stat['valid_domain_count']),
                str(file_stat['invalid_domain_count'])
            ])
        lines.extend(MarkdownWriter.create_table(
            ["파일ID", "총QnA", "유효도메인", "무효도메인"],
            file_rows
        ))
        lines.append("")
        
        # 8. 유효하지 않은 도메인 상세 정보
        if stats['invalid_domain_details']:
            lines.extend(MarkdownWriter.create_section("8. 유효하지 않은 도메인 상세 정보", level=2))
            for domain, items in sorted(stats['invalid_domain_details'].items()):
                lines.extend(MarkdownWriter.create_section(f"{domain} - {len(items)}개", level=3))
                for i, item in enumerate(items[:10]):
                    lines.append(f"{i+1}. **파일**: {item['file_id']}, **페이지**: {item['page']}")
                    lines.append(f"   - 제목: {item['title']}")
                    lines.append(f"   - 챕터: {item['chapter']}")
                    lines.append(f"   - 원래 도메인: '{item['original_domain']}'")
                    lines.append(f"   - QnA 타입: {item['qna_type']}")
                    lines.append(f"   - 질문: {item['question']}")
                    if item.get('ss_pattern'):
                        lines.append(f"   - SS패턴: {item['ss_pattern']}")
                    lines.append("")
                if len(items) > 10:
                    lines.append(f"... 외 {len(items) - 10}개\n")
        
        # 9. Domain-Type 조합별 상세 정보
        if 'domain_type_details' in stats and stats['domain_type_details']:
            lines.extend(MarkdownWriter.create_section("9. Domain-Type 조합별 상세 정보", level=2))
            for domain in sorted(stats['domain_type_details'].keys()):
                lines.extend(MarkdownWriter.create_section(domain, level=3))
                for qna_type in sorted(stats['domain_type_details'][domain].keys()):
                    items = stats['domain_type_details'][domain][qna_type]
                    lines.extend(MarkdownWriter.create_section(f"{qna_type} ({len(items)}개)", level=4))
                    
                    detail_rows = []
                    for item in items[:20]:
                        title = item.get('title', '')[:50]
                        chapter = item.get('chapter', '')[:30]
                        detail_rows.append([
                            item.get('file_id', ''),
                            title,
                            chapter,
                            item.get('page', '')
                        ])
                    
                    lines.extend(MarkdownWriter.create_table(
                        ["파일ID", "제목", "챕터", "페이지"],
                        detail_rows
                    ))
                    
                    if len(items) > 20:
                        lines.append(f"\n... 외 {len(items) - 20}개")
                    lines.append("")
        
        # 파일 저장
        MarkdownWriter.save('\n'.join(lines), output_file)

