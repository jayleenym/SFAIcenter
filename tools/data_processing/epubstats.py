import PyPDF2
import pandas as pd
import os
import sys
import subprocess
from tqdm import tqdm

# 프로젝트 루트 경로 추가 (tools 모듈 import를 위해)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(os.path.dirname(current_dir))  # data_processing -> tools -> root
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)


def epub_to_pdf(filepath, oname: None, rename : None, ten: False):

    if rename: filename = filepath.replace(oname, rename).replace(".EPUB", ".pdf")
    else:      filename = filepath.replace(".EPUB", ".pdf")
    
    if ten:
        output_filename = filename.replace(".pdf", "-10p.pdf")
        result = subprocess.run(["/Applications/calibre.app/Contents/MacOS/ebook-convert", filepath, output_filename, "--base-font-size", "10"], 
                              capture_output=True, text=True)
    else:
        output_filename = filename
        result = subprocess.run(["/Applications/calibre.app/Contents/MacOS/ebook-convert", filepath, output_filename], 
                              capture_output=True, text=True)
    
    # Check if conversion was successful
    if result.returncode != 0:
        raise RuntimeError(f"EPUB to PDF conversion failed for {filepath}: {result.stderr}")
    
    # Verify the output file exists and is actually a file (not a directory)
    if not os.path.exists(output_filename):
        raise FileNotFoundError(f"Converted PDF file not found: {output_filename}")
    
    if os.path.isdir(output_filename):
        raise IsADirectoryError(f"Expected PDF file but got directory: {output_filename}")
    
    if not output_filename.lower().endswith('.pdf'):
        raise ValueError(f"Output file does not have .pdf extension: {output_filename}")

    return output_filename


def check_pdf_pages(cycle, output_file):
    from tools.core.utils import FileManager
    file_manager = FileManager()
    df = file_manager.load_excel_metadata(cycle)
    dir = os.path.join(file_manager.original_data_path, f'{cycle}C', 'Lv1')
    if not os.path.exists(dir):
        print(f"경로가 존재하지 않습니다: {dir}")
        return
    
    for file in tqdm(os.listdir(dir)):
        file_id = file.split(".")[0]
        if file.endswith(".PDF") or file.endswith(".pdf"):
            reader = PyPDF2.PdfReader(os.path.join(dir, file))
            df.loc[file_id, '본 페이지수'] = len(reader.pages)
            # print(file_id, len(reader.pages))

        if file.endswith(".EPUB"):
            try:
                name = epub_to_pdf(os.path.join(dir, file), file, file_id, ten=False)
                reader = PyPDF2.PdfReader(name)
                df.loc[file_id, '본 페이지수'] = len(reader.pages)

                name10 = epub_to_pdf(os.path.join(dir, file), file, file_id, ten=True)
                reader2 = PyPDF2.PdfReader(name10)
                df.loc[file_id, '10p 페이지수'] = len(reader2.pages)
            except Exception as e:
                print(f"Error processing {file_id}: {e}")
                continue
        else:
            continue
    
    df.reset_index(inplace=True)
    df.rename(columns={'index': '관리번호'}, inplace=True)
    df.to_excel(output_file, index=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycle', type=int, default=4)
    parser.add_argument('--output_file', type=str, default='pdf_pages.xlsx')
    args = parser.parse_args()
    check_pdf_pages(args.cycle, args.output_file)