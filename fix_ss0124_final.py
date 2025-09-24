import json
import re

def fix_ss0124_final():
    # 현재 SS0124.json 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    
    # 백업 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124_backup.json', 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    # 백업 파일에서 정답과 해설 추출
    answers = {}
    explanations = {}
    
    for content in backup_data['contents']:
        page_content = content['page_contents']
        
        # 정답 추출
        if '정답:' in page_content:
            matches = re.findall(r'(\d+)\.\s*([①②③④⑤])', page_content)
            for match in matches:
                q_num = int(match[0])
                answer = match[1]
                answers[q_num] = answer
        
        # 해설 추출 - 모든 해설 페이지에서 추출
        if '문제' in page_content and '정답:' in page_content:
            problem_sections = re.split(r'문제 (\d+):', page_content)
            
            for i in range(1, len(problem_sections), 2):
                if i + 1 < len(problem_sections):
                    q_num = int(problem_sections[i])
                    explanation = problem_sections[i + 1].strip()
                    if explanation and len(explanation) > 10:  # 의미있는 해설만
                        explanations[q_num] = explanation
    
    print(f"백업에서 추출된 정답: {len(answers)}개")
    print(f"백업에서 추출된 해설: {len(explanations)}개")
    
    # 현재 파일 수정
    fixed_options = 0
    filled_explanations = 0
    
    for content in current_data['contents']:
        if 'add_info' in content and content['add_info']:
            for info in content['add_info']:
                if info['type'] == 'question' and 'description' in info:
                    # 1. options 수정 (① 뒤에 한 칸 띄기)
                    options = info['description']['options']
                    if options:
                        new_options = []
                        for option in options:
                            if re.match(r'^[①②③④⑤]', option):
                                # ① 뒤에 한 칸 띄기
                                new_option = re.sub(r'^([①②③④⑤])', r'\1 ', option)
                                new_options.append(new_option)
                            else:
                                new_options.append(option)
                        if new_options != options:  # 변경사항이 있을 때만
                            info['description']['options'] = new_options
                            fixed_options += 1
                    
                    # 2. explanation이 비어있으면 백업에서 찾아서 채우기
                    if not info['description']['explanation'] or info['description']['explanation'].strip() == "":
                        q_num = int(info['description']['number'])
                        if q_num in explanations:
                            info['description']['explanation'] = explanations[q_num]
                            filled_explanations += 1
                    
                    # 3. answer도 백업에서 확인
                    if not info['description']['answer'] or info['description']['answer'].strip() == "":
                        q_num = int(info['description']['number'])
                        if q_num in answers:
                            info['description']['answer'] = answers[q_num]
    
    print(f"Options 수정: {fixed_options}개")
    print(f"Explanation 채움: {filled_explanations}개")
    
    # 수정된 파일 저장
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=4)
    
    print("수정 완료!")

if __name__ == "__main__":
    fix_ss0124_final()
