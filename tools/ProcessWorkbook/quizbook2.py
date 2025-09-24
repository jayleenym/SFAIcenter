import re, os, json
from typing import List, Dict, Any

# INPUT_PATH = "/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/data/FINAL/2C_0902/Lv2/SS0121_workbook/SS0122.json"

CIRCLED = {str(i): c for i, c in zip(range(1, 11), "①②③④⑤⑥⑦⑧⑨⑩")}
UNCIRCLED = {v: k for k, v in CIRCLED.items()}

QUESTION_HEAD_RE = re.compile(r"문제\s*(\d+)\s*:", re.S)
OPTION_SPLIT_RE = re.compile(r"([①-⑩])\s*(.*?)(?=(?:[①-⑩])|\Z)", re.S)
THEME_BLOCK_RE = re.compile(
    r"(Theme\s*\d+\s*:\s*)(.+?)(?=\n{2,}|Theme\s*\d+\s*:|문제\s*\d+\s*:|$)",
    re.I | re.S
)

# 정답/해설 파트: "정답 및 해설:" 이후 페이지들을 모두 이어붙이고
# "문제 N 정답: ④ 풀이 및 해설: ..." 단위로 쪼갠다.
ANSWER_BLOCK_START_RE = re.compile(r"정답\s*및\s*해설\s*:", re.S)
ANSWER_ITEM_RE = re.compile(
    r"문제\s*(\d+)\s*정답\s*:\s*([①-⑩0-9])\s*(?:풀이\s*및\s*해설\s*:\s*)?(.*?)(?=문제\s*\d+\s*정답\s*:|$)",
    re.S
)

def normalize_answer_mark(mark: str) -> str:
    mark = mark.strip()
    if mark in CIRCLED.values():
        return mark
    if mark.isdigit() and mark in CIRCLED:
        return CIRCLED[mark]
    # 방어적 처리: 첫 글자만 취하고 없으면 빈값
    return CIRCLED.get(re.sub(r"\D", "", mark) or "","")

# def collapse_spaces(s: str) -> str:
#     # 보기 텍스트 등에서 줄바꿈이 쓸데없이 섞인 경우를 정돈
#     return re.sub(r"[ \t]+", " ", s).strip()
def collapse_spaces(s: str) -> str:
    # 줄바꿈과 탭을 모두 공백으로 변환 후, 연속 공백을 하나로 축소
    return re.sub(r"\s+", " ", s).strip()

def extract_theme(text: str) -> str:
    """
    'Theme n: 제목'이 줄바꿈으로 끊겨 있어도
    다음 단락/다음 Theme/다음 문제 시작 전까지를 한 덩어리로 묶어서 반환.
    """
    m = THEME_BLOCK_RE.search(text)
    if not m:
        return ""
    head, body = m.group(1), m.group(2)
    # 본문 제목의 줄바꿈/중복 공백 정리
    body_clean = re.sub(r"\s+", " ", body).strip()
    return (head + body_clean).strip()


def stitch_answer_text(pages: List[Dict[str, Any]]) -> str:
    """
    '정답 및 해설:'이 등장하는 첫 페이지부터 마지막까지를 이어붙여 하나의 텍스트로 만든다.
    """
    start_idx = None
    for i, p in enumerate(pages):
        if ANSWER_BLOCK_START_RE.search(p.get("page_contents","")):
            start_idx = i
            break
    if start_idx is None:
        # '정답 및 해설:' 타이틀 없이 바로 '문제 N 정답:'으로 시작하는 경우가 있을 수 있음
        # 이때는 모든 페이지 텍스트를 합쳐 후속 정규식에서 거른다.
        merged = "\n".join(p.get("page_contents","") for p in pages)
        return merged

    merged = []
    for p in pages[start_idx:]:
        merged.append(p.get("page_contents",""))
    return "\n".join(merged)

