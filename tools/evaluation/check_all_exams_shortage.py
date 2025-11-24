#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""모든 exam(1st~5th)별 부족한 subdomain 확인"""

import json
import os
from collections import defaultdict

# 경로 설정
onedrive_path = r'c:\Users\Jin\OneDrive\데이터L\selectstar'
exam_config_path = os.path.join(onedrive_path, 'evaluation', 'eval_data', 'exam_config.json')
exam_dir = os.path.join(onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam')

print("=" * 100)
print("모든 Exam별 부족한 Subdomain 확인")
print("=" * 100)

# exam_config.json 로드
print("\n1. exam_config.json 로딩 중...")
with open(exam_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 목표 문제 수 추출 (subdomain별)
target_counts = {}
for exam_name, exam_data in config['exams'].items():
    for domain in exam_data['domains']:
        if domain not in target_counts:
            target_counts[domain] = {}
        for subdomain, subdomain_info in exam_data['domain_details'][domain]['subdomains'].items():
            target_counts[domain][subdomain] = subdomain_info['count']

print(f"   목표 문제 수 추출 완료: {len(target_counts)}개 도메인")

# 각 exam별로 분석
exam_names = ['1st', '2nd', '3rd', '4th', '5th']
all_shortage_results = {}

for exam_name in exam_names:
    print(f"\n2. {exam_name} exam 분석 중...")
    exam_path = os.path.join(exam_dir, exam_name)
    
    if not os.path.exists(exam_path):
        print(f"   경로를 찾을 수 없습니다: {exam_path}")
        continue
    
    # exam 데이터 로드
    exam_data = []
    for filename in os.listdir(exam_path):
        if filename.endswith('.json'):
            filepath = os.path.join(exam_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                exam_data.extend(json.load(f))
    
    print(f"   로드된 문제: {len(exam_data)}개")
    
    # 실제 문제 수 계산 (subdomain별)
    actual_counts = defaultdict(lambda: defaultdict(int))
    for question in exam_data:
        domain = question.get('domain', '')
        subdomain = question.get('subdomain', '')
        if domain and subdomain:
            actual_counts[domain][subdomain] += 1
    
    # 부족한 subdomain 찾기
    shortage_subdomains = []
    for domain in sorted(target_counts.keys()):
        for subdomain in sorted(target_counts[domain].keys()):
            target = target_counts[domain][subdomain]
            actual = actual_counts[domain][subdomain]
            if actual < target:
                shortage = target - actual
                shortage_subdomains.append({
                    'domain': domain,
                    'subdomain': subdomain,
                    'target': target,
                    'actual': actual,
                    'shortage': shortage
                })
    
    all_shortage_results[exam_name] = {
        'total_questions': len(exam_data),
        'shortage_count': len(shortage_subdomains),
        'shortages': shortage_subdomains
    }
    
    if shortage_subdomains:
        print(f"   ⚠️  부족한 subdomain: {len(shortage_subdomains)}개")
    else:
        print(f"   ✅ 모든 subdomain이 목표를 충족했습니다!")

# 결과 출력
print("\n" + "=" * 100)
print("전체 요약")
print("=" * 100)

for exam_name in exam_names:
    result = all_shortage_results.get(exam_name, {})
    shortage_count = result.get('shortage_count', 0)
    total_questions = result.get('total_questions', 0)
    
    if shortage_count > 0:
        print(f"\n【{exam_name} exam】 ⚠️  부족한 subdomain: {shortage_count}개 (총 문제: {total_questions}개)")
        print("-" * 100)
        for shortage in result['shortages']:
            print(f"  - {shortage['domain']} > {shortage['subdomain']}: "
                  f"목표 {shortage['target']}, 실제 {shortage['actual']}, 부족 {shortage['shortage']}")
    else:
        print(f"\n【{exam_name} exam】 ✅ 모든 subdomain 충족 (총 문제: {total_questions}개)")

# 상세 결과를 파일로 저장
output_file = 'all_exams_shortage_analysis.md'
print(f"\n3. 상세 결과를 {output_file} 파일로 저장 중...")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# 모든 Exam별 부족한 Subdomain 분석\n\n")
    
    for exam_name in exam_names:
        result = all_shortage_results.get(exam_name, {})
        shortage_count = result.get('shortage_count', 0)
        total_questions = result.get('total_questions', 0)
        shortages = result.get('shortages', [])
        
        f.write(f"## {exam_name} Exam\n\n")
        f.write(f"- 총 문제 수: {total_questions}개\n")
        f.write(f"- 부족한 subdomain 수: {shortage_count}개\n\n")
        
        if shortage_count > 0:
            f.write("| 도메인 | Subdomain | 목표 | 실제 | 부족 |\n")
            f.write("|--------|-----------|------|------|------|\n")
            for shortage in shortages:
                f.write(f"| {shortage['domain']} | {shortage['subdomain']} | "
                       f"{shortage['target']} | {shortage['actual']} | **{shortage['shortage']}** |\n")
        else:
            f.write("✅ 모든 subdomain이 목표 문제 수를 충족했습니다!\n")
        
        f.write("\n")

print(f"   저장 완료: {output_file}")

# JSON 파일로도 저장
json_output_file = 'all_exams_shortage_analysis.json'
with open(json_output_file, 'w', encoding='utf-8') as f:
    json.dump(all_shortage_results, f, ensure_ascii=False, indent=2)

print(f"   저장 완료: {json_output_file}")

print("\n" + "=" * 100)
print("분석 완료!")
print("=" * 100)

