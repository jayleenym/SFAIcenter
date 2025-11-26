#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9_multiple_to_essay/essay_w_keyword.json 파일의 문제들을 
4_multiple_exam의 1st/2nd/3rd/4th/5th 세트에 매칭하여 5개의 JSON 파일로 분리
"""

import os
import sys
import json
import random
from collections import defaultdict

# tools 모듈 import를 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
_temp_tools_dir = os.path.dirname(current_dir)  # transformed -> tools
sys.path.insert(0, _temp_tools_dir)
from tools import tools_dir, ONEDRIVE_PATH
project_root = os.path.dirname(tools_dir)  # tools -> project_root
sys.path.insert(0, tools_dir)
sys.path.insert(0, project_root)
    
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
    
    # essay_file = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', 'best_ans.json')
    essay_file = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', 'full_explanation.json')
    exam_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '4_multiple_exam')
    output_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', 'questions')
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # best_ans.json 파일 읽기
    print(f"full_explanation.json 파일 읽는 중...")
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
    
    # 기존 파일들 로드 (있는 경우) - 샘플링 순서 보존을 위해
    existing_sampled = {}  # 기존 샘플링된 문제들 (순서 보존)
    existing_remaining = {}  # 기존 remaining 문제들
    existing_keys = {}  # 각 세트별로 이미 존재하는 (file_id, tag) 키 추적
    for exam_set in exam_sets:
        existing_file = os.path.join(output_dir, f'essay_questions_{exam_set}.json')
        remaining_file = os.path.join(output_dir, f'essay_questions_{exam_set}_remaining.json')
        
        existing_sampled[exam_set] = []
        existing_remaining[exam_set] = []
        existing_keys[exam_set] = set()
        
        # 기존 샘플링된 파일 로드
        if os.path.exists(existing_file):
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    existing_sampled[exam_set] = json.load(f)
                    # explanation이 있는 문제들만 유지하고 키 추적
                    filtered_sampled = []
                    for q in existing_sampled[exam_set]:
                        file_id = q.get('file_id')
                        tag = q.get('tag')
                        explanation = q.get('explanation', '').strip() if q.get('explanation') else ''
                        # explanation이 있는 문제만 유지
                        if explanation and file_id and tag:
                            key = (file_id, tag)
                            existing_keys[exam_set].add(key)
                            filtered_sampled.append(q)
                    existing_sampled[exam_set] = filtered_sampled
                    print(f"{exam_set} 기존 샘플링 파일 로드: {len(existing_sampled[exam_set])}개 문제 (explanation 있는 것만 유지)")
            except Exception as e:
                print(f"경고: {existing_file} 파일 읽기 오류: {e}")
                existing_sampled[exam_set] = []
        
        # 기존 remaining 파일 로드
        if os.path.exists(remaining_file):
            try:
                with open(remaining_file, 'r', encoding='utf-8') as f:
                    existing_remaining[exam_set] = json.load(f)
                    # explanation이 있는 문제들만 유지하고 키 추적
                    filtered_remaining = []
                    for q in existing_remaining[exam_set]:
                        file_id = q.get('file_id')
                        tag = q.get('tag')
                        explanation = q.get('explanation', '').strip() if q.get('explanation') else ''
                        # explanation이 있는 문제만 유지
                        if explanation and file_id and tag:
                            key = (file_id, tag)
                            existing_keys[exam_set].add(key)
                            filtered_remaining.append(q)
                    existing_remaining[exam_set] = filtered_remaining
                    print(f"{exam_set} 기존 remaining 파일 로드: {len(existing_remaining[exam_set])}개 문제 (explanation 있는 것만 유지)")
            except Exception as e:
                print(f"경고: {remaining_file} 파일 읽기 오류: {e}")
                existing_remaining[exam_set] = []
    
    # 각 essay 문제를 해당하는 exam 세트에 분류 (새로운 문제만)
    new_questions_by_set = defaultdict(list)  # 각 세트별로 새로운 문제들
    unmatched_essays = []
    
    for essay_q in essay_questions:
        file_id = essay_q.get('file_id')
        tag = essay_q.get('tag')
        
        # explanation이 비어있으면 넘어가기
        explanation = essay_q.get('explanation', '').strip() if essay_q.get('explanation') else ''
        if not explanation:
            continue
        
        if not file_id or not tag:
            unmatched_essays.append(essay_q)
            continue
        
        key = (file_id, tag)
        matched = False
        
        # 각 exam 세트에서 찾기
        for exam_set in exam_sets:
            if key in exam_data[exam_set]:
                # 기존에 없는 새로운 문제만 추가
                if key not in existing_keys[exam_set]:
                    new_questions_by_set[exam_set].append(essay_q)
                matched = True
                break
        
        if not matched:
            unmatched_essays.append(essay_q)
    
    # 결과 출력 및 통계 정보 수집
    print("\n=== 분류 결과 ===")
    statistics = {
        'total_essay_questions': len(essay_questions),
        'exam_sets': {},
        'unmatched_count': len(unmatched_essays)
    }
    
    for exam_set in exam_sets:
        existing_sampled_count = len(existing_sampled[exam_set])
        existing_remaining_count = len(existing_remaining[exam_set])
        new_count = len(new_questions_by_set[exam_set])
        print(f"{exam_set}: 기존 샘플링 {existing_sampled_count}개, 기존 remaining {existing_remaining_count}개, 신규 {new_count}개")
        statistics['exam_sets'][exam_set] = {
            'existing_sampled_count': existing_sampled_count,
            'existing_remaining_count': existing_remaining_count,
            'new_count': new_count
        }
    
    if unmatched_essays:
        print(f"매칭되지 않은 문제: {len(unmatched_essays)}개")
    
    # 통계 정보 저장
    statistics_file = os.path.join(output_dir, 'classification_statistics.json')
    with open(statistics_file, 'w', encoding='utf-8') as f:
        json.dump(statistics, f, ensure_ascii=False, indent=4)
    print(f"\n통계 정보 저장 완료: {statistics_file}")
    
    # 기존 샘플링 순서 보존하면서 100개 채우기
    print("\n=== 샘플링 순서 보존 및 100개 채우기 ===")
    random.seed(42)  # 재현 가능한 결과를 위한 seed 고정
    
    sampled_essays = {}
    remaining_essays = {}
    
    for exam_set in exam_sets:
        # 기존 샘플링된 문제들을 순서대로 유지
        sampled = existing_sampled[exam_set].copy()
        
        # 사용 가능한 문제 풀: 기존 remaining + 새로운 문제들
        available_pool = existing_remaining[exam_set] + new_questions_by_set[exam_set]
        
        # 100개가 안 되면 available_pool에서 채우기
        if len(sampled) < 100:
            needed = 100 - len(sampled)
            if len(available_pool) >= needed:
                # 필요한 만큼 추가
                sampled.extend(available_pool[:needed])
                remaining_essays[exam_set] = available_pool[needed:]
            else:
                # 모든 available_pool 추가
                sampled.extend(available_pool)
                remaining_essays[exam_set] = []
        else:
            # 100개 이상이면 그대로 유지하고 나머지는 remaining에
            remaining_essays[exam_set] = available_pool
        
        sampled_essays[exam_set] = sampled
        
        # 원본 파일에서 explanation 빈 문제가 제거된 수 계산
        original_file = os.path.join(output_dir, f'essay_questions_{exam_set}.json')
        original_count = 0
        if os.path.exists(original_file):
            try:
                with open(original_file, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                    original_count = len(original_data)
            except:
                pass
        
        removed_count = original_count - len(existing_sampled[exam_set])  # explanation 빈 문제 제거된 수
        added_count = len(sampled) - len(existing_sampled[exam_set])  # 새로 추가된 수
        
        print(f"{exam_set}: {len(sampled)}개 (기존 순서 보존, 제거: {removed_count}개, 추가: {added_count}개), remaining {len(remaining_essays[exam_set])}개")
        statistics['exam_sets'][exam_set]['sampled'] = len(sampled)
        statistics['exam_sets'][exam_set]['remaining'] = len(remaining_essays[exam_set])
        statistics['exam_sets'][exam_set]['added_count'] = added_count
        statistics['exam_sets'][exam_set]['removed_count'] = removed_count
    
    # 검증: 샘플링된 문제 + 나머지 문제 = 전체 문제 수
    print("\n=== 검증 중 ===")
    for exam_set in exam_sets:
        total_available = len(existing_sampled[exam_set]) + len(existing_remaining[exam_set]) + len(new_questions_by_set[exam_set])
        sampled_count = len(sampled_essays[exam_set])
        remaining_count = len(remaining_essays[exam_set])
        total_count = sampled_count + remaining_count
        if total_available != total_count:
            print(f"경고: {exam_set} 세트의 문제 수가 일치하지 않습니다! (전체: {total_available}, 합계: {total_count})")
        else:
            print(f"{exam_set} 세트 검증 완료: {total_available} = {sampled_count} + {remaining_count}")
    
    # 업데이트된 통계 정보 저장
    with open(statistics_file, 'w', encoding='utf-8') as f:
        json.dump(statistics, f, ensure_ascii=False, indent=4)
    
    # 각 세트별로 JSON 파일 저장
    print("\n=== 파일 저장 중 ===")
    for exam_set in exam_sets:
        # 샘플링된 100개 저장
        output_file = os.path.join(output_dir, f'essay_questions_{exam_set}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sampled_essays[exam_set], f, ensure_ascii=False, indent=4)
        print(f"{exam_set} 세트 저장 완료: {output_file} ({len(sampled_essays[exam_set])}개 문제)")
        
        # 선택되지 않은 나머지 문제들 저장
        if remaining_essays[exam_set]:
            remaining_file = os.path.join(output_dir, f'essay_questions_{exam_set}_remaining.json')
            with open(remaining_file, 'w', encoding='utf-8') as f:
                json.dump(remaining_essays[exam_set], f, ensure_ascii=False, indent=4)
            print(f"{exam_set} 세트 나머지 저장 완료: {remaining_file} ({len(remaining_essays[exam_set])}개 문제)")
    
    # 매칭되지 않은 문제가 있으면 별도 파일로 저장
    if unmatched_essays:
        unmatched_file = os.path.join(output_dir, 'essay_questions_unmatched.json')
        with open(unmatched_file, 'w', encoding='utf-8') as f:
            json.dump(unmatched_essays, f, ensure_ascii=False, indent=4)
        print(f"매칭되지 않은 문제 저장: {unmatched_file} ({len(unmatched_essays)}개 문제)")
    
    print("\n완료!")

if __name__ == '__main__':
    main()