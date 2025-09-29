import re
import copy
from typing import Dict, Any, List

PUNCT_BEFORE = r'[\.\"”\'’\)\]\}〉》」』>]'  # 번호 앞에 올 수 있는 문장부호들

def transform_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    여러 페이지를 일괄 변환.
    각 페이지당 1문항으로 가정하여 {note_<page>_0001} 형태로 변환.
    """
    return [convert_page_record(it) for it in items]

def convert_page_record(record: Dict[str, Any]) -> Dict[str, Any]:
    rec = copy.deepcopy(record)
    page = rec.get("page", "0000")
    text = rec.get("page_contents", "")

    # 1) footnote 정의 추출
    foot_def_pat = re.compile(r'^\s*___\s*(\d+)\s+(.*)$', flags=re.MULTILINE)
    foot_defs: List[tuple[str, str]] = foot_def_pat.findall(text)

    # 2) 본문에서 footnote 정의 줄 제거
    text = foot_def_pat.sub("", text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    add_info = rec.get("add_info", []) or []

    # 3) 본문 참조 치환 + add_info 작성
    for idx, (num, desc) in enumerate(foot_defs, start=1):
        tag = f"note_{page}_{idx:04d}"

        ref_pat = re.compile(rf'({PUNCT_BEFORE}){re.escape(num)}(?=\s)', flags=re.UNICODE)
        new_text, n_sub = ref_pat.subn(rf'\1{{{tag}}}', text, count=1)
        if n_sub == 0:
            alt_pat = re.compile(rf'(?<!\d){re.escape(num)}(?=\s)', flags=re.UNICODE)
            new_text, _ = alt_pat.subn(rf'{{{tag}}}', text, count=1)
        text = new_text

        # description에 번호를 포함해서 저장
        add_info.append({
            "tag": tag,
            "type": "footnote",
            "description": f"{num} {desc.strip()}",
            "caption": None,
            "file_path": None,
            "bbox": None
        })

    return {
        **rec,
        "page_contents": text,
        "add_info": add_info
    }


data_list = origin.get('contents')
converted_list = transform_list(data_list)

origin['contents'] = converted_list
json.dump(origin, open(os.path.join(data_dir, name+"_footnote", name+'_new.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
