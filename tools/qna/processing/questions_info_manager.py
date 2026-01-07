#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
문제 정보 관리 모듈
- questions_info.json 파일 생성 및 관리
- 기존 _DST.json 파일들에서 참조 정보를 추출하여 저장
- fill_domain.py에서 lookup 용도로 사용
"""

import os
import glob
import json
import logging
from typing import Dict, Any, List, Tuple, Optional


class QuestionsInfoManager:
    """문제 정보 관리 클래스"""
    
    # 저장할 필드 목록
    INFO_FIELDS = ['file_id', 'tag', 'domain', 'subdomain', 'is_calculation', 'is_table', 'classification_reason']
    
    def __init__(self, onedrive_path: str, logger: logging.Logger = None):
        self.onedrive_path = onedrive_path
        self.logger = logger or logging.getLogger(__name__)
        self.subdomain_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '2_subdomain')
        self.info_file = os.path.join(self.subdomain_dir, 'questions_info.json')
    
    def _extract_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """문제 항목에서 필요한 정보만 추출"""
        info = {}
        for field in self.INFO_FIELDS:
            if field in item:
                info[field] = item[field]
        return info
    
    def _is_valid_info(self, info: Dict[str, Any]) -> bool:
        """유효한 정보인지 확인 (domain, subdomain이 채워져 있어야 함)"""
        domain = str(info.get('domain', '')).strip()
        subdomain = str(info.get('subdomain', '')).strip()
        
        invalid_values = ['', '분류실패', 'API호출실패', '파싱실패', 'None', 'null']
        
        return (domain and subdomain and 
                domain not in invalid_values and 
                subdomain not in invalid_values)
    
    def load(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """
        questions_info.json 파일을 로드하여 lookup dict 반환
        
        Returns:
            {(file_id, tag): {domain, subdomain, ...}} 형태의 딕셔너리
        """
        if not os.path.exists(self.info_file):
            self.logger.info(f"questions_info.json 파일이 없습니다. 빈 딕셔너리 반환")
            return {}
        
        try:
            with open(self.info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            lookup = {}
            for item in data:
                file_id = str(item.get('file_id', ''))
                tag = str(item.get('tag', ''))
                if file_id and tag:
                    lookup[(file_id, tag)] = item
            
            self.logger.info(f"questions_info.json 로드 완료: {len(lookup)}개 항목")
            return lookup
            
        except Exception as e:
            self.logger.error(f"questions_info.json 로드 실패: {e}")
            return {}
    
    def save(self, lookup: Dict[Tuple[str, str], Dict[str, Any]]) -> bool:
        """
        lookup dict를 questions_info.json 파일로 저장
        
        Args:
            lookup: {(file_id, tag): {domain, subdomain, ...}} 형태의 딕셔너리
            
        Returns:
            저장 성공 여부
        """
        try:
            # dict를 list로 변환
            data = list(lookup.values())
            
            # file_id, tag 기준으로 정렬
            data.sort(key=lambda x: (x.get('file_id', ''), x.get('tag', '')))
            
            os.makedirs(self.subdomain_dir, exist_ok=True)
            
            with open(self.info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"questions_info.json 저장 완료: {len(data)}개 항목")
            return True
            
        except Exception as e:
            self.logger.error(f"questions_info.json 저장 실패: {e}")
            return False
    
    def update(self, new_items: List[Dict[str, Any]]) -> int:
        """
        새로운 항목들로 questions_info.json 업데이트
        
        Args:
            new_items: 새로운 문제 항목 리스트
            
        Returns:
            업데이트된 항목 수
        """
        lookup = self.load()
        updated_count = 0
        
        for item in new_items:
            info = self._extract_info(item)
            
            if not self._is_valid_info(info):
                continue
            
            file_id = str(info.get('file_id', ''))
            tag = str(info.get('tag', ''))
            
            if not file_id or not tag:
                continue
            
            key = (file_id, tag)
            
            # 기존에 없거나 새 정보가 더 완전한 경우 업데이트
            if key not in lookup or self._is_valid_info(info):
                lookup[key] = info
                updated_count += 1
        
        if updated_count > 0:
            self.save(lookup)
        
        return updated_count
    
    def build_from_dst_files(self) -> Dict[str, int]:
        """
        모든 _DST.json 파일들에서 정보를 추출하여 questions_info.json 생성
        
        Returns:
            {'total': 전체 항목 수, 'valid': 유효 항목 수} 형태의 통계
        """
        dst_files = glob.glob(os.path.join(self.subdomain_dir, '*_DST.json'))
        
        if not dst_files:
            self.logger.warning("_DST.json 파일이 없습니다.")
            return {'total': 0, 'valid': 0}
        
        lookup = {}
        total_count = 0
        valid_count = 0
        
        for dst_file in dst_files:
            try:
                with open(dst_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, list):
                    continue
                
                file_name = os.path.basename(dst_file)
                self.logger.info(f"처리 중: {file_name} ({len(data)}개 항목)")
                
                for item in data:
                    total_count += 1
                    info = self._extract_info(item)
                    
                    if not self._is_valid_info(info):
                        continue
                    
                    file_id = str(info.get('file_id', ''))
                    tag = str(info.get('tag', ''))
                    
                    if not file_id or not tag:
                        continue
                    
                    key = (file_id, tag)
                    lookup[key] = info
                    valid_count += 1
                    
            except Exception as e:
                self.logger.error(f"파일 처리 실패 {dst_file}: {e}")
        
        # 저장
        self.save(lookup)
        
        stats = {
            'total': total_count,
            'valid': valid_count,
            'files_processed': len(dst_files)
        }
        
        self.logger.info(f"questions_info.json 생성 완료: {stats}")
        return stats


def main():
    """CLI로 실행 시"""
    import argparse
    
    parser = argparse.ArgumentParser(description='questions_info.json 관리')
    parser.add_argument('--onedrive', type=str, required=True, help='OneDrive 경로')
    parser.add_argument('--build', action='store_true', help='_DST.json 파일들에서 questions_info.json 생성')
    
    args = parser.parse_args()
    
    # 로거 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    manager = QuestionsInfoManager(args.onedrive)
    
    if args.build:
        stats = manager.build_from_dst_files()
        print(f"\n=== 완료 ===")
        print(f"처리된 파일: {stats.get('files_processed', 0)}개")
        print(f"전체 항목: {stats.get('total', 0)}개")
        print(f"유효 항목: {stats.get('valid', 0)}개")


if __name__ == '__main__':
    main()

