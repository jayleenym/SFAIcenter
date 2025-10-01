#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 QnA 도메인 병렬처리 스크립트
"""

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# 프로젝트 루트를 sys.path에 추가
sys.path.append('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter')
from tools.ProcessQnA import add_qna_domain

def process_qna_batch(batch_data, batch_id, output_dir, model="grok-beta/grok-2-1212"):
    """배치 데이터를 처리하는 함수"""
    try:
        # 임시 입력 파일 생성
        temp_input = os.path.join(output_dir, f'temp_batch_{batch_id}.json')
        temp_output = os.path.join(output_dir, f'result_batch_{batch_id}.json')
        
        # 배치 데이터를 임시 파일에 저장
        with open(temp_input, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=4)
        
        print(f"배치 {batch_id} 시작: {len(batch_data)}개 항목")
        
        # add_qna_domain 함수 호출
        add_qna_domain(temp_input, temp_output, model)
        
        # 임시 입력 파일 삭제
        os.remove(temp_input)
        
        print(f"배치 {batch_id} 완료: {temp_output}")
        return temp_output
        
    except Exception as e:
        print(f"배치 {batch_id} 오류: {e}")
        return None

def main():
    # 파일 경로
    base_dir = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FIN_workbook/1C"
    original_file = os.path.join(base_dir, "merged_extracted_qna_Lv2345.json")
    processed_file = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345.json")
    
    # 출력 디렉토리
    output_dir = os.path.join(base_dir, "parallel_results")
    os.makedirs(output_dir, exist_ok=True)
    
    print("원본 데이터 로딩...")
    with open(original_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    print("처리된 데이터 로딩...")
    with open(processed_file, 'r', encoding='utf-8') as f:
        processed_data = json.load(f)
    
    # 처리되지 않은 데이터 찾기 (간단한 방법)
    unprocessed = []
    for i, item in enumerate(original_data):
        if i < len(processed_data):
            if not processed_data[i].get('qna_domain', '').strip():
                unprocessed.append(item)
        else:
            unprocessed.append(item)
    
    print(f"처리되지 않은 데이터: {len(unprocessed)}개")
    
    if not unprocessed:
        print("모든 데이터가 처리되었습니다!")
        return
    
    # 데이터를 배치로 나누기 (각 배치당 20개)
    batch_size = 20
    batches = [unprocessed[i:i+batch_size] for i in range(0, len(unprocessed), batch_size)]
    
    print(f"데이터를 {len(batches)}개 배치로 나눔")
    
    # 병렬 처리
    results = []
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_qna_batch, batch, i, output_dir) 
                  for i, batch in enumerate(batches)]
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    # 결과 병합
    print("결과 병합 중...")
    final_data = []
    
    # 기존 처리된 데이터 추가
    final_data.extend(processed_data)
    
    # 새로 처리된 데이터 추가
    for result_file in results:
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            final_data.extend(batch_data)
        except Exception as e:
            print(f"결과 파일 읽기 오류 {result_file}: {e}")
    
    # 최종 파일 저장
    final_output = os.path.join(base_dir, "merged_extracted_qna_domain_Lv2345_final.json")
    with open(final_output, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"최종 결과 저장: {final_output}")
    print(f"총 데이터: {len(final_data)}개")
    
    # 임시 파일 정리
    for result_file in results:
        try:
            os.remove(result_file)
        except:
            pass

if __name__ == "__main__":
    main()
