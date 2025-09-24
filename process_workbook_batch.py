import json
import re
import os

def process_workbook_file(file_path):
    """단일 workbook 파일을 처리하는 함수"""
    print(f"처리 중: {file_path}")
    
    # 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 백업 파일 생성
    backup_path = file_path.replace('.json', '_backup.json')
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    # 새로운 구조로 변환
    new_contents = []
    current_theme = ""
    
    # 정답과 해설 추출
    answers = {}
    explanations = {}
    
    # 모든 페이지를 순회하면서 정답과 해설 추출
    for content in data['contents']:
        page_content = content['page_contents']
        
        # 정답 추출 - 다양한 패턴 지원
        if '정답:' in page_content and '문제' in page_content:
            # "문제 1: ④문제 2: ③" 형태에서 추출
            matches = re.findall(r'문제 (\d+):\s*([①②③④⑤])', page_content)
            for match in matches:
                q_num = int(match[0])
                answer = match[1]
                answers[q_num] = answer
        
        # 해설 추출 - 다양한 패턴 지원
        if '풀이 및 해설:' in page_content or ('문제' in page_content and '정답:' in page_content and '해설:' in page_content):
            # 문제별로 분리
            problem_sections = re.split(r'문제 (\d+):', page_content)
            
            for i in range(1, len(problem_sections), 2):
                if i + 1 < len(problem_sections):
                    q_num = int(problem_sections[i])
                    explanation = problem_sections[i + 1].strip()
                    if explanation and len(explanation) > 10:  # 의미있는 해설만
                        explanations[q_num] = explanation
    
    # 이제 문제들을 처리
    for content in data['contents']:
        page_content = content['page_contents']
        
        # Theme 감지
        if page_content.startswith('Theme '):
            current_theme = page_content.strip()
            continue
            
        # 정답/해설 섹션은 건너뛰기
        if any(keyword in page_content for keyword in ['정답 모음', '풀이 및 해설 모음', '정답:', '해설:']):
            continue
            
        # 문제 감지 및 처리
        if page_content.startswith('문제 '):
            # 문제 번호 추출
            match = re.match(r'문제 (\d+)', page_content)
            if match:
                q_num = int(match.group(1))
                
                # 문제 텍스트에서 선택지 추출
                lines = page_content.split('\n')
                question_text = ""
                options = []
                
                for line in lines[1:]:  # "문제 X" 제외
                    if re.match(r'[①②③④⑤]', line.strip()):
                        options.append(line.strip())
                    elif line.strip() and not line.strip().startswith('문제'):
                        question_text += line + '\n'
                
                question_text = question_text.strip()
                
                # 정답과 해설 가져오기
                answer = answers.get(q_num, "")
                explanation = explanations.get(q_num, "")
                
                # 새로운 구조로 변환
                new_content = {
                    "page": content['page'],
                    "chapter": current_theme,
                    "page_contents": f"{{q_{content['page']}_0001}}",
                    "add_info": [
                        {
                            "tag": f"q_{content['page']}_0001",
                            "type": "question",
                            "description": {
                                "number": str(q_num),
                                "question": question_text,
                                "options": options,
                                "answer": answer,
                                "explanation": explanation
                            },
                            "caption": [],
                            "file_path": None,
                            "bbox": None
                        }
                    ]
                }
                
                new_contents.append(new_content)
    
    # 새로운 데이터 구조 생성
    new_data = {
        "file_id": data['file_id'],
        "title": data['title'],
        "cat1_domain": data['cat1_domain'],
        "cat2_sub": data['cat2_sub'],
        "cat3_specific": data['cat3_specific'],
        "pub_date": data['pub_date'],
        "contents": new_contents
    }
    
    # 처리된 파일 저장
    processed_path = file_path.replace('.json', '_processed.json')
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    
    print(f"  - 추출된 정답: {len(answers)}개")
    print(f"  - 추출된 해설: {len(explanations)}개")
    print(f"  - 처리된 문제: {len(new_contents)}개")
    
    return new_data

