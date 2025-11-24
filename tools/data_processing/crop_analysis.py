#!/usr/bin/env python3
"""
Crop 파일 분석 스크립트
경로를 인자로 받아 crop 파일들을 정리하고, BEFORE/AFTER 비교 분석을 수행합니다.
"""

import argparse
import os
import re
import pandas as pd
from collections import defaultdict


def extract_page_number(filename):
    """파일명에서 페이지 번호 추출"""
    # tb_0167_0001.png -> 0167, img_0158_0002.png -> 0158, etc_0167_0001.png -> 0167
    match = re.search(r'(?:tb_|img_|etc_)(\d{4})', filename)
    return match.group(1) if match else None


def organize_crop_files(crop_dir):
    """crop_dir의 폴더별로 파일들을 정리"""
    results = []
    
    for root, dirs, files in os.walk(crop_dir):
        # .DS_Store 파일 제외
        files = [f for f in files if f != '.DS_Store']
        
        if not files:  # 파일이 없으면 건너뛰기
            continue
        
        folder_name = os.path.basename(root)
        
        # 파일들을 테이블, 이미지, 기타로 분류
        table_files = []
        image_files = []
        etc_files = []
        pages_with_files = set()
        
        for file in files:
            if file.startswith('tb_'):
                table_files.append(file)
                page_num = extract_page_number(file)
                if page_num:
                    pages_with_files.add(page_num)
            elif file.startswith('img_'):
                image_files.append(file)
                page_num = extract_page_number(file)
                if page_num:
                    pages_with_files.add(page_num)
            elif file.startswith('etc_'):
                etc_files.append(file)
                page_num = extract_page_number(file)
                if page_num:
                    pages_with_files.add(page_num)
        
        # 결과 저장
        results.append({
            '폴더명': folder_name,
            '테이블_파일_수': len(table_files),
            '테이블_파일_목록': ', '.join(sorted(table_files)),
            '이미지_파일_수': len(image_files),
            '이미지_파일_목록': ', '.join(sorted(image_files)),
            '기타_파일_수': len(etc_files),
            '기타_파일_목록': ', '.join(sorted(etc_files)),
            '파일이_있는_페이지_수': len(pages_with_files),
            '파일이_있는_페이지_목록': ', '.join(sorted(pages_with_files))
        })
    
    return results


