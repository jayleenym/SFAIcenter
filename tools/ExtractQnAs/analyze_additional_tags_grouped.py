#!/usr/bin/env python3
"""
Script to analyze extracted QnA JSON files and find entries that have 
additional_tags_found but empty additional_tag_data.
Groups multiple tags for the same question into a single entry.
Creates a report of entries that need empty QnA data in SS0000_q_0000_0000 format.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

def extract_file_id_from_filename(filename: str) -> str:
    """Extract file ID from filename like SS0419_extracted_qna.json -> SS0419"""
    match = re.match(r'(SS\d+)_extracted_qna\.json', filename)
    if match:
        return match.group(1)
    return "SS0000"

def extract_page_from_tag(tag: str) -> int:
    """Extract page number from tag like {tb_0233_0001} -> 233"""
    # Remove curly braces and extract the middle number
    clean_tag = tag.strip('{}')
    parts = clean_tag.split('_')
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None

def find_min_page_per_file(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Find the minimum page number for each file_id from additional_tags.
    
    Args:
        data: List of entries from the JSON report
        
    Returns:
        Dictionary with file_id as key and min page info as value
    """
    file_min_pages = defaultdict(lambda: {'min_page': float('inf'), 'entries': []})
    
    for entry in data:
        file_id = entry['file_id']
        additional_tags = entry['additional_tags']
        
        # Extract page numbers from all tags in this entry
        page_numbers = []
        for tag in additional_tags:
            page_num = extract_page_from_tag(tag)
            if page_num is not None:
                page_numbers.append(page_num)
        
        # If we found any page numbers, check if any is smaller than current min
        if page_numbers:
            min_page_in_entry = min(page_numbers)
            
            if min_page_in_entry < file_min_pages[file_id]['min_page']:
                file_min_pages[file_id]['min_page'] = min_page_in_entry
                file_min_pages[file_id]['entries'] = [entry]
            elif min_page_in_entry == file_min_pages[file_id]['min_page']:
                file_min_pages[file_id]['entries'].append(entry)
    
    # Convert defaultdict to regular dict and filter out files with no valid pages
    result = {}
    for file_id, info in file_min_pages.items():
        if info['min_page'] != float('inf'):
            result[file_id] = {
                'min_page': info['min_page'],
                'entry_count': len(info['entries']),
                'sample_entries': info['entries'][:3]  # Show first 3 entries as examples
            }
    
    return result

def analyze_qna_entry(entry: Dict[str, Any], file_id: str, entry_index: int) -> Dict[str, Any]:
    """Analyze a single QnA entry and return info about missing additional_tag_data"""
    additional_tags_found = entry.get("additional_tags_found", [])
    additional_tag_data = entry.get("additional_tag_data", [])
    
    # If there are additional tags found but no corresponding data
    if additional_tags_found and not additional_tag_data:
        return {
            "file_id": file_id,
            "entry_index": entry_index,
            "main_tag": entry.get("qna_data", {}).get("tag", ""),
            "page": entry.get("page", ""),
            "question_number": entry.get("qna_data", {}).get("description", {}).get("number", ""),
            "additional_tags": additional_tags_found,  # Keep as list
            "question_preview": entry.get("qna_data", {}).get("description", {}).get("question", "")[:100] + "..." if len(entry.get("qna_data", {}).get("description", {}).get("question", "")) > 100 else entry.get("qna_data", {}).get("description", {}).get("question", ""),
            "suggested_empty_tags": [tag.strip('{}') for tag in additional_tags_found]
        }
    
    return None

