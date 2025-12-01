#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4_multiple_exam의 회차별 시험지에서 문제 번호(file_id, tag) 리스트를 추출하여 JSON 파일로 저장
"""

import os
import json
from typing import Dict, List, Any
from pathlib import Path


def extract_question_ids_from_exam(exam_file: str) -> List[Dict[str, str]]:
    """
    시험지 파일에서 문제 번호(file_id, tag) 리스트 추출
    
    Args:
        exam_file: 시험지 JSON 파일 경로
    
    Returns:
        [{"file_id": "...", "tag": "..."}, ...] 형태의 리스트
    """
    with open(exam_file, 'r', encoding='utf-8') as f:
        exam_data = json.load(f)
    
    question_ids = []
    for question in exam_data:
        file_id = question.get('file_id', '')
        tag = question.get('tag', '')
        if file_id and tag:
            question_ids.append({
                'file_id': file_id,
                'tag': tag
            })
    
    return question_ids


def extract_all_exam_question_lists(onedrive_path: str) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """
    4_multiple_exam의 모든 회차별 시험지에서 문제 번호 리스트 추출
    
    Args:
        onedrive_path: OneDrive 경로
    
    Returns:
        {
            "1st": {
                "금융일반": [{"file_id": "...", "tag": "..."}, ...],
                "금융실무1": [{"file_id": "...", "tag": "..."}, ...],
                ...
            },
            "2nd": {...},
            ...
        }
    """
    exam_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam')
    
    if not os.path.exists(exam_dir):
        raise FileNotFoundError(f"시험지 디렉토리를 찾을 수 없습니다: {exam_dir}")
    
    result = {}
    set_names = ['1st', '2nd', '3rd', '4th', '5th']
    
    for set_name in set_names:
        set_dir = os.path.join(exam_dir, set_name)
        if not os.path.exists(set_dir):
            continue
        
        result[set_name] = {}
        
        # 해당 세트의 모든 시험지 파일 찾기
        for exam_file in os.listdir(set_dir):
            if exam_file.endswith('_exam.json') and not exam_file.endswith('_filled_modification_log.json'):
                exam_path = os.path.join(set_dir, exam_file)
                
                # 시험 이름 추출 (예: "금융일반_exam.json" -> "금융일반")
                exam_name = exam_file.replace('_exam.json', '')
                
                try:
                    question_ids = extract_question_ids_from_exam(exam_path)
                    result[set_name][exam_name] = question_ids
                    print(f"  {set_name}/{exam_name}: {len(question_ids)}개 문제 추출")
                except Exception as e:
                    print(f"  ⚠️  {set_name}/{exam_name} 추출 실패: {e}")
    
    return result


def save_question_lists(question_lists: Dict[str, Dict[str, List[Dict[str, str]]]], 
                       output_file: str):
    """
    추출된 문제 번호 리스트를 JSON 파일로 저장
    
    Args:
        question_lists: extract_all_exam_question_lists의 반환값
        output_file: 출력 파일 경로
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(question_lists, f, ensure_ascii=False, indent=2)
    
    print(f"\n문제 번호 리스트 저장 완료: {output_file}")


def load_question_lists(question_list_file: str) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """
    저장된 문제 번호 리스트 로드
    
    Args:
        question_list_file: 문제 번호 리스트 JSON 파일 경로
    
    Returns:
        {
            "1st": {
                "금융일반": [{"file_id": "...", "tag": "..."}, ...],
                ...
            },
            ...
        }
    """
    with open(question_list_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """메인 함수"""
    import argparse
    import platform
    
    parser = argparse.ArgumentParser(description='4_multiple_exam의 회차별 시험지에서 문제 번호 리스트 추출')
    parser.add_argument('--onedrive_path', type=str, default=None,
                       help='OneDrive 경로 (None이면 자동 감지)')
    parser.add_argument('--output', type=str, default=None,
                       help='출력 파일 경로 (기본값: evaluation/eval_data/4_multiple_exam/exam_question_lists.json)')
    
    args = parser.parse_args()
    
    # OneDrive 경로 자동 감지
    if args.onedrive_path is None:
        home_dir = os.path.expanduser("~")
        system = platform.system()
        if system == "Windows":
            onedrive_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
        else:
            onedrive_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
    else:
        onedrive_path = args.onedrive_path
    
    if not os.path.exists(onedrive_path):
        print(f"❌ OneDrive 경로를 찾을 수 없습니다: {onedrive_path}")
        return
    
    # 출력 파일 경로 설정
    if args.output is None:
        output_file = os.path.join(onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam', 'exam_question_lists.json')
    else:
        output_file = args.output
    
    print("=" * 80)
    print("4_multiple_exam 회차별 시험지 문제 번호 리스트 추출")
    print("=" * 80)
    print(f"OneDrive 경로: {onedrive_path}")
    print(f"출력 파일: {output_file}\n")
    
    try:
        # 문제 번호 리스트 추출
        question_lists = extract_all_exam_question_lists(onedrive_path)
        
        # 통계 출력
        print("\n" + "=" * 80)
        print("추출 결과 요약")
        print("=" * 80)
        for set_name in ['1st', '2nd', '3rd', '4th', '5th']:
            if set_name in question_lists:
                total = sum(len(questions) for questions in question_lists[set_name].values())
                print(f"{set_name}: {len(question_lists[set_name])}개 시험지, 총 {total}개 문제")
                for exam_name, questions in question_lists[set_name].items():
                    print(f"  - {exam_name}: {len(questions)}개")
        
        # 저장
        save_question_lists(question_lists, output_file)
        
        print("\n✅ 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

