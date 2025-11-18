#!/usr/bin/env python3
"""
Script to find multiple-choice questions with null or empty options and save to files.
"""

import json, re
import os
import glob
from collections import defaultdict

def find_multiple_choice_invalid_options(file_path):
    """Find multiple-choice questions with invalid options (empty or invalid format) in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        invalid_cases = []
        
        # 파일 이름에 _extracted_qna가 포함되어 있으면 중첩 구조, 그 외에는 평탄화된 구조
        is_nested_structure = '_extracted_qna' in file_path
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # 중첩 구조 처리 (파일 이름에 _extracted_qna가 포함된 경우)
            if is_nested_structure:
                if 'qna_type' in item and 'qna_data' in item:
                    qna_type = item['qna_type']
                    qna_data = item['qna_data']
                    
                    # multiple-choice인 경우만 체크
                    if qna_type != 'multiple-choice':
                        continue
                    
                    # qna_data가 None이거나 dict가 아닌 경우 스킵
                    if not isinstance(qna_data, dict) or 'description' not in qna_data:
                        continue
                    
                    description = qna_data.get('description')
                    
                    # description이 None이거나 dict가 아닌 경우 스킵
                    if not isinstance(description, dict) or 'options' not in description:
                        continue
                    
                    options = description.get('options')
                    tag = qna_data.get('tag', 'unknown')
                    answer = description.get('answer', '')
                    question = description.get('question', '')
                    page = item.get('page', '')
                    domain = item.get('domain', '') or item.get('qna_domain', '')
                    subdomain = item.get('subdomain', '') or item.get('qna_subdomain', '')
                    classification_reason = item.get('classification_reason', '') or item.get('qna_reason', '')
                    is_calculation = item.get('is_calculation', '')
                else:
                    continue
            # 평탄화된 구조 처리 (파일 이름에 _extracted_qna가 없는 경우)
            else:
                if 'options' in item:
                    options = item['options']
                    tag = item.get('tag', 'unknown')
                    answer = item.get('answer', '')
                    question = item.get('question', '')
                    page = item.get('page', '')
                    domain = item.get('domain', '')
                    subdomain = item.get('subdomain', '')
                    classification_reason = item.get('classification_reason', '')
                    is_calculation = item.get('is_calculation', '')
                else:
                    # options가 없는 경우 스킵
                    continue
            
            # Case 1: options가 null이거나 빈 배열인 경우
            if options is None or options == []:
                invalid_cases.append({
                    'file': file_path,
                    'tag': tag,
                    'answer': answer,
                    'question': question,
                    'page': page,
                    'domain': domain,
                    'subdomain': subdomain,
                    'classification_reason': classification_reason,
                    'is_calculation': is_calculation,
                    'invalid_type': 'empty',
                    'options': options,
                    'invalid_options_detail': None
                })
            # Case 2: options가 있지만 ①②③④⑤로 시작하지 않는 경우
            elif isinstance(options, list) and len(options) > 0:
                invalid_options_detail = []
                for i, option in enumerate(options):
                    if option and isinstance(option, str):
                        # ①②③④⑤로 시작하는지 확인 (공백 제거 후)
                        option_stripped = option.strip()
                        if not re.match(r'^[①②③④⑤]', option_stripped):
                            invalid_options_detail.append({
                                'option_index': i,
                                'original_option': option
                            })
                
                # 하나라도 잘못된 형식이면 추가
                if invalid_options_detail:
                    invalid_cases.append({
                        'file': file_path,
                        'tag': tag,
                        'answer': answer,
                        'question': question,
                        'page': page,
                        'domain': domain,
                        'subdomain': subdomain,
                        'classification_reason': classification_reason,
                        'is_calculation': is_calculation,
                        'invalid_type': 'invalid_format',
                        'options': options,
                        'invalid_options_detail': invalid_options_detail
                    })
        
        return invalid_cases
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return []

def main(file_path: str=None):
    """Main function to find all multiple-choice questions with invalid options and save to files."""
    if file_path is None:
        # pipeline/config에서 ONEDRIVE_PATH import 시도
        try:
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            sys.path.insert(0, project_root)
            from pipeline.config import ONEDRIVE_PATH
            pattern = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', '*', 'Lv5', '*_extracted_qna.json')
        except ImportError:
            # fallback: pipeline이 없는 경우 기본값 사용
            pattern = "evaluation/workbook_data/*/Lv5/*_extracted_qna.json"
        json_files = glob.glob(pattern, recursive=True)
        print(f"Finding multiple-choice questions with null or empty options in {len(json_files)} files...")
    else:
        json_files = [file_path]
        print(f"Finding multiple-choice questions with null or empty options in {file_path} file...")
    
    all_invalid_cases = []
    file_stats = defaultdict(int)
    invalid_type_stats = defaultdict(int)
    
    for file_path in json_files:
        invalid_cases = find_multiple_choice_invalid_options(file_path)
        if invalid_cases:
            file_stats[file_path] = len(invalid_cases)
            all_invalid_cases.extend(invalid_cases)
            for case in invalid_cases:
                invalid_type_stats[case['invalid_type']] += 1
    
    # Save detailed results to JSON file
    # 파일명 추출 (플랫폼 독립적)
    if json_files:
        last_file = json_files[-1] if isinstance(json_files, list) else json_files
        file_basename = os.path.basename(last_file).replace('.json', '')
    else:
        file_basename = 'all_files'
    
    # ONEDRIVE_PATH 기반 경로 사용
    try:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        sys.path.insert(0, project_root)
        from pipeline.config import ONEDRIVE_PATH
        output_base = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', 'invalid_options')
    except ImportError:
        # fallback: 현재 디렉토리 기준
        output_base = os.path.join('evaluation', 'eval_data', 'invalid_options')
    
    os.makedirs(output_base, exist_ok=True)
    output_file = os.path.join(output_base, f'invalid_options_detailed_{file_basename}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_invalid_cases, f, ensure_ascii=False, indent=2)
    
    # Save summary to text file
    summary_file = os.path.join(output_base, f'invalid_options_summary_{file_basename}.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("MULTIPLE-CHOICE QUESTIONS WITH INVALID OPTIONS - SUMMARY REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total multiple-choice questions with invalid options: {len(all_invalid_cases)}\n\n")
        
        f.write("By invalid type:\n")
        f.write(f"  empty: {invalid_type_stats['empty']} (options가 null이거나 빈 배열)\n")
        f.write(f"  invalid_format: {invalid_type_stats['invalid_format']} (옵션이 ①②③④⑤로 시작하지 않음)\n\n")
        
        if all_invalid_cases:
            # Group by domain
            domain_counts = defaultdict(int)
            for case in all_invalid_cases:
                domain_counts[case['domain']] += 1
            
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
                f.write(f"{i}. {case['tag']} (page {case['page']}, {case['domain']}")
                if case.get('subdomain'):
                    f.write(f", {case['subdomain']}")
                f.write(f")\n")
                f.write(f"   File: {case['file']}\n")
                f.write(f"   Answer: {case['answer']}\n")
                f.write(f"   Invalid type: {case['invalid_type']}\n")
                if case['invalid_type'] == 'empty':
                    f.write(f"   Options: {case['options']}\n")
                elif case['invalid_type'] == 'invalid_format':
                    f.write(f"   Options: {case['options']}\n")
                    f.write(f"   Invalid options detail:\n")
                    for detail in case.get('invalid_options_detail', []):
                        f.write(f"     - Index {detail['option_index']}: {detail['original_option']}\n")
                f.write(f"   Question: {case['question'][:200]}{'...' if len(case['question']) > 200 else ''}\n")
                f.write(f"   Reason: {case['classification_reason']}\n\n")
        else:
            f.write("No multiple-choice questions with invalid options found!\n")
    
    print(f"\nResults saved to:")
    print(f"  - {output_file} (detailed JSON data)")
    print(f"  - {summary_file} (summary report)")
    print(f"\nTotal cases found: {len(all_invalid_cases)}")
    print(f"  - empty: {invalid_type_stats['empty']} (options가 null이거나 빈 배열)")
    print(f"  - invalid_format: {invalid_type_stats['invalid_format']} (옵션이 ①②③④⑤로 시작하지 않음)")

if __name__ == "__main__":
    # pipeline/config에서 ONEDRIVE_PATH import 시도
    try:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        sys.path.insert(0, project_root)
        from pipeline.config import ONEDRIVE_PATH
        file_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '2_subdomain', 'multiple_subdomain_classified_ALL.json')
    except ImportError:
        # fallback: pipeline이 없는 경우 플랫폼별 기본값 사용
        import platform
        system = platform.system()
        home_dir = os.path.expanduser("~")
        if system == "Windows":
            file_path = os.path.join(home_dir, "Desktop", "SFAIcenter", "evaluation", "eval_data", "2_subdomain", "multiple_subdomain_classified_ALL.json")
        else:
            file_path = os.path.join(home_dir, "Desktop", "Desktop_AICenter✨", "SFAIcenter", "evaluation", "eval_data", "2_subdomain", "multiple_subdomain_classified_ALL.json")
    
    main(file_path=file_path)