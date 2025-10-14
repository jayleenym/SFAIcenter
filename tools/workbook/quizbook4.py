# 5분 손해사정사 제3보험 (321494387) - 기출/답안 추출
new = {
    'file_id': origin['file_id'],
    'title': origin['title'],
    'cat1_domain': origin['cat1_domain'],
    'cat2_sub': origin['cat2_sub'],
    'cat3_specific': origin['cat3_specific'],
    'pub_date': origin['pub_date'],
    'contents': [],
}


for i in range(len(origin['contents'])):
    # i = 126
    c = origin['contents'][i]

    base_add_info = {
    'tag': "",
    'type': "question",
    "description": {
        "number": "",
        "question": "",
        "options": 0,
        'answer' : "",
        "explanation": ""
    },
    "caption":[],
    "file_path": 0,
    "bbox": 0
    }
    # 문제추출
    q_re = r'\[[0-9]{4} 기출\]'
    ans_re = r'\[[0-9]{4} 답안\]'
    key_re = r'\s키워드'

    # break
    try:
    # if 1:
        # [기출] ~ [답안]꼴
        q_start = re.search(q_re, c['page_contents']).span()[0]
        q_end = re.search(ans_re, c['page_contents'][q_start:]).span()[0] # 그꼴이 아니면 여기서 에러남
        a_start = q_end + q_start
        
        question = c['page_contents'][q_start:q_start+q_end]

       
        # caption 달기
        caption = re.findall(r'\[([0-9]{4} 기출)\]', question)[0]
        base_add_info['caption'].append(caption)

        question = re.sub(q_re, "", question).strip()      

         # 문제번호 뽑기
        number = re.findall(r"\D?(\d+)\D?\s", question)[0]
        base_add_info['description']['number'] = number.strip()
        question = re.sub(r"\D?\d+\D?\s", "", question).strip()


        # 태그 처리
        tag = f"q_{c['page']}_0001"
        base_add_info['tag'] = tag

        
                
        # 한 페이지에 [답안] 없으면
        if re.search(key_re, c['page_contents'][a_start:]) is None:
            print("in two pages")
            c2 = origin['contents'][i+1]
            a_end = re.search(key_re, c2['page_contents']).span()[0]
            # print(c2)
            answer = c['page_contents'][a_start:] + '\n' + c2['page_contents'][:a_end]

            c['page_contents'] += '\n' + c2['page_contents'][:a_end]
            c2['page_contents'] = c2['page_contents'].replace(c2['page_contents'][:a_end], "")

            c['page_contents'] = c['page_contents'].replace(c['page_contents'][q_start:], "{"+tag+"}")

            if c2['page_contents'].strip().startswith('키워드'):
                keyword_org = c2['page_contents'].strip().split("\n")[0]
                keyword = keyword_org.replace("키워드", "키워드: ").replace("  ", " ")
                base_add_info['caption'].append(keyword)
                c2['page_contents'] = c2['page_contents'].replace("\n"+keyword_org, "")
            # print(c2)
        # 한 페이지에 [답안]까지 있음
        else:
            print("in one page")
            a_end = re.search(key_re, c['page_contents'][a_start:]).span()[0]
            answer = c['page_contents'][a_start:a_start+a_end]
            if c['page_contents'][a_start+a_end:].strip().startswith('키워드'):
                keyword_org = c['page_contents'][a_start+a_end:].strip().split("\n")[0]
                keyword = keyword_org.replace("키워드", "키워드: ").replace("  ", " ")
                base_add_info['caption'].append(keyword)

            c['page_contents'] = c['page_contents'].replace(c['page_contents'][q_start:a_start+a_end], "{"+tag+"}")
            c['page_contents'] = c['page_contents'].replace("\n"+keyword_org, "")

        answer = re.sub(ans_re, "", answer)
        

        base_add_info['description']['question'] = question.strip()
        base_add_info['description']['answer'] = answer.strip()

        c['add_info'].append(base_add_info)

    except Exception as e:
    # else:
        if re.search(q_re, c['page_contents']) is not None:
            print(c['page'])
        else:
            # print(e, c['page'])
            pass

    # break
    if len(c['page_contents']) > 0:
        new['contents'].append(c)
    



    # break

# json.dump(origin, open(os.path.join(data_dir, name, name+'_new.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
