#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Origin_Exam1_금융실무1_type.json의 문제들과 동일한 문제(file_id와 tag가 같은)로 
최대한 구성하고, 부족한 문제는 exam_config.json 확인해서 채워넣는 스크립트
"""

import os
import json
import random
import copy
import re
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import sys
import os
# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'tools'))
from core.exam_config import ExamConfig
from qna.extraction.tag_processor import TagProcessor

def load_json(file_path: str) -> List[Dict]:
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: List[Dict], file_path: str):
    """JSON 파일을 저장합니다."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_exam_name_from_filename(file_path: str) -> str:
    """
    파일명에서 시험 이름을 추출합니다.
    
    예시:
    - Origin_Exam1_금융실무1_type.json -> 금융실무1
    - Origin_Exam1_금융실무2_type.json -> 금융실무2
    - Origin_Exam1_금융심화_type.json -> 금융심화
    - Origin_Exam1_금융일반_type.json -> 금융일반
    
    Args:
        file_path: 파일 경로 또는 파일명
        
    Returns:
        추출된 시험 이름 (예: "금융실무1")
    """
    filename = os.path.basename(file_path)
    
    # 패턴 1: Origin_Exam1_금융실무1_type.json
    pattern1 = r'Origin_Exam\d+_(금융실무[12]|금융심화|금융일반)_type\.json'
    match = re.search(pattern1, filename)
    if match:
        return match.group(1)
    
    # 패턴 2: 금융실무1_exam.json 같은 형태
    pattern2 = r'(금융실무[12]|금융심화|금융일반)_exam'
    match = re.search(pattern2, filename)
    if match:
        return match.group(1)
    
    # 패턴 3: 파일명에 직접 포함된 경우
    exam_names = ['금융실무1', '금융실무2', '금융심화', '금융일반']
    for exam_name in exam_names:
        if exam_name in filename:
            return exam_name
    
    # 기본값으로 금융실무1 반환 (하위 호환성)
    print(f"경고: 파일명에서 시험 이름을 추출할 수 없어 기본값 '금융실무1'을 사용합니다: {filename}")
    return '금융실무1'

def find_extracted_qna_file(file_id: str, onedrive_path: str = None) -> str:
    """file_id에 해당하는 _extracted_qna.json 파일 경로를 찾습니다."""
    if onedrive_path is None:
        # 프로젝트 루트 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workbook_base = os.path.join(current_dir, 'evaluation', 'workbook_data')
    else:
        workbook_base = os.path.join(onedrive_path, 'evaluation', 'workbook_data')
    
    for root, dirs, files in os.walk(workbook_base):
        for file in files:
            if file == f'{file_id}_extracted_qna.json':
                return os.path.join(root, file)
    return None

def load_extracted_qna_item(file_id: str, tag: str, extracted_qna_cache: Dict, onedrive_path: str = None) -> Dict[str, Any]:
    """_extracted_qna.json 파일에서 특정 file_id와 tag에 해당하는 항목을 로드합니다."""
    cache_key = file_id
    if cache_key not in extracted_qna_cache:
        extracted_qna_file = find_extracted_qna_file(file_id, onedrive_path)
        if not extracted_qna_file:
            return None
        try:
            with open(extracted_qna_file, 'r', encoding='utf-8') as f:
                extracted_qna_cache[cache_key] = json.load(f)
        except Exception as e:
            print(f"경고: _extracted_qna.json 파일 로드 실패 ({extracted_qna_file}): {e}")
            return None
    
    extracted_qna_data = extracted_qna_cache[cache_key]
    
    # 태그 정규화: 중괄호 제거하여 비교
    tag_normalized = tag.strip('{}') if tag else ''
    
    # _extracted_qna.json의 각 항목을 직접 확인
    for item in extracted_qna_data:
        # qna_data에서 tag 추출
        qna_data = item.get('qna_data', {})
        item_tag = qna_data.get('tag', '')
        
        # 태그 비교 (중괄호 제거하여 비교)
        item_tag_normalized = item_tag.strip('{}') if item_tag else ''
        
        if item_tag_normalized == tag_normalized:
            return item
    
    return None

