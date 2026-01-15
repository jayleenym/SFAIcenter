#!/usr/bin/env python3
"""
중복 QnA 검사 및 삭제 스크립트
- 문제/정답/해설/선택지가 모두 동일한 진짜 중복을 찾아 리포트 생성
- 옵션으로 중복 삭제 가능
"""

import json
import os
import sys
import glob
import shutil
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

# tools 모듈 import
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, project_root)
    from tools import ONEDRIVE_PATH
except ImportError:
    import platform
    system = platform.system()
    home_dir = os.path.expanduser("~")
    if system == "Windows":
        ONEDRIVE_PATH = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
    else:
        ONEDRIVE_PATH = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")


def check_duplicates_single_file(file_path: str, return_details: bool = False) -> Tuple[int, int, Optional[Dict]]:
    """
    단일 파일에서 문제/정답/해설/선택지가 모두 동일한 진짜 중복을 확인
    
    Args:
        file_path: 검사할 파일 경로
        return_details: 상세 정보 반환 여부
        
    Returns:
        (총 QnA 수, 중복 그룹 수, 중복 상세정보)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {file_path} - {e}")
        return (0, 0, {}) if return_details else (0, 0)
    
    print(f"📁 파일: {os.path.basename(file_path)}")
    print(f"   총 Q&A 개수: {len(data)}")
    
    # 문제/정답/해설/선택지를 조합한 키로 중복 확인
    content_keys = defaultdict(list)
    
    for i, item in enumerate(data):
        qna_data = item.get('qna_data', {})
        description = qna_data.get('description', {})
        
        question = description.get('question', '').strip()
        answer = description.get('answer', '').strip()
        explanation = description.get('explanation', '').strip()
        options = description.get('options', [])
        tag = qna_data.get('tag', '')  # q_0000_0000 형식의 태그
        
        options_str = '|'.join([opt.strip() for opt in options]) if options else ''
        content_key = f"{question}|{answer}|{explanation}|{options_str}"
        
        content_keys[content_key].append({
            'index': i,
            'page': item.get('page', ''),
            'tag': tag,
            'question': question,
            'answer': answer,
            'explanation': explanation,
            'options': options
        })
    
    # 진짜 중복 찾기
    real_duplicates = {key: items for key, items in content_keys.items() if len(items) > 1}
    
    print(f"   고유한 Q&A 조합: {len(content_keys)}개")
    print(f"   중복된 Q&A 조합: {len(real_duplicates)}개")
    
    if real_duplicates:
        print(f"   ⚠️  진짜 중복 발견:")
        for i, (content_key, items) in enumerate(real_duplicates.items()):
            print(f"     중복 그룹 {i+1}:")
            for item in items:
                tag_info = f", 태그 {item['tag']}" if item.get('tag') else ""
                print(f"       - 인덱스 {item['index']}, 페이지 {item['page']}{tag_info}: {item['question'][:20]}...")
    else:
        print(f"   ✅ 진짜 중복 없음")
    
    if return_details:
        return len(data), len(real_duplicates), real_duplicates
    else:
        return len(data), len(real_duplicates)


def save_duplicates_report(duplicates_data: Dict[str, Any], output_dir: str) -> str:
    """중복 검사 결과를 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    txt_file = os.path.join(os.path.dirname(output_dir), f"duplicates_report_{timestamp}.txt")
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("중복 검사 결과 리포트\n")
        f.write("=" * 80 + "\n")
        f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"검사된 파일 수: {duplicates_data['summary']['total_files']}개\n")
        f.write(f"총 Q&A 개수: {duplicates_data['summary']['total_qna']}개\n")
        f.write(f"총 중복 그룹 수: {duplicates_data['summary']['total_duplicates']}개\n")
        f.write(f"중복이 있는 파일 수: {duplicates_data['summary']['files_with_duplicates']}개\n")
        f.write("\n")
        
        if duplicates_data['summary']['files_with_duplicates'] > 0:
            f.write("중복이 발견된 파일들:\n")
            f.write("-" * 40 + "\n")
            
            for file_info in duplicates_data['files_with_duplicates']:
                f.write(f"\n📁 파일: {file_info['filename']}\n")
                f.write(f"   경로: {file_info['filepath']}\n")
                f.write(f"   총 Q&A 개수: {file_info['total_qna']}개\n")
                f.write(f"   중복 그룹 수: {file_info['duplicate_groups']}개\n")
                f.write("\n")
                
                for group_idx, (content_key, items) in enumerate(file_info['duplicates'].items(), 1):
                    f.write(f"   중복 그룹 {group_idx}:\n")
                    for item in items:
                        f.write(f"     - 인덱스 {item['index']}, 페이지 {item['page']}\n")
                        f.write(f"       문제: {item['question'][:100]}{'...' if len(item['question']) > 100 else ''}\n")
                        f.write(f"       정답: {item['answer'][:100]}{'...' if len(item['answer']) > 100 else ''}\n")
                        f.write(f"       해설: {item['explanation'][:100]}{'...' if len(item['explanation']) > 100 else ''}\n")
                        if item.get('options'):
                            f.write(f"       선택지:\n")
                            for opt_idx, option in enumerate(item['options'], 1):
                                f.write(f"         {opt_idx}. {option[:80]}{'...' if len(option) > 80 else ''}\n")
                        f.write("\n")
        else:
            f.write("✅ 모든 파일에서 중복 없음 - 모든 Q&A가 고유합니다!\n")
    
    return txt_file


