import json
import re

def process_ss0125():
    # SS0125.json 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0125_workbook/SS0125.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 새로운 구조로 변환
    new_contents = []
    current_theme = ""
    
    # 정답과 해설 추출
    answers = {}
    explanations = {}
    
    # 모든 페이지를 순회하면서 정답과 해설 추출
    for content in data['contents']:
        page_content = content['page_contents']
        
        # 정답 추출
        if '정답:' in page_content and '문제' in page_content:
            # "문제 1: ④문제 2: ③" 형태에서 추출
            matches = re.findall(r'문제 (\d+):\s*([①②③④⑤])', page_content)
            for match in matches:
                q_num = int(match[0])
                answer = match[1]
                answers[q_num] = answer
        
        # 해설 추출
        if '풀이 및 해설:' in page_content:
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
        if '정답 모음' in page_content or '풀이 및 해설 모음' in page_content or '정답:' in page_content:
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
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0125_workbook/SS0125_processed.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    
    print(f"처리 완료: {len(new_contents)}개의 문제가 변환되었습니다.")
    return new_data

if __name__ == "__main__":
    process_ss0125()
