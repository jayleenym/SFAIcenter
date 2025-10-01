#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빈 도메인 데이터를 처리하는 스크립트
"""

import json
import os
import sys
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# 프로젝트 루트를 sys.path에 추가
sys.path.append('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter')
from tools.ProcessQnA import add_qna_domain

def find_empty_domain_data(final_file: str) -> List[Dict[str, Any]]:
    """빈 도메인 데이터를 찾는 함수"""
    print("최종 파일 로딩...")
    with open(final_file, 'r', encoding='utf-8') as f:
        final_data = json.load(f)
    
    print(f"총 데이터: {len(final_data)}개")
    
    # 빈 도메인 데이터 찾기
    empty_domain_data = []
    for item in final_data:
        if not item.get('qna_domain', '').strip():
            empty_domain_data.append(item)
    
    print(f"빈 도메인 데이터: {len(empty_domain_data)}개")
    
    # file_id별 통계
    file_id_stats = {}
    for item in empty_domain_data:
        file_id = item.get('file_id', 'Unknown')
        file_id_stats[file_id] = file_id_stats.get(file_id, 0) + 1
    
    print("빈 도메인 데이터 file_id별 통계 (상위 10개):")
    sorted_stats = sorted(file_id_stats.items(), key=lambda x: x[1], reverse=True)
    for file_id, count in sorted_stats[:10]:
        print(f"  - {file_id}: {count}개")
    
    return empty_domain_data

def split_data_into_chunks(data: List[Dict[str, Any]], chunk_size: int = 50) -> List[List[Dict[str, Any]]]:
    """데이터를 여러 묶음으로 나누는 함수"""
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        chunks.append(chunk)
    
    print(f"데이터를 {len(chunks)}개의 묶음으로 나눔 (각 묶음당 최대 {chunk_size}개)")
    return chunks

def process_chunk_worker(chunk_data: List[Dict[str, Any]], chunk_id: int, output_dir: str, model: str = 'x-ai/grok-4-fast') -> str:
    """개별 묶음을 처리하는 워커 함수"""
    try:
        # 임시 파일 생성
        temp_file = os.path.join(output_dir, f'temp_empty_chunk_{chunk_id}.json')
        output_file = os.path.join(output_dir, f'processed_empty_chunk_{chunk_id}.json')
        
        # 임시 파일에 데이터 저장
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=4)
        
        print(f"빈 도메인 묶음 {chunk_id} 처리 시작 (데이터 {len(chunk_data)}개)")
        
        # add_qna_domain 함수 호출
        result = add_qna_domain(temp_file, output_file, model)
        
        # 임시 파일 삭제
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        print(f"빈 도메인 묶음 {chunk_id} 처리 완료: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"빈 도메인 묶음 {chunk_id} 처리 오류: {e}")
        # 임시 파일 정리
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return None

def merge_processed_chunks(chunk_files: List[str], final_output: str) -> List[Dict[str, Any]]:
    """처리된 묶음들을 최종 파일로 합치는 함수"""
    merged_data = []
    
    for chunk_file in chunk_files:
        if chunk_file and os.path.exists(chunk_file):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                merged_data.extend(chunk_data)
                print(f"빈 도메인 묶음 파일 병합 완료: {os.path.basename(chunk_file)} ({len(chunk_data)}개)")
            except Exception as e:
                print(f"빈 도메인 묶음 파일 병합 오류 {chunk_file}: {e}")
    
    # 최종 파일 저장
    try:
        with open(final_output, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        print(f"빈 도메인 최종 병합 완료: {final_output} ({len(merged_data)}개)")
    except Exception as e:
        print(f"빈 도메인 최종 병합 오류: {e}")
    
    return merged_data

def main():
    """메인 실행 함수"""
    base_dir = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/1C"
    final_file = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345_final.json")
    
    # 출력 디렉토리 설정
    output_dir = os.path.join(base_dir, "empty_domain_processing")
    os.makedirs(output_dir, exist_ok=True)
    
    # 설정
    chunk_size = 50  # 각 묶음당 처리할 데이터 개수
    max_workers = 3  # 병렬 처리 워커 수 (API 제한 고려)
    model = 'x-ai/grok-4-fast'  # 사용할 모델
    
    print("=" * 60)
    print("빈 도메인 데이터 병렬처리 시작")
    print("=" * 60)
    
    # 1. 빈 도메인 데이터 찾기
    print("\n1. 빈 도메인 데이터 찾는 중...")
    empty_domain_data = find_empty_domain_data(final_file)
    
    if not empty_domain_data:
        print("처리할 빈 도메인 데이터가 없습니다.")
        return
    
    # 2. 데이터를 묶음으로 나누기
    print(f"\n2. 데이터를 묶음으로 나누는 중...")
    chunks = split_data_into_chunks(empty_domain_data, chunk_size)
    
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
                    print(f"빈 도메인 묶음 {chunk_id} 완료: {result_file}")
                else:
                    print(f"빈 도메인 묶음 {chunk_id} 실패")
            except Exception as e:
                print(f"빈 도메인 묶음 {chunk_id} 예외 발생: {e}")
    
    # 4. 결과 병합
    print(f"\n4. 처리된 묶음들을 병합하는 중...")
    final_output = os.path.join(base_dir, "empty_domain_processed.json")
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
    
    print("\n빈 도메인 병렬처리 완료!")

if __name__ == "__main__":
    main()
