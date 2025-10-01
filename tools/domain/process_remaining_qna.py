#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
처리되지 않은 QnA 데이터를 찾아서 병렬처리하는 스크립트
"""

import json
import os
import sys
import shutil
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
sys.path.append('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter')
from tools.ProcessQnA import add_qna_domain

def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """JSON 파일을 로드하는 함수"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"파일 로드 오류 {file_path}: {e}")
        return []

def find_unprocessed_data(original_file: str, processed_file: str) -> List[Dict[str, Any]]:
    """
    처리되지 않은 데이터를 찾는 함수
    
    Args:
        original_file: 원본 파일 경로 (merged_extracted_qna_Lv2345.json)
        processed_file: 처리된 파일 경로 (merged_extracted_qna_domain_Lv2345.json)
    
    Returns:
        처리되지 않은 데이터 리스트
    """
    print("원본 데이터 로딩 중...")
    original_data = load_json_file(original_file)
    print(f"원본 데이터 개수: {len(original_data)}")
    
    print("처리된 데이터 로딩 중...")
    processed_data = load_json_file(processed_file)
    print(f"처리된 데이터 개수: {len(processed_data)}")
    
    # 처리된 데이터의 인덱스와 qna_domain 매핑
    processed_domains = {}
    for i, item in enumerate(processed_data):
        if i < len(original_data):
            # qna_data의 tag를 키로 사용하여 매핑
            tag = item.get('qna_data', {}).get('tag', '')
            domain = item.get('qna_domain', '')
            processed_domains[tag] = domain
    
    # 처리되지 않은 데이터 찾기
    unprocessed_data = []
    for i, item in enumerate(original_data):
        tag = item.get('qna_data', {}).get('tag', '')
        if tag in processed_domains:
            domain = processed_domains[tag]
            if domain and domain.strip():  # 도메인이 비어있지 않은 경우
                # 처리된 데이터로 업데이트
                item['qna_domain'] = domain
            else:
                # 도메인이 비어있는 경우 처리되지 않은 것으로 간주
                unprocessed_data.append(item)
        else:
            # 태그가 매핑에 없는 경우 처리되지 않은 것으로 간주
            unprocessed_data.append(item)
    
    print(f"처리되지 않은 데이터 개수: {len(unprocessed_data)}")
    return unprocessed_data

def split_data_into_chunks(data: List[Dict[str, Any]], chunk_size: int = 100) -> List[List[Dict[str, Any]]]:
    """
    데이터를 여러 묶음으로 나누는 함수
    
    Args:
        data: 나눌 데이터 리스트
        chunk_size: 각 묶음의 크기
    
    Returns:
        나뉜 데이터 묶음들의 리스트
    """
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        chunks.append(chunk)
    
    print(f"데이터를 {len(chunks)}개의 묶음으로 나눔 (각 묶음당 최대 {chunk_size}개)")
    return chunks

