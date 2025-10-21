#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from collections import defaultdict, Counter

def classify_questions_by_domain_chapter(multiple_for_grp):
    """
    multiple_for_grp 리스트에서 qna_domain과 chapter별로 문제를 분류합니다.
    
    Args:
        multiple_for_grp: 문제 데이터 리스트
    
    Returns:
        dict: 도메인별, 챕터별로 분류된 문제 딕셔너리
    """
    
    # 도메인별, 챕터별 분류를 위한 딕셔너리
    domain_chapter_classification = defaultdict(lambda: defaultdict(list))
    
    print(f"총 {len(multiple_for_grp)}개 문제를 도메인과 챕터별로 분류합니다...")
    
    for i, question in enumerate(multiple_for_grp):
        try:
            # 도메인과 챕터 정보 추출
            domain = question.get('qna_domain', 'Unknown Domain')
            chapter = question.get('chapter', 'Unknown Chapter')
            book_title = question.get('title', 'Unknown Book')
            
            # 문제 데이터를 해당 도메인-챕터에 추가
            domain_chapter_classification[domain][chapter].append({
                'index': i,
                'question_data': question,
                'book_title': book_title
            })
            
        except Exception as e:
            print(f"문제 {i} 처리 중 오류 발생: {e}")
            continue
    
    return dict(domain_chapter_classification)

def analyze_domain_chapters(domain_chapter_data):
    """
    도메인별로 보유하고 있는 챕터들을 분석합니다.
    
    Args:
        domain_chapter_data: 분류된 문제 데이터
    
    Returns:
        tuple: (도메인별 챕터 분석, 도메인별 도서-챕터 매핑)
    """
    
    domain_chapter_analysis = {}
    domain_book_chapters = {}
    
    print("\n도메인별 챕터 분석을 수행합니다...")
    
    for domain, chapters in domain_chapter_data.items():
        # 도메인별 통계
        total_questions = sum(len(questions) for questions in chapters.values())
        total_chapters = len(chapters)
        
        # 도메인별 도서-챕터 매핑
        book_chapter_mapping = defaultdict(set)
        for chapter_name, questions in chapters.items():
            for item in questions:
                book_title = item['book_title']
                book_chapter_mapping[book_title].add(chapter_name)
        
        # 도메인별 챕터 분석 데이터
        domain_chapter_analysis[domain] = {
            'domain_name': domain,
            'total_questions': total_questions,
            'total_chapters': total_chapters,
            'total_books': len(book_chapter_mapping),
            'chapters': list(chapters.keys()),
            'chapter_question_counts': {
                chapter: len(questions) for chapter, questions in chapters.items()
            }
        }
        
        # 도메인별 도서-챕터 매핑
        domain_book_chapters[domain] = {
            book_title: list(chapters) for book_title, chapters in book_chapter_mapping.items()
        }
        
        print(f"  📊 {domain}: {total_questions}개 문제, {total_chapters}개 챕터, {len(book_chapter_mapping)}개 도서")
    
    return domain_chapter_analysis, domain_book_chapters

