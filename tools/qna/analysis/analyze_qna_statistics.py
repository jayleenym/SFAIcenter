#!/usr/bin/env python3
"""
QnA 통계 분석 스크립트
- statistics_analyzer.py의 래퍼
"""

import os
import sys

# tools 모듈 import를 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # analysis -> qna -> tools -> root
sys.path.insert(0, _temp_tools_dir)

from tools import ONEDRIVE_PATH, PROJECT_ROOT_PATH
from tools.qna.analysis.statistics_analyzer import QnAStatisticsAnalyzer

def main():
    """메인 함수"""
    # 경로 설정
    try:
        base_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data')
        txt_output_file = os.path.join(PROJECT_ROOT_PATH, 'STATS_qna.md')
    except ImportError:
        # fallback
        base_path = os.path.expanduser("~/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/workbook_data")
        txt_output_file = "STATS_qna.md"
    
    print("🔍 workbook_data 하위의 extracted_qna.json 파일들을 찾는 중...")
    
    analyzer = QnAStatisticsAnalyzer(base_path)
    files = analyzer.find_extracted_qna_files()
    
    if not files:
        print("❌ extracted_qna.json 파일을 찾을 수 없습니다.")
        return
    
    print(f"✅ {len(files)}개의 파일을 찾았습니다.")
    
    print("\n📊 QnA 통계 분석을 시작합니다...")
    stats = analyzer.analyze()
    
    # 통계 출력 (간단하게)
    print(f"총 QnA 항목 수: {stats['total_qna_items']:,}")
    print(f"유효한 도메인 항목: {stats['valid_domain_items']:,}")
    
    # 마크다운 상세 보고서 저장
    analyzer.save_report(stats, txt_output_file)

if __name__ == "__main__":
    main()
