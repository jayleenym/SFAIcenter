import json
import re

def process_ss0124():
    # SS0124.json 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 새로운 구조로 변환
    new_contents = []
    current_theme = ""
    
    # 정답과 해설 추출
    answers = {}
    explanations = {}
    
    # 먼저 정답과 해설을 추출
    for content in data['contents']:
        page_content = content['page_contents']
        
        # 정답 모음 섹션 처리
        if '정답 모음' in page_content or '정답:' in page_content:
            # 정답 텍스트에서 문제별 정답 추출
            answer_text = page_content.replace('정답 모음', '').strip()
            # Theme별로 분리
            theme_sections = re.split(r'Theme \d+:', answer_text)
            
            for theme_section in theme_sections[1:]:  # 첫 번째는 빈 문자열
                # 각 Theme의 정답들을 추출
                lines = theme_section.strip().split('\n')
                for line in lines:
                    if re.match(r'\d+\.\s*[①②③④⑤]', line):
                        # 연속된 정답들을 분리 (예: "1. ③2. ②3. ③")
                        matches = re.findall(r'(\d+)\.\s*([①②③④⑤])', line)
                        for match in matches:
                            q_num = int(match[0])
                            answer = match[1]
                            answers[q_num] = answer
            continue
            
        # 풀이 및 해설 모음 섹션 처리
        if '풀이 및 해설 모음' in page_content or '풀이 및 해설:' in page_content:
            # 해설 텍스트를 문제별로 분리
            explanation_text = page_content.replace('풀이 및 해설 모음', '').strip()
            
            # Theme별로 분리
            if '풀이 및 해설 모음' in page_content:
                theme_sections = re.split(r'Theme \d+:', explanation_text)
                for theme_section in theme_sections[1:]:  # 첫 번째는 빈 문자열
                    # 문제별로 분리 (문제 1:, 문제 2: 등으로 구분)
                    problem_sections = re.split(r'문제 (\d+):', theme_section)
                    
                    for i in range(1, len(problem_sections), 2):
                        if i + 1 < len(problem_sections):
                            q_num = int(problem_sections[i])
                            explanation = problem_sections[i + 1].strip()
                            explanations[q_num] = explanation
            else:
                # 개별 Theme의 해설 처리
                problem_sections = re.split(r'문제 (\d+):', explanation_text)
                
                for i in range(1, len(problem_sections), 2):
                    if i + 1 < len(problem_sections):
                        q_num = int(problem_sections[i])
                        explanation = problem_sections[i + 1].strip()
                        explanations[q_num] = explanation
            continue
    
    # 이제 문제들을 처리
    for content in data['contents']:
        page_content = content['page_contents']
        
        # Theme 감지
        if page_content.startswith('Theme '):
            current_theme = page_content.strip()
            continue
            
        # 정답/해설 섹션은 건너뛰기
        if '정답 모음' in page_content or '풀이 및 해설 모음' in page_content:
            continue
            
        # 문제 감지 및 처리
        if page_content.startswith('문제 '):
            # 문제 번호 추출
            match = re.match(r'문제 (\d+):', page_content)
            if match:
                q_num = int(match.group(1))
                
                # 문제 텍스트에서 선택지 추출
                lines = page_content.split('\n')
                question_text = ""
                options = []
                
                for line in lines[1:]:  # "문제 X:" 제외
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
                    "page_contents": f"{{q_{content['page']}_{q_num:04d}}}",
                    "add_info": [
                        {
                            "tag": f"q_{content['page']}_{q_num:04d}",
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
    
    # 디버깅: 정답과 해설 확인
    print(f"추출된 정답 수: {len(answers)}")
    print(f"추출된 해설 수: {len(explanations)}")
    print("정답 예시:", dict(list(answers.items())[:5]))
    print("해설 예시:", dict(list(explanations.items())[:2]))
    
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
    
    # 새로운 파일로 저장
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124_processed.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    
    print(f"처리 완료: {len(new_contents)}개의 문제가 변환되었습니다.")
    return new_data

if __name__ == "__main__":
    process_ss0124()
