#!/usr/bin/env python3
"""
백업 JSON 파일의 page_contents를 파싱하여 구조화된 정보를 추출하는 도구
제nn회, 번호, 질문, 옵션, 해설을 분리하여 add_info 형태로 변환합니다.
"""

import json
import re
import os
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime


class PageContentParser:
    def __init__(self):
        """페이지 내용 파서 초기화"""
        # 정규표현식 패턴들
        self.session_pattern = r'제(\d+)회'
        self.question_number_pattern = r'^(\d{2})\s+(.+?)(?=\n①|\n해설|$)'
        self.option_pattern = r'[①②③④⑤]\s+(.+?)(?=\n[①②③④⑤]|\n해설|$)'
        self.explanation_pattern = r'해설\s*([①②③④⑤]?)\s*(.+?)(?=\n제\d+회|\n\d{2}\s|$)'
        
    def extract_session_info(self, text: str) -> List[str]:
        """제nn회 정보를 추출합니다."""
        sessions = re.findall(self.session_pattern, text)
        return sessions
    
    def split_by_sessions(self, text: str) -> List[Dict[str, str]]:
        """텍스트를 회차별로 분리합니다."""
        # 제nn회 패턴으로 분리
        parts = re.split(r'(제\d+회)', text)
        
        sessions = []
        current_session = None
        
        for i, part in enumerate(parts):
            if re.match(r'제\d+회', part):
                if current_session:
                    sessions.append(current_session)
                current_session = {
                    'session': part,
                    'content': ''
                }
            elif current_session:
                current_session['content'] += part
        
        if current_session:
            sessions.append(current_session)
            
        return sessions
    
    def parse_question_content(self, content: str) -> List[Dict[str, Any]]:
        """질문 내용을 파싱합니다."""
        questions = []
        
        # 질문 번호와 내용 추출 (더 유연한 패턴 사용)
        question_matches = re.finditer(r'^(\d{1,2})\s+(.+?)(?=\n①|\n해설|$)', content, re.MULTILINE | re.DOTALL)
        
        for match in question_matches:
            question_num = match.group(1)
            question_text = match.group(2).strip()
            
            # 해당 질문 이후의 내용 추출
            start_pos = match.end()
            next_question_match = re.search(r'^\d{1,2}\s+', content[start_pos:], re.MULTILINE)
            end_pos = start_pos + next_question_match.start() if next_question_match else len(content)
            
            question_content = content[start_pos:end_pos].strip()
            
            # 해설 추출 (더 정확한 패턴 사용)
            explanation_match = re.search(r'해설\s*([①②③④⑤]?)\s*(.+?)(?=\n제\d+회|\n\d{1,2}\s|$)', question_content, re.DOTALL)
            
            answer = ""
            explanation = ""
            if explanation_match:
                # answer = explanation_match.group(1).strip()
                explanation = explanation_match.group(1).strip() + " " + explanation_match.group(2).strip()
            
            # 옵션에서 해설 부분 제거
            options_text = re.sub(r'\n해설.*$', '', question_content, flags=re.DOTALL)
            options = self.extract_options(options_text)
            
            # 질문이 있고 옵션이 있는 경우만 추가
            if question_text and options:
                questions.append({
                    'number': question_num,
                    'question': question_text,
                    'options': options,
                    'answer': answer,
                    'explanation': explanation
                })
        
        return questions
    
    def extract_options(self, text: str) -> List[str]:
        """옵션들을 추출합니다."""
        options = []
        option_matches = re.finditer(r'([①②③④⑤]\s+.+?)(?=\n[①②③④⑤]|\n해설|$)', text, re.DOTALL)
        
        for match in option_matches:
            option_text = match.group(1).strip()
            # 줄바꿈을 공백으로 변환
            option_text = re.sub(r'\s+', ' ', option_text)
            options.append(option_text)
        
        return options
    
    def parse_page_content(self, page_content: str, page_num: str) -> Tuple[List[Dict[str, Any]], str]:
        """페이지 내용을 전체적으로 파싱합니다."""
        add_info_items = []
        new_page_contents = ""
        
        # 첫 번째 페이지의 특수한 경우 처리 (15회 변)
        if "15회 변" in page_content and "CHAPTER" in page_content:
            # 첫 번째 질문을 수동으로 파싱
            lines = page_content.split('\n')
            question_text = ""
            options = []
            answer = ""
            explanation = ""
            
            for i, line in enumerate(lines):
                if line.strip().startswith('01 '):
                    question_text = line.strip()[3:]  # "01 " 제거
                    # 다음 줄들에서 옵션 추출
                    for j in range(i+1, len(lines)):
                        option_line = lines[j].strip()
                        if option_line.startswith('①'):
                            options.append(option_line)  # 번호 포함
                        elif option_line.startswith('②'):
                            options.append(option_line)  # 번호 포함
                        elif option_line.startswith('③'):
                            options.append(option_line)  # 번호 포함
                        elif option_line.startswith('④'):
                            options.append(option_line)  # 번호 포함
                        elif option_line.startswith('⑤'):
                            options.append(option_line)  # 번호 포함
                        elif option_line.startswith('해설'):
                            explanation_text = option_line[2:]  # "해설 " 제거
                            # 답 추출
                            # answer_match = re.search(r'([①②③④⑤])', explanation_text)
                            # if answer_match:
                            #     answer = answer_match.group(1)
                            explanation = explanation_text
                            break
            
            if question_text and options:
                tag = f"q_{page_num}_0001"
                add_info_item = {
                    "tag": tag,
                    "type": "question",
                    "description": {
                        "number": "01",
                        "question": question_text,
                        "options": options,
                        "answer": answer,
                        "explanation": explanation
                    },
                    "caption": ["15회 변"],
                    "file_path": None,
                    "bbox": None
                }
                add_info_items.append(add_info_item)
                
                # page_contents를 태그 형태로 변환
                new_page_contents = f"CHAPTER. 01. 총설\n{{{tag}}}"
        
        # 회차별로 분리
        sessions = self.split_by_sessions(page_content)
        
        if not new_page_contents:  # 첫 번째 페이지가 아닌 경우
            tag_parts = []
        
        for session in sessions:
            session_name = session['session']
            content = session['content']
            
            # 질문들 파싱
            questions = self.parse_question_content(content)
            
            for i, question in enumerate(questions):
                tag = f"q_{page_num}_{len(add_info_items)+i+1:04d}"
                
                add_info_item = {
                    "tag": tag,
                    "type": "question",
                    "description": {
                        "number": question['number'],
                        "question": question['question'],
                        "options": question['options'],
                        "answer": question['answer'],
                        "explanation": question['explanation']
                    },
                    "caption": [session_name],
                    "file_path": None,
                    "bbox": None
                }
                
                add_info_items.append(add_info_item)
                
                # page_contents에 태그 추가
                if not new_page_contents:  # 첫 번째 페이지가 아닌 경우
                    tag_parts.append(f"{{{tag}}}")
        
        # page_contents 생성
        if not new_page_contents and tag_parts:
            new_page_contents = "\n".join(tag_parts)
        
        return add_info_items, new_page_contents


