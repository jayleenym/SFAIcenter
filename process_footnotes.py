import re
import json
from typing import List, Dict, Any

def process_footnotes_improved(content: str, page: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    개선된 각주 처리 함수
    """
    footnotes = []
    footnote_counter = 1
    
    # ───── 구분선 찾기
    if '─────' not in content:
        return content, footnotes
    
    print(f"페이지 {page}: ───── 구분선 발견")
    
    # ───── 이후의 모든 내용을 가져오기
    parts = content.split('─────')
    if len(parts) < 2:
        return content, footnotes
    
    footnote_section = parts[1]
    print(f"각주 섹션 내용 (처음 200자): {repr(footnote_section[:200])}")
    
    # 각주 항목들을 추출 (•, ••, •••로 시작하는 각 줄)
    footnote_lines = []
    lines = footnote_section.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == '•' or line == '••' or line == '•••':
            # •, ••, ••• 다음 줄이 실제 각주 내용
            if i + 1 < len(lines):
                footnote_content = lines[i + 1].strip()
                if footnote_content:
                    footnote_lines.append(footnote_content)
                i += 2  # • 줄과 내용 줄을 모두 건너뛰기
            else:
                i += 1
        else:
            i += 1
    
    # 각주 이후의 본문 찾기 (•로 시작하지 않는 첫 번째 줄부터)
    # 단, 각주 내용 자체는 제외하고 나머지 본문만 유지
    main_content_after_footnotes = ""
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('•'):
            # •로 시작하지 않는 첫 번째 줄부터가 본문
            # 하지만 각주 내용은 제외하고 나머지만 유지
            remaining_lines = []
            for j in range(i, len(lines)):
                current_line = lines[j].strip()
                # 각주 내용이 아닌 경우만 포함
                if current_line and not current_line.startswith('•'):
                    # 이전에 추출한 각주 내용과 일치하지 않는 경우만 포함
                    is_footnote_content = False
                    for footnote_content in footnote_lines:
                        if current_line == footnote_content:
                            is_footnote_content = True
                            break
                    if not is_footnote_content:
                        remaining_lines.append(lines[j])
                elif not current_line:
                    # 빈 줄은 그대로 유지
                    remaining_lines.append(lines[j])
            main_content_after_footnotes = '\n'.join(remaining_lines)
            break
    
    print(f"페이지 {page}: {len(footnote_lines)}개 각주 항목 발견")
    for i, line in enumerate(footnote_lines):
        print(f"  - 각주 {i+1}: {line[:50]}...")
    
    if not footnote_lines:
        return content, footnotes
    
    # 본문에서 각주 표시를 찾아서 태그로 변환
    # •, ••, ••• 패턴을 찾되, 단어 뒤에 오는 것과 단독으로 있는 것 모두 처리
    # 한글, 영문, 숫자 모두 포함하도록 수정 (공백 포함)
    footnote_pattern = r'([가-힣a-zA-Z0-9\s]+)(•+)|(•+)'
    
    def replace_footnote(match):
        nonlocal footnote_counter
        word = match.group(1)
        dots = match.group(2) or match.group(3)  # 단어 뒤의 • 또는 단독 • 처리
        
        # 각주 번호 계산 (•의 개수)
        footnote_num = len(dots)
        
        # 해당하는 각주 내용 찾기
        if footnote_num <= len(footnote_lines):
            footnote_content = footnote_lines[footnote_num - 1]
            
            # add_info에 추가할 footnote 정보
            footnote_info = {
                "tag": f"note_{page}_{footnote_counter:04d}",
                "type": "footnote",
                "description": footnote_content,
                "caption": None,
                "file_path": None,
                "bbox": None
            }
            footnotes.append(footnote_info)
            
            # 본문에서 각주 표시를 태그로 변환
            tag = f"{{note_{page}_{footnote_counter:04d}}}"
            footnote_counter += 1
            
            if word:
                return word + tag
            else:
                return tag
        else:
            return match.group(0)  # 매칭되는 각주 내용이 없으면 원본 유지
    
    # ───── 구분선 이전의 본문에서 각주 표시를 태그로 변환
    main_content_before_footnotes = content.split('─────')[0]
    modified_content_before = re.sub(footnote_pattern, replace_footnote, main_content_before_footnotes)
    
    # 최종 본문: 변환된 구분선 이전 본문 + 각주 이후의 본문
    modified_content = modified_content_before + main_content_after_footnotes
    
    return modified_content, footnotes

def process_all_footnotes(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    JSON 데이터의 모든 페이지에서 각주를 처리하는 완전한 함수
    """
    processed_data = json_data.copy()
    total_footnotes = 0
    
    if 'contents' in processed_data:
        for content_item in processed_data['contents']:
            if 'page_contents' in content_item and 'page' in content_item:
                page_num = content_item['page']
                original_content = content_item['page_contents']
                
                # 각주 처리
                modified_content, footnotes = process_footnotes_improved(original_content, page_num)
                
                # 본문 업데이트
                content_item['page_contents'] = modified_content
                
                # add_info에 footnote 추가
                if 'add_info' not in content_item:
                    content_item['add_info'] = []
                
                # 기존 add_info에 새로운 footnote들 추가
                content_item['add_info'].extend(footnotes)
                total_footnotes += len(footnotes)
                
                if footnotes:
                    print(f"페이지 {page_num}: {len(footnotes)}개 각주 처리됨")
    
    print(f"총 {total_footnotes}개 각주가 처리되었습니다.")
    return processed_data

if __name__ == "__main__":
    # 실제 파일에 적용
    INPUT_PATH = '/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0014_conversation/SS0014.json'
    
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    
    print("각주 처리 시작...")
    processed_data = process_all_footnotes(original_data)
    
    # 결과 확인 - 각주가 있는 페이지들만 출력
    print("\n=== 각주 처리 결과 ===")
    for i, content_item in enumerate(processed_data['contents']):
        footnotes = [item for item in content_item.get('add_info', []) if item.get('type') == 'footnote']
        if footnotes:
            print(f"\n페이지 {content_item['page']} ({i+1}번째):")
            print(f"  - 각주 개수: {len(footnotes)}")
            for j, footnote in enumerate(footnotes[:2]):  # 처음 2개만 출력
                print(f"  - 각주 {j+1}: {footnote['description'][:50]}...")
            if len(footnotes) > 2:
                print(f"  - ... 외 {len(footnotes)-2}개")
    
    # 처리된 결과를 파일에 저장
    OUTPUT_PATH = INPUT_PATH.replace('.json', '_footnotes_processed.json')
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n처리된 파일이 저장되었습니다: {OUTPUT_PATH}")
