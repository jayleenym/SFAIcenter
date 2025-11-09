#!/usr/bin/env python3
"""
Script to verify the reclassification results and show statistics.
"""

import json
import glob
from collections import Counter

def analyze_qna_types(file_path):
    """Analyze QnA types in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        qna_types = []
        for item in data:
            if isinstance(item, dict) and 'qna_type' in item:
                qna_types.append(item['qna_type'])
        
        return Counter(qna_types)
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return Counter()

def main():
    """Main function to analyze all files."""
    # pipeline/config에서 ONEDRIVE_PATH import 시도
    try:
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        sys.path.insert(0, project_root)
        from pipeline.config import ONEDRIVE_PATH
        pattern = os.path.join(ONEDRIVE_PATH, 'evaluation/workbook_data/*/Lv5/*_extracted_qna.json')
    except ImportError:
        # fallback: pipeline이 없는 경우 기본값 사용
        pattern = "evaluation/workbook_data/*/Lv5/*_extracted_qna.json"
    json_files = glob.glob(pattern, recursive=True)
    
    print(f"Analyzing {len(json_files)} files...")
    print("=" * 60)
    
    total_stats = Counter()
    file_stats = []
    
    for file_path in json_files:
        stats = analyze_qna_types(file_path)
        if stats:
            file_stats.append((file_path, stats))
            total_stats.update(stats)
    
    # Print per-file statistics
    for file_path, stats in file_stats:
        if stats:
            print(f"\n{file_path.split('/')[-1]}:")
            for qna_type, count in sorted(stats.items()):
                print(f"  {qna_type}: {count}")
    
    # Print total statistics
    print("\n" + "=" * 60)
    print("TOTAL STATISTICS:")
    print("=" * 60)
    for qna_type, count in sorted(total_stats.items()):
        print(f"{qna_type}: {count}")
    
    total_qna = sum(total_stats.values())
    print(f"\nTotal QnA items: {total_qna}")
    
    # Print percentages
    print("\nPERCENTAGES:")
    print("-" * 30)
    for qna_type, count in sorted(total_stats.items()):
        percentage = (count / total_qna) * 100
        print(f"{qna_type}: {percentage:.1f}%")

if __name__ == "__main__":
    main()