def replace_tags_in_exam_data(exam_data: List[Dict], onedrive_path: str = None) -> List[Dict]:
    """태그 대치 수행"""
    extracted_qna_cache = {}
    exam_data_with_tags_replaced = []
    replaced_count = 0
    not_found_count = 0
    no_tag_data_count = 0
    
    for item in exam_data:
        file_id = item.get('file_id', '')
        tag = item.get('tag', '')
        
        # 깊은 복사로 원본 데이터 보호
        item_copy = copy.deepcopy(item)
        
        # 태그 대치 전에 태그가 있는지 확인
        tag_pattern = r'\{(f_\d{4}_\d{4}|tb_\d{4}_\d{4}|note_\d{4}_\d{4}|etc_\d{4}_\d{4})\}'
        has_tags_before = False
        
        # qna_data 구조 확인
        qna_data = item_copy.get('qna_data', {})
        is_qna_data_structure = 'description' in qna_data if qna_data else False
        
        if is_qna_data_structure:
            desc = qna_data['description']
            content_fields = [
                desc.get('question', ''),
                desc.get('answer', ''),
                desc.get('explanation', '')
            ]
            if desc.get('options'):
                content_fields.extend(desc['options'] if isinstance(desc['options'], list) else [desc['options']])
        else:
            # 직접 필드 구조
            content_fields = [
                item_copy.get('question', ''),
                item_copy.get('answer', ''),
                item_copy.get('explanation', '')
            ]
            if item_copy.get('options'):
                content_fields.extend(item_copy['options'] if isinstance(item_copy['options'], list) else [item_copy['options']])
        
        for field_content in content_fields:
            if field_content and re.search(tag_pattern, str(field_content)):
                has_tags_before = True
                break
        
        extracted_qna_item = load_extracted_qna_item(file_id, tag, extracted_qna_cache, onedrive_path)
        if extracted_qna_item:
            additional_tag_data = extracted_qna_item.get('additional_tag_data', [])
            if additional_tag_data:
                # 태그 대치 수행
                if is_qna_data_structure:
                    # qna_data 구조인 경우
                    item_copy = TagProcessor.replace_tags_in_qna_data(item_copy, additional_tag_data)
                else:
                    # 직접 필드 구조인 경우
                    if 'question' in item_copy and item_copy['question']:
                        item_copy['question'] = TagProcessor.replace_tags_in_text(item_copy['question'], additional_tag_data)
                    if 'answer' in item_copy and item_copy['answer']:
                        item_copy['answer'] = TagProcessor.replace_tags_in_text(item_copy['answer'], additional_tag_data)
                    if 'explanation' in item_copy and item_copy['explanation']:
                        item_copy['explanation'] = TagProcessor.replace_tags_in_text(item_copy['explanation'], additional_tag_data)
                    if 'options' in item_copy and item_copy['options']:
                        if isinstance(item_copy['options'], list):
                            item_copy['options'] = [TagProcessor.replace_tags_in_text(option, additional_tag_data) for option in item_copy['options']]
                        else:
                            item_copy['options'] = TagProcessor.replace_tags_in_text(item_copy['options'], additional_tag_data)
                
                # 태그 대치 후 확인
                has_tags_after = False
                if is_qna_data_structure:
                    qna_data_after = item_copy.get('qna_data', {})
                    if 'description' in qna_data_after:
                        desc_after = qna_data_after['description']
                        content_fields_after = [
                            desc_after.get('question', ''),
                            desc_after.get('answer', ''),
                            desc_after.get('explanation', '')
                        ]
                        if desc_after.get('options'):
                            content_fields_after.extend(desc_after['options'] if isinstance(desc_after['options'], list) else [desc_after['options']])
                else:
                    content_fields_after = [
                        item_copy.get('question', ''),
                        item_copy.get('answer', ''),
                        item_copy.get('explanation', '')
                    ]
                    if item_copy.get('options'):
                        content_fields_after.extend(item_copy['options'] if isinstance(item_copy['options'], list) else [item_copy['options']])
                
                for field_content in content_fields_after:
                    if field_content and re.search(tag_pattern, str(field_content)):
                        has_tags_after = True
                        break
                
                if has_tags_before and not has_tags_after:
                    replaced_count += 1
                elif has_tags_before and has_tags_after:
                    print(f"경고: 태그 대치 후에도 태그가 남아있음: {file_id}_{tag}")
            else:
                no_tag_data_count += 1
        else:
            not_found_count += 1
            if has_tags_before:
                print(f"경고: _extracted_qna.json에서 항목을 찾을 수 없음: {file_id}_{tag}")
        
        # additional_tag_data 필드 제거 (exam 파일에는 불필요)
        item_cleaned = {k: v for k, v in item_copy.items() if k != 'additional_tag_data'}
        exam_data_with_tags_replaced.append(item_cleaned)
    
    print(f"태그 대치 완료: 성공={replaced_count}, 찾을 수 없음={not_found_count}, 태그데이터 없음={no_tag_data_count}, 전체={len(exam_data)}")
    return exam_data_with_tags_replaced