def compare_analysis_files(before_file, after_file):
    """BEFORE와 AFTER 파일을 비교하여 차이점 분석"""
    
    # Excel 파일 읽기
    df_before = pd.read_excel(before_file, dtype=str)
    df_after = pd.read_excel(after_file, dtype=str)
    
    # 폴더명을 기준으로 매칭
    before_dict = {row['폴더명']: row for _, row in df_before.iterrows()}
    after_dict = {row['폴더명']: row for _, row in df_after.iterrows()}
    
    results = []
    
    for folder_name in before_dict.keys():
        if folder_name not in after_dict:
            # AFTER에 없는 폴더
            results.append({
                '폴더명': folder_name,
                '상태': 'AFTER에_없는_폴더',
                '테이블_파일_수': before_dict[folder_name]['테이블_파일_수'],
                '이미지_파일_수': before_dict[folder_name]['이미지_파일_수'],
                '기타_파일_수': before_dict[folder_name].get('기타_파일_수', '0'),
                '없어진_테이블_파일': before_dict[folder_name]['테이블_파일_목록'],
                '없어진_이미지_파일': before_dict[folder_name]['이미지_파일_목록'],
                '없어진_기타_파일': before_dict[folder_name].get('기타_파일_목록', ''),
                '없어진_페이지_수': before_dict[folder_name]['파일이_있는_페이지_수'],
                '없어진_페이지_목록': before_dict[folder_name]['파일이_있는_페이지_목록']
            })
        else:
            # 두 파일 모두에 있는 폴더 - 파일 비교
            before_row = before_dict[folder_name]
            after_row = after_dict[folder_name]
            
            # 파일 목록 비교
            before_table_files = set(before_row['테이블_파일_목록'].split(', ')) if pd.notna(before_row['테이블_파일_목록']) and before_row['테이블_파일_목록'] != '' else set()
            after_table_files = set(after_row['테이블_파일_목록'].split(', ')) if pd.notna(after_row['테이블_파일_목록']) and after_row['테이블_파일_목록'] != '' else set()
            
            before_image_files = set(before_row['이미지_파일_목록'].split(', ')) if pd.notna(before_row['이미지_파일_목록']) and before_row['이미지_파일_목록'] != '' else set()
            after_image_files = set(after_row['이미지_파일_목록'].split(', ')) if pd.notna(after_row['이미지_파일_목록']) and after_row['이미지_파일_목록'] != '' else set()
            
            before_etc_files = set(before_row.get('기타_파일_목록', '').split(', ')) if pd.notna(before_row.get('기타_파일_목록', '')) and before_row.get('기타_파일_목록', '') != '' else set()
            after_etc_files = set(after_row.get('기타_파일_목록', '').split(', ')) if pd.notna(after_row.get('기타_파일_목록', '')) and after_row.get('기타_파일_목록', '') != '' else set()
            
            # AFTER에 없는 파일들
            missing_table_files = before_table_files - after_table_files
            missing_image_files = before_image_files - after_image_files
            missing_etc_files = before_etc_files - after_etc_files
            
            # 페이지 비교
            before_pages = set(before_row['파일이_있는_페이지_목록'].split(', ')) if pd.notna(before_row['파일이_있는_페이지_목록']) and before_row['파일이_있는_페이지_목록'] != '' else set()
            after_pages = set(after_row['파일이_있는_페이지_목록'].split(', ')) if pd.notna(after_row['파일이_있는_페이지_목록']) and after_row['파일이_있는_페이지_목록'] != '' else set()
            missing_pages = list(before_pages - after_pages)
            
            if missing_table_files or missing_image_files or missing_etc_files or missing_pages:
                results.append({
                    '폴더명': folder_name,
                    '상태': '일부_파일_누락',
                    '테이블_파일_수': before_row['테이블_파일_수'],
                    '이미지_파일_수': before_row['이미지_파일_수'],
                    '기타_파일_수': before_row.get('기타_파일_수', '0'),
                    '없어진_테이블_파일': ', '.join(sorted(missing_table_files)) if missing_table_files else '',
                    '없어진_이미지_파일': ', '.join(sorted(missing_image_files)) if missing_image_files else '',
                    '없어진_기타_파일': ', '.join(sorted(missing_etc_files)) if missing_etc_files else '',
                    '없어진_페이지_수': len(missing_pages),
                    '없어진_페이지_목록': ', '.join(sorted(missing_pages)) if missing_pages else '',
                    '최종_페이지_목록': ", ".join(sorted(after_pages))
                })
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Crop 파일 분석 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # BEFORE 상태 저장
  python crop_analysis.py /path/to/crop_dir --before
  
  # AFTER 상태 저장 및 비교
  python crop_analysis.py /path/to/crop_dir --after
        """
    )
    parser.add_argument('crop_dir', type=str, help='분석할 crop 디렉토리 경로')
    parser.add_argument('--before', action='store_true', help='BEFORE 상태를 분석하고 저장')
    parser.add_argument('--after', action='store_true', help='AFTER 상태를 분석하고 저장하며 BEFORE와 비교')
    
    args = parser.parse_args()
    
    # 경로 검증
    if not os.path.isdir(args.crop_dir):
        print(f"오류: '{args.crop_dir}' 디렉토리가 존재하지 않습니다.")
        return 1
    
    # 파일명 생성 (경로의 기본 이름 사용)
    base_name = os.path.basename(os.path.normpath(args.crop_dir))
    before_file = f'{base_name}_BEFORE.xlsx'
    after_file = f'{base_name}_AFTER.xlsx'
    comparison_file = f'file_comparison_{base_name}_analysis.xlsx'
    
    if args.before:
        print(f"BEFORE 상태 분석 중: {args.crop_dir}")
        results = organize_crop_files(args.crop_dir)
        df = pd.DataFrame(results)
        
        print(f"총 {len(results)}개 폴더를 처리했습니다.")
        print("\n처리 결과:")
        print(df)
        
        df.to_excel(before_file, index=False)
        print(f"\nBEFORE 파일 저장 완료: {before_file}")
        
    elif args.after:
        print(f"AFTER 상태 분석 중: {args.crop_dir}")
        results = organize_crop_files(args.crop_dir)
        df = pd.DataFrame(results)
        
        print(f"총 {len(results)}개 폴더를 처리했습니다.")
        print("\n처리 결과:")
        print(df)
        
        df.to_excel(after_file, index=False)
        print(f"\nAFTER 파일 저장 완료: {after_file}")
        
        # BEFORE 파일이 존재하는지 확인
        if not os.path.exists(before_file):
            print(f"\n경고: BEFORE 파일({before_file})이 존재하지 않아 비교 분석을 건너뜁니다.")
            return 0
        
        # 비교 분석 실행
        print(f"\nBEFORE와 AFTER 파일 비교 분석 중...")
        comparison_results = compare_analysis_files(before_file, after_file)
        
        if comparison_results:
            df_comparison = pd.DataFrame(comparison_results)
            
            print(f"총 {len(comparison_results)}개 폴더에서 차이점을 발견했습니다.")
            print("\n비교 결과:")
            print(df_comparison)
            
            df_comparison.to_excel(comparison_file, index=False)
            print(f"\n비교 분석 파일 저장 완료: {comparison_file}")
        else:
            print("\n차이점이 발견되지 않았습니다.")
            
    else:
        print("오류: --before 또는 --after 옵션 중 하나를 지정해야 합니다.")
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

