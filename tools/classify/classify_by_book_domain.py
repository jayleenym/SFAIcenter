#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from collections import defaultdict, Counter

def classify_questions_by_book_domain(multiple_for_grp):
    """
    multiple_for_grp 리스트에서 도서와 domain별로 문제를 분류합니다.
    
    Args:
        multiple_for_grp: 문제 데이터 리스트
    
    Returns:
        dict: 도서별, 도메인별로 분류된 문제 딕셔너리
    """
    
    # 도서별, 도메인별 분류를 위한 딕셔너리
    book_domain_classification = defaultdict(lambda: defaultdict(list))
    
    print(f"총 {len(multiple_for_grp)}개 문제를 도서와 도메인별로 분류합니다...")
    
    for i, question in enumerate(multiple_for_grp):
        try:
            # 도서 제목과 도메인 정보 추출
            id = question.get('file_id', 'Unknown ID')
            title = question.get('title', 'Unknown Book')
            book_title = f"{id}_{title}"
            domain = question.get('qna_domain', 'Unknown Domain')
            
            # 문제 데이터를 해당 도서-도메인에 추가
            book_domain_classification[book_title][domain].append({
                'index': i,
                'question_data': question
            })
            
        except Exception as e:
            print(f"문제 {i} 처리 중 오류 발생: {e}")
            continue
    
    return dict(book_domain_classification)

