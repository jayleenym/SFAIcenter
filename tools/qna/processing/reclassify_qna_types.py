#!/usr/bin/env python3
"""
Script to reclassify QnA types with corrected multiple-choice criteria.
"""

import json
import os
import glob
import re
import sys
from pathlib import Path

# tools 모듈 import를 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(os.path.dirname(current_dir))  # processing -> qna -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)
from qna.qna_processor import QnATypeClassifier

def analyze_extracted_qna(qna_info: dict):
    """
    Q&A 타입 분류 (QnATypeClassifier 사용)
    """
    return QnATypeClassifier.classify_qna_type(qna_info)

def reclassify_qna_data(data):
    """
    Recursively reclassify QnA types in the data structure.
    """
    changes_made = 0
    
    if isinstance(data, dict):
        # Check if this is a QnA item that needs reclassification
        if ('qna_type' in data and 
            'qna_data' in data and 
            isinstance(data['qna_data'], dict) and
            'description' in data['qna_data'] and
            isinstance(data['qna_data']['description'], dict)):
            
            old_type = data.get('qna_type', '')
            new_type = analyze_extracted_qna(data['qna_data'])
            
            if new_type and new_type != old_type:
                data['qna_type'] = new_type
                changes_made += 1
                print(f"  Reclassified: {data['qna_data'].get('tag', 'unknown')} from '{old_type}' to '{new_type}'")
        
        # Recursively process nested dictionaries
        for key, value in data.items():
            changes_made += reclassify_qna_data(value)
    
    elif isinstance(data, list):
        # Recursively process list items
        for item in data:
            changes_made += reclassify_qna_data(item)
    
    return changes_made

def process_json_file(file_path):
    """
    Process a single JSON file to reclassify QnA types.
    """
    print(f"Processing: {file_path}")
    
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reclassify the data
        changes_made = reclassify_qna_data(data)
        
        if changes_made > 0:
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ Reclassified {changes_made} QnA items")
        else:
            print(f"  - No changes needed")
            
    except Exception as e:
        print(f"  ✗ Error processing {file_path}: {e}")

def main():
    """
    Main function to process all extracted_qna.json files.
    """
    # Find all extracted_qna.json files
    # pipeline/config에서 ONEDRIVE_PATH import 시도
    try:
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        sys.path.insert(0, project_root)
        from tools import ONEDRIVE_PATH
        pattern = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', '*', 'Lv5', '*_extracted_qna.json')
    except ImportError:
        # fallback: pipeline이 없는 경우 기본값 사용
        pattern = "evaluation/workbook_data/*/Lv5/*_extracted_qna.json"
    json_files = glob.glob(pattern, recursive=True)
    
    if not json_files:
        print("No extracted_qna.json files found!")
        return
    
    print(f"Found {len(json_files)} JSON files to process:")
    for file_path in json_files:
        print(f"  - {file_path}")
    
    print("\nReclassifying QnA types with corrected multiple-choice criteria...")
    total_changes = 0
    
    for file_path in json_files:
        process_json_file(file_path)
        print()
    
    print("All files processed!")

if __name__ == "__main__":
    main()
