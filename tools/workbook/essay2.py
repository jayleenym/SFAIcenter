# 차량손해사정사
import json, re, os
from collections import defaultdict

# ===== 설정(필요시 확장) =====
QUESTION_ENDINGS = r"(?:하시오|설명하시오|서술하시오|쓰시오|논하시오|기술하시오|약술하시오)\."
# 문항번호 형식: 줄 시작의 '01' '02' ... (필요하면 \d{1,2}로 완화 가능)
QUESTION_HEADER = re.compile(
    rf"(?m)^\s*(?P<num>\d{{2}})\s+(?P<q>.*?{QUESTION_ENDINGS})",
    re.DOTALL
)

def build_big_text(contents):
    """페이지 경계를 마커로 넣어 하나의 거대 텍스트로 합칩니다."""
    parts = []
    for c in contents:
        page = c.get("page","0000")
        txt = (c.get("page_contents") or "").replace("\r\n","\n").replace("\r","\n")
        parts.append(f"\n<<<PAGE {page} START>>>\n{txt}\n<<<PAGE {page} END>>>")
    return "\n".join(parts)

def last_page_before(pos, big_text):
    """pos 이전 마지막 START 마커의 페이지 번호(문자열 4자리)를 반환."""
    m = list(re.finditer(r"<<<PAGE (\d{4}) START>>>", big_text[:pos]))
    return m[-1].group(1) if m else "0000"

def clean_markers(s: str) -> str:
    """페이지 마커 제거 및 양끝 공백 정리."""
    s = re.sub(r"<<<PAGE \d{4} (?:START|END)>>>", "", s)
    return s.strip()

def extract_qas_to_add_info(book: dict) -> dict:
    """요구 스키마로 Q/A를 추출하여 각 페이지의 add_info에 채워 넣고 book을 반환."""
    contents = book.get("contents", [])
    # 페이지 → 인덱스 매핑
    page_to_idx = {c.get("page","0000"): i for i, c in enumerate(contents)}
    # 페이지별 연속 번호 카운터
    seq_counter = defaultdict(int)

    # 하나의 텍스트로 합치고, 문제 헤더 전역 탐색
    big = build_big_text(contents)
    matches = list(QUESTION_HEADER.finditer(big))

    # 결과 누적 구조(페이지별)
    per_page_items = defaultdict(list)

    for i, m in enumerate(matches):
        qnum  = m.group("num")
        qtext = m.group("q").strip()
        qstart = m.start()
        qend   = m.end()
        # 다음 문제 시작 전까지(문서 끝까지) 전부 answer
        next_start = matches[i+1].start() if i+1 < len(matches) else len(big)
        answer_raw = big[qend:next_start]
        answer = clean_markers(answer_raw)

        # 문제 시작한 페이지
        page = last_page_before(qstart, big)
        seq_counter[page] += 1
        tag = f"q_{int(page):04d}_{seq_counter[page]:04d}"

        item = {
            "tag": tag,
            "type": "question",
            "description": {
                "number": qnum,
                "question": qtext,
                "options": None,
                "answer": answer,
                "explanation": ""
            },
            "caption": [""],
            "file_path": None,
            "bbox": None
        }
        per_page_items[page].append(item)

    # 원본 book에 add_info로 주입(기존 값이 있으면 뒤에 붙임)
    for page, items in per_page_items.items():
        idx = page_to_idx.get(page)
        if idx is None:
            continue
        if "add_info" not in contents[idx] or not isinstance(contents[idx]["add_info"], list):
            contents[idx]["add_info"] = []
        contents[idx]["add_info"].extend(items)

    book["contents"] = contents
    return book


# def main(INPUT_PATH) -> None:
#     BACKUP_PATH = INPUT_PATH + ".bak"
    
#     if not os.path.exists(INPUT_PATH):
#         raise FileNotFoundError(INPUT_PATH)

#     with open(INPUT_PATH, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     with open(BACKUP_PATH, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)

#     contents: List[Dict[str, Any]] = data.get("contents", [])
#     data["contents"] = ???(contents)

#     with open(INPUT_PATH, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    IN_PATH  = "data_yejin/FINAL/1C_0910/Lv3_4/361239919_workbook/361239919.json"          # 입력 JSON 경로
    OUT_PATH = "data_yejin/FINAL/1C_0910/Lv3_4/361239919_workbook/361239919_new.json"   # 출력 JSON 경로

    with open(IN_PATH, "r", encoding="utf-8") as f:
        book = json.load(f)

    book_filled = extract_qas_to_add_info(book)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(book_filled, f, ensure_ascii=False, indent=4)

    print(f"Saved: {OUT_PATH}")
