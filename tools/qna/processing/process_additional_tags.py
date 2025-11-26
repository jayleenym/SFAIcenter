#!/usr/bin/env python3
"""
extracted_qna.json의 additional_tag_data를 처리하는 통합 스크립트

1. fix_missing_tags_with_add_info: additional_tags_found에 있지만 additional_tag_data에 없는 태그들을 추가
2. fill_additional_tag_data: 빈 "data":{}를 원본 파일의 add_info에서 데이터로 채움
"""

import json
import re
import sys
import os
import shutil
from typing import Dict, List, Any

# pipeline/config에서 ONEDRIVE_PATH import 시도
try:
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    sys.path.insert(0, project_root)
    from tools import ONEDRIVE_PATH
except ImportError:
    # fallback: pipeline이 없는 경우 플랫폼별 기본값 사용
    import platform
    system = platform.system()
    home_dir = os.path.expanduser("~")
    if system == "Windows":
        ONEDRIVE_PATH = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
    else:
        ONEDRIVE_PATH = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")


def load_json_file(file_path: str) -> Dict[str, Any]:
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(data: List[Dict[str, Any]], file_path: str) -> None:
    """JSON 파일을 저장합니다."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_page_from_tag(tag: str) -> str:
    """tag에서 페이지 번호를 추출합니다.
    예: {img_0205_0001} -> 0205
    """
    # 중괄호 제거
    clean_tag = tag.strip('{}')
    
    # 패턴 매칭: img_0205_0001, f_0205_0001, tb_0205_0001, note_0205_0001, etc_0205_0001 등
    match = re.match(r'^(img|f|tb|note|etc)_(\d{4})_\d+$', clean_tag)
    if match:
        return match.group(2)
    
    return None

def find_tag_data_in_add_info(add_info: List[Dict], tag: str) -> Dict[str, Any]:
    """add_info에서 특정 tag에 해당하는 데이터를 찾습니다."""
    clean_tag = tag.strip('{}')
    
    for item in add_info:
        if item.get('tag') == clean_tag:
            return item
    
    return None

def extract_tags_from_qna_content(qna_item: Dict) -> List[str]:
    """Q&A 내용에서 img_, f_, tb_, etc_, note_ 태그를 추출합니다."""
    qna_content = ""
    if 'qna_data' in qna_item and 'description' in qna_item['qna_data']:
        desc = qna_item['qna_data']['description']
        # question, answer, explanation, options에서 태그 추출
        for field in ['question', 'answer', 'explanation', 'options']:
            if field in desc and desc[field]:
                if field == 'options' and isinstance(desc[field], list):
                    # options는 리스트이므로 각 항목을 합침
                    for option in desc[field]:
                        qna_content += str(option) + " "
                elif field == 'explanation':
                    # explanation은 긴 문자열이므로 명시적으로 처리
                    qna_content += str(desc[field]) + " "
                else:
                    # question, answer 등 문자열 필드
                    qna_content += str(desc[field]) + " "
    
    # Q&A 내용에서 tb, img, f, etc, note 태그 추출
    tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
    img_tags = re.findall(r'\{img_\d{4}_\d{4}\}', qna_content)
    f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
    etc_tags = re.findall(r'\{etc_\d{4}_\d{4}\}', qna_content)
    footnote_tags = re.findall(r'\{note_\d{4}_\d{4}\}', qna_content)
    
    return tb_tags + img_tags + f_tags + etc_tags + footnote_tags

def fix_missing_tags_with_add_info(qna_data: List[Dict], source_data: Dict) -> tuple:
    """additional_tags_found에 있지만 additional_tag_data에 없는 태그들을 추가합니다."""
    
    # add_info에서 태그 데이터 수집
    source_tags_data = {}
    for item in source_data.get('contents', []):
        if "add_info" in item and isinstance(item["add_info"], list):
            for add_item in item["add_info"]:
                if "tag" in add_item:
                    source_tags_data[add_item["tag"]] = add_item
        
        # 기존 data 섹션도 확인
        if "data" in item and isinstance(item["data"], list):
            for data_item in item["data"]:
                if "tag" in data_item:
                    source_tags_data[data_item["tag"]] = data_item
        # top-level 'tag'도 확인
        if "tag" in item:
            source_tags_data[item["tag"]] = item

    tags_added_from_source = 0
    tags_added_empty = 0
    tags_found_in_content = 0

    for i, entry in enumerate(qna_data):
        # 기존 additional_tags_found 가져오기
        additional_tags_found = set(entry.get("additional_tags_found", []))
        
        # Q&A 내용에서 추가 태그 추출
        content_tags = extract_tags_from_qna_content(entry)
        if content_tags:
            print(f"항목 {i}에서 Q&A 내용에서 {len(content_tags)}개의 태그 발견: {content_tags}")
            # 새로 발견된 태그들을 additional_tags_found에 추가
            for tag in content_tags:
                additional_tags_found.add(tag)
            tags_found_in_content += len(content_tags)
        
        # additional_tags_found 업데이트
        entry["additional_tags_found"] = list(additional_tags_found)
        
        additional_tag_data_tags = {item["tag"] for item in entry.get("additional_tag_data", [])}

        missing_in_data = additional_tags_found - additional_tag_data_tags

        if missing_in_data:
            print(f"항목 {i}에서 {len(missing_in_data)}개의 누락된 태그 발견: {list(missing_in_data)}")
            
            for tag_with_braces in missing_in_data:
                # Remove braces for lookup in source_tags_data
                tag_without_braces = tag_with_braces.strip('{}')
                
                if tag_without_braces in source_tags_data:
                    # Add the found tag data to additional_tag_data
                    if "additional_tag_data" not in entry:
                        entry["additional_tag_data"] = []
                    
                    # 원본 데이터를 그대로 사용하되, tag는 중괄호가 있는 형태로 유지
                    tag_data = source_tags_data[tag_without_braces].copy()
                    tag_data["tag"] = tag_with_braces  # 중괄호가 있는 형태로 설정
                    
                    entry["additional_tag_data"].append(tag_data)
                    tags_added_from_source += 1
                    print(f"  - {tag_with_braces} 추가됨 (원본에서 찾음)")
                else:
                    # Add with empty data
                    if "additional_tag_data" not in entry:
                        entry["additional_tag_data"] = []
                    entry["additional_tag_data"].append({
                        "tag": tag_with_braces,
                        "data": {}
                    })
                    tags_added_empty += 1
                    print(f"  - {tag_with_braces} 추가됨 (빈 데이터로)")

    return tags_added_from_source, tags_added_empty, tags_found_in_content

def fill_additional_tag_data(qna_data: List[Dict], source_data: Dict) -> tuple:
    """빈 additional_tag_data의 "data":{}를 원본 파일의 add_info에서 채웁니다."""
    
    # 페이지별 add_info를 인덱싱
    page_add_info = {}
    for page_data in source_data.get('contents', []):
        page_num = page_data.get('page')
        if page_num:
            page_add_info[page_num] = page_data.get('add_info', [])
    
    print(f"Found {len(page_add_info)} pages in source file")
    
    # extracted_qna의 각 항목을 처리
    filled_count = 0
    total_empty = 0
    
    for item in qna_data:
        if 'additional_tag_data' in item:
            for tag_data in item['additional_tag_data']:
                if tag_data.get('data') == {}:  # 빈 data 객체
                    total_empty += 1
                    tag = tag_data.get('tag')
                    
                    if tag:
                        # 페이지 번호 추출
                        page_num = extract_page_from_tag(tag)
                        
                        if page_num and page_num in page_add_info:
                            # 해당 페이지의 add_info에서 tag 데이터 찾기
                            found_data = find_tag_data_in_add_info(page_add_info[page_num], tag)
                            
                            if found_data:
                                tag_data['data'] = found_data
                                filled_count += 1
                                print(f"Filled data for {tag} from page {page_num}")
                            else:
                                print(f"Warning: Could not find data for {tag} in page {page_num}")
                        else:
                            print(f"Warning: Could not extract page number from tag {tag}")
    
    return filled_count, total_empty

def process_additional_tags(cycle: str, file_id: str) -> bool:
    """additional_tag_data를 처리하는 메인 함수. 성공시 True, 실패시 False 반환"""
    
    # 파일 경로 설정
    extracted_qna_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', f'{cycle}C', 'Lv5', f'{file_id}_extracted_qna.json')
    source_path = os.path.join(ONEDRIVE_PATH, 'data', 'FINAL', f'{cycle}C', 'Lv5', file_id, f'{file_id}.json')
    backup_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', f'{cycle}C', 'Lv5', '_backup')
    backup_path = os.path.join(backup_dir, f'{file_id}_extracted_qna.json.bak')
    
    # 백업 디렉토리 생성 (존재하지 않는 경우)
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"Processing {file_id}...")
    print("=" * 50)
    
    # 기존 파일 백업
    if os.path.exists(extracted_qna_path):
        print(f"Backing up original file to: {backup_path}")
        shutil.copy2(extracted_qna_path, backup_path)
    else:
        print(f"Warning: Original file not found: {extracted_qna_path}")
        return False
    
    # 파일 로드
    print("Loading files...")
    qna_data = load_json_file(extracted_qna_path)
    source_data = load_json_file(source_path)
    
    # 1단계: 누락된 태그 추가
    print("\n1단계: 누락된 태그 추가 중...")
    tags_added_from_source, tags_added_empty, tags_found_in_content = fix_missing_tags_with_add_info(qna_data, source_data)
    
    print(f"\n1단계 완료:")
    print(f"  - Q&A 내용에서 발견된 태그: {tags_found_in_content}개")
    print(f"  - 원본에서 찾아서 추가된 태그: {tags_added_from_source}개")
    print(f"  - 빈 데이터로 추가된 태그: {tags_added_empty}개")
    
    # 2단계: 빈 data 채우기
    print("\n2단계: 빈 data 채우기 중...")
    filled_count, total_empty = fill_additional_tag_data(qna_data, source_data)
    
    print(f"\n2단계 완료:")
    print(f"  - 빈 data 필드: {total_empty}개")
    print(f"  - 성공적으로 채워진 필드: {filled_count}개")
    print(f"  - 채우지 못한 필드: {total_empty - filled_count}개")
    
    # 채우지 못한 필드가 있으면 실패로 처리
    unfilled_count = total_empty - filled_count
    if unfilled_count > 0:
        print(f"\n❌ 실패: {unfilled_count}개의 빈 필드를 채우지 못했습니다.")
        return False
    
    # 결과 저장 (원본 파일명으로 저장)
    save_json_file(qna_data, extracted_qna_path)
    print(f"\n처리된 파일이 저장되었습니다: {extracted_qna_path}")
    print(f"원본 파일은 백업되었습니다: {backup_path}")
    
    print("\n" + "=" * 50)
    print("처리 완료!")
    return True

def find_all_extracted_qna_files(cycle: str) -> List[str]:
    """지정된 경로의 모든 extracted_qna 파일을 찾습니다."""
    extracted_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', f'{cycle}C', 'Lv5')
    
    if not os.path.exists(extracted_dir):
        print(f"디렉토리가 존재하지 않습니다: {extracted_dir}")
        return []
    
    extracted_files = []
    for file in os.listdir(extracted_dir):
        if file.endswith('_extracted_qna.json') and file != 'merged_extracted_qna.json':
            # file_id 추출 (파일명에서 _extracted_qna.json 제거)
            file_id = file.replace('_extracted_qna.json', '')
            extracted_files.append(file_id)
    
    return sorted(extracted_files)

def process_all_files(cycle: str) -> None:
    """모든 extracted_qna 파일을 처리합니다."""
    print(f"{cycle}C의 모든 extracted_qna 파일을 처리합니다...")
    print("=" * 60)
    
    # 모든 파일 찾기
    file_ids = find_all_extracted_qna_files(cycle)
    
    if not file_ids:
        print("처리할 파일이 없습니다.")
        return
    
    print(f"발견된 파일 개수: {len(file_ids)}개")
    print(f"파일 목록: {', '.join(file_ids)}")
    print("\n" + "=" * 60)
    
    # 각 파일 처리
    success_count = 0
    error_count = 0
    error_files = []
    
    for i, file_id in enumerate(file_ids, 1):
        print(f"\n[{i}/{len(file_ids)}] 처리 중: {file_id}")
        print("-" * 40)
        
        try:
            success = process_additional_tags(cycle, file_id)
            if success:
                success_count += 1
                print(f"✅ {file_id} 처리 완료")
            else:
                error_count += 1
                error_files.append(file_id)
                print(f"❌ {file_id} 처리 실패: 빈 필드를 채우지 못함")
        except Exception as e:
            error_count += 1
            error_files.append(file_id)
            print(f"❌ {file_id} 처리 실패: {e}")
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("전체 처리 완료!")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {error_count}개")
    
    if error_files:
        print(f"실패한 파일: {', '.join(error_files)}")

if __name__ == "__main__":
    if len(sys.argv) > 3:
        print("사용법:")
        print("  python process_additional_tags.py [cycle] [file_id]")
        print("")
        print("예시:")
        print("  python process_additional_tags.py 1 SS0332  # 특정 파일 처리")
        print("  python process_additional_tags.py 1         # 특정 cycle의 모든 파일 처리")
        print("  python process_additional_tags.py           # cycle 1~3 모두 처리")
        sys.exit(1)
    
    if len(sys.argv) == 1:
        # cycle 입력이 없으면 1~3 모두 처리
        print("cycle 입력이 없어 cycle 1, 2, 3을 모두 처리합니다...")
        print("=" * 60)
        
        for cycle in ['1', '2', '3']:
            print(f"\n{'='*60}")
            print(f"Cycle {cycle} 처리 시작")
            print(f"{'='*60}")
            process_all_files(cycle)
        
        print("\n" + "=" * 60)
        print("모든 cycle 처리 완료!")
        sys.exit(0)
    
    cycle = sys.argv[1]
    
    if len(sys.argv) == 3:
        # 특정 파일 처리
        file_id = sys.argv[2]
        success = process_additional_tags(cycle, file_id)
        if success:
            print(f"\n✅ {file_id} 처리 완료!")
        else:
            print(f"\n❌ {file_id} 처리 실패!")
            sys.exit(1)
    else:
        # 모든 파일 처리
        process_all_files(cycle)
