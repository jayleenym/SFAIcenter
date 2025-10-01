#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
누락된 QnA 데이터를 찾아서 처리하는 스크립트
"""

import json
import os
import sys
from typing import List, Dict, Any

# 프로젝트 루트를 sys.path에 추가
sys.path.append('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter')
from tools.ProcessQnA import add_qna_domain

def find_missing_data(original_file: str, completed_file: str) -> List[Dict[str, Any]]:
    """누락된 데이터를 찾는 함수 (tag와 file_id를 함께 고려)"""
    print("원본 데이터 로딩...")
    with open(original_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    print("처리된 데이터 로딩...")
    with open(completed_file, 'r', encoding='utf-8') as f:
        completed_data = json.load(f)
    
    # 처리된 데이터의 고유 식별자를 set으로 만들기 (file_id + tag 조합)
    completed_identifiers = set()
    for item in completed_data:
        file_id = item.get('file_id', '')
        tag = item.get('qna_data', {}).get('tag', '')
        if file_id and tag:
            identifier = f"{file_id}_{tag}"
            completed_identifiers.add(identifier)
    
    # 누락된 데이터 찾기
    missing_data = []
    for item in original_data:
        file_id = item.get('file_id', '')
        tag = item.get('qna_data', {}).get('tag', '')
        if file_id and tag:
            identifier = f"{file_id}_{tag}"
            if identifier not in completed_identifiers:
                missing_data.append(item)
    
    print(f"처리된 데이터 식별자 수: {len(completed_identifiers)}개")
    print(f"누락된 데이터: {len(missing_data)}개")
    
    # 누락된 데이터의 file_id별 통계
    file_id_stats = {}
    for item in missing_data:
        file_id = item.get('file_id', 'Unknown')
        file_id_stats[file_id] = file_id_stats.get(file_id, 0) + 1
    
    print("누락된 데이터 file_id별 통계:")
    for file_id, count in sorted(file_id_stats.items()):
        print(f"  - {file_id}: {count}개")
    
    return missing_data

def process_missing_data(missing_data: List[Dict[str, Any]], output_file: str, model: str = 'x-ai/grok-4-fast'):
    """누락된 데이터를 처리하는 함수"""
    if not missing_data:
        print("처리할 데이터가 없습니다.")
        return
    
    # 임시 파일 생성
    temp_file = 'temp_missing_data.json'
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(missing_data, f, ensure_ascii=False, indent=4)
    
    print(f"누락된 {len(missing_data)}개 데이터 처리 시작...")
    
    # add_qna_domain 함수 호출
    result = add_qna_domain(temp_file, output_file, model)
    
    # 임시 파일 삭제
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    print(f"처리 완료: {output_file}")
    return result

def merge_with_completed(completed_file: str, missing_file: str, final_file: str):
    """처리된 데이터와 누락된 데이터를 병합하는 함수"""
    print("데이터 병합 중...")
    
    # 기존 처리된 데이터 로드
    with open(completed_file, 'r', encoding='utf-8') as f:
        completed_data = json.load(f)
    
    # 누락된 데이터 처리 결과 로드
    with open(missing_file, 'r', encoding='utf-8') as f:
        missing_data = json.load(f)
    
    # 병합
    merged_data = completed_data + missing_data
    
    # 최종 파일 저장
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=4)
    
    print(f"최종 병합 완료: {final_file}")
    print(f"총 데이터: {len(merged_data)}개")
    
    return merged_data

def main():
    """메인 실행 함수"""
    base_dir = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/1C"
    original_file = os.path.join(base_dir, "merged_extracted_qna_Lv2345.json")
    completed_file = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345_completed.json")
    missing_file = os.path.join(base_dir, "missing_qna_processed.json")
    final_file = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345_final.json")
    
    print("=" * 60)
    print("누락된 QnA 데이터 처리 시작")
    print("=" * 60)
    
    # 1. 누락된 데이터 찾기
    missing_data = find_missing_data(original_file, completed_file)
    
    if not missing_data:
        print("누락된 데이터가 없습니다.")
        return
    
    # 2. 누락된 데이터 처리
    process_missing_data(missing_data, missing_file)
    
    # 3. 기존 데이터와 병합
    merge_with_completed(completed_file, missing_file, final_file)
    
    print("\n처리 완료!")

if __name__ == "__main__":
    main()
