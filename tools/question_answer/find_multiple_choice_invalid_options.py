#!/usr/bin/env python3
"""
Script to find multiple-choice questions with null or empty options and save to files.
"""

import json
import glob
from collections import defaultdict

def find_multiple_choice_invalid_options(file_path):
    """Find multiple-choice questions with null or empty options in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        invalid_cases = []
        
        for item in data:
            if isinstance(item, dict) and 'qna_type' in item and 'qna_data' in item:
                qna_type = item['qna_type']
                qna_data = item['qna_data']
                
                if isinstance(qna_data, dict) and 'description' in qna_data:
                    description = qna_data['description']
                    
                    if isinstance(description, dict) and 'options' in description:
                        options = description['options']
                        tag = qna_data.get('tag', 'unknown')
                        
                        # multiple-choice인데 options가 null이거나 빈 배열인 경우
                        if qna_type == 'multiple-choice' and (options is None or options == []):
                            invalid_cases.append({
                                'file': file_path,
                                'tag': tag,
                                'answer': description.get('answer', ''),
                                'question': description.get('question', ''),
                                'page': item.get('page', ''),
                                'qna_domain': item.get('qna_domain', ''),
                                'qna_reason': item.get('qna_reason', ''),
                                'options_type': 'null' if options is None else 'empty_array'
                            })
        
        return invalid_cases
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def main():
    """Main function to find all multiple-choice questions with invalid options and save to files."""
    pattern = "data/FIN_workbook/*/Lv5/*_extracted_qna.json"
    json_files = glob.glob(pattern, recursive=True)
    
    print(f"Finding multiple-choice questions with null or empty options in {len(json_files)} files...")
    
    all_invalid_cases = []
    file_stats = defaultdict(int)
    options_type_stats = defaultdict(int)
    
    for file_path in json_files:
        invalid_cases = find_multiple_choice_invalid_options(file_path)
        if invalid_cases:
            file_stats[file_path] = len(invalid_cases)
            all_invalid_cases.extend(invalid_cases)
            for case in invalid_cases:
                options_type_stats[case['options_type']] += 1
    
    # Save detailed results to JSON file
    output_file = "multiple_choice_invalid_options_detailed.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_invalid_cases, f, ensure_ascii=False, indent=2)
    
    # Save summary to text file
    summary_file = "multiple_choice_invalid_options_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("MULTIPLE-CHOICE QUESTIONS WITH INVALID OPTIONS - SUMMARY REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total multiple-choice questions with invalid options: {len(all_invalid_cases)}\n\n")
        
        f.write("By options type:\n")
        f.write(f"  null: {options_type_stats['null']}\n")
        f.write(f"  empty array ([]): {options_type_stats['empty_array']}\n\n")
        
        if all_invalid_cases:
            # Group by domain
            domain_counts = defaultdict(int)
            for case in all_invalid_cases:
                domain_counts[case['qna_domain']] += 1
            
            f.write("By domain:\n")
            for domain, count in sorted(domain_counts.items()):
                f.write(f"  {domain}: {count}\n")
            
            f.write(f"\nFiles with issues: {len(file_stats)}\n")
            for file_path, count in sorted(file_stats.items()):
                f.write(f"  {file_path}: {count}\n")
            
            # Show first 30 examples
            f.write(f"\nFirst 30 examples:\n")
            f.write("-" * 50 + "\n")
            for i, case in enumerate(all_invalid_cases[:30], 1):
                f.write(f"{i}. {case['tag']} (page {case['page']}, {case['qna_domain']})\n")
                f.write(f"   File: {case['file']}\n")
                f.write(f"   Answer: {case['answer']}\n")
                f.write(f"   Options type: {case['options_type']}\n")
                f.write(f"   Question: {case['question'][:200]}{'...' if len(case['question']) > 200 else ''}\n")
                f.write(f"   Reason: {case['qna_reason']}\n\n")
        else:
            f.write("No multiple-choice questions with invalid options found!\n")
    
    print(f"\nResults saved to:")
    print(f"  - {output_file} (detailed JSON data)")
    print(f"  - {summary_file} (summary report)")
    print(f"\nTotal cases found: {len(all_invalid_cases)}")
    print(f"  - null options: {options_type_stats['null']}")
    print(f"  - empty array options: {options_type_stats['empty_array']}")

if __name__ == "__main__":
    main()
