#!/usr/bin/env python3
"""
workbook_data 하위의 extracted_qna.json 파일들을 분석하여
qna_domain/qna_type별 통계를 확인하는 스크립트
"""

import json
import os
import glob
import re
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime

# 유효한 Domain Type 정의
VALID_DOMAINS = {
    '경제', '경영', '회계', '세무', '노무', '통계', 
    '내부통제', '영업', '디지털', '자산운용', '리스크관리', '보험계약', '보상처리'
}

def find_extracted_qna_files(base_path):
    """workbook_data 하위의 모든 extracted_qna.json 파일을 찾습니다."""
    pattern = os.path.join(base_path, "**", "*extracted_qna.json")
    files = glob.glob(pattern, recursive=True)
    # merged로 시작하는 파일들과 백업 파일들 제외
    filtered_files = []
    for f in files:
        if (not f.endswith('.bak') and 
            not f.endswith('.backup') and 
            not os.path.basename(f).startswith('merged')):
            filtered_files.append(f)
    return filtered_files

def is_valid_domain(domain):
    """도메인이 유효한지 확인합니다."""
    return domain in VALID_DOMAINS

def extract_ss_pattern_from_question(question_text):
    """질문에서 SS0000_q_0000_0000 패턴을 추출합니다."""
    if not question_text:
        return None
    
    # SS0000_q_0000_0000 패턴 찾기
    pattern = r'SS\d{4}_q_\d{4}_\d{4}'
    matches = re.findall(pattern, question_text)
    return matches[0] if matches else None

