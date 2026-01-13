#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB/PDF 페이지 수 분석 스크립트

EPUB 파일을 PDF로 변환하고 페이지 수를 분석합니다.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

import PyPDF2
import pandas as pd
from tqdm import tqdm

# 프로젝트 루트 경로 추가 (tools 모듈 import를 위해)
current_dir = Path(__file__).parent
project_root_dir = current_dir.parent.parent
if str(project_root_dir) not in sys.path:
    sys.path.insert(0, str(project_root_dir))


# Calibre ebook-convert 경로
CALIBRE_CONVERT_PATH = "/Applications/calibre.app/Contents/MacOS/ebook-convert"


def epub_to_pdf(
    filepath: str,
    original_name: Optional[str] = None,
    rename_to: Optional[str] = None,
    use_10pt_font: bool = False
) -> str:
    """
    EPUB 파일을 PDF로 변환합니다.
    
    Args:
        filepath: EPUB 파일 경로
        original_name: 원본 파일명 (교체 대상)
        rename_to: 새로운 파일명 (교체할 이름)
        use_10pt_font: True면 10pt 폰트로 변환
        
    Returns:
        변환된 PDF 파일 경로
        
    Raises:
        RuntimeError: 변환 실패 시
        FileNotFoundError: 변환된 파일이 없을 때
        IsADirectoryError: 결과가 디렉토리일 때
        ValueError: 확장자가 .pdf가 아닐 때
    """
    # 출력 파일명 결정
    if rename_to and original_name:
        filename = filepath.replace(original_name, rename_to).replace(".EPUB", ".pdf")
    else:
        filename = filepath.replace(".EPUB", ".pdf")
    
    # 10pt 폰트 사용 시 파일명 변경
    if use_10pt_font:
        output_filename = filename.replace(".pdf", "-10p.pdf")
        cmd = [CALIBRE_CONVERT_PATH, filepath, output_filename, "--base-font-size", "10"]
    else:
        output_filename = filename
        cmd = [CALIBRE_CONVERT_PATH, filepath, output_filename]
    
    # 변환 실행
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"EPUB to PDF conversion failed for {filepath}: {result.stderr}")
    
    # 결과 파일 검증
    if not os.path.exists(output_filename):
        raise FileNotFoundError(f"Converted PDF file not found: {output_filename}")
    
    if os.path.isdir(output_filename):
        raise IsADirectoryError(f"Expected PDF file but got directory: {output_filename}")
    
    if not output_filename.lower().endswith('.pdf'):
        raise ValueError(f"Output file does not have .pdf extension: {output_filename}")

    return output_filename


def check_pdf_pages(cycle: int, output_file: str) -> None:
    """
    지정된 사이클의 PDF/EPUB 파일들의 페이지 수를 확인합니다.
    
    Args:
        cycle: 처리할 사이클 번호
        output_file: 결과를 저장할 Excel 파일 경로
    """
    from tools.core.utils import FileManager
    
    file_manager = FileManager()
    df = file_manager.load_excel_metadata(cycle)
    
    target_dir = os.path.join(file_manager.original_data_path, f'{cycle}C', 'Lv1')
    
    if not os.path.exists(target_dir):
        print(f"경로가 존재하지 않습니다: {target_dir}")
        return
    
    files = [f for f in os.listdir(target_dir) if not f.startswith('.')]
    
    for file in tqdm(files, desc="PDF 페이지 수 확인"):
        file_id = file.split(".")[0]
        file_path = os.path.join(target_dir, file)
        
        # PDF 파일 처리
        if file.lower().endswith('.pdf'):
            try:
                reader = PyPDF2.PdfReader(file_path)
                df.loc[file_id, '본 페이지수'] = len(reader.pages)
            except Exception as e:
                print(f"Error reading PDF {file_id}: {e}")
                continue
        
        # EPUB 파일 처리
        elif file.endswith(".EPUB"):
            try:
                # 기본 PDF 변환
                pdf_path = epub_to_pdf(file_path, file, file_id, use_10pt_font=False)
                reader = PyPDF2.PdfReader(pdf_path)
                df.loc[file_id, '본 페이지수'] = len(reader.pages)
                
                # 10pt 폰트 PDF 변환
                pdf_10pt_path = epub_to_pdf(file_path, file, file_id, use_10pt_font=True)
                reader_10pt = PyPDF2.PdfReader(pdf_10pt_path)
                df.loc[file_id, '10p 페이지수'] = len(reader_10pt.pages)
                
            except Exception as e:
                print(f"Error processing EPUB {file_id}: {e}")
                continue
    
    # 결과 저장
    df.reset_index(inplace=True)
    df.rename(columns={'index': '관리번호'}, inplace=True)
    df.to_excel(output_file, index=False)
    print(f"결과 저장 완료: {output_file}")


def main() -> int:
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PDF/EPUB 파일의 페이지 수를 분석합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--cycle', '-c',
        type=int,
        default=4,
        help='처리할 사이클 번호 (기본값: 4)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='pdf_pages.xlsx',
        help='결과 Excel 파일 경로 (기본값: pdf_pages.xlsx)'
    )
    
    args = parser.parse_args()
    
    check_pdf_pages(args.cycle, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
