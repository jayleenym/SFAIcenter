#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험지 문제 번호 추출 유틸리티

이 모듈은 시험지에서 문제 번호(file_id, tag, domain, subdomain)를 추출하는 기능을 제공합니다.

기능:
    - extract_question_ids_from_exam: 단일 시험지에서 문제 번호 추출
    - extract_exam_question_lists: 4_multiple_exam의 시험지에서 문제 번호 추출
    - save_question_lists: 문제 번호 리스트를 JSON 파일로 저장
    - load_question_lists: 저장된 문제 번호 리스트 로드

사용 예:
    # 커맨드라인에서 실행
    python -m tools.exam.extract_exam_question_list --onedrive_path /path/to/onedrive
    
    # 코드에서 사용
    from tools.exam import extract_exam_question_lists, save_question_lists
    question_lists = extract_exam_question_lists(onedrive_path)
    save_question_lists(question_lists, output_file)
"""

import os
import json
from typing import Dict, List


def extract_question_ids_from_exam(exam_file: str, include_domain: bool = True) -> List[Dict[str, str]]:
    """
    시험지 파일에서 문제 번호(file_id, tag, domain, subdomain) 리스트 추출
    
    Args:
        exam_file: 시험지 JSON 파일 경로
        include_domain: domain/subdomain 정보 포함 여부
    
    Returns:
        [{"file_id": "...", "tag": "...", "domain": "...", "subdomain": "..."}, ...] 형태의 리스트
    """
    with open(exam_file, 'r', encoding='utf-8') as f:
        exam_data = json.load(f)
    
    question_ids = []
    for question in exam_data:
        file_id = question.get('file_id', '')
        tag = question.get('tag', '')
        if file_id and tag:
            item = {
                'file_id': file_id,
                'tag': tag
            }
            if include_domain:
                item['domain'] = question.get('domain', '')
                item['subdomain'] = question.get('subdomain', '')
            question_ids.append(item)
    
    return question_ids


def extract_exam_question_lists(onedrive_path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    4_multiple_exam의 시험지에서 문제 번호 리스트 추출
    
    exam_create.py에서 생성하는 형식과 동일하게 추출합니다.
    duplicate_filter.py에서 사용하는 형식입니다.
    
    Args:
        onedrive_path: OneDrive 경로
    
    Returns:
        {
            "금융일반": [{"file_id": "...", "tag": "...", "domain": "...", "subdomain": "..."}, ...],
            "금융실무1": [...],
            "표해석": [...],
            ...
        }
    """
    exam_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam')
    
    if not os.path.exists(exam_dir):
        raise FileNotFoundError(f"시험지 디렉토리를 찾을 수 없습니다: {exam_dir}")
    
    result = {}
    
    # 4_multiple_exam 디렉토리의 모든 시험지 파일 찾기 (직접 있는 파일들)
    for exam_file in os.listdir(exam_dir):
        if exam_file.endswith('_exam.json'):
            exam_path = os.path.join(exam_dir, exam_file)
            
            # 디렉토리는 건너뛰기
            if os.path.isdir(exam_path):
                continue
            
            # 시험 이름 추출 (예: "금융일반_exam.json" -> "금융일반")
            exam_name = exam_file.replace('_exam.json', '')
            
            try:
                question_ids = extract_question_ids_from_exam(exam_path, include_domain=True)
                result[exam_name] = question_ids
                print(f"  {exam_name}: {len(question_ids)}개 문제 추출")
            except Exception as e:
                print(f"  ⚠️  {exam_name} 추출 실패: {e}")
    
    return result


def save_question_lists(question_lists: Dict[str, List[Dict[str, str]]], 
                       output_file: str):
    """
    추출된 문제 번호 리스트를 JSON 파일로 저장
    
    Args:
        question_lists: extract_exam_question_lists의 반환값
        output_file: 출력 파일 경로
    """
    dir_path = os.path.dirname(output_file)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(question_lists, f, ensure_ascii=False, indent=2)


def load_question_lists(question_list_file: str) -> Dict[str, List[Dict[str, str]]]:
    """
    저장된 문제 번호 리스트 로드
    
    Args:
        question_list_file: 문제 번호 리스트 JSON 파일 경로
    
    Returns:
        {
            "금융일반": [{"file_id": "...", "tag": "...", "domain": "...", "subdomain": "..."}, ...],
            ...
        }
    """
    with open(question_list_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """메인 함수"""
    import argparse
    import platform
    
    parser = argparse.ArgumentParser(description='4_multiple_exam 시험지에서 문제 번호 리스트 추출')
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
    print("4_multiple_exam 시험지 문제 번호 리스트 추출")
    print("=" * 80)
    print(f"OneDrive 경로: {onedrive_path}")
    print(f"출력 파일: {output_file}\n")
    
    try:
        # 문제 번호 리스트 추출
        question_lists = extract_exam_question_lists(onedrive_path)
        
        # 통계 출력
        print("\n" + "=" * 80)
        print("추출 결과 요약")
        print("=" * 80)
        total_questions = 0
        for exam_name, questions in sorted(question_lists.items()):
            print(f"  {exam_name}: {len(questions)}개 문제")
            total_questions += len(questions)
        print(f"\n총 {len(question_lists)}개 시험지, {total_questions}개 문제")
        
        # 저장
        save_question_lists(question_lists, output_file)
        print(f"\n문제 번호 리스트 저장 완료: {output_file}")
        
        print("\n✅ 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

