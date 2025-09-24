import json
import re
import os

def extract_answers_and_explanations_from_new_file(new_file_path):
    """_new.json 파일에서 정답과 해설을 추출하는 함수"""
    with open(new_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    answers = {}
    explanations = {}
    
    for content in data['contents']:
        page_content = content['page_contents']
        
        # 정답 추출
        if '정답 Theme' in page_content or '정답:' in page_content:
            # "정답 Theme 11. ③2. ③3. ④4. ①5. ②6. ③7. ①8. ②9. ③ 10. ④" 형태에서 추출
            if 'Theme' in page_content:
                # Theme별로 분리
                theme_sections = re.split(r'Theme (\d+)', page_content)
                for i in range(1, len(theme_sections), 2):
                    if i + 1 < len(theme_sections):
                        theme_num = int(theme_sections[i])
                        answers_text = theme_sections[i + 1].strip()
                        
                        # 문제별 정답 추출
                        matches = re.findall(r'(\d+)\.\s*([①②③④⑤])', answers_text)
                        for match in matches:
                            q_num = int(match[0])
                            answer = match[1]
                            answers[q_num] = answer
            else:
                # 일반적인 정답 형태
                matches = re.findall(r'(\d+)\.\s*([①②③④⑤])', page_content)
                for match in matches:
                    q_num = int(match[0])
                    answer = match[1]
                    answers[q_num] = answer
        
        # 해설 추출
        if '풀이 및 해설:' in page_content or '해설:' in page_content:
            # 문제별로 분리
            problem_sections = re.split(r'문제 (\d+)', page_content)
            
            for i in range(1, len(problem_sections), 2):
                if i + 1 < len(problem_sections):
                    q_num = int(problem_sections[i])
                    explanation_text = problem_sections[i + 1].strip()
                    
                    # "정답: ③ 해설: ..." 형태에서 해설 추출
                    if '정답:' in explanation_text and '해설:' in explanation_text:
                        # 정답과 해설 분리
                        parts = explanation_text.split('해설:')
                        if len(parts) > 1:
                            explanation = parts[1].strip()
                            if explanation and len(explanation) > 10:
                                explanations[q_num] = explanation
    
    return answers, explanations

def fill_answers_and_explanations(workbook_file_path, new_file_path):
    """workbook 파일에 정답과 해설을 채워넣는 함수"""
    print(f"처리 중: {workbook_file_path}")
    
    # _new.json 파일에서 정답과 해설 추출
    answers, explanations = extract_answers_and_explanations_from_new_file(new_file_path)
    
    print(f"  - 추출된 정답: {len(answers)}개")
    print(f"  - 추출된 해설: {len(explanations)}개")
    
    # workbook 파일 읽기
    with open(workbook_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    filled_answers = 0
    filled_explanations = 0
    
    # 각 문제에 정답과 해설 채워넣기
    for content in data['contents']:
        if 'add_info' in content and content['add_info']:
            for info in content['add_info']:
                if info['type'] == 'question' and 'description' in info:
                    q_num = int(info['description']['number'])
                    
                    # 정답 채워넣기
                    if q_num in answers and (not info['description']['answer'] or info['description']['answer'].strip() == ""):
                        info['description']['answer'] = answers[q_num]
                        filled_answers += 1
                    
                    # 해설 채워넣기
                    if q_num in explanations and (not info['description']['explanation'] or info['description']['explanation'].strip() == ""):
                        info['description']['explanation'] = explanations[q_num]
                        filled_explanations += 1
    
    # 수정된 파일 저장
    with open(workbook_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"  - 채워진 정답: {filled_answers}개")
    print(f"  - 채워진 해설: {filled_explanations}개")
    print(f"✅ {workbook_file_path} 처리 완료")

def process_all_workbooks():
    """모든 workbook 파일의 정답과 해설을 채워넣기"""
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
        workbook_path = os.path.join(base_path, file_rel_path)
        new_path = workbook_path.replace('.json', '_new.json')
        
        if os.path.exists(workbook_path) and os.path.exists(new_path):
            try:
                fill_answers_and_explanations(workbook_path, new_path)
            except Exception as e:
                print(f"❌ {file_rel_path} 처리 중 오류: {str(e)}")
        else:
            print(f"❌ {file_rel_path} 또는 {file_rel_path.replace('.json', '_new.json')} 파일을 찾을 수 없습니다")
        
        print("-" * 50)

if __name__ == "__main__":
    process_all_workbooks()
