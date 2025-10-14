import re, os
import json
from copy import deepcopy
from typing import Dict, Tuple, List, Any, Optional

CHOICE_PATTERN = "①②③④⑤⑥⑦⑧⑨⑩"

def normalize_spaces(s: str) -> str:
    # 줄바꿈 사이 의미 보존: 연속 공백 정리, \r 제거
    return re.sub(r"[ \t]+", " ", s.replace("\r", ""))

def extract_theme_full(text: str) -> Optional[str]:
    """
    다양한 줄바꿈을 고려해 Theme 헤더를 'Theme X: 이름' 형태로 복원
    예)
      'Theme 1:\n경제학의 기본\n개념' -> 'Theme 1: 경제학의 기본 개념'
      'Theme 1: 경제학의 기본 개념 정답:' -> 'Theme 1: 경제학의 기본 개념'
    """
    t = text.replace("\r", "")
    m = re.search(r"Theme\s*(\d+)\s*:\s*([\s\S]+?)($|정답|문제|\n문제|\n풀이|해설)", t)
    if not m:
        # 케이스: "Theme 1: 경제학의 기본 개념 정답:" 같은 줄에서 '정답' 앞까지만 잘라내기
        m2 = re.search(r"(Theme\s*\d+\s*:\s*[^\n:]+)", t)
        if m2:
            return m2.group(1).strip()
        return None
    num = m.group(1)
    name_raw = m.group(2)
    name = " ".join([seg for seg in name_raw.splitlines() if seg.strip()])
    name = re.sub(r"\s*정답\s*$", "", name).strip(" :")
    return f"Theme {num}: {name}".strip()

def parse_answer_key_page(text: str) -> Tuple[Optional[str], Dict[int, str]]:
    """
    'Theme X: ... 정답:' 페이지에서 '문제 1: ④문제 2: ①...'를 파싱
    반환: (theme_full, {문제번호: '④', ...})
    """
    theme_full = extract_theme_full(text)
    ans_map = {}
    # "문제 1: ④" / "문제 1:④" / "문제 1 : ④" 모두 허용
    for num, ch in re.findall(r"문제\s*(\d+)\s*[:：]\s*([{}])".format(CHOICE_PATTERN), text):
        ans_map[int(num)] = ch
    return theme_full, ans_map

def parse_explanations_page(text: str) -> List[Tuple[str, int, str]]:
    """
    '풀이 및 해설Theme X: ... 문제 1.\n풀이 및 해설: ...' 같은 페이지에서
    각 (theme_full, 문제번호, 해설문) 리스트로 추출
    """
    out = []
    # 페이지 내에서 Theme가 여러 번 바뀔 수 있으니 블록을 Theme 단위로 쪼갠 후 문제별로 파싱
    # Theme 헤더를 경계로 split
    # 경계 포함 split: re.split(capturing)
    blocks = re.split(r"(Theme\s*\d+\s*:\s*[\s\S]*?(?=Theme\s*\d+\s*:|$))", text.replace("\r", ""))
    # re.split은 첫 원소가 잡다한 프리앰블일 수 있음 → 유효 Theme 블록만 처리
    for blk in blocks:
        theme_full = extract_theme_full(blk)
        if not theme_full:
            continue
        # 각 문제 블록: "문제 N." 으로 시작해서 다음 문제/Theme/문서 끝 전까지
        for m in re.finditer(r"문제\s*(\d+)\.\s*([\s\S]*?)(?=\n문제\s*\d+\.|Theme\s*\d+\s*:|$)", blk):
            qnum = int(m.group(1))
            body = m.group(2)
            # '풀이 및 해설:' 이후부터 다음 경계 전까지가 해설
            em = re.search(r"풀이\s*및\s*해설\s*[:：]?\s*([\s\S]*)", body)
            if em:
                exp_text = em.group(1).strip()
                out.append((theme_full, qnum, exp_text))
            else:
                # 간혹 '해설:'만 쓰인 경우 보조
                em2 = re.search(r"해설\s*[:：]?\s*([\s\S]*)", body)
                if em2:
                    out.append((theme_full, qnum, em2.group(1).strip()))
    return out

def split_question_block(block: str) -> Tuple[str, List[str]]:
    """
    한 '문제 N.' 블록에서 '질문 본문'과 '선지 리스트' 분리
    선지는 ①~⑩ 로 시작하는 라인들.
    """
    # 선택지 경계 찾기
    # 첫 선택지 위치
    first_choice = re.search(rf"[{CHOICE_PATTERN}]", block)
    if not first_choice:
        question_text = block.strip()
        options = []
        return question_text, options

    idx = first_choice.start()
    question_text = block[:idx].strip()
    tail = block[idx:]
    # 선택지들을 줄 단위로 모으기
    options = re.findall(rf"[{CHOICE_PATTERN}][^\n]*", tail)
    options = [opt.strip() for opt in options if opt.strip()]
    return question_text, options