def parse_answers(pages: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    반환: {'1': {'answer':'④','explanation':'...'}, ...}
    """
    merged = stitch_answer_text(pages)
    items = {}
    for m in ANSWER_ITEM_RE.finditer(merged):
        qnum = m.group(1).strip()
        ans_mark = normalize_answer_mark(m.group(2))
        expl = m.group(3).strip()
        items[qnum] = {
            "answer": ans_mark,
            "explanation": expl
        }
    return items

def split_question_blocks(text: str) -> List[Dict[str, Any]]:
    res = []
    heads = list(QUESTION_HEAD_RE.finditer(text))
    for i, h in enumerate(heads):
        qnum = h.group(1).strip()
        start = h.end()
        end = heads[i+1].start() if i+1 < len(heads) else len(text)
        body = text[start:end].strip()

        options = []
        # 옵션 시작 위치: 첫 번째 '①-⑩'
        first_opt_match = re.search(r"[①-⑩]", body)
        if first_opt_match:
            q_text = body[:first_opt_match.start()].strip()
            opts_part = body[first_opt_match.start():]

            # 변경된 정규식으로 번호별 분리 (줄바꿈 없어도 OK)
            for mark, opt_text in OPTION_SPLIT_RE.findall(opts_part):
                options.append(f"{mark} {collapse_spaces(opt_text)}")
        else:
            q_text = body
            options = []

        res.append({
            "number": qnum,
            "question": collapse_spaces(q_text),
            "options": options
        })
    return res


def assign_chapters(pages: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    가장 가까운 과거 Theme 라인을 chapter 로 사용.
    반환: {'0004':'Theme 1: ...', ...}
    """
    chapter_map = {}
    current_ch = ""
    for p in pages:
        pid = p.get("page")
        text = p.get("page_contents","")
        ch = extract_theme(text)
        if ch:
            current_ch = ch
        chapter_map[pid] = current_ch
    return chapter_map

def build_output(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    요구 포맷으로 변환.
    """
    answers = parse_answers(pages)
    chapters = assign_chapters(pages)

    out_pages = []
    # 페이지 단위 시퀀스 카운터
    per_page_seq = {}

    for p in pages:
        pid = p.get("page")
        text = p.get("page_contents","")
        qs = split_question_blocks(text)
        if not qs:
            # 질문 없는 페이지는 원형 유지 (ex. 목차/테마/정답해설 페이지만 있는 페이지는 보통 스킵)
            # 필요 시 그대로 내보내고 싶다면 아래 주석 해제
            # out_pages.append(p.copy())
            continue

        # 페이지 내 태그들
        tags = []
        add_info_items = []
        per_page_seq.setdefault(pid, 0)

        for q in qs:
            per_page_seq[pid] += 1
            seq = f"{per_page_seq[pid]:04d}"
            tag = f"q_{pid}_{seq}"
            tags.append(f"{{{tag}}}")

            number = q["number"]
            merged = {
                "tag": tag,
                "type": "question",
                "description": {
                    "number": number,
                    "question": q["question"],
                    "options": q["options"],
                    "answer": answers.get(number, {}).get("answer",""),
                    "explanation": answers.get(number, {}).get("explanation","").strip()
                },
                "caption": [],
                "file_path": None,
                "bbox": None
            }
            add_info_items.append(merged)

        out_pages.append({
            "page": pid,
            "chapter": chapters.get(pid,""),
            "page_contents": "\n".join(tags),
            "add_info": add_info_items
        })

    return out_pages

# --------- 사용 예시 ----------
# pages = [...]  # 질문에 제공된 리스트를 그대로 대입
# result = build_output(pages)
# print(json.dumps(result, ensure_ascii=False, indent=2))
def main(INPUT_PATH) -> None:
    BACKUP_PATH = INPUT_PATH + ".bak"
    
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(INPUT_PATH)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    contents: List[Dict[str, Any]] = data.get("contents", [])
    data["contents"] = build_output(contents)

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)