#!/usr/bin/env python3
"""
유효하지 않은 선택지 찾기 스크립트
- 객관식 문제에서 선택지가 null이거나 빈 배열인 경우 찾기
- 선택지가 ①②③④⑤로 시작하지 않는 경우 찾기
"""

import json
import re
import os
import sys
import glob
from collections import defaultdict
from typing import Dict, List, Any, Optional

# tools 모듈 import
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, project_root)
    from tools import ONEDRIVE_PATH
except ImportError:
    import platform
    system = platform.system()
    home_dir = os.path.expanduser("~")
    if system == "Windows":
        ONEDRIVE_PATH = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
    else:
        ONEDRIVE_PATH = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")


def find_invalid_options_in_file(file_path: str) -> List[Dict[str, Any]]:
    """
    단일 파일에서 유효하지 않은 선택지를 가진 객관식 문제 찾기
    
    Args:
        file_path: 검사할 파일 경로
        
    Returns:
        유효하지 않은 선택지 정보 리스트
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        invalid_cases = []
        is_nested_structure = '_extracted_qna' in file_path
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # 중첩 구조 처리
            if is_nested_structure:
                if 'qna_type' in item and 'qna_data' in item:
                    qna_type = item['qna_type']
                    qna_data = item['qna_data']
                    
                    if qna_type != 'multiple-choice':
                        continue
                    
                    if not isinstance(qna_data, dict) or 'description' not in qna_data:
                        continue
                    
                    description = qna_data.get('description')
                    
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
            # 평탄화된 구조 처리
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
                        option_stripped = option.strip()
                        if not re.match(r'^[①②③④⑤]', option_stripped):
                            invalid_options_detail.append({
                                'option_index': i,
                                'original_option': option
                            })
                
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


def find_invalid_options(file_path: Optional[str] = None) -> None:
    """
    객관식 문제에서 유효하지 않은 선택지를 찾아 리포트 생성
    
    Args:
        file_path: 검사할 파일 경로 (None이면 전체 검사)
    """
    if file_path is None:
        pattern = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', '*', 'Lv5', '*_extracted_qna.json')
        json_files = glob.glob(pattern, recursive=True)
        print(f"Finding multiple-choice questions with invalid options in {len(json_files)} files...")
    else:
        json_files = [file_path]
        print(f"Finding multiple-choice questions with invalid options in {file_path} file...")
    
    all_invalid_cases = []
    file_stats = defaultdict(int)
    invalid_type_stats = defaultdict(int)
    
    for fp in json_files:
        invalid_cases = find_invalid_options_in_file(fp)
        if invalid_cases:
            file_stats[fp] = len(invalid_cases)
            all_invalid_cases.extend(invalid_cases)
            for case in invalid_cases:
                invalid_type_stats[case['invalid_type']] += 1
    
    # 결과 저장
    if json_files:
        last_file = json_files[-1] if isinstance(json_files, list) else json_files
        file_basename = os.path.basename(last_file).replace('.json', '')
    else:
        file_basename = 'all_files'
    
    output_base = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', 'invalid_options')
    os.makedirs(output_base, exist_ok=True)
    
    # JSON 상세 결과 저장
    output_file = os.path.join(output_base, f'invalid_options_detailed_{file_basename}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_invalid_cases, f, ensure_ascii=False, indent=2)
    
    # 텍스트 요약 저장
    summary_file = os.path.join(output_base, f'invalid_options_summary_{file_basename}.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("MULTIPLE-CHOICE QUESTIONS WITH INVALID OPTIONS - SUMMARY REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total multiple-choice questions with invalid options: {len(all_invalid_cases)}\n\n")
        
        f.write("By invalid type:\n")
        f.write(f"  empty: {invalid_type_stats['empty']} (options가 null이거나 빈 배열)\n")
        f.write(f"  invalid_format: {invalid_type_stats['invalid_format']} (옵션이 ①②③④⑤로 시작하지 않음)\n\n")
        
        if all_invalid_cases:
            domain_counts = defaultdict(int)
            for case in all_invalid_cases:
                domain_counts[case['domain']] += 1
            
            f.write("By domain:\n")
            for domain, count in sorted(domain_counts.items()):
                f.write(f"  {domain}: {count}\n")
            
            f.write(f"\nFiles with issues: {len(file_stats)}\n")
            for fp, count in sorted(file_stats.items()):
                f.write(f"  {fp}: {count}\n")
            
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


def main():
    """메인 함수"""
    file_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '2_subdomain', 'multiple-choice_DST.json')
    find_invalid_options(file_path=file_path)


if __name__ == "__main__":
    main()