class JSONRefinementProcessor:
    def __init__(self, backup_file_path: str):
        """
        JSON 정제 프로세서 초기화
        
        Args:
            backup_file_path: 백업 JSON 파일 경로
        """
        self.backup_file_path = backup_file_path
        self.parser = PageContentParser()
        self.data = None
        
    def load_backup_file(self) -> Dict[str, Any]:
        """백업 파일을 로드합니다."""
        try:
            with open(self.backup_file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✓ 백업 파일 로드 완료: {os.path.basename(self.backup_file_path)}")
            return self.data
        except Exception as e:
            print(f"✗ 백업 파일 로드 실패: {e}")
            return None
    
    def process_all_pages(self) -> Dict[str, Any]:
        """모든 페이지의 내용을 처리합니다."""
        if not self.data:
            return None
        
        processed_data = self.data.copy()
        contents = processed_data.get('contents', [])
        
        # 메타데이터 정리
        processed_data['file_id'] = 'SS0267'  # 원본 파일 ID로 변경
        processed_data['ISBN'] = '9791198804068'  # ISBN 추가
        processed_data['cat3_specific'] = '감정평가사'  # 더 구체적인 분류로 변경
        
        total_questions = 0
        processed_pages = 0
        
        print(f"\n🔍 총 {len(contents)}개 페이지 처리 시작...")
        
        for i, page in enumerate(contents):
            page_content = page.get('page_contents', '')
            page_num = page.get('page', f'{i:04d}')
            
            if page_content.strip():
                try:
                    # 페이지 내용 파싱
                    add_info_items, new_page_contents = self.parser.parse_page_content(page_content, page_num)
                    
                    if add_info_items:
                        page['add_info'] = add_info_items
                        page['page_contents'] = new_page_contents  # 새로운 page_contents로 교체
                        total_questions += len(add_info_items)
                        processed_pages += 1
                        
                        if processed_pages <= 5:  # 처음 5개 페이지만 로그 출력
                            print(f"  페이지 {page_num}: {len(add_info_items)}개 질문 추출")
                    
                except Exception as e:
                    print(f"  ✗ 페이지 {page_num} 처리 실패: {e}")
        
        print(f"\n✅ 처리 완료:")
        print(f"  - 처리된 페이지: {processed_pages}개")
        print(f"  - 추출된 질문: {total_questions}개")
        
        return processed_data
    
    def save_refined_data(self, refined_data: Dict[str, Any], output_path: str = None) -> str:
        """정제된 데이터를 저장합니다."""
        if not refined_data:
            print("✗ 정제할 데이터가 없습니다.")
            return ""
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"SS0267_refined_from_backup_{timestamp}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(refined_data, f, ensure_ascii=False, indent=4)
            print(f"✓ 정제된 파일 저장 완료: {output_path}")
            return output_path
        except Exception as e:
            print(f"✗ 파일 저장 실패: {e}")
            return ""
    
    def generate_processing_report(self, refined_data: Dict[str, Any], output_path: str = None) -> str:
        """처리 결과 보고서를 생성합니다."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"processing_report_{timestamp}.txt"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("백업 파일 처리 결과 보고서\n")
                f.write("=" * 50 + "\n\n")
                
                contents = refined_data.get('contents', [])
                total_questions = 0
                pages_with_questions = 0
                
                f.write("📊 처리 결과 요약\n")
                f.write("-" * 20 + "\n")
                
                for page in contents:
                    add_info = page.get('add_info', [])
                    if add_info:
                        pages_with_questions += 1
                        total_questions += len(add_info)
                
                f.write(f"총 페이지 수: {len(contents)}\n")
                f.write(f"질문이 있는 페이지 수: {pages_with_questions}\n")
                f.write(f"총 추출된 질문 수: {total_questions}\n\n")
                
                # 페이지별 상세 정보 (처음 10개만)
                f.write("📄 페이지별 상세 정보 (처음 10개)\n")
                f.write("-" * 30 + "\n")
                
                count = 0
                for page in contents:
                    if count >= 10:
                        break
                    
                    add_info = page.get('add_info', [])
                    if add_info:
                        f.write(f"페이지 {page.get('page', 'N/A')}:\n")
                        for item in add_info:
                            desc = item.get('description', {})
                            f.write(f"  - {desc.get('number', 'N/A')}번: {desc.get('question', 'N/A')[:50]}...\n")
                            f.write(f"    답: {desc.get('answer', 'N/A')}, 옵션 수: {len(desc.get('options', []))}\n")
                        f.write("\n")
                        count += 1
            
            print(f"✓ 처리 보고서 생성 완료: {output_path}")
            return output_path
        except Exception as e:
            print(f"✗ 보고서 생성 실패: {e}")
            return ""


def main():
    """메인 실행 함수"""
    # 백업 파일 경로 설정
    backup_file_path = "/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/data/FINAL/2C/Lv3_4/SS0267_workbook/SS0267.json.bak"
    
    print("백업 파일 페이지 내용 파싱 및 정제 도구")
    print("=" * 50)
    
    # 프로세서 초기화
    processor = JSONRefinementProcessor(backup_file_path)
    
    # 백업 파일 로드
    data = processor.load_backup_file()
    if not data:
        print("✗ 백업 파일 로드에 실패했습니다.")
        return
    
    # 모든 페이지 처리
    print("\n🔧 페이지 내용 파싱 및 정제 중...")
    refined_data = processor.process_all_pages()
    
    if not refined_data:
        print("✗ 데이터 처리에 실패했습니다.")
        return
    
    # 정제된 데이터 저장
    print("\n💾 정제된 데이터 저장 중...")
    output_path = processor.save_refined_data(refined_data)
    
    # 처리 보고서 생성
    print("\n📝 처리 보고서 생성 중...")
    report_path = processor.generate_processing_report(refined_data)
    
    print(f"\n✅ 모든 작업이 완료되었습니다!")
    print(f"생성된 파일들:")
    print(f"  - {output_path}")
    print(f"  - {report_path}")


if __name__ == "__main__":
    main()
