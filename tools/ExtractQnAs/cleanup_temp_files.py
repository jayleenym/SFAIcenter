#!/usr/bin/env python3
"""
SS0000 도서들의 temp_page_0000.json 파일들과 _extracted_qna.json 파일의 Q&A 개수를 비교하여
개수가 같으면 temp 파일들을 삭제하는 스크립트
"""

import os
import json
import glob
from pathlib import Path
import sys

def count_qna_in_file(file_path):
    """JSON 파일에서 Q&A 개수를 세는 함수"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return len(data)
            else:
                print(f"Warning: {file_path} is not a list format")
                return 0
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def get_book_ids_from_extracted_files(extracted_dir):
    """extracted_qna.json 파일들에서 도서 ID들을 추출"""
    pattern = os.path.join(extracted_dir, "SS*_extracted_qna.json")
    extracted_files = glob.glob(pattern)
    
    book_ids = []
    for file_path in extracted_files:
        filename = os.path.basename(file_path)
        # SS0087_extracted_qna.json -> SS0087
        book_id = filename.replace('_extracted_qna.json', '')
        book_ids.append(book_id)
    
    book_ids = sorted(book_ids)
    
    return book_ids

def get_temp_files_for_book(extracted_dir, book_id):
    """특정 도서의 모든 temp_page 파일들을 반환"""
    pattern = os.path.join(extracted_dir, f"{book_id}_temp_page_*.json")
    return glob.glob(pattern)

def cleanup_temp_files(extracted_dir):
    """메인 함수: Q&A 개수를 비교하고 temp 파일들을 삭제"""
    print(f"Processing directory: {extracted_dir}")
    
    # extracted_qna.json 파일들에서 도서 ID 추출
    book_ids = get_book_ids_from_extracted_files(extracted_dir)
    print(f"Found book IDs: {book_ids}")
    
    total_deleted_files = 0
    total_deleted_size = 0
    
    for book_id in book_ids:
        print(f"\n--- Processing {book_id} ---")
        
        # extracted_qna.json 파일 경로
        extracted_file = os.path.join(extracted_dir, f"{book_id}_extracted_qna.json")
        
        # 해당 도서의 temp_page 파일들
        temp_files = get_temp_files_for_book(extracted_dir, book_id)
        
        if not temp_files:
            print(f"No temp files found for {book_id}")
            continue
            
        print(f"Found {len(temp_files)} temp files for {book_id}")
        
        # extracted_qna.json의 Q&A 개수
        extracted_qna_count = count_qna_in_file(extracted_file)
        print(f"Extracted Q&A count: {extracted_qna_count}")
        
        # temp 파일들의 총 Q&A 개수
        temp_qna_count = 0
        temp_file_sizes = []
        
        for temp_file in temp_files:
            count = count_qna_in_file(temp_file)
            temp_qna_count += count
            file_size = os.path.getsize(temp_file)
            temp_file_sizes.append((temp_file, file_size))
        
        print(f"Temp files Q&A count: {temp_qna_count}")
        
        # Q&A 개수가 같으면 temp 파일들 삭제
        if extracted_qna_count == temp_qna_count and extracted_qna_count > 0:
            print(f"✅ Q&A counts match! Deleting {len(temp_files)} temp files...")
            
            for temp_file, file_size in temp_file_sizes:
                try:
                    os.remove(temp_file)
                    total_deleted_files += 1
                    total_deleted_size += file_size
                    print(f"  Deleted: {os.path.basename(temp_file)} ({file_size:,} bytes)")
                except Exception as e:
                    print(f"  Error deleting {temp_file}: {e}")
        else:
            print(f"❌ Q&A counts don't match or extracted file is empty. Skipping deletion.")
            if extracted_qna_count == 0:
                print(f"  Extracted file is empty or invalid")
            else:
                print(f"  Extracted: {extracted_qna_count}, Temp: {temp_qna_count}")
    
    print(f"\n=== Summary ===")
    print(f"Total files deleted: {total_deleted_files}")
    print(f"Total size freed: {total_deleted_size:,} bytes ({total_deleted_size/1024/1024:.2f} MB)")

def main():
    # 대상 디렉토리
    cycle = sys.argv[1]
    extracted_dir = f"/Users/yejin/Library/CloudStorage/OneDrive-개인/데이터L/selectstar/data/FIN_workbook/{cycle}C/extracted"
    
    # 디렉토리 존재 확인
    if not os.path.exists(extracted_dir):
        print(f"Error: Directory {extracted_dir} does not exist")
        return
    
    # 사용자 확인
    print("This script will delete temp_page_*.json files if their Q&A count matches the extracted_qna.json file.")
    print(f"Target directory: {extracted_dir}")
    
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response != 'y':
        print("Operation cancelled.")
        return
    
    # 실행
    cleanup_temp_files(extracted_dir)

if __name__ == "__main__":
    main()