def remove_duplicates_from_file(file_path: str, duplicates_data: Dict, create_backup: bool = True) -> Tuple[int, int]:
    """
    파일에서 중복된 문제들을 삭제 (인덱스가 큰 것들 삭제)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if create_backup:
            backup_path = file_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(file_path, backup_path)
            print(f"📁 백업 파일 생성: {backup_path}")
        
        indices_to_remove = set()
        
        for content_key, items in duplicates_data.items():
            if len(items) > 1:
                sorted_items = sorted(items, key=lambda x: x['index'])
                for item in sorted_items[1:]:
                    indices_to_remove.add(item['index'])
        
        sorted_indices = sorted(indices_to_remove, reverse=True)
        
        removed_count = 0
        for index in sorted_indices:
            if 0 <= index < len(data):
                del data[index]
                removed_count += 1
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {removed_count}개의 중복 문제 삭제 완료")
        return removed_count, len(data)
        
    except Exception as e:
        print(f"❌ 중복 삭제 실패: {file_path} - {e}")
        return 0, 0


def find_extracted_qna_files(directory_path: str) -> List[str]:
    """디렉토리 하위의 모든 extracted_qna.json 파일을 찾는 함수"""
    pattern = os.path.join(directory_path, "**", "*extracted_qna.json")
    files = glob.glob(pattern, recursive=True)
    return sorted(files)


def check_duplicates(directory_path: str, remove_duplicates: bool = False) -> Tuple[int, int]:
    """
    디렉토리 하위의 모든 extracted_qna.json 파일을 검사
    
    Args:
        directory_path: 검사할 디렉토리 경로
        remove_duplicates: 중복 삭제 여부
        
    Returns:
        (총 QnA 수, 총 중복 그룹 수)
    """
    print(f"🔍 검사 대상 디렉토리: {directory_path}")
    
    files = find_extracted_qna_files(directory_path)
    
    if not files:
        print(f"❌ extracted_qna.json 파일을 찾을 수 없습니다.")
        return 0, 0
    
    print(f"📋 발견된 파일 수: {len(files)}개")
    print("=" * 80)
    
    total_qna = 0
    total_duplicates = 0
    files_with_duplicates = 0
    files_with_duplicates_data = []
    
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}]")
        qna_count, duplicate_count, duplicates = check_duplicates_single_file(file_path, return_details=True)
        
        total_qna += qna_count
        total_duplicates += duplicate_count
        if duplicate_count > 0:
            files_with_duplicates += 1
            files_with_duplicates_data.append({
                'filename': os.path.basename(file_path),
                'filepath': file_path,
                'total_qna': qna_count,
                'duplicate_groups': duplicate_count,
                'duplicates': duplicates
            })
        
        print("-" * 40)
    
    # 전체 요약
    print(f"\n{'='*80}")
    print(f"📊 전체 검사 결과 요약")
    print(f"{'='*80}")
    print(f"검사된 파일 수: {len(files)}개")
    print(f"총 Q&A 개수: {total_qna}개")
    print(f"총 중복 그룹 수: {total_duplicates}개")
    print(f"중복이 있는 파일 수: {files_with_duplicates}개")
    
    if total_duplicates == 0:
        print(f"✅ 모든 파일에서 중복 없음 - 모든 Q&A가 고유합니다!")
    else:
        print(f"⚠️  {files_with_duplicates}개 파일에서 중복 발견 - 정리가 필요합니다.")
        
        if files_with_duplicates >= 1:
            print(f"\n💾 중복 검사 결과를 파일로 저장합니다...")
            
            duplicates_data = {
                'summary': {
                    'total_files': len(files),
                    'total_qna': total_qna,
                    'total_duplicates': total_duplicates,
                    'files_with_duplicates': files_with_duplicates
                },
                'files_with_duplicates': files_with_duplicates_data
            }
            
            try:
                txt_file = save_duplicates_report(duplicates_data, directory_path)
                print(f"✅ 텍스트 리포트 저장: {txt_file}")
            except Exception as e:
                print(f"❌ 리포트 저장 실패: {e}")
            
            if remove_duplicates:
                print(f"\n🗑️  중복 문제 삭제를 시작합니다...")
                total_removed = 0
                files_processed = 0
                
                for file_info in files_with_duplicates_data:
                    file_path = file_info['filepath']
                    print(f"\n📁 처리 중: {os.path.basename(file_path)}")
                    
                    removed_count, remaining_count = remove_duplicates_from_file(
                        file_path, 
                        file_info['duplicates']
                    )
                    
                    if removed_count > 0:
                        total_removed += removed_count
                        files_processed += 1
                        print(f"   삭제된 문제: {removed_count}개")
                        print(f"   남은 문제: {remaining_count}개")
                
                print(f"\n📊 중복 삭제 완료:")
                print(f"   처리된 파일: {files_processed}개")
                print(f"   총 삭제된 문제: {total_removed}개")
                
                # 삭제 후 재검사
                print(f"\n🔍 삭제 후 재검사를 시작합니다...")
                check_duplicates(directory_path, remove_duplicates=False)
    
    return total_qna, total_duplicates


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python check_duplicates.py <cycle> [--remove]")
        print("예시: python check_duplicates.py 1")
        print("예시: python check_duplicates.py 1 --remove")
        sys.exit(1)
    
    cycle = sys.argv[1]
    remove_flag = len(sys.argv) >= 3 and sys.argv[2] == "--remove"
    
    directory_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data', f'{cycle}C', 'Lv5')
    
    if not os.path.exists(directory_path):
        print(f"❌ 디렉토리가 존재하지 않습니다: {directory_path}")
        sys.exit(1)
    
    if not os.path.isdir(directory_path):
        print(f"❌ 경로가 디렉토리가 아닙니다: {directory_path}")
        sys.exit(1)
    
    check_duplicates(directory_path, remove_flag)


if __name__ == "__main__":
    main()