def save_domain_classified_questions(domain_chapter_data, output_dir="book_domain_chapter_classified"):
    """
    분류된 문제들을 도메인별, 챕터별로 파일로 저장합니다.
    
    Args:
        domain_chapter_data: 분류된 문제 데이터
        output_dir: 출력 디렉토리
    """
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n분류된 문제들을 '{output_dir}' 디렉토리에 저장합니다...")
    
    # 통계 정보
    total_domains = len(domain_chapter_data)
    total_chapters = sum(len(chapters) for chapters in domain_chapter_data.values())
    total_questions = sum(
        len(questions) 
        for chapters in domain_chapter_data.values() 
        for questions in chapters.values()
    )
    
    print(f"총 {total_domains}개 도메인, {total_chapters}개 챕터, {total_questions}개 문제")
    
    # 도메인별로 파일 저장
    domain_summary = []
    
    for domain, chapters in domain_chapter_data.items():
        # 도메인명에서 파일명으로 사용할 수 없는 문자 제거
        safe_domain_name = "".join(c for c in domain if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_domain_name = safe_domain_name.replace(' ', '_')
        
        domain_file = os.path.join(output_dir, f"domain_{safe_domain_name}.json")
        
        # 도메인별 데이터 구성
        domain_data = {
            'domain_info': {
                'domain_name': domain,
                'total_chapters': len(chapters),
                'total_questions': sum(len(questions) for questions in chapters.values())
            },
            'chapters': {}
        }
        
        # 챕터별 데이터 구성
        for chapter_name, questions in chapters.items():
            chapter_data = {
                'chapter_name': chapter_name,
                'question_count': len(questions),
                'books': list(set(item['book_title'] for item in questions)),
                'questions': []
            }
            
            for item in questions:
                # 원본 데이터 구조에서 문제 데이터 추출
                question_data = {
                    'index': item['index'],
                    'file_id': item['question_data'].get('file_id', ''),
                    'book_title': item['book_title'],
                    'chapter': item['question_data'].get('chapter', ''),
                    # 'page': item['question_data'].get('page', ''),
                    'qna_domain': item['question_data'].get('qna_domain', ''),
                    'qna_id': item['question_data'].get('qna_id', ''),
                    'qna_reason': item['question_data'].get('qna_reason', ''),
                    'question': item['question_data'].get('qna_question', ''),
                    'options': item['question_data'].get('qna_options', []),
                    'answer': item['question_data'].get('qna_answer', ''),
                    'explanation': item['question_data'].get('qna_explanation', '')
                }
                chapter_data['questions'].append(question_data)
            
            domain_data['chapters'][chapter_name] = chapter_data
        
        # 도메인별 JSON 파일 저장
        with open(domain_file, 'w', encoding='utf-8') as f:
            json.dump(domain_data, f, ensure_ascii=False, indent=2)
        
        # 요약 정보 수집
        domain_summary.append({
            'domain_name': domain,
            'file_name': f"domain_{safe_domain_name}.json",
            'total_chapters': len(chapters),
            'total_questions': sum(len(questions) for questions in chapters.values()),
            'chapters': list(chapters.keys())
        })
        
        print(f"  📊 {domain}: {len(chapters)}개 챕터, {sum(len(questions) for questions in chapters.values())}개 문제")
    
    # 전체 요약 정보 저장
    summary_file = os.path.join(output_dir, "domain_classification_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_domains': total_domains,
            'total_chapters': total_chapters,
            'total_questions': total_questions,
            'domains': domain_summary
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 분류 완료!")
    print(f"📁 저장 위치: {output_dir}/")
    print(f"📊 요약 정보: {summary_file}")
    
    return domain_summary

def save_domain_chapter_analysis(domain_chapter_analysis, domain_book_chapters, output_dir="book_domain_chapter_classified"):
    """
    도메인별 챕터 분석 결과를 저장합니다.
    
    Args:
        domain_chapter_analysis: 도메인별 챕터 분석 데이터
        domain_book_chapters: 도메인별 도서-챕터 매핑
        output_dir: 출력 디렉토리
    """
    
    # 도메인별 챕터 분석 결과 저장
    analysis_file = os.path.join(output_dir, "domain_chapter_analysis.json")
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump({
            'domain_analysis': domain_chapter_analysis,
            'domain_book_chapters': domain_book_chapters
        }, f, ensure_ascii=False, indent=2)
    
    print(f"📊 도메인별 챕터 분석 결과가 '{analysis_file}'에 저장되었습니다.")
    
    return analysis_file

def create_domain_chapter_report(domain_chapter_analysis, domain_book_chapters, output_dir="book_domain_chapter_classified"):
    """
    도메인별 챕터 분석 리포트를 생성합니다.
    
    Args:
        domain_chapter_analysis: 도메인별 챕터 분석 데이터
        domain_book_chapters: 도메인별 도서-챕터 매핑
        output_dir: 출력 디렉토리
    """
    
    report = []
    report.append("# 도메인별, 챕터별 문제 분류 분석 리포트")
    report.append("=" * 60)
    
    # 전체 통계
    total_domains = len(domain_chapter_analysis)
    total_chapters = sum(data['total_chapters'] for data in domain_chapter_analysis.values())
    total_questions = sum(data['total_questions'] for data in domain_chapter_analysis.values())
    total_books = sum(data['total_books'] for data in domain_chapter_analysis.values())
    
    report.append(f"## 전체 통계")
    report.append(f"- 총 도메인 수: {total_domains}개")
    report.append(f"- 총 챕터 수: {total_chapters}개")
    report.append(f"- 총 문제 수: {total_questions}개")
    report.append(f"- 총 도서 수: {total_books}개")
    report.append(f"- 평균 도메인당 챕터 수: {total_chapters/total_domains:.1f}개")
    report.append(f"- 평균 도메인당 문제 수: {total_questions/total_domains:.1f}개")
    report.append("")
    
    # 도메인별 상세 정보
    report.append("## 도메인별 상세 정보")
    
    # 문제 수 순으로 정렬
    sorted_domains = sorted(domain_chapter_analysis.items(), key=lambda x: x[1]['total_questions'], reverse=True)
    
    for domain, data in sorted_domains:
        report.append(f"### 📊 {domain}")
        report.append(f"- 총 문제 수: {data['total_questions']}개")
        report.append(f"- 총 챕터 수: {data['total_chapters']}개")
        report.append(f"- 총 도서 수: {data['total_books']}개")
        report.append("")
        
        # 챕터별 문제 분포 (상위 10개)
        chapter_counts = data['chapter_question_counts']
        sorted_chapters = sorted(chapter_counts.items(), key=lambda x: x[1], reverse=True)
        
        report.append("**챕터별 문제 분포 (상위 10개):**")
        for chapter_name, count in sorted_chapters[:10]:
            report.append(f"- {chapter_name}: {count}개")
        report.append("")
        
        # 도서별 챕터 분포
        if domain in domain_book_chapters:
            book_chapters = domain_book_chapters[domain]
            report.append("**도서별 챕터 분포:**")
            for book_title, chapters in sorted(book_chapters.items(), key=lambda x: len(x[1]), reverse=True):
                report.append(f"- **{book_title}**: {len(chapters)}개 챕터")
                for chapter in sorted(chapters)[:5]:  # 상위 5개 챕터만 표시
                    report.append(f"  - {chapter}")
                if len(chapters) > 5:
                    report.append(f"  - ... 외 {len(chapters) - 5}개 챕터")
            report.append("")
        
        report.append("---")
        report.append("")
    
    # 도메인별 챕터 공통성 분석
    report.append("## 도메인별 챕터 공통성 분석")
    
    # 모든 챕터 수집
    all_chapters = set()
    for data in domain_chapter_analysis.values():
        all_chapters.update(data['chapters'])
    
    # 챕터별 도메인 분포
    chapter_domain_mapping = defaultdict(list)
    for domain, data in domain_chapter_analysis.items():
        for chapter in data['chapters']:
            chapter_domain_mapping[chapter].append(domain)
    
    # 여러 도메인에서 공통으로 사용되는 챕터
    common_chapters = {chapter: domains for chapter, domains in chapter_domain_mapping.items() if len(domains) > 1}
    
    if common_chapters:
        report.append("**여러 도메인에서 공통으로 사용되는 챕터:**")
        for chapter, domains in sorted(common_chapters.items(), key=lambda x: len(x[1]), reverse=True):
            report.append(f"- **{chapter}**: {', '.join(domains)} ({len(domains)}개 도메인)")
        report.append("")
    
    # 도메인별 고유 챕터
    report.append("**도메인별 고유 챕터 (해당 도메인에서만 사용):**")
    for domain, data in sorted_domains:
        unique_chapters = []
        for chapter in data['chapters']:
            if len(chapter_domain_mapping[chapter]) == 1:
                unique_chapters.append(chapter)
        
        if unique_chapters:
            report.append(f"- **{domain}**: {len(unique_chapters)}개 고유 챕터")
            for chapter in sorted(unique_chapters)[:5]:  # 상위 5개만 표시
                report.append(f"  - {chapter}")
            if len(unique_chapters) > 5:
                report.append(f"  - ... 외 {len(unique_chapters) - 5}개")
        else:
            report.append(f"- **{domain}**: 고유 챕터 없음 (모든 챕터가 다른 도메인과 공유)")
        report.append("")
    
    # 리포트 파일 저장
    report_file = os.path.join(output_dir, "book_domain_chapter_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"📋 도메인별 챕터 분석 리포트가 '{report_file}'에 저장되었습니다.")

def main():
    """
    메인 실행 함수
    """
    
    # multiple_for_grp 리스트를 로드
    print("multiple_for_grp 리스트를 로드합니다...")
    
    try:
        with open('/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/multiple.json', 'r', encoding='utf-8') as f:
            multiple_for_grp = json.load(f)
        print(f"✅ {len(multiple_for_grp)}개 문제를 로드했습니다.")
    except FileNotFoundError:
        print("❌ multiple.json 파일을 찾을 수 없습니다.")
        print("multiple_for_grp 리스트를 직접 제공해주세요.")
        return
    except Exception as e:
        print(f"❌ 파일 로드 중 오류 발생: {e}")
        return
    
    # 도메인과 챕터별로 분류
    domain_chapter_data = classify_questions_by_domain_chapter(multiple_for_grp)
    
    # 도메인별 챕터 분석
    domain_chapter_analysis, domain_book_chapters = analyze_domain_chapters(domain_chapter_data)
    
    # 분류된 문제들을 파일로 저장
    domain_summary = save_domain_classified_questions(domain_chapter_data)
    
    # 도메인별 챕터 분석 결과 저장
    analysis_file = save_domain_chapter_analysis(domain_chapter_analysis, domain_book_chapters)
    
    # 도메인별 챕터 분석 리포트 생성
    create_domain_chapter_report(domain_chapter_analysis, domain_book_chapters)
    
    print(f"\n🎉 모든 작업이 완료되었습니다!")
    print(f"📁 결과 파일들: domain_chapter_classified/ 디렉토리")
    print(f"📊 도메인별 챕터 분석: domain_chapter_analysis.json")
    print(f"📋 도메인별 챕터 리포트: domain_chapter_report.md")

if __name__ == "__main__":
    main()
