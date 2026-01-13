#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 파일에서 빈 페이지를 제거하는 CLI 스크립트

이 스크립트는 지정된 경로의 모든 JSON 파일에서
"page_contents": ""와 "add_info": []인 페이지를 제거합니다.

사용 예시:
    python cleanup_empty_pages.py /path/to/directory
    python cleanup_empty_pages.py /path/to/single/file.json
    python cleanup_empty_pages.py /path/to/directory --dry-run
"""

import sys
import argparse
from pathlib import Path

from .json_cleaner import JSONCleaner


def main() -> int:
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
        '--no-backup',
        action='store_true',
        help='백업 파일을 생성하지 않음'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세한 출력'
    )
    
    args = parser.parse_args()
    
    # 경로 확인
    target_path = Path(args.path)
    if not target_path.exists():
        print(f"❌ 경로가 존재하지 않습니다: {target_path}")
        return 1
    
    # JSONCleaner 인스턴스 생성
    cleaner = JSONCleaner(verbose=args.verbose or args.dry_run)
    
    # JSON 파일 찾기
    json_files = cleaner.find_json_files(target_path)
    
    if not json_files:
        print("❌ 처리할 JSON 파일을 찾을 수 없습니다.")
        return 1
    
    print(f"📂 {len(json_files)}개의 JSON 파일을 찾았습니다.")
    
    if args.dry_run:
        print("🔍 DRY RUN 모드: 파일을 실제로 수정하지 않습니다.")
    
    # 디렉토리 정리 실행
    result = cleaner.cleanup_directory(
        target_path,
        create_backup=not args.no_backup,
        dry_run=args.dry_run
    )
    
    # 결과 요약
    print(f"\n📊 처리 완료!")
    print(f"   - 처리된 파일: {result.processed_files}개")
    print(f"   - 제거된 페이지: {result.total_removed}개")
    print(f"   - 원본 페이지: {result.total_original}개")
    if result.total_original > 0:
        print(f"   - 제거 비율: {result.removal_rate:.1f}%")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
