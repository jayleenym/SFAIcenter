import json
import re

def fix_spacing_and_tags():
    # SS0124.json 파일 읽기
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed_options = 0
    fixed_tags = 0
    
    for content in data['contents']:
        # 1. page_contents 태그 수정 (마지막 4자리를 0001로)
        if 'page_contents' in content and content['page_contents'].startswith('{q_'):
            old_tag = content['page_contents']
            # q_0004_0001 -> q_0004_0001 (이미 0001이면 변경하지 않음)
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
                
                # 3. options 띄어쓰기 수정
                if info['type'] == 'question' and 'description' in info:
                    options = info['description']['options']
                    if options:
                        new_options = []
                        for option in options:
                            # ① 뒤에 과도한 공백 제거 (2개 이상의 공백을 1개로)
                            cleaned_option = re.sub(r'^([①②③④⑤])\s{2,}', r'\1 ', option)
                            new_options.append(cleaned_option)
                        
                        if new_options != options:
                            info['description']['options'] = new_options
                            fixed_options += 1
    
    print(f"Options 띄어쓰기 수정: {fixed_options}개")
    print(f"태그 수정: {fixed_tags}개")
    
    # 수정된 파일 저장
    with open('/Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter/data_yejin/FINAL/2C_0902/Lv2/SS0124_workbook/SS0124.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print("수정 완료!")

if __name__ == "__main__":
    fix_spacing_and_tags()
