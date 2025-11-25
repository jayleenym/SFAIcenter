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
            # pipeline/config에서 ONEDRIVE_PATH import 시도
            try:
                import sys
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(current_dir))
                sys.path.insert(0, project_root)
                from pipeline.config import ONEDRIVE_PATH
                self.base_path = ONEDRIVE_PATH
            except ImportError:
                # fallback: pipeline이 없는 경우 플랫폼별 기본값 사용
                import platform
                system = platform.system()
                home_dir = os.path.expanduser("~")
                
                if system == "Windows":
                    # Windows OneDrive 경로
                    self.base_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
                else:
                    # macOS 기본 경로
                    self.base_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
        else:
            self.base_path = base_path
        
        self.cycle_path = {1: '1C', 2: '2C', 3: '3C'}
        self.original_data_path = os.path.join(self.base_path, 'data', 'ORIGINAL')
        self.final_data_path = os.path.join(self.base_path, 'data', 'FINAL')
    
    def load_excel_metadata(self, cycle: int, base_path: str = None) -> pd.DataFrame:
        """Excel 파일에서 도서 메타데이터 읽기 및 병합"""
        if base_path is None:
            base_path = self.base_path
        
        analysis = {1: '1차 분석', 2: '2차 분석', 3: '3차 분석', 4: '4차 분석'}
        buy = {1: '1차 구매', 2: '2차 구매', 3: '3차 구매', 4: '4차 구매'}
        
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
    
    def get_json_file_list(self, cycle: int, data_path: str = None) -> List[str]:
        """지정된 사이클의 JSON 파일 리스트 반환"""
        if data_path:
            # data_path가 주어졌을 때, 이미 cycle_path가 포함되어 있는지 확인
            # 예: data_path가 ".../1C/Lv2" 형태면 그대로 사용
            if self.cycle_path[cycle] in data_path:
                target_path = data_path
            else:
                # cycle_path가 없으면 추가
                target_path = os.path.join(data_path, self.cycle_path[cycle])
        else:
            # data_path가 없으면 기본 경로 사용
            target_path = os.path.join(self.final_data_path, self.cycle_path[cycle])
        
        json_files = []
        for root, _, files in os.walk(target_path):
            for f in files:
                if f.endswith(".json") and ('_' not in f):
                    json_files.append(os.path.join(root, f))
        
        return sorted(json_files)
    
    def organize_files_by_level(self, cycle: int, data_path: str = None):
        """JSON 파일을 레벨(Lv2, Lv3/4, Lv5)별로 분류하여 이동"""
        base_path = data_path if data_path else self.final_data_path
        target_path = os.path.join(base_path, self.cycle_path[cycle])
        
        excel = self.load_excel_metadata(cycle)
        lv2_ids = {str(d) for d in excel[excel['분류'] == 'Lv2'].index}
        lv3_ids = {str(d) for d in excel[excel['분류'] == 'Lv3/4'].index}
        lv5_ids = {str(d) for d in excel[excel['분류'] == 'Lv5'].index}
        
        lv2_dir = os.path.join(target_path, "Lv2")
        lv34_dir = os.path.join(target_path, "Lv3_4")
        lv5_dir = os.path.join(target_path, "Lv5")
        
        for dir_path in [lv2_dir, lv34_dir, lv5_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        for filename in os.listdir(target_path):
            file_path = os.path.join(target_path, filename)
            if not os.path.isfile(file_path):
                continue
            
            file_id = os.path.splitext(filename)[0]
            if file_id in lv3_ids:
                shutil.move(file_path, lv34_dir)
            elif file_id in lv5_ids:
                shutil.move(file_path, lv5_dir)
            elif file_id in lv2_ids:
                shutil.move(file_path, lv2_dir)


class TextProcessor:
    """텍스트 처리 유틸리티 클래스"""
    
    @staticmethod
    def remove_inline_newlines(text: str) -> str:
        """문장 내 엔터 제거 (문장 끝 엔터는 유지)"""
        return re.sub(r'(?<![.?!\]])\n(?!\n)(?![.?!])', ' ', text)
    
    @staticmethod
    def split_text_with_newline_removal(text: str, separator: str) -> List[str]:
        """엔터 제거 후 텍스트 분리"""
        # remove_inline_newlines를 재사용
        cleaned_text = TextProcessor.remove_inline_newlines(text)
        return cleaned_text.split(separator)
    
    @staticmethod
    def extract_choice_options(text: str) -> List[str]:
        """선택지(①~⑤) 추출"""
        pattern = r'([①②③④⑤]\s*[^①②③④⑤]*)'
        options = re.findall(pattern, text)
        return [opt.replace("\n", " ").strip() for opt in options if opt.strip()]
    
    @staticmethod
    def convert_to_circle_number(number: int) -> str:
        """숫자를 원형 숫자(①~⑤)로 변환"""
        circle_numbers = {'1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤'}
        return circle_numbers.get(str(number), str(number))
    
    @staticmethod
    def fill_missing_chapters(file_data: Dict) -> Dict:
        """빈 챕터 정보를 이전 페이지의 챕터로 채우기"""
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
    def merge_broken_paragraphs(file_data: Dict) -> Dict:
        """페이지 경계에서 끊어진 문단 병합"""
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
            
            if last_line and not last_line.endswith(("다.", "다.\"", "?", "!", ".", "…")):
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
    def convert_json_format(file_id: str, cycle: int, pages: List[Dict], file_manager: FileManager) -> Dict:
        """JSON 데이터 구조 변환 (원본 형식 → 표준 형식)"""
        merge_excel = file_manager.load_excel_metadata(cycle)
        
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