def build_exam_from_origin(
    origin_file: str,
    source_file: str,
    config_path: str = None,
    output_file: str = None,
    seed: int = 42
):
    """
    Origin 파일의 문제들을 매칭하고, 부족한 문제는 source에서 채워넣습니다.
    
    Args:
        origin_file: Origin_Exam1_금융실무1_type.json 파일 경로
        source_file: multiple-choice_subdomain_classified_ALL.json 파일 경로
        config_path: exam_config.json 파일 경로 (None이면 기본 경로 사용)
        output_file: 출력 파일 경로 (None이면 자동 생성)
        seed: 랜덤 시드
    """
    random.seed(seed)
    
    print("=" * 80)
    print("시험 문제 구성 시작")
    print("=" * 80)
    
    # 1. 파일 로드
    print(f"\n1. Origin 파일 로딩: {origin_file}")
    origin_questions = load_json(origin_file)
    print(f"   - Origin 문제 수: {len(origin_questions)}개")
    
    print(f"\n2. Source 파일 로딩: {source_file}")
    source_questions = load_json(source_file)
    print(f"   - Source 문제 수: {len(source_questions)}개")
    
    # source를 (file_id, tag)로 인덱싱
    source_index = {}
    for q in source_questions:
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        if file_id and tag:
            source_index[(file_id, tag)] = q
    
    print(f"   - Source 인덱스 크기: {len(source_index)}개")
    
    # 2. 파일명에서 시험 이름 추출
    exam_name = extract_exam_name_from_filename(origin_file)
    print(f"\n3. 시험 이름 추출: {exam_name}")
    
    # 3. exam_config.json 로드
    print(f"\n4. exam_config.json 로딩")
    if config_path is None:
        # 기본 경로 찾기
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(project_root, 'evaluation', 'eval_data', 'exam_config.json')
    
    exam_config = ExamConfig(config_path=config_path)
    stats = exam_config.get_exam_statistics()
    
    if exam_name not in stats:
        available_exams = ', '.join(stats.keys())
        raise ValueError(f"exam_config.json에 '{exam_name}' 시험이 없습니다. 사용 가능한 시험: {available_exams}")
    
    exam_stats = stats[exam_name]
    print(f"   - {exam_name} 도메인 수: {len(exam_stats)}개")
    
    # 4. Origin 문제들을 매칭
    print(f"\n5. Origin 문제 매칭 시작")
    matched_questions = []
    matched_keys = set()
    not_found_questions = []
    not_found_in_source_list = []  # Source에 없는 문제들 (removed_questions에 추가할 용도)
    
    for origin_q in origin_questions:
        file_id = origin_q.get('file_id', '')
        tag = origin_q.get('tag', '')
        key = (file_id, tag)
        
        if key in source_index:
            matched_questions.append(source_index[key])
            matched_keys.add(key)
        else:
            # Source에 없는 문제 정보 저장
            not_found_info = {
                'file_id': file_id,
                'tag': tag,
                'domain': origin_q.get('domain', ''),
                'subdomain': origin_q.get('subdomain', ''),
                'question': origin_q.get('question', '')[:200] + '...' if len(origin_q.get('question', '')) > 200 else origin_q.get('question', ''),
                'reason': 'Origin에는 있지만 Source에 없어서 제외됨'
            }
            not_found_questions.append({
                'file_id': file_id,
                'tag': tag,
                'question': not_found_info['question']
            })
            not_found_in_source_list.append(not_found_info)
    
    print(f"   - 매칭된 문제: {len(matched_questions)}개")
    print(f"   - 매칭 실패: {len(not_found_questions)}개")
    
    if not_found_questions:
        print(f"\n   매칭 실패한 문제들 (최대 10개 표시):")
        for i, q in enumerate(not_found_questions[:10]):
            print(f"   {i+1}. file_id={q['file_id']}, tag={q['tag']}")
            print(f"      question: {q['question']}")
    
    # 5. 현재 구성된 문제의 domain/subdomain 분포 확인
    print(f"\n6. 현재 구성된 문제의 domain/subdomain 분포 확인")
    current_distribution = defaultdict(lambda: defaultdict(int))
    
    for q in matched_questions:
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        if domain and subdomain:
            current_distribution[domain][subdomain] += 1
    
    # 6. 필요한 문제 수와 현재 문제 수 비교
    print(f"\n7. 필요한 문제 수와 현재 문제 수 비교")
    needed_distribution = {}
    shortage = defaultdict(lambda: defaultdict(int))
    
    for domain_name, domain_data in exam_stats.items():
        needed_distribution[domain_name] = {}
        for subdomain_name, count in domain_data['exam_subdomain_distribution'].items():
            needed_distribution[domain_name][subdomain_name] = count
            current_count = current_distribution[domain_name][subdomain_name]
            shortage_count = max(0, count - current_count)
            shortage[domain_name][subdomain_name] = shortage_count
            
            print(f"   - {domain_name} > {subdomain_name}:")
            print(f"     필요: {count}개, 현재: {current_count}개, 부족: {shortage_count}개")
    
    # 7. 부족한 문제 채우기
    print(f"\n8. 부족한 문제 채우기 시작")
    used_questions = matched_keys.copy()
    added_questions = []
    
    # source를 domain/subdomain별로 그룹화
    source_by_domain_subdomain = defaultdict(lambda: defaultdict(list))
    for q in source_questions:
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        if domain and subdomain and file_id and tag:
            key = (file_id, tag)
            if key not in used_questions:
                source_by_domain_subdomain[domain][subdomain].append(q)
    
    # 각 domain/subdomain별로 부족한 문제 채우기
    for domain_name in shortage.keys():
        for subdomain_name, needed_count in shortage[domain_name].items():
            if needed_count > 0:
                available = source_by_domain_subdomain[domain_name][subdomain_name]
                
                if len(available) >= needed_count:
                    # 충분한 문제가 있으면 랜덤 선택
                    selected = random.sample(available, needed_count)
                    added_questions.extend(selected)
                    for q in selected:
                        used_questions.add((q.get('file_id', ''), q.get('tag', '')))
                    print(f"   - {domain_name} > {subdomain_name}: {needed_count}개 추가")
                else:
                    # 부족하면 가능한 만큼만 추가
                    selected = available[:needed_count]
                    added_questions.extend(selected)
                    for q in selected:
                        used_questions.add((q.get('file_id', ''), q.get('tag', '')))
                    print(f"   - {domain_name} > {subdomain_name}: {len(selected)}개 추가 (부족: {needed_count - len(selected)}개)")
    
    # 8. 최종 결과 구성
    print(f"\n9. 최종 결과 구성")
    final_questions = matched_questions + added_questions
    
    # (file_id, tag) 조합으로 중복 체크 (같은 조합이 있으면 제거)
    seen_keys = set()
    deduplicated_questions = []
    duplicate_count = 0
    
    for q in final_questions:
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        key = (file_id, tag)
        
        if key not in seen_keys:
            seen_keys.add(key)
            deduplicated_questions.append(q)
        else:
            duplicate_count += 1
            print(f"   경고: 동일한 (file_id, tag) 조합 제거 - file_id={file_id}, tag={tag}")
    
    if duplicate_count > 0:
        print(f"   - 중복 제거된 문제: {duplicate_count}개")
    
    # domain/subdomain별로 정렬 (exam_config의 순서대로)
    final_sorted = []
    for domain_name in exam_stats.keys():
        domain_questions = [q for q in deduplicated_questions if q.get('domain') == domain_name]
        
        # subdomain별로 그룹화
        subdomain_groups = defaultdict(list)
        for q in domain_questions:
            subdomain = q.get('subdomain', '')
            if subdomain:
                subdomain_groups[subdomain].append(q)
        
        # exam_config의 subdomain 순서대로 정렬
        for subdomain_name in exam_stats[domain_name]['exam_subdomain_distribution'].keys():
            if subdomain_name in subdomain_groups:
                final_sorted.extend(subdomain_groups[subdomain_name])
    
    # 정렬되지 않은 문제들도 추가 (혹시 모를 경우)
    remaining = [q for q in deduplicated_questions if q not in final_sorted]
    if remaining:
        print(f"   경고: 정렬되지 않은 문제 {len(remaining)}개 발견")
        final_sorted.extend(remaining)
    
    # 9. 초과 문제 삭제 (각 subdomain별로 필요한 개수보다 많으면 랜덤하게 삭제)
    print(f"\n9-1. 초과 문제 삭제 시작")
    final_after_removal = []
    removed_count = 0
    removed_questions_list = []  # 삭제된 문제 정보 저장용
    
    # Source에 없는 문제들도 removed_questions_list에 추가
    removed_questions_list.extend(not_found_in_source_list)
    removed_count += len(not_found_in_source_list)
    if len(not_found_in_source_list) > 0:
        print(f"   - Source에 없는 문제: {len(not_found_in_source_list)}개 (removed_questions에 추가됨)")
    
    # domain/subdomain별로 그룹화
    questions_by_subdomain = defaultdict(lambda: defaultdict(list))
    for q in final_sorted:
        domain = q.get('domain', '')
        subdomain = q.get('subdomain', '')
        if domain and subdomain:
            questions_by_subdomain[domain][subdomain].append(q)
    
    # 각 subdomain별로 필요한 개수 확인하고 초과분 삭제
    for domain_name in exam_stats.keys():
        for subdomain_name, needed_count in exam_stats[domain_name]['exam_subdomain_distribution'].items():
            if domain_name in questions_by_subdomain and subdomain_name in questions_by_subdomain[domain_name]:
                subdomain_questions = questions_by_subdomain[domain_name][subdomain_name]
                current_count = len(subdomain_questions)
                
                if current_count > needed_count:
                    # 초과분이 있으면 랜덤하게 삭제
                    excess_count = current_count - needed_count
                    random.shuffle(subdomain_questions)
                    selected_questions = subdomain_questions[:needed_count]
                    removed_questions = subdomain_questions[needed_count:]
                    
                    # 삭제된 문제 정보 저장
                    for removed_q in removed_questions:
                        removed_questions_list.append({
                            'file_id': removed_q.get('file_id', ''),
                            'tag': removed_q.get('tag', ''),
                            'domain': domain_name,
                            'subdomain': subdomain_name,
                            'question': removed_q.get('question', '')[:200] + '...' if len(removed_q.get('question', '')) > 200 else removed_q.get('question', ''),
                            'reason': f'초과 문제 삭제 ({current_count}개 → {needed_count}개)'
                        })
                    
                    final_after_removal.extend(selected_questions)
                    removed_count += excess_count
                    print(f"   - {domain_name} > {subdomain_name}: {current_count}개 → {needed_count}개 (삭제: {excess_count}개)")
                else:
                    # 초과분이 없으면 그대로 추가
                    final_after_removal.extend(subdomain_questions)
            else:
                # subdomain에 문제가 없는 경우 (이미 부족한 것으로 처리됨)
                pass
    
    # subdomain 정보가 없는 문제들도 추가 (혹시 모를 경우)
    questions_without_subdomain = [q for q in final_sorted 
                                   if not q.get('domain') or not q.get('subdomain')]
    if questions_without_subdomain:
        print(f"   경고: subdomain 정보가 없는 문제 {len(questions_without_subdomain)}개 발견 (그대로 유지)")
        final_after_removal.extend(questions_without_subdomain)
    
    if removed_count > 0:
        excess_removed = removed_count - len(not_found_in_source_list)
        if len(not_found_in_source_list) > 0:
            print(f"   - Source에 없는 문제: {len(not_found_in_source_list)}개")
        if excess_removed > 0:
            print(f"   - 초과 문제 삭제: {excess_removed}개")
        print(f"   - 총 삭제된 문제: {removed_count}개")
    else:
        print(f"   - 삭제된 문제 없음")
    
    # 10. 최종 통계
    print(f"\n10. 최종 통계")
    print(f"   - Origin에서 매칭된 문제: {len(matched_questions)}개")
    print(f"   - 추가된 문제: {len(added_questions)}개")
    print(f"   - 삭제된 초과 문제: {removed_count}개")
    print(f"   - 총 문제 수: {len(final_after_removal)}개")
    
    final_distribution = defaultdict(lambda: defaultdict(int))
    for q in final_after_removal:
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
    
    # 11. 태그 대치 수행
    print(f"\n11. 태그 대치 수행")
    onedrive_path = None  # 필요시 설정
    final_sorted_with_tags_replaced = replace_tags_in_exam_data(final_after_removal, onedrive_path)
    
    # 11. 파일 저장
    if output_file is None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(
            project_root, 
            'evaluation', 
            'eval_data', 
            '4_multiple_exam', 
            '1st', 
            f'{exam_name}_exam_from_origin.json'
        )
    
    print(f"\n12. 결과 파일 저장: {output_file}")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    save_json(final_sorted_with_tags_replaced, output_file)
    
    # 13. Origin 파일과 최종 결과 파일 비교하여 누락된 문제 찾기
    print(f"\n13. Origin 파일과 최종 결과 파일 비교")
    
    # 최종 결과 파일의 (file_id, tag) 키 수집
    final_result_keys = set()
    for q in final_sorted_with_tags_replaced:
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        if file_id and tag:
            final_result_keys.add((file_id, tag))
    
    # Origin 파일의 (file_id, tag) 키 수집
    origin_keys = set()
    origin_questions_by_key = {}
    for q in origin_questions:
        file_id = q.get('file_id', '')
        tag = q.get('tag', '')
        if file_id and tag:
            key = (file_id, tag)
            origin_keys.add(key)
            origin_questions_by_key[key] = q
    
    # Origin에는 있지만 최종 결과에는 없는 문제들 찾기
    missing_in_final = origin_keys - final_result_keys
    missing_in_final_list = []
    
    for key in missing_in_final:
        origin_q = origin_questions_by_key[key]
        file_id, tag = key
        
        # 이미 not_found_in_source_list에 있는지 확인
        already_in_removed = any(
            rq.get('file_id') == file_id and rq.get('tag') == tag 
            for rq in removed_questions_list
        )
        
        if not already_in_removed:
            missing_in_final_list.append({
                'file_id': file_id,
                'tag': tag,
                'domain': origin_q.get('domain', ''),
                'subdomain': origin_q.get('subdomain', ''),
                'question': origin_q.get('question', '')[:200] + '...' if len(origin_q.get('question', '')) > 200 else origin_q.get('question', ''),
                'reason': 'Origin에는 있지만 최종 결과에 없음 (다른 이유로 제외됨)'
            })
    
    if len(missing_in_final_list) > 0:
        print(f"   - Origin에는 있지만 최종 결과에 없는 문제: {len(missing_in_final_list)}개 발견")
        removed_questions_list.extend(missing_in_final_list)
        removed_count += len(missing_in_final_list)
    else:
        print(f"   - Origin과 최종 결과가 일치함")
    
    # 14. 수정 내역 저장
    print(f"\n14. 수정 내역 저장")
    
    # 삭제된 문제 분류
    excess_removed_count = removed_count - len(not_found_in_source_list) - len(missing_in_final_list)
    
    modification_log = {
        'exam_name': exam_name,
        'timestamp': None,  # 나중에 추가
        'summary': {
            'total_questions': len(final_sorted_with_tags_replaced),
            'matched_from_origin': len(matched_questions),
            'added_questions': len(added_questions),
            'removed_questions_total': removed_count,
            'removed_excess_questions': excess_removed_count,
            'removed_not_found_in_source': len(not_found_in_source_list),
            'removed_missing_in_final': len(missing_in_final_list),
            'not_found_count': len(not_found_questions)
        },
        'added_questions': [
            {
                'file_id': q.get('file_id', ''),
                'tag': q.get('tag', ''),
                'domain': q.get('domain', ''),
                'subdomain': q.get('subdomain', ''),
                'question': q.get('question', '')[:200] + '...' if len(q.get('question', '')) > 200 else q.get('question', ''),
                'reason': '부족한 문제 추가'
            }
            for q in added_questions
        ],
        'removed_questions': removed_questions_list,
        'not_found_questions': not_found_questions,
        'final_distribution': {
            domain_name: {
                subdomain_name: final_distribution[domain_name][subdomain_name]
                for subdomain_name in exam_stats[domain_name]['exam_subdomain_distribution'].keys()
            }
            for domain_name in exam_stats.keys()
        }
    }
    
    # 타임스탬프 추가
    from datetime import datetime
    modification_log['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 수정 내역 파일 경로
    log_file = output_file.replace('.json', '_modification_log.json')
    save_json(modification_log, log_file)
    print(f"   - 수정 내역 저장: {log_file}")
    print(f"   - removed_questions 총 {len(removed_questions_list)}개 (초과 삭제: {excess_removed_count}개, Source 없음: {len(not_found_in_source_list)}개, 최종 결과 누락: {len(missing_in_final_list)}개)")
    
    # 15. 요약 리포트
    print(f"\n" + "=" * 80)
    print("작업 완료")
    print("=" * 80)
    print(f"시험 이름: {exam_name}")
    print(f"출력 파일: {output_file}")
    print(f"수정 내역 파일: {log_file}")
    print(f"총 문제 수: {len(final_sorted_with_tags_replaced)}개")
    print(f"  - Origin 매칭: {len(matched_questions)}개")
    print(f"  - 추가: {len(added_questions)}개")
    print(f"  - 삭제: {removed_count}개")
    print(f"    * 초과 문제 삭제: {excess_removed_count}개")
    print(f"    * Source에 없음: {len(not_found_in_source_list)}개")
    print(f"    * 최종 결과 누락: {len(missing_in_final_list)}개")
    print(f"  - 매칭 실패: {len(not_found_questions)}개")
    
    return {
        'exam_name': exam_name,
        'output_file': output_file,
        'modification_log_file': log_file,
        'total_questions': len(final_sorted_with_tags_replaced),
        'matched_from_origin': len(matched_questions),
        'added_questions': len(added_questions),
        'removed_questions': removed_count,
        'not_found_count': len(not_found_questions),
        'not_found_questions': not_found_questions
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Origin_Exam 파일의 문제들로 시험을 구성하고 부족한 문제를 채웁니다. 파일명에서 시험 이름(금융실무1/금융실무2/금융심화/금융일반)을 자동으로 추출합니다.'
    )
    parser.add_argument(
        '--origin',
        type=str,
        default='/Users/jinym/Library/CloudStorage/OneDrive-개인/데이터L/데이터검수/재설계/완본/Origin_Exam1_금융실무1_type.json',
        help='Origin_Exam 파일 경로 (예: Origin_Exam1_금융실무1_type.json, Origin_Exam1_금융실무2_type.json 등)'
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
        help='출력 파일 경로 (기본값: evaluation/eval_data/4_multiple_exam/1st/{시험이름}_exam_from_origin.json)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='랜덤 시드 (기본값: 42)'
    )
    
    args = parser.parse_args()
    
    # 기본 경로 설정
    if args.source is None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        args.source = os.path.join(
            project_root,
            'evaluation',
            'eval_data',
            '2_subdomain',
            'multiple-choice_subdomain_classified_ALL.json'
        )
    
    result = build_exam_from_origin(
        origin_file=args.origin,
        source_file=args.source,
        config_path=args.config,
        output_file=args.output,
        seed=args.seed
    )
    
    print(f"\n결과: {result}")

