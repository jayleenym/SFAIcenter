import os, re, json
from typing import List, Dict, Any
import tools.ProcessFiles as pf

BASE_PATH = pf.BASE_PATH
CYCLE_PATH = pf.CYCLE_PATH
ORIGINAL_DATA_PATH = pf.ORIGINAL_DATA_PATH
FINAL_DATA_PATH = pf.FINAL_DATA_PATH

def format_change(i: int, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # merge_excel = pf.get_excel_data(i)

    # revision = {
    #     'file_id': str(merge_excel.loc[id, 'ISBN']),
    #     'title': merge_excel.loc[id, '도서명'],
    #     'cat1_domain': merge_excel.loc[id, '코퍼스 1분류'],
    #     'cat2_sub': merge_excel.loc[id, '코퍼스 2분류'],
    #     'cat3_specific': merge_excel.loc[id, '비고'],
    #     'pub_date': str(merge_excel.loc[id, '출판일'])[:10],
    #     'contents': [],
    # }
    # if 
    # for c in contents:
    #     if len(c) > 0:
    #         contents_base = {
    #         'page': f"{int(origin[i]['page']):04d}",
    #         'chapter': "",
    #         'page_contents': origin[i]['content'],
    #             "add_info": []
    #         }
    # revision['contents'].append(contents_base)
    # break
    return 0



def n_split(txt, sep):
    result = re.sub(r'(?<![.?!①②③④⑤\[\]])\n(?!\n)', ' ', txt)
    return result.split(sep)

def remove_enter(txt):
    # 문장 내 엔터 처리 (안함)
    return re.sub(r'(?<![.?!\]])\n(?!\n)', ' ', txt)

def extract_options(txt):
    pattern = r'([①②③④⑤]\s*[^①②③④⑤]*)'
    options = re.findall(pattern, txt)
    return [opt.replace("\n", " ").strip() for opt in options if opt.strip()]

def replace_number(number):
    circle_numbers = {'1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤'}
    return circle_numbers[str(number)]

def extract_chapter(c, n):
    #  chapter 추출하기
    page = int(c['page']) - n
    regex = fr"^(.*)\n{page}\n"

    chapter = re.findall(regex, c['page_contents'])

    c['chapter'] = chapter[0].strip()
    c['page_contents'] = re.sub(regex, "", c['page_contents'])
    
    # 248779244.json
    # c['page_contents'] = re.sub(fr"^{page}[가-힇]?", "", c['page_contents'])
    # c['page_contents'] = re.sub(title+str(page)+'\n', "", c['page_contents'])
    return c

def fill_chapter(file):
    pages = file["contents"]
    new_pages = []
    for i in range(len(pages)):
        c = pages[i]
        # chapter 채우기
        if (c['chapter'] == "") and i >= 1:
            c['chapter'] = pages[i-1]['chapter']
    
        if len(c['page_contents']) > 0:
                new_pages.append(c)

    output = file.copy()
    output["contents"] = new_pages
    return output



def extract_footnote(file):
    pages = file["contents"]
    
    # # 각주 처리
    # for fn in range(1, 43):
    #     if f"\n{fn} " in c['page_contents']:
    #         start = c['page_contents'].find(f"\n{fn} ")
    #         tag = f"note_{c['page']}_{len(c['add_info'])+1:04}"

    #         c['add_info'].append(
    #             {
    #                 "tag": tag,
    #                 "type": "footnote",
    #                 "description": c['page_contents'][start+1:], # 두개 겹쳐있으면 그대로..
    #                 "caption": 0,
    #                 "file_path": 0,
    #                 "bbox": 0
    #             }
    #         )
    #         c['page_contents'] = c['page_contents'].replace(c['page_contents'][start:], "{"+tag+"}")
    return c


def merge_paragraphs(file):
    pages = file["contents"]
    merged_pages = []
    buffer = ""

    for i, page in enumerate(pages):
        text = page["page_contents"]

        # 이전 페이지의 문단이 끊겼다면 이어 붙임
        if buffer:
            text = buffer.rstrip("\n") + " " + text.lstrip("\n")
            buffer = ""

        # 줄 단위로 분리
        lines = text.split("\n")

        # 현재 페이지 마지막 줄 확인
        last_line = lines[-1].strip()

        # 마지막 줄이 완전한 문단이 아니라면 → buffer에 저장
        if last_line and not last_line.endswith(("다.", "다.”", "다.\"","?", "!", ".", "…")):
            buffer = lines.pop(-1)

        # 다시 합쳐 저장
        page["page_contents"] = "\n".join(lines)
        merged_pages.append(page)

    # 마지막 buffer 남아있으면 마지막 페이지에 합침
    if buffer and merged_pages:
        merged_pages[-1]["page_contents"] += " " + buffer

    # 새로운 JSON 저장
    output = file.copy()
    output["contents"] = merged_pages

    return output