def parse_questions_on_page(text: str) -> List[Tuple[int, str, List[str], str]]:
    """
    페이지 내 '문제 N.'들을 찾아 (문제번호, 질문본문, 선지[], 원본블록텍스트) 리스트 반환
    """
    results = []
    for m in re.finditer(r"문제\s*(\d+)\.\s*([\s\S]*?)(?=\n문제\s*\d+\.|$)", text.replace("\r", "")):
        qnum = int(m.group(1))
        block = m.group(2)
        qtext, options = split_question_block(block)
        results.append((qnum, qtext, options, m.group(0)))
    return results

def build_unified_structure(contents) -> Dict[str, Any]:
    """
    입력 도서 JSON(book) → 같은 구조를 유지하며,
    질문이 있는 페이지의 page_contents를 {q_페이지_####} 자리표시자로 교체하고,
    add_info에 표준 question 객체를 추가.
    정답/해설은 해당 테마의 매칭 값이 존재할 때만 채움.
    """
    # contents = deepcopy(book["contents"])

    # 1) 정답 맵, 해설 맵 구성 (theme_full -> {qnum: answer/expl})
    theme_to_ans: Dict[str, Dict[int, str]] = {}
    theme_to_exp: Dict[str, Dict[int, str]] = {}

    for page in contents:
        txt = page.get("page_contents", "")
        if "정답" in txt and "문제" in txt:
            theme_full, amap = parse_answer_key_page(txt)
            if theme_full:
                theme_to_ans.setdefault(theme_full, {}).update(amap)

    for page in contents:
        txt = page.get("page_contents", "")
        if "풀이" in txt and "해설" in txt:
            for theme_full, qnum, exp_text in parse_explanations_page(txt):
                theme_to_exp.setdefault(theme_full, {})[qnum] = exp_text

    # 2) 순회하며 Theme 추적 + 질문 붙이기
    current_theme_full: Optional[str] = None
    page_id_to_placeholders: Dict[str, List[str]] = {}

    for page in contents:
        page_text = page.get("page_contents", "")
        # Theme 갱신 시도
        theme_here = extract_theme_full(page_text)
        if theme_here:
            current_theme_full = theme_here

        # 문제 파싱
        qlist = parse_questions_on_page(page_text)
        if not qlist:
            continue

        # 페이지 내 여러 문제 처리
        placeholders = []
        add_info = page.get("add_info") or []
        for idx, (qnum, qtext, options, raw_block) in enumerate(qlist, start=1):
            tag = f"q_{page['page']}_{idx:04d}"
            placeholders.append(f"{{{tag}}}")

            # 정답/해설 매칭
            answer = None
            explanation = None
            if current_theme_full:
                answer = theme_to_ans.get(current_theme_full, {}).get(qnum)
                explanation = theme_to_exp.get(current_theme_full, {}).get(qnum)

            # description.number는 문제번호 문자열로
            desc = {
                "number": str(qnum),
                "question": qtext.strip(),
                "options": options,
            }
            if answer is not None:
                desc["answer"] = answer  # 정답 키에서만 채움 (직접 풀이 금지)
            if explanation is not None:
                desc["explanation"] = explanation

            add_info.append({
                "tag": tag,
                "type": "question",
                "description": desc,
                "caption": [],
                "file_path": None,
                "bbox": None
            })

        # page_contents를 자리표시자로 교체 (여러 개면 줄바꿈으로 연결)
        page["page_contents"] = "\n".join(placeholders)
        page["add_info"] = add_info

    # 3) 결과 조립
    # out = deepcopy(book)
    # out["contents"] = contents
    # return out
    return contents

# # === 사용 예시 ===
# if __name__ == "__main__":
#     # 아래 demo_book은 질문에 제시된 JSON을 변수로 담아 사용하세요.
#     # out = build_unified_structure(demo_book)
#     # print(json.dumps(out, ensure_ascii=False, indent=2))
#     pass

def main(INPUT_PATH) -> None:
    BACKUP_PATH = INPUT_PATH + ".bak"
    
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(INPUT_PATH)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    contents: List[Dict[str, Any]] = data.get("contents", [])
    data["contents"] = build_unified_structure(contents)
    # data = build_unified_structure(data)

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)