#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crop 파일 분석 스크립트

경로를 인자로 받아 crop 파일들을 정리하고, BEFORE/AFTER 비교 분석을 수행합니다.

사용 예시:
    python crop_analysis.py /path/to/crop_dir --before
    python crop_analysis.py /path/to/crop_dir --after
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class FolderStats:
    """폴더별 파일 통계"""
    folder_name: str
    table_files: List[str] = field(default_factory=list)
    image_files: List[str] = field(default_factory=list)
    etc_files: List[str] = field(default_factory=list)
    pages_with_files: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            '폴더명': self.folder_name,
            '테이블_파일_수': len(self.table_files),
            '테이블_파일_목록': ', '.join(sorted(self.table_files)),
            '이미지_파일_수': len(self.image_files),
            '이미지_파일_목록': ', '.join(sorted(self.image_files)),
            '기타_파일_수': len(self.etc_files),
            '기타_파일_목록': ', '.join(sorted(self.etc_files)),
            '파일이_있는_페이지_수': len(self.pages_with_files),
            '파일이_있는_페이지_목록': ', '.join(sorted(self.pages_with_files))
        }


class CropAnalyzer:
    """Crop 파일 분석기"""
    
    # 파일 유형별 접두사
    FILE_PREFIXES = {
        'table': 'tb_',
        'image': 'img_',
        'etc': 'etc_'
    }
    
    # 페이지 번호 추출 패턴
    PAGE_PATTERN = re.compile(r'(?:tb_|img_|etc_)(\d{4})')
    
    def __init__(self, crop_dir: str):
        """
        CropAnalyzer 초기화
        
        Args:
            crop_dir: 분석할 crop 디렉토리 경로
        """
        self.crop_dir = Path(crop_dir)
        self.base_name = self.crop_dir.name
    
    @property
    def before_file(self) -> str:
        """BEFORE 파일 경로"""
        return f'{self.base_name}_BEFORE.xlsx'
    
    @property
    def after_file(self) -> str:
        """AFTER 파일 경로"""
        return f'{self.base_name}_AFTER.xlsx'
    
    @property
    def comparison_file(self) -> str:
        """비교 분석 파일 경로"""
        return f'file_comparison_{self.base_name}_analysis.xlsx'
    
    def _extract_page_number(self, filename: str) -> Optional[str]:
        """파일명에서 페이지 번호 추출"""
        match = self.PAGE_PATTERN.search(filename)
        return match.group(1) if match else None
    
    def _classify_file(self, filename: str, stats: FolderStats) -> None:
        """파일을 유형별로 분류"""
        page_num = self._extract_page_number(filename)
        
        if filename.startswith(self.FILE_PREFIXES['table']):
            stats.table_files.append(filename)
        elif filename.startswith(self.FILE_PREFIXES['image']):
            stats.image_files.append(filename)
        elif filename.startswith(self.FILE_PREFIXES['etc']):
            stats.etc_files.append(filename)
        else:
            return  # 분류되지 않은 파일은 무시
        
        if page_num:
            stats.pages_with_files.add(page_num)
    
    def organize_crop_files(self) -> List[FolderStats]:
        """crop_dir의 폴더별로 파일들을 정리"""
        results = []
        
        for root, dirs, files in os.walk(self.crop_dir):
            # 시스템 파일 제외
            files = [f for f in files if not f.startswith('.')]
            
            if not files:
                continue
            
            folder_name = os.path.basename(root)
            stats = FolderStats(folder_name=folder_name)
            
            for file in files:
                self._classify_file(file, stats)
            
            # 분류된 파일이 있는 경우만 결과에 추가
            if stats.table_files or stats.image_files or stats.etc_files:
                results.append(stats)
        
        return results
    
    @staticmethod
    def _parse_file_list(value: Any) -> Set[str]:
        """셀 값을 파일 목록 집합으로 변환"""
        if pd.isna(value) or value == '':
            return set()
        return set(str(value).split(', '))
    
    def compare_analysis_files(self) -> List[Dict[str, Any]]:
        """BEFORE와 AFTER 파일을 비교하여 차이점 분석"""
        if not os.path.exists(self.before_file):
            print(f"⚠️ BEFORE 파일이 없습니다: {self.before_file}")
            return []
        
        if not os.path.exists(self.after_file):
            print(f"⚠️ AFTER 파일이 없습니다: {self.after_file}")
            return []
        
        df_before = pd.read_excel(self.before_file, dtype=str)
        df_after = pd.read_excel(self.after_file, dtype=str)
        
        before_dict = {row['폴더명']: row for _, row in df_before.iterrows()}
        after_dict = {row['폴더명']: row for _, row in df_after.iterrows()}
        
        results = []
        
        for folder_name, before_row in before_dict.items():
            if folder_name not in after_dict:
                # AFTER에 없는 폴더
                results.append({
                    '폴더명': folder_name,
                    '상태': 'AFTER에_없는_폴더',
                    '테이블_파일_수': before_row['테이블_파일_수'],
                    '이미지_파일_수': before_row['이미지_파일_수'],
                    '기타_파일_수': before_row.get('기타_파일_수', '0'),
                    '없어진_테이블_파일': before_row['테이블_파일_목록'],
                    '없어진_이미지_파일': before_row['이미지_파일_목록'],
                    '없어진_기타_파일': before_row.get('기타_파일_목록', ''),
                    '없어진_페이지_수': before_row['파일이_있는_페이지_수'],
                    '없어진_페이지_목록': before_row['파일이_있는_페이지_목록']
                })
            else:
                # 두 파일 모두에 있는 폴더 - 파일 비교
                after_row = after_dict[folder_name]
                
                # 파일 목록 비교
                before_table = self._parse_file_list(before_row['테이블_파일_목록'])
                after_table = self._parse_file_list(after_row['테이블_파일_목록'])
                
                before_image = self._parse_file_list(before_row['이미지_파일_목록'])
                after_image = self._parse_file_list(after_row['이미지_파일_목록'])
                
                before_etc = self._parse_file_list(before_row.get('기타_파일_목록', ''))
                after_etc = self._parse_file_list(after_row.get('기타_파일_목록', ''))
                
                before_pages = self._parse_file_list(before_row['파일이_있는_페이지_목록'])
                after_pages = self._parse_file_list(after_row['파일이_있는_페이지_목록'])
                
                # 누락된 항목들
                missing_table = before_table - after_table
                missing_image = before_image - after_image
                missing_etc = before_etc - after_etc
                missing_pages = before_pages - after_pages
                
                if missing_table or missing_image or missing_etc or missing_pages:
                    results.append({
                        '폴더명': folder_name,
                        '상태': '일부_파일_누락',
                        '테이블_파일_수': before_row['테이블_파일_수'],
                        '이미지_파일_수': before_row['이미지_파일_수'],
                        '기타_파일_수': before_row.get('기타_파일_수', '0'),
                        '없어진_테이블_파일': ', '.join(sorted(missing_table)) if missing_table else '',
                        '없어진_이미지_파일': ', '.join(sorted(missing_image)) if missing_image else '',
                        '없어진_기타_파일': ', '.join(sorted(missing_etc)) if missing_etc else '',
                        '없어진_페이지_수': len(missing_pages),
                        '없어진_페이지_목록': ', '.join(sorted(missing_pages)) if missing_pages else '',
                        '최종_페이지_목록': ', '.join(sorted(after_pages))
                    })
        
        return results
    
    def analyze_before(self) -> pd.DataFrame:
        """BEFORE 상태 분석 및 저장"""
        print(f"BEFORE 상태 분석 중: {self.crop_dir}")
        
        results = self.organize_crop_files()
        df = pd.DataFrame([r.to_dict() for r in results])
        
        print(f"총 {len(results)}개 폴더를 처리했습니다.")
        print("\n처리 결과:")
        print(df)
        
        df.to_excel(self.before_file, index=False)
        print(f"\nBEFORE 파일 저장 완료: {self.before_file}")
        
        return df
    
    def analyze_after(self) -> pd.DataFrame:
        """AFTER 상태 분석, 저장 및 비교"""
        print(f"AFTER 상태 분석 중: {self.crop_dir}")
        
        results = self.organize_crop_files()
        df = pd.DataFrame([r.to_dict() for r in results])
        
        print(f"총 {len(results)}개 폴더를 처리했습니다.")
        print("\n처리 결과:")
        print(df)
        
        df.to_excel(self.after_file, index=False)
        print(f"\nAFTER 파일 저장 완료: {self.after_file}")
        
        # BEFORE 파일이 존재하면 비교 분석 실행
        if not os.path.exists(self.before_file):
            print(f"\n⚠️ BEFORE 파일({self.before_file})이 존재하지 않아 비교 분석을 건너뜁니다.")
            return df
        
        print(f"\nBEFORE와 AFTER 파일 비교 분석 중...")
        comparison_results = self.compare_analysis_files()
        
        if comparison_results:
            df_comparison = pd.DataFrame(comparison_results)
            print(f"총 {len(comparison_results)}개 폴더에서 차이점을 발견했습니다.")
            print("\n비교 결과:")
            print(df_comparison)
            
            df_comparison.to_excel(self.comparison_file, index=False)
            print(f"\n비교 분석 파일 저장 완료: {self.comparison_file}")
        else:
            print("\n✅ 차이점이 발견되지 않았습니다.")
        
        return df


def main() -> int:
    """메인 함수"""
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
        print(f"❌ '{args.crop_dir}' 디렉토리가 존재하지 않습니다.")
        return 1
    
    analyzer = CropAnalyzer(args.crop_dir)
    
    if args.before:
        analyzer.analyze_before()
    elif args.after:
        analyzer.analyze_after()
    else:
        print("❌ --before 또는 --after 옵션 중 하나를 지정해야 합니다.")
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
