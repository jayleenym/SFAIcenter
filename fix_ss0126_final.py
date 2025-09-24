import json
import re

def fix_ss0126_final():
    # 처리된 SS0126_processed.json 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0126_workbook/SS0126_processed.json', 'r', encoding='utf-8') as f:
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
    
    print(f"Options 수정: {fixed_options}개")
    print(f"태그 수정: {fixed_tags}개")
    
    # 수정된 파일 저장
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0126_workbook/SS0126.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print("SS0126.json 수정 완료!")

if __name__ == "__main__":
    fix_ss0126_final()
