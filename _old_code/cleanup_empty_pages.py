#!/usr/bin/env python3
"""
JSON 파일에서 빈 페이지를 제거하는 스크립트

이 스크립트는 지정된 경로의 모든 JSON 파일에서
"page_contents": ""와 "add_info": []인 페이지를 제거합니다.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any


def is_empty_page(page: Dict[str, Any]) -> bool:
    """
    페이지가 비어있는지 확인합니다.
    
    Args:
        page: 페이지 딕셔너리
        
    Returns:
        bool: 페이지가 비어있으면 True, 그렇지 않으면 False
    """
    return (page.get("page_contents", "") == "" and 
            page.get("add_info", []) == [])


def cleanup_json_file(file_path: Path) -> tuple[int, int]:
    """
    JSON 파일에서 빈 페이지를 제거합니다.
    
    Args:
        file_path: JSON 파일 경로
        
    Returns:
        tuple: (제거된 페이지 수, 원본 페이지 수)
    """
    try:
        # JSON 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # contents가 없거나 리스트가 아닌 경우 스킵
        if 'contents' not in data or not isinstance(data['contents'], list):
            print(f"⚠️  {file_path}: 'contents' 필드가 없거나 리스트가 아닙니다.")
            return 0, 0
        
        original_count = len(data['contents'])
        
        # 빈 페이지가 아닌 페이지만 필터링
        filtered_contents = [page for page in data['contents'] if not is_empty_page(page)]
        
        removed_count = original_count - len(filtered_contents)
        
        if removed_count > 0:
            # 필터링된 내용으로 업데이트
            data['contents'] = filtered_contents
            
            # 백업 파일 생성
            backup_path = file_path.with_suffix('.json.bak')
            if not backup_path.exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"📁 백업 파일 생성: {backup_path}")
            
            # 원본 파일에 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {file_path}: {removed_count}개 페이지 제거 (총 {original_count}개 → {len(filtered_contents)}개)")
        else:
            print(f"ℹ️  {file_path}: 제거할 빈 페이지가 없습니다.")
        
        return removed_count, original_count
        
    except json.JSONDecodeError as e:
        print(f"❌ {file_path}: JSON 파싱 오류 - {e}")
        return 0, 0
    except Exception as e:
        print(f"❌ {file_path}: 처리 중 오류 발생 - {e}")
        return 0, 0


def find_json_files(directory: Path) -> List[Path]:
    """
    디렉토리에서 모든 JSON 파일을 찾습니다.
    
    Args:
        directory: 검색할 디렉토리 경로
        
    Returns:
        List[Path]: 찾은 JSON 파일들의 경로 리스트
    """
    json_files = []
    
    if directory.is_file() and directory.suffix == '.json':
        json_files.append(directory)
    elif directory.is_dir():
        json_files = list(directory.rglob('*.json'))
    else:
        print(f"❌ {directory}: 유효하지 않은 경로입니다.")
        return []
    
    return json_files


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='JSON 파일에서 빈 페이지를 제거합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python cleanup_empty_pages.py /path/to/directory
  python cleanup_empty_pages.py /path/to/single/file.json
  python cleanup_empty_pages.py /path/to/directory --dry-run
        """
    )
    
    parser.add_argument(
        'path',
        help='처리할 JSON 파일 또는 디렉토리 경로'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제로 파일을 수정하지 않고 미리보기만 수행'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='상세한 출력'
    )
    
    args = parser.parse_args()
    
    # 경로 확인
    target_path = Path(args.path)
    if not target_path.exists():
        print(f"❌ 경로가 존재하지 않습니다: {target_path}")
        sys.exit(1)
    
    # JSON 파일 찾기
    json_files = find_json_files(target_path)
    
    if not json_files:
        print("❌ 처리할 JSON 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    print(f"📂 {len(json_files)}개의 JSON 파일을 찾았습니다.")
    
    if args.dry_run:
        print("🔍 DRY RUN 모드: 파일을 실제로 수정하지 않습니다.")
    
    # 통계 변수
    total_removed = 0
    total_original = 0
    processed_files = 0
    
    # 각 JSON 파일 처리
    for json_file in json_files:
        if args.verbose:
            print(f"\n📄 처리 중: {json_file}")
        
        if args.dry_run:
            # DRY RUN 모드에서는 실제 제거하지 않고 분석만
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'contents' not in data or not isinstance(data['contents'], list):
                    print(f"⚠️  {json_file}: 'contents' 필드가 없거나 리스트가 아닙니다.")
                    continue
                
                original_count = len(data['contents'])
                empty_pages = [page for page in data['contents'] if is_empty_page(page)]
                removed_count = len(empty_pages)
                
                if removed_count > 0:
                    print(f"🔍 {json_file}: {removed_count}개 빈 페이지 발견 (총 {original_count}개 중)")
                    if args.verbose:
                        for page in empty_pages:
                            print(f"   - 페이지 {page.get('page', 'N/A')}: {page.get('chapter', 'N/A')}")
                else:
                    print(f"ℹ️  {json_file}: 빈 페이지 없음")
                
                total_removed += removed_count
                total_original += original_count
                processed_files += 1
                
            except Exception as e:
                print(f"❌ {json_file}: 분석 중 오류 - {e}")
        else:
            # 실제 처리
            removed, original = cleanup_json_file(json_file)
            total_removed += removed
            total_original += original
            if removed > 0 or original > 0:
                processed_files += 1
    
    # 결과 요약
    print(f"\n📊 처리 완료!")
    print(f"   - 처리된 파일: {processed_files}개")
    print(f"   - 제거된 페이지: {total_removed}개")
    print(f"   - 원본 페이지: {total_original}개")
    if total_original > 0:
        print(f"   - 제거 비율: {total_removed/total_original*100:.1f}%")


if __name__ == "__main__":
    main()
