import json
import os
import pandas as pd
import warnings
import shutil
# warnings.filterwarnings('ignore')

BASE_PATH = "/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/selectstar"
ORIGINAL_DATA_PATH = os.path.join(BASE_PATH, 'data', 'ORIGINAL', '1C')

CYCLE_PATH = {
    1 : '1C',
    2 : '2C_0902',
    3 : '3C_0902' 
    }

FINAL_DATA_PATH = os.path.join(BASE_PATH, 'data', 'FINAL')


def get_excel_data(i: int, base_path = None):
    if base_path:
        base_path
    else:
        base_path = BASE_PATH

    analysis = {1:'1차 분석', 2:'2차 분석', 3: '3차 분석'}
    buy = {1:'1차 구매', 2:'2차 구매', 3: '3차 구매'}

    excel_analy = pd.read_excel(os.path.join(base_path, '도서목록_전체통합.xlsx'), sheet_name=analysis[i], header=3)[['관리번호', 'ISBN', '도서명', '분류']]
    excel_buy = pd.read_excel(os.path.join(base_path, '도서목록_전체통합.xlsx'), sheet_name=buy[i], header=4)[['ISBN', '도서명', '출판일', '코퍼스 1분류', '코퍼스 2분류', '비고']]
    excel_buy.fillna("", inplace=True)

    merge_excel = pd.merge(excel_analy, excel_buy, on=['ISBN', '도서명'], how='inner')
    merge_excel = merge_excel[['관리번호', 'ISBN', '도서명', '출판일', '코퍼스 1분류', '코퍼스 2분류', '비고', '분류']].set_index('관리번호')

    return merge_excel



def change_names(excel, from_name: str, to_name: str, file_path):
    for (fn, tn) in zip(excel[from_name], excel[to_name]):
        print(fn, tn)
        # 복사할 파일 경로
        # source_file = os.path.join(data_dir, '1C_0902', str(isbn)+'.json')
        # 복사할 목적지 경로
        # destination_path = os.path.join(data_dir, '1C_0902')
        # 이름변경
        shutil.copy2(file_path, file_path.replace(fn, tn))
        break


def move_jsons(i):
    # 폴더 만들어 옮기기
    excel = get_excel_data(i)
    FINAL_DATA_PATH = os.path.join(FINAL_DATA_PATH, CYCLE_PATH[i])

    Lv2_isbn_id = [str(d) for d in excel[excel['분류'] == 'Lv2'].index]
    Lv3_isbn_id = [str(d) for d in excel[excel['분류'] == 'Lv3/4'].index]
    Lv5_isbn_id = [str(d) for d in excel[excel['분류'] == 'Lv5'].index]
    
    lv2 = os.path.join(FINAL_DATA_PATH, "Lv2")
    lv34 = os.path.join(FINAL_DATA_PATH, "Lv3_4")
    lv5 = os.path.join(FINAL_DATA_PATH, "Lv5")
    
    for id in os.listdir(FINAL_DATA_PATH):
        if os.path.splitext(id)[0] in Lv3_isbn_id:
            shutil.move(os.path.join(FINAL_DATA_PATH, str(id)), lv34)
        elif os.path.splitext(id)[0] in Lv5_isbn_id:
            shutil.move(os.path.join(FINAL_DATA_PATH, str(id)), lv5)
        elif os.path.splitext(id)[0] in Lv2_isbn_id:
            shutil.move(os.path.join(FINAL_DATA_PATH, str(id)), lv2)


def get_filelist(i, data_path = None, FINAL_DATA_PATH = FINAL_DATA_PATH):
    if data_path:
        FINAL_DATA_PATH = data_path
    else:
        FINAL_DATA_PATH = os.path.join(FINAL_DATA_PATH, CYCLE_PATH[i])

    json_files = []
    for root, _, files in os.walk(FINAL_DATA_PATH):
        for f in files:
            if f.endswith(".json") and ('_' not in f):
            #  and ('Lv5' not in root):
                json_files.append(os.path.join(root, f))
                # json_files.append(int(os.path.splitext(f)[0]))
    return sorted(json_files)