#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통계 저장 및 집계 유틸리티
- 마크다운 형식 통계 저장
- 통계 집계 및 로깅
"""

import os
from typing import Dict, Any, List


class StatisticsSaver:
    """통계 저장 및 집계 클래스"""
    
    @staticmethod
    def save_statistics_markdown(stats: Dict[str, Any], set_name: str, output_path: str):
        """
        통계 정보를 마크다운 형식으로 저장
        
        Args:
            stats: 집계된 통계 정보
            set_name: 세트 이름 (예: '1st', '2nd')
            output_path: 출력 파일 경로
        """
        lines = []
        lines.append(f"# {set_name} 세트 변형 통계")
        lines.append("")
        lines.append("## 전체 요약")
        lines.append("")
        lines.append("| 항목 | 개수 |")
        lines.append("|------|------|")
        lines.append(f"| 총 문제 수 | {stats['total_questions']} |")
        lines.append(f"| 변형된 문제 | {stats['transformed_count']} |")
        lines.append(f"| 변형되지 않은 문제 | {stats['not_transformed_count']} |")
        lines.append("")
        
        lines.append("## 변형 타입별 통계")
        lines.append("")
        lines.append("| 변형 타입 | 개수 |")
        lines.append("|----------|------|")
        lines.append(f"| pick_abcd | {stats['pick_abcd']} |")
        lines.append(f"| pick_right_2 | {stats['pick_right_2']} |")
        lines.append(f"| pick_right_3 | {stats['pick_right_3']} |")
        lines.append(f"| pick_right_4 | {stats['pick_right_4']} |")
        lines.append(f"| pick_right_5 | {stats['pick_right_5']} |")
        lines.append(f"| pick_wrong_2 | {stats['pick_wrong_2']} |")
        lines.append(f"| pick_wrong_3 | {stats['pick_wrong_3']} |")
        lines.append(f"| pick_wrong_4 | {stats['pick_wrong_4']} |")
        lines.append(f"| pick_wrong_5 | {stats['pick_wrong_5']} |")
        lines.append("")
        
        # pick_right 합계
        pick_right_total = stats['pick_right_2'] + stats['pick_right_3'] + stats['pick_right_4'] + stats['pick_right_5']
        # pick_wrong 합계
        pick_wrong_total = stats['pick_wrong_2'] + stats['pick_wrong_3'] + stats['pick_wrong_4'] + stats['pick_wrong_5']
        
        lines.append("### 변형 타입별 합계")
        lines.append("")
        lines.append("| 변형 타입 | 개수 |")
        lines.append("|----------|------|")
        lines.append(f"| pick_abcd | {stats['pick_abcd']} |")
        lines.append(f"| pick_right (전체) | {pick_right_total} |")
        lines.append(f"| pick_wrong (전체) | {pick_wrong_total} |")
        lines.append("")
        
        lines.append("## 시험지별 상세 통계")
        lines.append("")
        
        for exam_name, exam_stats in stats.get('by_exam', {}).items():
            lines.append(f"### {exam_name}")
            lines.append("")
            lines.append("| 항목 | 개수 |")
            lines.append("|------|------|")
            lines.append(f"| 총 문제 수 | {exam_stats.get('total_questions', 0)} |")
            lines.append(f"| 변형된 문제 | {exam_stats.get('transformed_count', 0)} |")
            lines.append(f"| 변형되지 않은 문제 | {exam_stats.get('not_transformed_count', 0)} |")
            lines.append("")
            lines.append("| 변형 타입 | 개수 |")
            lines.append("|----------|------|")
            lines.append(f"| pick_abcd | {exam_stats.get('pick_abcd', 0)} |")
            lines.append(f"| pick_right_2 | {exam_stats.get('pick_right_2', 0)} |")
            lines.append(f"| pick_right_3 | {exam_stats.get('pick_right_3', 0)} |")
            lines.append(f"| pick_right_4 | {exam_stats.get('pick_right_4', 0)} |")
            lines.append(f"| pick_right_5 | {exam_stats.get('pick_right_5', 0)} |")
            lines.append(f"| pick_wrong_2 | {exam_stats.get('pick_wrong_2', 0)} |")
            lines.append(f"| pick_wrong_3 | {exam_stats.get('pick_wrong_3', 0)} |")
            lines.append(f"| pick_wrong_4 | {exam_stats.get('pick_wrong_4', 0)} |")
            lines.append(f"| pick_wrong_5 | {exam_stats.get('pick_wrong_5', 0)} |")
            lines.append("")
        
        # 마크다운 파일 저장
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    @staticmethod
    def aggregate_set_statistics(set_statistics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        메모리의 모든 시험지 통계를 집계
        
        Args:
            set_statistics: 시험지별 통계 딕셔너리
            
        Returns:
            집계된 통계 정보
        """
        aggregated = {
            'total_questions': 0,
            'transformed_count': 0,
            'not_transformed_count': 0,
            'pick_abcd': 0,
            'pick_right_2': 0,
            'pick_right_3': 0,
            'pick_right_4': 0,
            'pick_right_5': 0,
            'pick_wrong_2': 0,
            'pick_wrong_3': 0,
            'pick_wrong_4': 0,
            'pick_wrong_5': 0,
            'by_exam': {}
        }
        
        for exam_name, stats in set_statistics.items():
            aggregated['by_exam'][exam_name] = stats
            
            # 집계
            aggregated['total_questions'] += stats.get('total_questions', 0)
            aggregated['transformed_count'] += stats.get('transformed_count', 0)
            aggregated['not_transformed_count'] += stats.get('not_transformed_count', 0)
            aggregated['pick_abcd'] += stats.get('pick_abcd', 0)
            aggregated['pick_right_2'] += stats.get('pick_right_2', 0)
            aggregated['pick_right_3'] += stats.get('pick_right_3', 0)
            aggregated['pick_right_4'] += stats.get('pick_right_4', 0)
            aggregated['pick_right_5'] += stats.get('pick_right_5', 0)
            aggregated['pick_wrong_2'] += stats.get('pick_wrong_2', 0)
            aggregated['pick_wrong_3'] += stats.get('pick_wrong_3', 0)
            aggregated['pick_wrong_4'] += stats.get('pick_wrong_4', 0)
            aggregated['pick_wrong_5'] += stats.get('pick_wrong_5', 0)
        
        return aggregated
    
    @staticmethod
    def log_statistics(stats: Dict[str, Any], exam_name: str, logger):
        """
        통계 정보를 로그로 출력
        
        Args:
            stats: 통계 정보
            exam_name: 시험 이름
            logger: 로거 인스턴스
        """
        logger.info(f"\n    [{exam_name}] 변형 통계:")
        logger.info(f"      총 문제 수: {stats['total_questions']}개")
        logger.info(f"      변형된 문제: {stats['transformed_count']}개")
        logger.info(f"      변형되지 않은 문제: {stats['not_transformed_count']}개")
        logger.info(f"      - pick_abcd: {stats['pick_abcd']}개")
        logger.info(f"      - pick_right_2: {stats['pick_right_2']}개")
        logger.info(f"      - pick_right_3: {stats['pick_right_3']}개")
        logger.info(f"      - pick_right_4: {stats['pick_right_4']}개")
        logger.info(f"      - pick_right_5: {stats['pick_right_5']}개")
        logger.info(f"      - pick_wrong_2: {stats['pick_wrong_2']}개")
        logger.info(f"      - pick_wrong_3: {stats['pick_wrong_3']}개")
        logger.info(f"      - pick_wrong_4: {stats['pick_wrong_4']}개")
        logger.info(f"      - pick_wrong_5: {stats['pick_wrong_5']}개")

