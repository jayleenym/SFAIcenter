import json
import re

def fix_options():
    # SS0124.json 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed_count = 0
    
    # 각 문제의 options를 개별 선택지로 분리
    for content in data['contents']:
        if 'add_info' in content and content['add_info']:
            for info in content['add_info']:
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
                                    new_options.append(option_number + option_text)
                        
                        if len(new_options) > 1:  # 분리가 성공한 경우만
                            info['description']['options'] = new_options
                            fixed_count += 1
                            print(f"수정된 문제 {fixed_count}: {len(new_options)}개 선택지로 분리")
    
    print(f"총 {fixed_count}개 문제의 options를 분리했습니다.")
    
    # 수정된 파일 저장
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print("Options 분리 완료!")

if __name__ == "__main__":
    fix_options()