def process_chunk_worker(chunk_data: List[Dict[str, Any]], chunk_id: int, output_dir: str, model: str = None) -> str:
    """
    개별 묶음을 처리하는 워커 함수
    
    Args:
        chunk_data: 처리할 데이터 묶음
        chunk_id: 묶음 ID
        output_dir: 출력 디렉토리
        model: 사용할 모델명
    
    Returns:
        처리된 파일 경로
    """
    try:
        # 임시 파일 생성
        temp_file = os.path.join(output_dir, f'temp_chunk_{chunk_id}.json')
        output_file = os.path.join(output_dir, f'processed_chunk_{chunk_id}.json')
        
        # 임시 파일에 데이터 저장
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=4)
        
        print(f"묶음 {chunk_id} 처리 시작 (데이터 {len(chunk_data)}개)")
        
        # add_qna_domain 함수 호출
        result = add_qna_domain(temp_file, output_file, model)
        
        # 임시 파일 삭제
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        print(f"묶음 {chunk_id} 처리 완료: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"묶음 {chunk_id} 처리 오류: {e}")
        # 임시 파일 정리
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return None

def merge_processed_chunks(chunk_files: List[str], final_output: str) -> List[Dict[str, Any]]:
    """
    처리된 묶음들을 최종 파일로 합치는 함수
    
    Args:
        chunk_files: 처리된 묶음 파일 경로들
        final_output: 최종 출력 파일 경로
    
    Returns:
        합쳐진 데이터
    """
    merged_data = []
    
    for chunk_file in chunk_files:
        if chunk_file and os.path.exists(chunk_file):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                merged_data.extend(chunk_data)
                print(f"묶음 파일 병합 완료: {os.path.basename(chunk_file)} ({len(chunk_data)}개)")
            except Exception as e:
                print(f"묶음 파일 병합 오류 {chunk_file}: {e}")
    
    # 최종 파일 저장
    try:
        with open(final_output, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        print(f"최종 병합 완료: {final_output} ({len(merged_data)}개)")
    except Exception as e:
        print(f"최종 병합 오류: {e}")
    
    return merged_data

def main():
    """메인 실행 함수"""
    # 파일 경로 설정
    base_dir = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/1C"
    original_file = os.path.join(base_dir, "merged_extracted_qna_Lv2345.json")
    processed_file = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345.json")
    
    # 출력 디렉토리 설정
    output_dir = os.path.join(base_dir, "parallel_processing")
    os.makedirs(output_dir, exist_ok=True)
    
    # 설정
    chunk_size = 100  # 각 묶음당 처리할 데이터 개수
    max_workers = 5  # 병렬 처리 워커 수
    # model = "grok-beta/grok-2-1212"  # 사용할 모델
    model = 'x-ai/grok-4-fast'
    
    print("=" * 60)
    print("QnA 도메인 병렬처리 시작")
    print("=" * 60)
    
    # 1. 처리되지 않은 데이터 찾기
    print("\n1. 처리되지 않은 데이터 찾는 중...")
    unprocessed_data = find_unprocessed_data(original_file, processed_file)
    
    if not unprocessed_data:
        print("처리할 데이터가 없습니다.")
        return
    
    # 2. 데이터를 묶음으로 나누기
    print(f"\n2. 데이터를 묶음으로 나누는 중...")
    chunks = split_data_into_chunks(unprocessed_data, chunk_size)
    
    # 3. 병렬 처리
    print(f"\n3. 병렬 처리 시작 (워커 수: {max_workers})...")
    chunk_files = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 각 묶음에 대해 작업 제출
        future_to_chunk = {
            executor.submit(process_chunk_worker, chunk, i, output_dir, model): i 
            for i, chunk in enumerate(chunks)
        }
        
        # 완료된 작업들 처리
        for future in as_completed(future_to_chunk):
            chunk_id = future_to_chunk[future]
            try:
                result_file = future.result()
                if result_file:
                    chunk_files.append(result_file)
                    print(f"묶음 {chunk_id} 완료: {result_file}")
                else:
                    print(f"묶음 {chunk_id} 실패")
            except Exception as e:
                print(f"묶음 {chunk_id} 예외 발생: {e}")
    
    # 4. 결과 병합
    print(f"\n4. 처리된 묶음들을 병합하는 중...")
    final_output = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345_completed.json")
    merged_data = merge_processed_chunks(chunk_files, final_output)
    
    # 5. 통계 출력
    print(f"\n5. 처리 완료 통계:")
    print(f"- 처리된 총 데이터: {len(merged_data)}개")
    print(f"- 사용된 묶음 수: {len(chunks)}개")
    print(f"- 성공한 묶음: {len(chunk_files)}개")
    print(f"- 최종 파일: {final_output}")
    
    # 6. 임시 파일 정리
    print(f"\n6. 임시 파일 정리 중...")
    for chunk_file in chunk_files:
        try:
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        except Exception as e:
            print(f"임시 파일 삭제 오류 {chunk_file}: {e}")
    
    print("\n병렬처리 완료!")

if __name__ == "__main__":
    main()