def fix_options_and_tags(file_path):
    """options 분리 및 태그 수정"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed_options = 0
    fixed_tags = 0
    
    for content in data['contents']:
        # 1. page_contents 태그 수정 (마지막 4자리를 0001로)
        if 'page_contents' in content and content['page_contents'].startswith('{q_'):
            old_tag = content['page_contents']
            if not old_tag.endswith('_0001}'):
                new_tag = re.sub(r'_(\d{4})\}$', '_0001}', old_tag)
                content['page_contents'] = new_tag
                fixed_tags += 1
        
        # 2. add_info의 태그도 수정
        if 'add_info' in content and content['add_info']:
            for info in content['add_info']:
                if info['type'] == 'question' and 'tag' in info:
                    old_tag = info['tag']
                    if not old_tag.endswith('_0001'):
                        new_tag = re.sub(r'_(\d{4})$', '_0001', old_tag)
                        info['tag'] = new_tag
                        fixed_tags += 1
                
                # 3. options 분리 및 띄어쓰기 수정
                if info['type'] == 'question' and 'description' in info:
                    options = info['description']['options']
                    if options and len(options) == 1:
                        # 하나의 문자열로 합쳐진 options를 개별 선택지로 분리
                        combined_options = options[0]
                        
                        # ①②③④⑤ 패턴으로 분리
                        separated_options = re.split(r'([①②③④⑤])', combined_options)
                        
                        # 빈 문자열 제거하고 선택지 번호와 내용을 합치기
                        new_options = []
                        for i in range(1, len(separated_options), 2):
                            if i + 1 < len(separated_options):
                                option_number = separated_options[i]
                                option_text = separated_options[i + 1].strip()
                                if option_text:
                                    # ① 뒤에 한 칸 띄어쓰기
                                    new_option = option_number + ' ' + option_text
                                    new_options.append(new_option)
                        
                        if len(new_options) > 1:  # 분리가 성공한 경우만
                            info['description']['options'] = new_options
                            fixed_options += 1
                    elif options and len(options) > 1:
                        # 이미 분리된 options의 띄어쓰기 수정
                        new_options = []
                        for option in options:
                            if re.match(r'^[①②③④⑤]', option):
                                # ① 뒤에 과도한 공백 제거 (2개 이상의 공백을 1개로)
                                cleaned_option = re.sub(r'^([①②③④⑤])\s{2,}', r'\1 ', option)
                                new_options.append(cleaned_option)
                            else:
                                new_options.append(option)
                        
                        if new_options != options:
                            info['description']['options'] = new_options
                            fixed_options += 1
    
    # 수정된 파일 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"  - Options 수정: {fixed_options}개")
    print(f"  - 태그 수정: {fixed_tags}개")

def process_all_workbooks():
    """모든 workbook 파일을 일괄 처리"""
    base_path = "/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2"
    
    # 처리할 파일 목록
    files_to_process = [
        "SS0126_workbook/SS0126.json",
        "SS0127_workbook/SS0127.json", 
        "SS0128_workbook/SS0128.json",
        "SS0129_workbook/SS0129.json",
        "SS0134_workbook/SS0134.json",
        "SS0136_workbook/SS0136.json",
        "SS0137_workbook/SS0137.json"
    ]
    
    for file_rel_path in files_to_process:
        file_path = os.path.join(base_path, file_rel_path)
        
        if os.path.exists(file_path):
            try:
                # 1단계: 기본 변환
                process_workbook_file(file_path)
                
                # 2단계: options 분리 및 태그 수정
                processed_path = file_path.replace('.json', '_processed.json')
                if os.path.exists(processed_path):
                    fix_options_and_tags(processed_path)
                    
                    # 3단계: 원본 파일 교체
                    original_path = file_path.replace('.json', '_original.json')
                    if os.path.exists(original_path):
                        os.remove(original_path)  # 기존 백업 삭제
                    os.rename(file_path, original_path)
                    os.rename(processed_path, file_path)
                    
                    print(f"✅ {file_rel_path} 처리 완료")
                else:
                    print(f"❌ {file_rel_path} 처리 실패 - processed 파일 없음")
                    
            except Exception as e:
                print(f"❌ {file_rel_path} 처리 중 오류: {str(e)}")
        else:
            print(f"❌ {file_rel_path} 파일을 찾을 수 없습니다")
        
        print("-" * 50)

if __name__ == "__main__":
    process_all_workbooks()
