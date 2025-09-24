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


def check_pdf_pages(input, ouput, dir):
    df = pd.read_excel(input, header=4)[['관리 ID', '도서명']]

    for file in tqdm(os.listdir(dir)):
        isbn = file.split(".")[0]

        if file.endswith(".EPUB"):
            name = epub_to_pdf(dir+file, file, isbn)
            reader = PyPDF2.PdfReader(name)
            df.loc[df[df['ISBN'] == int(isbn)].index[0], '본 페이지수'] = len(reader.pages)

            name10 = epub_to_pdf(dir+file, file, isbn, True)    
            reader2 = PyPDF2.PdfReader(name10)
            df.loc[df[df['ISBN'] == int(isbn)].index[0], '10p 페이지수'] = len(reader2.pages)


        if file.endswith(".PDF") or file.endswith(".pdf"):
            reader = PyPDF2.PdfReader(dir+file)
            # df.loc[df[df['ISBN'] == int(isbn)].index[0], '본 페이지수'] = len(reader3.pages)
            df.loc[df[df['관리 ID'] == isbn].index[0], '본 페이지수'] = len(reader.pages)
            
    df.to_excel(ouput, index=False)