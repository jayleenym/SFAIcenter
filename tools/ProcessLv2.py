import os, re
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

def fill_chapter(pages):
    new_pages = []
    for i in range(len(pages)):
        c = pages[i]
        # chapter 채우기
        if (c['chapter'] == "") and i >= 1:
            c['chapter'] = pages[i-1]['chapter']
    
        if len(c['page_contents']) > 0:
                new_pages.append(c)

    return new_pages




# def extract_qna(c):
#     print('---------------------')
#     print(c['page'])
# # for i in range(len())
#     # 문제추출
#     # qn_re = r'\[문제\d+\]\s'
#     qn_re = r'\s?문제 [0-9]+:'
#     # qn_re = r'\s?[0-9][0-9]'
#     # info_re = r'\[\w+[.]?\d+\w\]\s'
#     # q_re = r"\s*[^?]*\?"
#     # ans_re = r"\[정답\]"
#     ans_re = r"\s?정답:"
#     # exp_re = r"\s\[해설\]"
#     exp_re = r"\s?해설:"
#     option_re = r"\s?①"
    
#     base_add_info = {
#                         'tag': "",
#                         'type': "question",
#                         "description": {
#                             "number": "",
#                             "question": "",
#                             "options": [],
#                             'answer' : "",
#                             "explanation": ""
#                         },
#                         "caption":[],
#                         "file_path": 0,
#                         "bbox": 0
#                         }

#     # 문제는 있음
#     if re.search(qn_re, c['page_contents']) is not None:

#         base_add_info['tag'] = f"q_{c['page']}_0001"

#         start = re.search(qn_re, c['page_contents']).span()[0]
#         try:
#             end = re.search(ans_re, c['page_contents']).span()[1]
#             # 한 페이지에 문제~정답 모두 있음
#             # qna = [qa for qa in re.split(fr"({qn_re}|{info_re}|{q_re}|{exp_re}|{ans_re})", c['page_contents'][start:]) if qa !=""]
#             qna = [qa for qa in re.split(fr"({qn_re}|{option_re}|{exp_re}|{ans_re})", c['page_contents'][start:]) if qa !=""]
#             # 태그처리
#             c['page_contents'] = c['page_contents'].replace(c['page_contents'][start:end+2], "\n{"+f"q_{c['page']}_0001"+"}")
        
#         except:
#             # 다음페이지 살펴보기
#             c2 = origin['contents'][i+1]
#             if re.search(ans_re, c2['page_contents']) is not None:
#                 end = re.search(ans_re, c2['page_contents']).span()[1]

#                 qna = [qa 
#                     # for qa in re.split(fr"({qn_re}|{info_re}|{q_re}|{exp_re}|{ans_re})", 
#                     for qa in re.split(fr"({qn_re}|{option_re}|{exp_re}|{ans_re})", 
#                                         c['page_contents'][start:]+c2['page_contents'][:end+2])
#                     if qa !=""
#                     ]
                
#                 # 태그처리
#                 c['page_contents'] = c['page_contents'].replace(c['page_contents'][start:], "\n{"+f"q_{c['page']}_0001"+"}")
#                 c2['page_contents'] = c2['page_contents'].replace(c2['page_contents'][:end+2], "")
            
#             # 그 다음 페이지도 살펴보기
#             elif re.search(ans_re, c2['page_contents']) is None:
#                 c3 = origin['contents'][i+2]
#                 if re.search(ans_re, c3['page_contents']) is not None:
#                     end = re.search(ans_re, c3['page_contents']).span()[1]
#                     qna = [qa 
#                         # for qa in re.split(fr"({qn_re}|{info_re}|{q_re}|{exp_re}|{ans_re})", 
#                         for qa in re.split(fr"({qn_re}|{option_re}|{exp_re}|{ans_re})", 
#                                             c['page_contents'][start:]+c2['page_contents']+c3['page_contents'][:end+2])
#                         if qa !=""
#                         ]
                    
#                     # 태그처리
#                     c['page_contents'] = c['page_contents'].replace(c['page_contents'][start:], "\n{"+f"q_{c['page']}_0001"+"}")
#                     c2['page_contents'] = c2['page_contents'].replace(c2['page_contents'], "")
#                     c3['page_contents'] = c3['page_contents'].replace(c3['page_contents'][:end+2], "")
#             else:
#                 print("못찾겟다..")

#         print(qna)
#         for x in range(len(qna)):
#             if re.search(qn_re, qna[x]) is not None:
#                 # number = re.search(r'\[문제(\d+)*\]', qna[x]).group(1)
#                 number = qna[x].strip()
#                 print('number:', number)
#                 # if int(number) < 10:
#                 #     number = f"{int(number):02}"
#                 base_add_info['description']['number'] = number
#                 try:
#                     question = qna[x+1]
#                     question = question.strip()

#                     base_add_info['description']['question'] = question
#                 except:
#                     print("(ERROR) question:", question)

#             # if re.search(info_re, qna[x]) is not None:
#             #     base_add_info['caption'].append(re.search(r'\[(\w+[.]?\d+\w)\]', qna[x]).group(1))
#             #     if base_add_info['caption'][0].startswith("문제"):
#             #         base_add_info['caption'].pop(0)

#             # if re.search(q_re, qna[x]) is not None:
#             #     question = re.search(r'\s*([^?]*\?)', qna[x]).group(1)
#             #     options = [ca.strip() for ca in n_split(qna[x+1].replace("❑",""), "\n") if ca != ""]
#             #     for ct in range(len(options)):
#             #         if '①' not in options[0]:
#             #             question += " "+options[0]
#                         # options = options[1:]
                
#             if re.search(option_re, qna[x]) is not None:
#                 try:
#                     options = [qna[x]+qna[x+1]]
#                 except:
#                     print("(ERROR) options:", options)
#                 if len(options) == 1:
#                     options = extract_options(options[0])
#                 print("options_re:", options)
#                 base_add_info['description']['options'] = options

#             if re.search(exp_re, qna[x]) is not None:
#                 explanation = qna[x+1].strip()
#                 print("explanation:", explanation)
#                 base_add_info['description']['explanation'] = explanation

#             if re.search(ans_re, qna[x]) is not None:
#                 answer = qna[x+1].strip()
#                 print("answer:", answer)
#                 if answer in "①②③④⑤":
#                     base_add_info['description']['answer'] = answer
#                 elif answer.isnumeric():
#                     answer = replace_number(answer)
#                     base_add_info['description']['answer'] = answer
#                 else:
#                     print(c['page'], end, answer)
            
#             # base_add_info['caption'].append("매경 TEST 기출 문제")

#         c['add_info'].append(base_add_info)
#     return c

def extract_footnote(c):
    # 각주 처리
    for fn in range(1, 43):
        if f"\n{fn} " in c['page_contents']:
            start = c['page_contents'].find(f"\n{fn} ")
            tag = f"note_{c['page']}_{len(c['add_info'])+1:04}"

            c['add_info'].append(
                {
                    "tag": tag,
                    "type": "footnote",
                    "description": c['page_contents'][start+1:], # 두개 겹쳐있으면 그대로..
                    "caption": 0,
                    "file_path": 0,
                    "bbox": 0
                }
            )
            c['page_contents'] = c['page_contents'].replace(c['page_contents'][start:], "{"+tag+"}")
    return c