def save_classified_questions(book_domain_data, output_dir="book_domain_classified"):
    """
    분류된 문제들을 도서별, 도메인별로 파일로 저장합니다.
    
    Args:
        book_domain_data: 분류된 문제 데이터
        output_dir: 출력 디렉토리
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n분류된 문제들을 '{output_dir}' 디렉토리에 저장합니다...")
    
    # 통계 정보
    total_books = len(book_domain_data)
    total_domains = sum(len(domains) for domains in book_domain_data.values())
    total_questions = sum(
        len(questions) 
        for domains in book_domain_data.values() 
        for questions in domains.values()
    )
    
    print(f"총 {total_books}개 도서, {total_domains}개 도메인, {total_questions}개 문제")
    
    # 도서별로 파일 저장
    book_summary = []
    
    for book_title, domains in book_domain_data.items():
        # 도서명에서 파일명으로 사용할 수 없는 문자 제거
        safe_book_name = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_book_name = safe_book_name.replace(' ', '_')
        
        book_file = os.path.join(output_dir, f"{safe_book_name}.json")
        
        # 도서별 데이터 구성
        book_data = {
            'book_info': {
                'title': book_title,
                'total_domains': len(domains),
                'total_questions': sum(len(questions) for questions in domains.values())
            },
            'domains': {}
        }
        
        # 도메인별 데이터 구성
        for domain_name, questions in domains.items():
            domain_data = {
                'domain_name': domain_name,
                'question_count': len(questions),
                'questions': []
            }
            
            for item in questions:
                question_data = {
                    'index': item['index'],
                    'tag': item['question_data'].get('qna_id', ''),
                    'domain': item['question_data'].get('qna_domain', ''),
                    'question': item['question_data'].get('qna_question', ''),
                    'options': item['question_data'].get('qna_options', []),
                    'answer': item['question_data'].get('qna_answer', ''),
                    'explanation': item['question_data'].get('qna_explanation', ''),
                    'file_id': item['question_data'].get('file_id', '')
                }
                domain_data['questions'].append(question_data)
            
            book_data['domains'][domain_name] = domain_data
        
        # 도서별 JSON 파일 저장
        with open(book_file, 'w', encoding='utf-8') as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
        
        # 요약 정보 수집
        book_summary.append({
            'book_title': book_title,
            'file_name': f"{safe_book_name}.json",
            'total_domains': len(domains),
            'total_questions': sum(len(questions) for questions in domains.values()),
            'domains': list(domains.keys())
        })
        
        print(f"  📚 {book_title}: {len(domains)}개 도메인, {sum(len(questions) for questions in domains.values())}개 문제")
    
    # 전체 요약 정보 저장
    summary_file = os.path.join(output_dir, "domain_classification_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_books': total_books,
            'total_domains': total_domains,
            'total_questions': total_questions,
            'books': book_summary
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 분류 완료!")
    print(f"📁 저장 위치: {output_dir}/")
    print(f"📊 요약 정보: {summary_file}")
    
    return book_summary

def create_analysis_report(book_domain_data, output_dir="book_domain_classified"):
    """
    분류 결과에 대한 분석 리포트를 생성합니다.
    
    Args:
        book_domain_data: 분류된 문제 데이터
        output_dir: 출력 디렉토리
    """
    
    report = []
    report.append("# 도서별, 도메인별 문제 분류 분석 리포트")
    report.append("=" * 60)
    
    # 전체 통계
    total_books = len(book_domain_data)
    total_domains = sum(len(domains) for domains in book_domain_data.values())
    total_questions = sum(
        len(questions) 
        for domains in book_domain_data.values() 
        for questions in domains.values()
    )
    
    report.append(f"## 전체 통계")
    report.append(f"- 총 도서 수: {total_books}개")
    report.append(f"- 총 도메인 수: {total_domains}개")
    report.append(f"- 총 문제 수: {total_questions}개")
    report.append(f"- 평균 도메인당 문제 수: {total_questions/total_domains:.1f}개")
    report.append("")
    
    # 도서별 상세 정보
    report.append("## 도서별 상세 정보")
    
    for book_title, domains in book_domain_data.items():
        book_question_count = sum(len(questions) for questions in domains.values())
        
        report.append(f"### 📚 {book_title}")
        report.append(f"- 총 도메인 수: {len(domains)}개")
        report.append(f"- 총 문제 수: {book_question_count}개")
        report.append("")
        
        # 도메인별 정보
        report.append("**도메인별 문제 분포:**")
        for domain_name, questions in sorted(domains.items(), key=lambda x: len(x[1]), reverse=True):
            report.append(f"- {domain_name}: {len(questions)}개")
        report.append("")
        report.append("---")
        report.append("")
    
    # 도메인별 통계
    report.append("## 도메인별 통계 (문제 수 상위 20개)")
    
    all_domains = []
    for book_title, domains in book_domain_data.items():
        for domain_name, questions in domains.items():
            all_domains.append({
                'book': book_title,
                'domain': domain_name,
                'question_count': len(questions)
            })
    
    # 문제 수 순으로 정렬
    all_domains.sort(key=lambda x: x['question_count'], reverse=True)
    
    for i, domain_info in enumerate(all_domains[:20], 1):
        report.append(f"{i}. **{domain_info['book']}** - {domain_info['domain']}: {domain_info['question_count']}개")
    
    # 전체 도메인 통계
    report.append("\n## 전체 도메인 통계")
    domain_counts = Counter()
    for domains in book_domain_data.values():
        for domain_name, questions in domains.items():
            domain_counts[domain_name] += len(questions)
    
    report.append("**도메인별 총 문제 수:**")
    for domain, count in domain_counts.most_common(20):
        report.append(f"- {domain}: {count}개")
    
    # 리포트 파일 저장
    report_file = os.path.join(output_dir, "domain_analysis_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"📊 분석 리포트가 '{report_file}'에 저장되었습니다.")

def main():
    """
    메인 실행 함수
    """
    
    # multiple_for_grp 리스트를 로드 (실제 사용 시에는 이 부분을 수정)
    print("multiple_for_grp 리스트를 로드합니다...")
    
    # 예시: multiple.json에서 데이터 로드
    try:
        with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/multiple.json', 'r', encoding='utf-8') as f:
            multiple_for_grp = json.load(f)
        print(f"✅ {len(multiple_for_grp)}개 문제를 로드했습니다.")
    except FileNotFoundError:
        print("❌ multiple.json 파일을 찾을 수 없습니다.")
        print("multiple_for_grp 리스트를 직접 제공해주세요.")
        return
    except Exception as e:
        print(f"❌ 파일 로드 중 오류 발생: {e}")
        return
    
    # 도서와 도메인별로 분류
    book_domain_data = classify_questions_by_book_domain(multiple_for_grp)
    
    # 분류된 문제들을 파일로 저장
    book_summary = save_classified_questions(book_domain_data)
    
    # 분석 리포트 생성
    create_analysis_report(book_domain_data)
    
    print(f"\n🎉 모든 작업이 완료되었습니다!")
    print(f"📁 결과 파일들: book_domain_classified/ 디렉토리")

if __name__ == "__main__":
    main()