def load_json_file(file_path):
    """JSON 파일을 로드합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def analyze_qna_statistics(files):
    """QnA 파일들을 분석하여 통계를 생성합니다."""
    stats = {
        'total_files': 0,
        'total_qna_items': 0,
        'valid_domain_items': 0,
        'invalid_domain_items': 0,
        'qna_domain_stats': defaultdict(int),
        'qna_type_stats': defaultdict(int),
        'domain_type_combination': defaultdict(lambda: defaultdict(int)),
        'file_stats': [],
        'domain_type_details': defaultdict(lambda: defaultdict(list)),
        'invalid_domain_details': defaultdict(list),
        'ss_pattern_details': defaultdict(list)
    }
    
    for file_path in files:
        print(f"Processing: {file_path}")
        data = load_json_file(file_path)
        
        if data is None:
            continue
            
        stats['total_files'] += 1
        file_id = os.path.basename(file_path).replace('_extracted_qna.json', '')
        file_qna_count = 0
        file_valid_domain_count = 0
        file_invalid_domain_count = 0
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            stats['total_qna_items'] += 1
            file_qna_count += 1
            
            qna_domain = item.get('qna_domain', '')
            qna_type = item.get('qna_type', 'Unknown')
            question_text = item.get('qna_data', {}).get('description', {}).get('question', '')
            
            # 빈 도메인을 ""로 명시
            if not qna_domain or qna_domain.strip() == '':
                qna_domain = ''
            
            # 도메인 유효성 검사
            if is_valid_domain(qna_domain):
                stats['valid_domain_items'] += 1
                file_valid_domain_count += 1
                
                # 기본 통계
                stats['qna_domain_stats'][qna_domain] += 1
                stats['qna_type_stats'][qna_type] += 1
                
                # 도메인-타입 조합 통계
                stats['domain_type_combination'][qna_domain][qna_type] += 1
                
                # 상세 정보 저장 (파일별)
                stats['domain_type_details'][qna_domain][qna_type].append({
                    'file_id': file_id,
                    'title': item.get('title', ''),
                    'chapter': item.get('chapter', ''),
                    'page': item.get('page', ''),
                    'qna_reason': item.get('qna_reason', ''),
                    'question': question_text[:100] + '...' if len(question_text) > 100 else question_text
                })
            else:
                stats['invalid_domain_items'] += 1
                file_invalid_domain_count += 1
                
                # SS 패턴 추출
                ss_pattern = extract_ss_pattern_from_question(question_text)
                
                # 유효하지 않은 도메인 상세 정보 저장
                stats['invalid_domain_details'][qna_domain].append({
                    'file_id': file_id,
                    'title': item.get('title', ''),
                    'chapter': item.get('chapter', ''),
                    'page': item.get('page', ''),
                    'qna_reason': item.get('qna_reason', ''),
                    'question': question_text[:100] + '...' if len(question_text) > 100 else question_text,
                    'ss_pattern': ss_pattern,
                    'original_domain': qna_domain,
                    'qna_type': qna_type
                })
                
                # SS 패턴별 그룹화
                if ss_pattern:
                    stats['ss_pattern_details'][ss_pattern].append({
                        'file_id': file_id,
                        'domain': qna_domain,
                        'type': qna_type,
                        'question': question_text[:100] + '...' if len(question_text) > 100 else question_text
                    })
        
        stats['file_stats'].append({
            'file_id': file_id,
            'file_path': file_path,
            'qna_count': file_qna_count,
            'valid_domain_count': file_valid_domain_count,
            'invalid_domain_count': file_invalid_domain_count
        })
    
    return stats

def print_statistics(stats):
    """통계 결과를 출력합니다."""
    print("=" * 80)
    print("QnA 통계 분석 결과")
    print("=" * 80)
    
    print(f"\n📊 전체 통계:")
    print(f"  - 처리된 파일 수: {stats['total_files']:,}")
    print(f"  - 총 QnA 항목 수: {stats['total_qna_items']:,}")
    print(f"  - 유효한 도메인 항목: {stats['valid_domain_items']:,}")
    print(f"  - 유효하지 않은 도메인 항목: {stats['invalid_domain_items']:,}")
    
    print(f"\n📈 유효한 QnA Domain별 통계:")
    domain_stats = sorted(stats['qna_domain_stats'].items(), key=lambda x: x[1], reverse=True)
    for domain, count in domain_stats:
        percentage = (count / stats['valid_domain_items']) * 100 if stats['valid_domain_items'] > 0 else 0
        print(f"  - {domain}: {count:,}개 ({percentage:.1f}%)")
    
    print(f"\n📋 QnA Type별 통계:")
    type_stats = sorted(stats['qna_type_stats'].items(), key=lambda x: x[1], reverse=True)
    for qna_type, count in type_stats:
        percentage = (count / stats['valid_domain_items']) * 100 if stats['valid_domain_items'] > 0 else 0
        print(f"  - {qna_type}: {count:,}개 ({percentage:.1f}%)")
    
    print(f"\n🔗 Domain-Type 조합별 통계:")
    for domain in sorted(stats['domain_type_combination'].keys()):
        print(f"\n  📌 {domain}:")
        type_combinations = sorted(stats['domain_type_combination'][domain].items(), 
                                 key=lambda x: x[1], reverse=True)
        for qna_type, count in type_combinations:
            percentage = (count / stats['qna_domain_stats'][domain]) * 100
            print(f"    - {qna_type}: {count:,}개 ({percentage:.1f}%)")
    
    if stats['invalid_domain_items'] > 0:
        print(f"\n⚠️  유효하지 않은 도메인 통계:")
        invalid_domain_stats = Counter()
        for domain, items in stats['invalid_domain_details'].items():
            invalid_domain_stats[domain] = len(items)
        for domain, count in invalid_domain_stats.most_common(10):
            print(f"  - {domain}: {count:,}개")

def save_txt_report(stats, output_file):
    """상세 보고서를 마크다운 파일로 저장합니다."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# QnA 통계 분석 상세\n\n")
        f.write(f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # 전체 통계
        f.write("## 1. 전체 통계\n\n")
        f.write("| 항목 | 값 |\n")
        f.write("|------|-----|\n")
        f.write(f"| 처리된 파일 수 | {stats['total_files']:,}개 |\n")
        f.write(f"| 총 QnA 항목 수 | {stats['total_qna_items']:,}개 |\n")
        f.write(f"| 유효한 도메인 항목 | {stats['valid_domain_items']:,}개 |\n")
        f.write(f"| 유효하지 않은 도메인 항목 | {stats['invalid_domain_items']:,}개 |\n\n")
        
        # 유효한 도메인별 통계
        f.write("## 2. 유효한 QnA Domain별 통계\n\n")
        f.write("| 도메인 | 개수 | 비율 |\n")
        f.write("|--------|------|------|\n")
        domain_stats = sorted(stats['qna_domain_stats'].items(), key=lambda x: x[1], reverse=True)
        for domain, count in domain_stats:
            percentage = (count / stats['valid_domain_items']) * 100 if stats['valid_domain_items'] > 0 else 0
            f.write(f"| {domain} | {count:,}개 | {percentage:.1f}% |\n")
        f.write("\n")
        
        # QnA Type별 통계
        f.write("## 3. QnA Type별 통계\n\n")
        f.write("| 타입 | 개수 | 비율 |\n")
        f.write("|------|------|------|\n")
        type_stats = sorted(stats['qna_type_stats'].items(), key=lambda x: x[1], reverse=True)
        for qna_type, count in type_stats:
            percentage = (count / stats['valid_domain_items']) * 100 if stats['valid_domain_items'] > 0 else 0
            f.write(f"| {qna_type} | {count:,}개 | {percentage:.1f}% |\n")
        f.write("\n")
        
        # Domain-Type 조합별 통계
        f.write("## 4. Domain-Type 조합별 통계\n\n")
        for domain in sorted(stats['domain_type_combination'].keys()):
            f.write(f"### {domain}\n\n")
            f.write("| 타입 | 개수 | 비율 |\n")
            f.write("|------|------|------|\n")
            type_combinations = sorted(stats['domain_type_combination'][domain].items(), 
                                     key=lambda x: x[1], reverse=True)
            for qna_type, count in type_combinations:
                percentage = (count / stats['qna_domain_stats'][domain]) * 100
                f.write(f"| {qna_type} | {count:,}개 | {percentage:.1f}% |\n")
            f.write("\n")
        
        # 유효하지 않은 도메인 통계
        if stats['invalid_domain_items'] > 0:
            f.write("## 5. 유효하지 않은 도메인 통계\n\n")
            f.write("| 도메인 | 개수 | 비율 |\n")
            f.write("|--------|------|------|\n")
            invalid_domain_stats = Counter()
            for domain, items in stats['invalid_domain_details'].items():
                invalid_domain_stats[domain] = len(items)
            for domain, count in invalid_domain_stats.most_common():
                percentage = (count / stats['invalid_domain_items']) * 100
                f.write(f"| {domain} | {count:,}개 | {percentage:.1f}% |\n")
            f.write("\n")
            
            # SS 패턴별 분석
            if stats['ss_pattern_details']:
                f.write("## 6. SS 패턴별 분석 (유효하지 않은 도메인)\n\n")
                for ss_pattern, items in sorted(stats['ss_pattern_details'].items()):
                    f.write(f"### {ss_pattern} - {len(items)}개\n\n")
                    for item in items[:5]:  # 상위 5개만 표시
                        f.write(f"- **파일**: {item['file_id']}, **도메인**: {item['domain']}, **타입**: {item['type']}\n")
                        f.write(f"  - 질문: {item['question']}\n")
                    if len(items) > 5:
                        f.write(f"\n... 외 {len(items) - 5}개\n")
                    f.write("\n")
        
        # 파일별 통계
        f.write("## 7. 파일별 통계\n\n")
        f.write("| 파일ID | 총QnA | 유효도메인 | 무효도메인 |\n")
        f.write("|--------|-------|-----------|-----------|\n")
        for file_stat in sorted(stats['file_stats'], key=lambda x: x['file_id']):
            f.write(f"| {file_stat['file_id']} | {file_stat['qna_count']} | {file_stat['valid_domain_count']} | {file_stat['invalid_domain_count']} |\n")
        f.write("\n")
        
        # 유효하지 않은 도메인 상세 정보
        if stats['invalid_domain_details']:
            f.write("## 8. 유효하지 않은 도메인 상세 정보\n\n")
            for domain, items in sorted(stats['invalid_domain_details'].items()):
                f.write(f"### {domain} - {len(items)}개\n\n")
                for i, item in enumerate(items[:10]):  # 상위 10개만 표시
                    f.write(f"{i+1}. **파일**: {item['file_id']}, **페이지**: {item['page']}\n")
                    f.write(f"   - 제목: {item['title']}\n")
                    f.write(f"   - 챕터: {item['chapter']}\n")
                    f.write(f"   - 원래 도메인: '{item['original_domain']}'\n")
                    f.write(f"   - QnA 타입: {item['qna_type']}\n")
                    f.write(f"   - 질문: {item['question']}\n")
                    if item['ss_pattern']:
                        f.write(f"   - SS패턴: {item['ss_pattern']}\n")
                    f.write("\n")
                if len(items) > 10:
                    f.write(f"... 외 {len(items) - 10}개\n\n")
        
        # Domain-Type 조합별 상세 정보
        if 'domain_type_details' in stats and stats['domain_type_details']:
            f.write("## 9. Domain-Type 조합별 상세 정보\n\n")
            for domain in sorted(stats['domain_type_details'].keys()):
                f.write(f"### {domain}\n\n")
                for qna_type in sorted(stats['domain_type_details'][domain].keys()):
                    items = stats['domain_type_details'][domain][qna_type]
                    f.write(f"#### {qna_type} ({len(items)}개)\n\n")
                    f.write("| 파일ID | 제목 | 챕터 | 페이지 |\n")
                    f.write("|--------|------|------|--------|\n")
                    for item in items[:20]:  # 상위 20개만 표시
                        title = item.get('title', '')[:50]  # 제목 길이 제한
                        chapter = item.get('chapter', '')[:30]  # 챕터 길이 제한
                        f.write(f"| {item.get('file_id', '')} | {title} | {chapter} | {item.get('page', '')} |\n")
                    if len(items) > 20:
                        f.write(f"\n... 외 {len(items) - 20}개\n")
                    f.write("\n")
    
    print(f"\n💾 상세 마크다운 보고서가 저장되었습니다: {output_file}")


def main():
    """메인 함수"""
    # pipeline/config에서 ONEDRIVE_PATH, PROJECT_ROOT_PATH import 시도
    try:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        sys.path.insert(0, project_root)
        from tools import ONEDRIVE_PATH, PROJECT_ROOT_PATH
        base_path = os.path.join(ONEDRIVE_PATH, 'evaluation', 'workbook_data')
        txt_output_file = os.path.join(PROJECT_ROOT_PATH, 'STATS_qna.md')
    except ImportError:
        # fallback: pipeline이 없는 경우 플랫폼별 기본값 사용
        import platform
        system = platform.system()
        home_dir = os.path.expanduser("~")
        if system == "Windows":
            base_path = os.path.join(home_dir, "Desktop", "SFAIcenter", "evaluation", "workbook_data")
            txt_output_file = os.path.join(home_dir, "Desktop", "SFAIcenter", "STATS_qna.md")
        else:
            base_path = os.path.join(home_dir, "Desktop", "Desktop_AICenter✨", "SFAIcenter", "evaluation", "workbook_data")
            txt_output_file = os.path.join(home_dir, "Desktop", "Desktop_AICenter✨", "SFAIcenter", "STATS_qna.md")
    
    print("🔍 workbook_data 하위의 extracted_qna.json 파일들을 찾는 중...")
    files = find_extracted_qna_files(base_path)
    
    if not files:
        print("❌ extracted_qna.json 파일을 찾을 수 없습니다.")
        return
    
    print(f"✅ {len(files)}개의 파일을 찾았습니다.")
    
    print("\n📊 QnA 통계 분석을 시작합니다...")
    stats = analyze_qna_statistics(files)
    
    # 통계 출력
    print_statistics(stats)
    
    # 마크다운 상세 보고서 저장
    save_txt_report(stats, txt_output_file)

if __name__ == "__main__":
    main()
