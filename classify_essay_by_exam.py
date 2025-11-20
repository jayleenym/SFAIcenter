#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9_multiple_to_essay/essay_w_keyword.json 파일의 문제들을 
4_multiple_exam의 1st/2nd/3rd/4th/5th 세트에 매칭하여 5개의 JSON 파일로 분리
"""

import os
import json
import platform
from collections import defaultdict
from tools.pipeline.config import ONEDRIVE_PATH
    
def load_exam_questions(exam_dir, exam_set_name):
    """
    특정 exam 세트의 모든 문제를 로드하고 (file_id, tag)를 키로 하는 딕셔너리 생성
    """
    exam_path = os.path.join(exam_dir, exam_set_name)
    if not os.path.exists(exam_path):
        print(f"경고: {exam_path} 경로가 존재하지 않습니다.")
        return {}
    
    exam_questions = {}
    
    # exam_set_name 폴더의 모든 JSON 파일 읽기
    for filename in os.listdir(exam_path):
        if filename.endswith('.json'):
            file_path = os.path.join(exam_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    questions = json.load(f)
                    # 각 문제를 (file_id, tag) 튜플을 키로 저장
                    for q in questions:
                        if 'file_id' in q and 'tag' in q:
                            key = (q['file_id'], q['tag'])
                            exam_questions[key] = q
            except Exception as e:
                print(f"경고: {file_path} 파일을 읽는 중 오류 발생: {e}")
    
    print(f"{exam_set_name} 세트: {len(exam_questions)}개 문제 로드 완료")
    return exam_questions

def main():
    # 경로 설정 - 현재 스크립트 위치 기준으로 evaluation_yejin 경로 사용
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, 'evaluation_yejin')
    
    # evaluation_yejin이 없으면 ONEDRIVE_PATH 사용 시도
    if not os.path.exists(base_path):
        base_path = os.path.join(ONEDRIVE_PATH, 'evaluation')
        print(f"evaluation_yejin을 찾을 수 없어 ONEDRIVE_PATH 사용: {base_path}")
    else:
        print(f"evaluation_yejin 경로 사용: {base_path}")
    
    essay_file = os.path.join(base_path, 'eval_data', '9_multiple_to_essay', 'essay_w_keyword.json')
    exam_dir = os.path.join(base_path, 'eval_data', '4_multiple_exam')
    output_dir = os.path.join(base_path, 'eval_data', '9_multiple_to_essay')
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # essay_w_keyword.json 파일 읽기
    print(f"essay_w_keyword.json 파일 읽는 중...")
    print(f"파일 경로: {essay_file}")
    if not os.path.exists(essay_file):
        print(f"오류: {essay_file} 파일이 존재하지 않습니다.")
        return
    
    try:
        print("JSON 파일 로딩 시작...")
        with open(essay_file, 'r', encoding='utf-8') as f:
            essay_questions = json.load(f)
        print(f"총 {len(essay_questions)}개의 서술형 문제 로드 완료")
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        print(f"파일 크기: {os.path.getsize(essay_file) / (1024*1024):.2f} MB")
        return
    
    # 각 exam 세트의 문제들 로드
    exam_sets = ['1st', '2nd', '3rd', '4th', '5th']
    exam_data = {}
    
    for exam_set in exam_sets:
        exam_data[exam_set] = load_exam_questions(exam_dir, exam_set)
    
    # 각 essay 문제를 해당하는 exam 세트에 분류
    classified_essays = defaultdict(list)
    unmatched_essays = []
    
    for essay_q in essay_questions:
        file_id = essay_q.get('file_id')
        tag = essay_q.get('tag')
        
        if not file_id or not tag:
            unmatched_essays.append(essay_q)
            continue
        
        key = (file_id, tag)
        matched = False
        
        # 각 exam 세트에서 찾기
        for exam_set in exam_sets:
            if key in exam_data[exam_set]:
                classified_essays[exam_set].append(essay_q)
                matched = True
                break
        
        if not matched:
            unmatched_essays.append(essay_q)
    
    # 결과 출력
    print("\n=== 분류 결과 ===")
    for exam_set in exam_sets:
        count = len(classified_essays[exam_set])
        print(f"{exam_set}: {count}개 문제")
    
    if unmatched_essays:
        print(f"매칭되지 않은 문제: {len(unmatched_essays)}개")
    
    # 각 세트별로 JSON 파일 저장
    print("\n=== 파일 저장 중 ===")
    for exam_set in exam_sets:
        output_file = os.path.join(output_dir, f'essay_w_keyword_{exam_set}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(classified_essays[exam_set], f, ensure_ascii=False, indent=4)
        print(f"{exam_set} 세트 저장 완료: {output_file} ({len(classified_essays[exam_set])}개 문제)")
    
    # 매칭되지 않은 문제가 있으면 별도 파일로 저장
    if unmatched_essays:
        unmatched_file = os.path.join(output_dir, 'essay_w_keyword_unmatched.json')
        with open(unmatched_file, 'w', encoding='utf-8') as f:
            json.dump(unmatched_essays, f, ensure_ascii=False, indent=4)
        print(f"매칭되지 않은 문제 저장: {unmatched_file} ({len(unmatched_essays)}개 문제)")
    
    print("\n완료!")

if __name__ == '__main__':
    main()

