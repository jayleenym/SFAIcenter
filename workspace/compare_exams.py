#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
두 시험 파일을 비교하여 차이점을 분석하는 스크립트
"""

import json
from collections import defaultdict
from typing import Dict, List, Any, Set

def load_json(file_path: str) -> List[Dict]:
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_exams(file1_path: str, file2_path: str):
    """두 시험 파일을 비교합니다."""
    print(f"파일 1 로딩 중: {file1_path}")
    exams1 = load_json(file1_path)
    print(f"파일 1: {len(exams1)}개 문제")
    
    print(f"\n파일 2 로딩 중: {file2_path}")
    exams2 = load_json(file2_path)
    print(f"파일 2: {len(exams2)}개 문제")
    
    # (file_id, tag) 조합을 기준으로 인덱싱 (같은 tag라도 file_id가 다르면 다른 문제)
    exams1_by_key = {}
    for exam in exams1:
        if 'file_id' in exam and 'tag' in exam:
            key = (exam.get('file_id'), exam.get('tag'))
            exams1_by_key[key] = exam
    
    exams2_by_key = {}
    for exam in exams2:
        if 'file_id' in exam and 'tag' in exam:
            key = (exam.get('file_id'), exam.get('tag'))
            exams2_by_key[key] = exam
    
    keys1 = set(exams1_by_key.keys())
    keys2 = set(exams2_by_key.keys())
    
    # tag만으로도 통계 제공 (참고용)
    tags1 = set(exam.get('tag') for exam in exams1 if 'tag' in exam)
    tags2 = set(exam.get('tag') for exam in exams2 if 'tag' in exam)
    
    print(f"\n=== 기본 통계 ===")
    print(f"파일 1의 고유 (file_id, tag) 조합 수: {len(keys1)}")
    print(f"파일 2의 고유 (file_id, tag) 조합 수: {len(keys2)}")
    print(f"공통 (file_id, tag) 조합 수: {len(keys1 & keys2)}")
    print(f"파일 1에만 있는 (file_id, tag) 조합 수: {len(keys1 - keys2)}")
    print(f"파일 2에만 있는 (file_id, tag) 조합 수: {len(keys2 - keys1)}")
    print(f"\n(참고) 파일 1의 고유 tag 수: {len(tags1)}")
    print(f"(참고) 파일 2의 고유 tag 수: {len(tags2)}")
    
    # 파일 1에만 있는 문제들
    only_in_file1 = keys1 - keys2
    if only_in_file1:
        print(f"\n=== 파일 1에만 있는 문제들 (최대 10개 표시) ===")
        for i, key in enumerate(sorted(only_in_file1)[:10]):
            exam = exams1_by_key[key]
            file_id, tag = key
            print(f"{i+1}. file_id: {file_id}, tag: {tag}")
            print(f"   question: {exam.get('question', '')[:100]}...")
            if i >= 9:
                print(f"   ... (총 {len(only_in_file1)}개 중 10개만 표시)")
                break
    
    # 파일 2에만 있는 문제들
    only_in_file2 = keys2 - keys1
    if only_in_file2:
        print(f"\n=== 파일 2에만 있는 문제들 (최대 10개 표시) ===")
        for i, key in enumerate(sorted(only_in_file2)[:10]):
            exam = exams2_by_key[key]
            file_id, tag = key
            print(f"{i+1}. file_id: {file_id}, tag: {tag}")
            print(f"   question: {exam.get('question', '')[:100]}...")
            if i >= 9:
                print(f"   ... (총 {len(only_in_file2)}개 중 10개만 표시)")
                break
    
    # 공통 문제들의 차이점 분석
    common_keys = keys1 & keys2
    differences = []
    
    print(f"\n=== 공통 문제들의 차이점 분석 ===")
    
    # 필드 차이 확인
    field_differences = defaultdict(int)
    question_differences = []
    answer_differences = []
    options_differences = []
    explanation_differences = []
    
    for key in sorted(common_keys):
        exam1 = exams1_by_key[key]
        exam2 = exams2_by_key[key]
        file_id, tag = key
        
        # question 비교
        if exam1.get('question') != exam2.get('question'):
            question_differences.append({
                'file_id': file_id,
                'tag': tag,
                'file1': exam1.get('question', ''),
                'file2': exam2.get('question', '')
            })
        
        # answer 비교
        if exam1.get('answer') != exam2.get('answer'):
            answer_differences.append({
                'file_id': file_id,
                'tag': tag,
                'file1': exam1.get('answer', ''),
                'file2': exam2.get('answer', '')
            })
        
        # options 비교
        options1 = exam1.get('options', [])
        options2 = exam2.get('options', [])
        if options1 != options2:
            options_differences.append({
                'file_id': file_id,
                'tag': tag,
                'file1': options1,
                'file2': options2
            })
        
        # explanation 비교
        if exam1.get('explanation') != exam2.get('explanation'):
            explanation_differences.append({
                'file_id': file_id,
                'tag': tag,
                'file1': exam1.get('explanation', ''),
                'file2': exam2.get('explanation', '')
            })
        
        # 필드 존재 여부 비교
        fields1 = set(exam1.keys())
        fields2 = set(exam2.keys())
        only_in_1 = fields1 - fields2
        only_in_2 = fields2 - fields1
        
        if only_in_1:
            for field in only_in_1:
                field_differences[f'파일1에만 있는 필드: {field}'] += 1
        if only_in_2:
            for field in only_in_2:
                field_differences[f'파일2에만 있는 필드: {field}'] += 1
    
    print(f"\n--- 필드 차이 ---")
    for field, count in sorted(field_differences.items()):
        print(f"{field}: {count}개 문제")
    
    print(f"\n--- 내용 차이 ---")
    print(f"question이 다른 문제: {len(question_differences)}개")
    print(f"answer가 다른 문제: {len(answer_differences)}개")
    print(f"options가 다른 문제: {len(options_differences)}개")
    print(f"explanation이 다른 문제: {len(explanation_differences)}개")
    
    # 차이점 상세 출력
    if question_differences:
        print(f"\n=== question이 다른 문제들 (최대 5개 표시) ===")
        for i, diff in enumerate(question_differences[:5]):
            print(f"\n{i+1}. file_id: {diff['file_id']}, tag: {diff['tag']}")
            print(f"   파일1: {diff['file1'][:150]}...")
            print(f"   파일2: {diff['file2'][:150]}...")
    
    if answer_differences:
        print(f"\n=== answer가 다른 문제들 (최대 10개 표시) ===")
        for i, diff in enumerate(answer_differences[:10]):
            print(f"{i+1}. file_id: {diff['file_id']}, tag: {diff['tag']}")
            print(f"   파일1: {diff['file1']}")
            print(f"   파일2: {diff['file2']}")
    
    if options_differences:
        print(f"\n=== options가 다른 문제들 (최대 3개 표시) ===")
        for i, diff in enumerate(options_differences[:3]):
            print(f"\n{i+1}. file_id: {diff['file_id']}, tag: {diff['tag']}")
            print(f"   파일1 옵션 수: {len(diff['file1'])}")
            print(f"   파일2 옵션 수: {len(diff['file2'])}")
            if len(diff['file1']) > 0:
                print(f"   파일1 첫 번째 옵션: {diff['file1'][0][:100]}...")
            if len(diff['file2']) > 0:
                print(f"   파일2 첫 번째 옵션: {diff['file2'][0][:100]}...")
    
    if explanation_differences:
        print(f"\n=== explanation이 다른 문제들 (최대 3개 표시) ===")
        for i, diff in enumerate(explanation_differences[:3]):
            print(f"\n{i+1}. file_id: {diff['file_id']}, tag: {diff['tag']}")
            print(f"   파일1: {diff['file1'][:200]}...")
            print(f"   파일2: {diff['file2'][:200]}...")
    
    # 요약 리포트 생성
    print(f"\n\n=== 요약 리포트 ===")
    print(f"총 문제 수 비교:")
    print(f"  - 파일 1: {len(exams1)}개")
    print(f"  - 파일 2: {len(exams2)}개")
    print(f"  - 공통 (file_id, tag) 조합: {len(common_keys)}개")
    print(f"  - 파일 1에만: {len(only_in_file1)}개")
    print(f"  - 파일 2에만: {len(only_in_file2)}개")
    print(f"\n공통 문제 중 내용 차이:")
    print(f"  - question 차이: {len(question_differences)}개")
    print(f"  - answer 차이: {len(answer_differences)}개")
    print(f"  - options 차이: {len(options_differences)}개")
    print(f"  - explanation 차이: {len(explanation_differences)}개")

if __name__ == "__main__":
    file1 = "evaluation/eval_data/4_multiple_exam/1st/금융실무1_exam.json"
    file2 = "/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/데이터검수/재설계/완본/Origin_Exam1_금융실무1_type.json"
    
    compare_exams(file1, file2)

