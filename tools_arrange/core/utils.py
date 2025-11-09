#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 유틸리티 클래스
"""

import os
import json
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import shutil


class FileManager:
    """파일 및 경로 관리 클래스"""
    
    def __init__(self, base_path: str = None):
        """
        Args:
            base_path: 기본 경로 (None이면 OneDrive 경로 사용)
        """
        if base_path is None:
            self.base_path = os.path.join(
                os.path.expanduser("~"), 
                "Library/CloudStorage/OneDrive-개인/데이터L/selectstar"
            )
        else:
            self.base_path = base_path
        
        self.cycle_path = {1: '1C', 2: '2C', 3: '3C'}
        self.original_data_path = os.path.join(self.base_path, 'data', 'ORIGINAL')
        self.final_data_path = os.path.join(self.base_path, 'data', 'FINAL')
    
    def get_excel_data(self, cycle: int, base_path: str = None) -> pd.DataFrame:
        """Excel 데이터 읽기 및 병합"""
        if base_path is None:
            base_path = self.base_path
        
        analysis = {1: '1차 분석', 2: '2차 분석', 3: '3차 분석'}
        buy = {1: '1차 구매', 2: '2차 구매', 3: '3차 구매'}
        
        excel_analy = pd.read_excel(
            os.path.join(base_path, 'book_list_ALL.xlsx'), 
            sheet_name=analysis[cycle], 
            header=3
        )[['관리번호', 'ISBN', '도서명', '분류']]
        
        excel_buy = pd.read_excel(
            os.path.join(base_path, 'book_list_ALL.xlsx'), 
            sheet_name=buy[cycle], 
            header=4
        )[['ISBN', '도서명', '출판일', '코퍼스 1분류', '코퍼스 2분류', '비고']]
        excel_buy.fillna("", inplace=True)
        
        merge_excel = pd.merge(excel_analy, excel_buy, on=['ISBN', '도서명'], how='inner')
        merge_excel = merge_excel[['관리번호', 'ISBN', '도서명', '출판일', '코퍼스 1분류', '코퍼스 2분류', '비고', '분류']].set_index('관리번호')
        
        return merge_excel
    
    def get_filelist(self, cycle: int, data_path: str = None) -> List[str]:
        """JSON 파일 리스트 가져오기"""
        if data_path:
            final_data_path = data_path
        else:
            final_data_path = self.final_data_path
        
        final_data_path = os.path.join(final_data_path, self.cycle_path[cycle])
        
        json_files = []
        for root, _, files in os.walk(final_data_path):
            for f in files:
                if f.endswith(".json") and ('_' not in f):
                    json_files.append(os.path.join(root, f))
        
        return sorted(json_files)
    
    def move_jsons(self, cycle: int, final_data_path: str = None):
        """JSON 파일을 레벨별로 이동"""
        if final_data_path is None:
            final_data_path = self.final_data_path
        
        excel = self.get_excel_data(cycle)
        final_path = os.path.join(final_data_path, self.cycle_path[cycle])
        
        Lv2_isbn_id = [str(d) for d in excel[excel['분류'] == 'Lv2'].index]
        Lv3_isbn_id = [str(d) for d in excel[excel['분류'] == 'Lv3/4'].index]
        Lv5_isbn_id = [str(d) for d in excel[excel['분류'] == 'Lv5'].index]
        
        lv2 = os.path.join(final_path, "Lv2")
        lv34 = os.path.join(final_path, "Lv3_4")
        lv5 = os.path.join(final_path, "Lv5")
        
        os.makedirs(lv2, exist_ok=True)
        os.makedirs(lv34, exist_ok=True)
        os.makedirs(lv5, exist_ok=True)
        
        for id in os.listdir(final_path):
            file_path = os.path.join(final_path, id)
            if os.path.isfile(file_path):
                file_id = os.path.splitext(id)[0]
                if file_id in Lv3_isbn_id:
                    shutil.move(file_path, lv34)
                elif file_id in Lv5_isbn_id:
                    shutil.move(file_path, lv5)
                elif file_id in Lv2_isbn_id:
                    shutil.move(file_path, lv2)


class TextProcessor:
    """텍스트 처리 유틸리티 클래스"""
    
    @staticmethod
    def n_split(txt: str, sep: str) -> List[str]:
        """엔터 제거 후 분리"""
        result = re.sub(r'(?<![.?!①②③④⑤\[\]])\n(?!\n)', ' ', txt)
        return result.split(sep)
    
    @staticmethod
    def remove_enter(txt: str) -> str:
        """문장 내 엔터 처리"""
        return re.sub(r'(?<![.?!\]])\n(?!\n)(?![.?!])', ' ', txt)
    
    @staticmethod
    def extract_options(txt: str) -> List[str]:
        """선택지 추출"""
        pattern = r'([①②③④⑤]\s*[^①②③④⑤]*)'
        options = re.findall(pattern, txt)
        return [opt.replace("\n", " ").strip() for opt in options if opt.strip()]
    
    @staticmethod
    def replace_number(number: int) -> str:
        """숫자를 원형 숫자로 변환"""
        circle_numbers = {'1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤'}
        return circle_numbers.get(str(number), str(number))
    
    @staticmethod
    def extract_chapter(page_data: Dict, page_offset: int) -> Dict:
        """챕터 추출"""
        page = int(page_data['page']) - page_offset
        regex = fr"^(.*)\n{page}\n"
        
        chapter = re.findall(regex, page_data['page_contents'])
        if chapter:
            page_data['chapter'] = chapter[0].strip()
            page_data['page_contents'] = re.sub(regex, "", page_data['page_contents'])
        
        return page_data
    
    @staticmethod
    def fill_chapter(file_data: Dict) -> Dict:
        """챕터 정보 채우기"""
        pages = file_data["contents"]
        new_pages = []
        
        for i in range(len(pages)):
            c = pages[i].copy()
            if (c['chapter'] == "") and i >= 1:
                c['chapter'] = pages[i-1]['chapter']
            
            if len(c['page_contents']) > 0:
                new_pages.append(c)
        
        output = file_data.copy()
        output["contents"] = new_pages
        return output
    
    @staticmethod
    def merge_paragraphs(file_data: Dict) -> Dict:
        """문단 병합"""
        pages = file_data["contents"]
        merged_pages = []
        buffer = ""
        
        for i, page in enumerate(pages):
            text = page["page_contents"]
            
            if buffer:
                text = buffer.rstrip("\n") + " " + text.lstrip("\n")
                buffer = ""
            
            lines = text.split("\n")
            last_line = lines[-1].strip()
            
            if last_line and not last_line.endswith(("다.", "다."", "다.\"", "?", "!", ".", "…")):
                buffer = lines.pop(-1)
            
            page["page_contents"] = "\n".join(lines)
            merged_pages.append(page)
        
        if buffer and merged_pages:
            merged_pages[-1]["page_contents"] += " " + buffer
        
        output = file_data.copy()
        output["contents"] = merged_pages
        return output
    
    @staticmethod
    def normalize_option_text(s: str) -> str:
        """선지 텍스트 정규화"""
        if s is None:
            return ""
        s = str(s).strip()
        s = re.sub(r"^\s*[①-⑤]\s*", "", s)
        s = re.sub(r"^\s*(?:\(?([1-5])\)?[.)])\s*", "", s)
        return s.strip()


class JSONHandler:
    """JSON 파일 처리 클래스"""
    
    @staticmethod
    def load(file_path: str) -> Any:
        """JSON 파일 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def save(data: Any, file_path: str, indent: int = 2) -> None:
        """JSON 파일 저장"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
    
    @staticmethod
    def format_change(file_id: str, cycle: int, pages: List[Dict], file_manager: FileManager) -> Dict:
        """JSON 포맷 변경"""
        merge_excel = file_manager.get_excel_data(cycle)
        
        revision = {
            'file_id': str(merge_excel.loc[file_id, 'ISBN']),
            'title': merge_excel.loc[file_id, '도서명'],
            'cat1_domain': merge_excel.loc[file_id, '코퍼스 1분류'],
            'cat2_sub': merge_excel.loc[file_id, '코퍼스 2분류'],
            'cat3_specific': merge_excel.loc[file_id, '비고'],
            'pub_date': str(merge_excel.loc[file_id, '출판일'])[:10],
            'contents': [],
        }
        
        for c in pages:
            if len(c) > 0:
                contents_base = {
                    'page': f"{int(c['page']):04d}",
                    'chapter': "",
                    'page_contents': c['content'],
                    "add_info": []
                }
                revision['contents'].append(contents_base)
        
        return revision

