import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple

# INPUT_PATH = "/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/data/FINAL/2C_0902/Lv2/SS0121_workbook/SS0121.json"
# INPUT_PATH = ""
# BACKUP_PATH = INPUT_PATH + ".bak"

# Patterns
ANSWER_RE = re.compile(r"정답\s*[:：]\s*([①-⑩A-E0-9]+)")
EXPLAIN_RE = re.compile(r"해설\s*[:：]\s*(.*)", re.DOTALL)
PROBLEM_RE = re.compile(r"문제\s*([0-9]+)\s*[:：]?\s*(.*)", re.DOTALL)
BRACED_TAG_RE = re.compile(r"^\{q_\d{4}_\d{4}\}$")

OPTION_BULLETS = [
    "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"
]


def split_options(text: str) -> Tuple[str, List[str]]:
    norm = re.sub(r"\s+", " ", text).strip()
    first_idx = min((norm.find(b) for b in OPTION_BULLETS if norm.find(b) != -1), default=-1)
    if first_idx == -1:
        return norm, []
    question_part = norm[:first_idx].strip()
    options_part = norm[first_idx:]

    options: List[str] = []
    bullet_positions = [m.start() for m in re.finditer(r"[①②③④⑤⑥⑦⑧⑨⑩]", options_part)]
    bullet_positions.append(len(options_part))
    for i in range(len(bullet_positions) - 1):
        start = bullet_positions[i]
        end = bullet_positions[i + 1]
        opt = options_part[start:end].strip()
        if opt:
            options.append(opt)
    return question_part, options


def extract_number(text: str) -> str:
    m = PROBLEM_RE.search(text)
    return m.group(1) if m else ""


def extract_answer(text: str) -> str:
    m = ANSWER_RE.search(text)
    return m.group(1).strip() if m else ""


def extract_explanation(text: str) -> str:
    m = EXPLAIN_RE.search(text)
    return m.group(1).strip() if m else ""


def build_tag(page: str, index_in_page: int) -> str:
    return f"q_{page}_{index_in_page:04d}"


def is_problem(text: str) -> bool:
    return "문제" in (text or "")


def is_answer_or_expl(text: str) -> bool:
    t = text or ""
    return ("정답" in t) or ("해설" in t)


def process_contents(contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    i = 0
    while i < len(contents):
        entry = contents[i]
        page_code: str = entry.get("page", "0000")
        text: str = entry.get("page_contents", "") or ""

        if not (is_problem(text) or is_answer_or_expl(text)):
            entry.setdefault("add_info", [])
            i += 1
            continue

        # Start a group from this page
        group_indices = [i]
        merged_texts = [text]
        j = i + 1
        # Extend group until we see both answer and explanation or hit a non-QA section
        have_answer = extract_answer("\n".join(merged_texts)) != ""
        have_expl = extract_explanation("\n".join(merged_texts)) != ""
        while j < len(contents) and (not (have_answer and have_expl)):
            nxt = contents[j].get("page_contents", "") or ""
            if not (is_problem(nxt) or is_answer_or_expl(nxt)):
                break
            group_indices.append(j)
            merged_texts.append(nxt)
            have_answer = extract_answer("\n".join(merged_texts)) != ""
            have_expl = extract_explanation("\n".join(merged_texts)) != ""
            j += 1

        merged = "\n".join(merged_texts)
        # Clean question block by removing trailing answer/expl sections
        cutoff_idx = len(merged)
        a_match = ANSWER_RE.search(merged)
        e_match = EXPLAIN_RE.search(merged)
        if a_match:
            cutoff_idx = min(cutoff_idx, a_match.start())
        if e_match:
            cutoff_idx = min(cutoff_idx, e_match.start())
        question_block = merged[:cutoff_idx].strip()
        # Remove leading '문제 N:' from question text
        question_block_clean = re.sub(r"^\s*문제\s*[0-9]+\s*[:：]?\s*", "", question_block)

        question_text, options = split_options(question_block_clean)
        number = extract_number(merged)
        answer = extract_answer(merged)
        explanation = extract_explanation(merged)

        # Always index as first question on that page for now
        tag = build_tag(page_code, 1)
        braced_tag = "{" + tag + "}"

        add_item = {
            "tag": tag,
            "type": "question",
            "description": {
                "number": number,
                "question": question_text,
                "options": options if options else None,
                "answer": answer,
                "explanation": explanation,
            },
            "caption": [],
            "file_path": None,
            "bbox": None
        }

        # Write to the first page in group
        contents[i]["add_info"] = [add_item]
        contents[i]["page_contents"] = braced_tag
        # Other pages in group: clear add_info and set empty page_contents
        for gi in group_indices[1:]:
            contents[gi].setdefault("add_info", [])
            contents[gi]["add_info"] = []
            contents[gi]["page_contents"] = ""

        # Continue after the group
        i = group_indices[-1] + 1

    # Cleanup pass: if a page only has a braced tag in page_contents and empty add_info, clear the body
    for entry in contents:
        body = entry.get("page_contents", "") or ""
        add_info = entry.get("add_info", []) or []
        if BRACED_TAG_RE.match(body) and len(add_info) == 0:
            entry["page_contents"] = ""

    return contents


def main(INPUT_PATH) -> None:
    BACKUP_PATH = INPUT_PATH + ".bak"
    
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(INPUT_PATH)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    contents: List[Dict[str, Any]] = data.get("contents", [])
    data["contents"] = process_contents(contents)

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)