def analyze_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Analyze a single JSON file and return missing additional_tag_data entries"""
    try:
        print(f"Analyzing: {file_path.name}")
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract file ID from filename
        file_id = extract_file_id_from_filename(file_path.name)
        
        # Analyze each entry
        missing_entries = []
        
        for i, entry in enumerate(data):
            entry_missing = analyze_qna_entry(entry, file_id, i)
            if entry_missing:
                missing_entries.append(entry_missing)
        
        if missing_entries:
            print(f"  Found {len(missing_entries)} entries with missing additional_tag_data")
        else:
            print(f"  No missing additional_tag_data found")
        
        return missing_entries
            
    except Exception as e:
        print(f"  ✗ Error analyzing {file_path.name}: {str(e)}")
        return []

def main():
    """Main function to analyze all extracted QnA files"""
    # Directory containing the extracted QnA files
    cycle = sys.argv[1]
    extracted_dir = Path(f"/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/{cycle}C/extracted")
    
    if not extracted_dir.exists():
        print(f"Error: Directory {extracted_dir} does not exist")
        return
    
    # Find all extracted QnA JSON files
    json_files = list(extracted_dir.glob("*_extracted_qna.json"))
    
    if not json_files:
        print("No extracted QnA JSON files found")
        return
    
    print(f"Found {len(json_files)} extracted QnA files")
    print("=" * 80)
    
    # Analyze each file
    all_missing_entries = []
    files_with_missing = 0
    
    for json_file in sorted(json_files):
        missing_entries = analyze_json_file(json_file)
        if missing_entries:
            all_missing_entries.extend(missing_entries)
            files_with_missing += 1
    
    print("=" * 80)
    print(f"Analysis complete!")
    print(f"Files analyzed: {len(json_files)}")
    print(f"Files with missing additional_tag_data: {files_with_missing}")
    print(f"Total entries needing empty QnA data: {len(all_missing_entries)}")
    
    # Create detailed report
    if all_missing_entries:
        print("\n" + "=" * 80)
        print("DETAILED REPORT (Sample) - Entries needing empty QnA data:")
        print("=" * 80)

        for i, entry in enumerate(all_missing_entries, 1):
            print(f"\n{i}. File: {entry['file_id']}")
            print(f"   Entry Index: {entry['entry_index']}")
            print(f"   Main Tag: {entry['main_tag']}")
            print(f"   Page: {entry['page']}")
            print(f"   Question Number: {entry['question_number']}")
            print(f"   Additional Tags: {entry['additional_tags']}")
            print(f"   Question Preview: {entry['question_preview']}")
            print(f"   Suggested Empty Tags: {entry['suggested_empty_tags']}")
            break
    # Save report to file
    report_file = Path(f"/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/{cycle}C/additional_tags_report_grouped.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(all_missing_entries, f, ensure_ascii=False, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Analyze minimum pages by file
    print("\nAnalyzing minimum pages by file_id...")
    min_pages = find_min_page_per_file(all_missing_entries)
    
    # Create summary statistics
    total_tags = sum(len(entry['additional_tags']) for entry in all_missing_entries)
    print(f"\nSUMMARY STATISTICS:")
    print(f"Files analyzed: {len(json_files)}")
    print(f"Files with missing additional_tag_data: {files_with_missing}")
    print(f"Total entries: {len(all_missing_entries)}")
    print(f"Total additional tags: {total_tags}")
    if len(all_missing_entries) > 0:
        print(f"Average tags per entry: {total_tags / len(all_missing_entries):.2f}")
    else:
        print(f"Average tags per entry: 0")
    
    # Minimum page statistics
    if min_pages:
        all_min_pages = [info['min_page'] for info in min_pages.values()]
        print(f"\nMINIMUM PAGE STATISTICS:")
        print(f"Files with valid page data: {len(min_pages)}")
        print(f"Overall minimum page: {min(all_min_pages):04d}")
        print(f"Overall maximum minimum page: {max(all_min_pages):04d}")
        print(f"Average minimum page: {sum(all_min_pages) / len(all_min_pages):.1f}")
        
        print(f"\nMINIMUM PAGE BY FILE:")
        for file_id in sorted(min_pages.keys()):
            info = min_pages[file_id]
            print(f"  {file_id}: Page {info['min_page']:04d} ({info['entry_count']} entries)")

if __name__ == "__main__":
    main()
