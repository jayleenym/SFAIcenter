#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
금융일반_exam.json 파일에 exam_config를 보고 부족한 문제를 
multiple-choice_subdomain_classified_ALL.json에서 subdomain 맞춰서 채워넣는 스크립트
원본의 문제와 순서는 유지합니다.
"""

import os
import json
import random
import copy
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import sys

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'tools'))
from core.exam_config import ExamConfig


def load_json(file_path: str) -> List[Dict]:
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: List[Dict], file_path: str):
    """JSON 파일을 저장합니다."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def fill_exam_shortage(
    exam_file: str,
    source_file: str = None,
    config_path: str = None,
    output_file: str = None,
    seed: int = 42
):
    """
    exam 파일의 부족한 문제를 source에서 채워넣습니다.
    원본의 문제와 순서는 유지합니다.
    
    Args:
        exam_file: 금융일반_exam.json 파일 경로
        source_file: multiple-choice_subdomain_classified_ALL.json 파일 경로 (None이면 기본 경로 사용)
        config_path: exam_config.json 파일 경로 (None이면 기본 경로 사용)
        output_file: 출력 파일 경로 (None이면 원본 파일 덮어쓰기)
        seed: 랜덤 시드
    """
    random.seed(seed)
    
    print("=" * 80)
    print("시험 문제 부족분 채우기 시작")
    print("=" * 80)
    
    # 1. 파일명에서 시험 이름 추출
    filename = os.path.basename(exam_file)
    exam_name = None
    exam_names = ['금융실무1', '금융실무2', '금융심화', '금융일반']
    for name in exam_names:
        if name in filename:
            exam_name = name
            break
    
    if exam_name is None:
        raise ValueError(f"파일명에서 시험 이름을 추출할 수 없습니다: {filename}")
    
    print(f"\n1. 시험 이름 추출: {exam_name}")
    
    # 2. exam 파일 로드
    print(f"\n2. Exam 파일 로딩: {exam_file}")
    exam_questions = load_json(exam_file)
    print(f"   - 현재 문제 수: {len(exam_questions)}개")
    
    # 3. exam_config.json 로드
    print(f"\n3. exam_config.json 로딩")
    if config_path is None:
        # 기본 경로 찾기
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(project_root, 'evaluation', 'eval_data', 'exam_config.json')
        
        # OneDrive 경로도 시도
        if not os.path.exists(config_path):
            import platform
            system = platform.system()
            home_dir = os.path.expanduser("~")
            if system == "Windows":
                onedrive_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
            else:
                onedrive_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
            config_path = os.path.join(onedrive_path, 'evaluation', 'eval_data', 'exam_config.json')
    
    exam_config = ExamConfig(config_path=config_path)
    stats = exam_config.get_exam_statistics()
    
    if exam_name not in stats:
        available_exams = ', '.join(stats.keys())
        raise ValueError(f"exam_config.json에 '{exam_name}' 시험이 없습니다. 사용 가능한 시험: {available_exams}")
    
    exam_stats = stats[exam_name]
    print(f"   - {exam_name} 도메인 수: {len(exam_stats)}개")
    
    # 4. 현재 문제의 domain/subdomain 분포 확인
    print(f"\n4. 현재 문제의 domain/subdomain 분포 확인")
    current_distribution = defaultdict(lambda: defaultdict(int))
    exam_questions_by_key = {}
    
    for q in exam_questions:
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        
        if domain and subdomain:
            current_distribution[domain][subdomain] += 1
        
        # (file_id, tag)로 인덱싱
        if file_id and tag:
            exam_questions_by_key[(file_id, tag)] = q
    
    # 5. 필요한 문제 수와 현재 문제 수 비교
    print(f"\n5. 필요한 문제 수와 현재 문제 수 비교")
    shortage = defaultdict(lambda: defaultdict(int))
    
    for domain_name, domain_data in exam_stats.items():
        for subdomain_name, needed_count in domain_data['exam_subdomain_distribution'].items():
            current_count = current_distribution[domain_name][subdomain_name]
            shortage_count = max(0, needed_count - current_count)
            shortage[domain_name][subdomain_name] = shortage_count
            
            print(f"   - {domain_name} > {subdomain_name}:")
            print(f"     필요: {needed_count}개, 현재: {current_count}개, 부족: {shortage_count}개")
    
    # 부족한 문제가 없으면 종료
    total_shortage = sum(sum(shortage[d].values()) for d in shortage)
    if total_shortage == 0:
        print(f"\n부족한 문제가 없습니다. 작업을 종료합니다.")
        return
    
    # 6. Source 파일 로드
    print(f"\n6. Source 파일 로딩")
    if source_file is None:
        # 기본 경로 찾기
        project_root = os.path.dirname(os.path.abspath(__file__))
        source_file = os.path.join(
            project_root,
            'evaluation',
            'eval_data',
            '2_subdomain',
            'multiple-choice_subdomain_classified_ALL.json'
        )
        
        # OneDrive 경로도 시도
        if not os.path.exists(source_file):
            import platform
            system = platform.system()
            home_dir = os.path.expanduser("~")
            if system == "Windows":
                onedrive_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
            else:
                onedrive_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
            source_file = os.path.join(onedrive_path, 'evaluation', 'eval_data', '2_subdomain', 'multiple-choice_subdomain_classified_ALL.json')
    
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"Source 파일을 찾을 수 없습니다: {source_file}")
    
    source_questions = load_json(source_file)
    print(f"   - Source 문제 수: {len(source_questions)}개")
    
    # 7. Source를 domain/subdomain별로 그룹화 (이미 사용된 문제 제외)
    print(f"\n7. Source 문제 그룹화")
    source_by_domain_subdomain = defaultdict(lambda: defaultdict(list))
    used_keys = set(exam_questions_by_key.keys())
    
    for q in source_questions:
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        
        if domain and subdomain and file_id and tag:
            key = (file_id, tag)
            if key not in used_keys:
                source_by_domain_subdomain[domain][subdomain].append(q)
    
    print(f"   - 사용 가능한 문제 수:")
    for domain_name in exam_stats.keys():
        for subdomain_name in exam_stats[domain_name]['exam_subdomain_distribution'].keys():
            available = len(source_by_domain_subdomain[domain_name][subdomain_name])
            needed = shortage[domain_name][subdomain_name]
            print(f"     {domain_name} > {subdomain_name}: {available}개 (필요: {needed}개)")
    
    # 8. 부족한 문제 채우기
    print(f"\n8. 부족한 문제 채우기 시작")
    added_questions = []
    
    # 각 domain/subdomain별로 부족한 문제 선택
    questions_to_add = defaultdict(lambda: defaultdict(list))
    
    for domain_name in exam_stats.keys():
        for subdomain_name, needed_count in shortage[domain_name].items():
            if needed_count > 0:
                available = source_by_domain_subdomain[domain_name][subdomain_name]
                
                if len(available) >= needed_count:
                    # 충분한 문제가 있으면 랜덤 선택
                    selected = random.sample(available, needed_count)
                    questions_to_add[domain_name][subdomain_name] = selected
                    for q in selected:
                        used_keys.add((q.get('file_id', ''), q.get('tag', '')))
                    added_questions.extend(selected)
                    print(f"   - {domain_name} > {subdomain_name}: {needed_count}개 선택")
                else:
                    # 부족하면 가능한 만큼만 추가
                    selected = available[:needed_count]
                    questions_to_add[domain_name][subdomain_name] = selected
                    for q in selected:
                        used_keys.add((q.get('file_id', ''), q.get('tag', '')))
                    added_questions.extend(selected)
                    print(f"   - {domain_name} > {subdomain_name}: {len(selected)}개 선택 (부족: {needed_count - len(selected)}개)")
    
    # 9. 최종 결과 구성 (원본 순서 유지 + 각 subdomain 그룹 끝에 추가)
    print(f"\n9. 최종 결과 구성")
    
    final_questions = []
    last_seen_subdomain = {}  # 각 (domain, subdomain)의 마지막 위치 추적
    
    # 원본 문제들을 순회하면서 각 subdomain의 마지막 문제 뒤에 추가
    for idx, q in enumerate(exam_questions):
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        
        # 현재 문제 추가
        final_questions.append(q)
        
        # 다음 문제를 확인하여 subdomain이 바뀌는지 체크
        next_domain = None
        next_subdomain = None
        if idx + 1 < len(exam_questions):
            next_q = exam_questions[idx + 1]
            next_domain = next_q.get('domain', '')
            next_subdomain = next_q.get('subdomain', '')
        
        # subdomain이 바뀌거나 마지막 문제인 경우, 현재 subdomain의 부족한 문제 추가
        if (domain and subdomain and 
            (next_domain != domain or next_subdomain != subdomain or idx == len(exam_questions) - 1)):
            # 이 subdomain에 추가할 문제가 있는지 확인
            if domain in questions_to_add and subdomain in questions_to_add[domain]:
                questions = questions_to_add[domain][subdomain]
                if questions:
                    final_questions.extend(questions)
                    print(f"   - {domain} > {subdomain}: {len(questions)}개 추가 (위치: {idx + 1} 이후)")
                    # 추가한 문제는 제거 (중복 방지)
                    questions_to_add[domain][subdomain] = []
    
    # 남은 문제들 추가 (혹시 모를 경우를 위해)
    for domain_name in questions_to_add.keys():
        for subdomain_name in questions_to_add[domain_name].keys():
            remaining = questions_to_add[domain_name][subdomain_name]
            if remaining:
                final_questions.extend(remaining)
                print(f"   - {domain_name} > {subdomain_name}: {len(remaining)}개 추가 (남은 문제)")
    
    # 10. 최종 통계
    print(f"\n10. 최종 통계")
    print(f"   - 원본 문제 수: {len(exam_questions)}개")
    print(f"   - 추가된 문제: {len(added_questions)}개")
    print(f"   - 총 문제 수: {len(final_questions)}개")
    
    final_distribution = defaultdict(lambda: defaultdict(int))
    for q in final_questions:
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        if domain and subdomain:
            final_distribution[domain][subdomain] += 1
    
    print(f"\n   최종 domain/subdomain 분포:")
    for domain_name in exam_stats.keys():
        print(f"   - {domain_name}:")
        for subdomain_name, needed_count in exam_stats[domain_name]['exam_subdomain_distribution'].items():
            final_count = final_distribution[domain_name][subdomain_name]
            status = "✓" if final_count >= needed_count else "✗"
            print(f"     {status} {subdomain_name}: {final_count}/{needed_count}개")
    
    # 11. 파일 저장
    if output_file is None:
        output_file = exam_file
    
    print(f"\n11. 결과 파일 저장: {output_file}")
    save_json(final_questions, output_file)
    
    # 12. 요약 리포트
    print(f"\n" + "=" * 80)
    print("작업 완료")
    print("=" * 80)
    print(f"시험 이름: {exam_name}")
    print(f"출력 파일: {output_file}")
    print(f"원본 문제 수: {len(exam_questions)}개")
    print(f"추가된 문제 수: {len(added_questions)}개")
    print(f"최종 문제 수: {len(final_questions)}개")
    
    return {
        'exam_name': exam_name,
        'output_file': output_file,
        'original_count': len(exam_questions),
        'added_count': len(added_questions),
        'final_count': len(final_questions)
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='exam 파일의 부족한 문제를 multiple-choice_subdomain_classified_ALL.json에서 채워넣습니다.'
    )
    parser.add_argument(
        '--exam',
        type=str,
        default='/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/evaluation/eval_data/4_multiple_exam/3rd/금융일반_exam.json',
        help='exam 파일 경로 (예: 금융일반_exam.json)'
    )
    parser.add_argument(
        '--source',
        type=str,
        default=None,
        help='multiple-choice_subdomain_classified_ALL.json 파일 경로 (기본값: evaluation/eval_data/2_subdomain/multiple-choice_subdomain_classified_ALL.json)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='exam_config.json 파일 경로 (기본값: evaluation/eval_data/exam_config.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 파일 경로 (기본값: 원본 파일 덮어쓰기)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='랜덤 시드 (기본값: 42)'
    )
    
    args = parser.parse_args()
    
    result = fill_exam_shortage(
        exam_file=args.exam,
        source_file=args.source,
        config_path=args.config,
        output_file=args.output,
        seed=args.seed
    )
    
    print(f"\n결과: {result}")

