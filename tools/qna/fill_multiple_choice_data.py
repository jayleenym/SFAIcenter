#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multiple-choice.json 파일에 multiple_subdomain_classified_ALL.json 파일의 데이터를 채워넣는 스크립트

file_id와 tag를 기준으로 매칭하여 domain, subdomain, classification_reason, is_calculation 필드를 채워넣습니다.
"""

import json
import os
import sys
import argparse
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from datetime import datetime

# tools 모듈 import를 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(current_dir)  # qna -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir
sys.path.insert(0, tools_dir)
from tools.core.utils import JSONHandler


def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """JSON 파일을 로드합니다. (JSONHandler 사용)"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    return JSONHandler.load(file_path)


def create_lookup_dict(source_data: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    source_data에서 (file_id, tag)를 키로 하는 lookup 딕셔너리를 생성합니다.
    
    Args:
        source_data: multiple_subdomain_classified_ALL.json의 데이터
        
    Returns:
        {(file_id, tag): {domain, subdomain, classification_reason, is_calculation}} 형태의 딕셔너리
    """
    lookup = {}
    
    for item in source_data:
        file_id = item.get('file_id')
        tag = item.get('tag')
        
        if file_id is None or tag is None:
            continue
        
        # file_id와 tag를 키로 사용
        key = (str(file_id), str(tag))
        
        # domain, subdomain, classification_reason, is_calculation 정보 추출
        lookup[key] = {
            'domain': item.get('domain'),
            'subdomain': item.get('subdomain'),
            'classification_reason': item.get('classification_reason'),
            'is_calculation': item.get('is_calculation')
        }
    
    return lookup


def fill_multiple_choice_data(
    multiple_choice_data: List[Dict[str, Any]],
    lookup_dict: Dict[Tuple[str, str], Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    multiple-choice.json 데이터를 lookup_dict를 사용하여 채워넣습니다.
    
    Args:
        multiple_choice_data: multiple-choice.json의 데이터
        lookup_dict: (file_id, tag)를 키로 하는 lookup 딕셔너리
        
    Returns:
        (업데이트된 데이터, 통계 정보)
    """
    stats = {
        'total': len(multiple_choice_data),
        'matched': 0,
        'unmatched': 0,
        'domain_filled': 0,
        'subdomain_filled': 0,
        'classification_reason_filled': 0,
        'is_calculation_filled': 0
    }
    
    for item in multiple_choice_data:
        file_id = item.get('file_id')
        tag = item.get('tag')
        
        if file_id is None or tag is None:
            stats['unmatched'] += 1
            continue
        
        key = (str(file_id), str(tag))
        
        if key in lookup_dict:
            source_data = lookup_dict[key]
            stats['matched'] += 1
            
            # domain 채우기
            if 'domain' in source_data and source_data['domain'] is not None:
                item['domain'] = source_data['domain']
                stats['domain_filled'] += 1
            
            # subdomain 채우기
            if 'subdomain' in source_data and source_data['subdomain'] is not None:
                item['subdomain'] = source_data['subdomain']
                stats['subdomain_filled'] += 1
            
            # classification_reason 채우기
            if 'classification_reason' in source_data and source_data['classification_reason'] is not None:
                item['classification_reason'] = source_data['classification_reason']
                stats['classification_reason_filled'] += 1
            
            # is_calculation 채우기
            if 'is_calculation' in source_data and source_data['is_calculation'] is not None:
                item['is_calculation'] = source_data['is_calculation']
                stats['is_calculation_filled'] += 1
        else:
            stats['unmatched'] += 1
    
    return multiple_choice_data, stats


def main():
    parser = argparse.ArgumentParser(
        description='multiple-choice.json 파일에 multiple_subdomain_classified_ALL.json의 데이터를 채워넣습니다.'
    )
    parser.add_argument(
        '--multiple_choice',
        type=str,
        default=None,
        help='multiple-choice.json 파일 경로'
    )
    parser.add_argument(
        '--source',
        type=str,
        default=None,
        help='multiple_subdomain_classified_ALL.json 파일 경로'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 파일 경로 (기본값: 자동 생성)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='원본 파일을 백업할지 여부'
    )
    
    args = parser.parse_args()
    
    # 기본 경로 설정 (evaluation_yejin 디렉토리 기준)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    eval_dir = os.path.join(project_root, 'evaluation_yejin', 'eval_data')
    
    # 파일 경로 설정
    if args.source:
        source_path = args.source
    else:
        source_path = os.path.join(eval_dir, '2_subdomain', 'multiple_subdomain_classified_ALL.json')
    
    if args.multiple_choice:
        multiple_choice_path = args.multiple_choice
    else:
        multiple_choice_path = os.path.join(eval_dir, '2_subdomain', 'multiple-choice.json')
    
    # 출력 파일 경로 생성 (타임스탬프 포함)
    if args.output:
        output_path = args.output
    else:
        # source 파일과 같은 디렉토리에 저장
        source_dir = os.path.dirname(source_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(source_dir, f'multiple_subdomain_classified_ALL_new.json')
    
    print(f"1. multiple_subdomain_classified_ALL.json 파일 로딩: {source_path}")
    source_data = load_json_file(source_path)
    
    print(f"2. multiple-choice.json 파일 로딩: {multiple_choice_path}")
    multiple_choice_data = load_json_file(multiple_choice_path)
    
    print(f"3. Lookup 딕셔너리 생성 중...")
    lookup_dict = create_lookup_dict(source_data)
    print(f"  - 총 {len(lookup_dict)}개의 (file_id, tag) 조합을 찾았습니다.")
    
    print(f"4. 데이터 채워넣기 중...")
    updated_data, stats = fill_multiple_choice_data(multiple_choice_data, lookup_dict)
    
    # 통계 출력
    print("\n=== 통계 ===")
    print(f"총 항목 수: {stats['total']}")
    print(f"매칭된 항목: {stats['matched']}")
    print(f"매칭되지 않은 항목: {stats['unmatched']}")
    print(f"domain 채워넣은 항목: {stats['domain_filled']}")
    print(f"subdomain 채워넣은 항목: {stats['subdomain_filled']}")
    print(f"classification_reason 채워넣은 항목: {stats['classification_reason_filled']}")
    print(f"is_calculation 채워넣은 항목: {stats['is_calculation_filled']}")
    
    # 5. 원본 multiple_subdomain_classified_ALL.json을 .bak으로 이름 변경
    source_bak_path = f"{source_path}.bak"
    print(f"\n5. 원본 파일 이름 변경 중: {source_path} -> {source_bak_path}")
    if os.path.exists(source_bak_path):
        os.remove(source_bak_path)
    os.rename(source_path, source_bak_path)
    
    # 6. 채워넣은 데이터를 multiple_subdomain_classified_ALL_new.json으로 저장
    print(f"\n6. 결과 저장 중: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    
    print("완료!")


if __name__ == '__main__':
    main()

