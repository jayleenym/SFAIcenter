import PyPDF2
import pandas as pd
import os
import subprocess
from tqdm import tqdm

def epub_to_pdf(filepath, oname: None, rename : None, ten: False):

    if rename: filename = filepath.replace(oname, rename).replace(".EPUB", ".pdf")
    else:      filename = filepath.replace(".EPUB", ".pdf")
    
    if ten:
        subprocess.run(["/Applications/calibre.app/Contents/MacOS/ebook-convert", filepath, filename.replace(".pdf", "-10p.pdf"), "--base-font-size", "10"])
    else:
        subprocess.run(["/Applications/calibre.app/Contents/MacOS/ebook-convert", filepath, filename])

    return filename


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
    
    df.reset_index(inplace=True)
    df.rename(columns={'index': '관리번호'}, inplace=True)
    df.to_excel(output_file, index=False)