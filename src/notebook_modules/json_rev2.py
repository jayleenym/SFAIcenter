# Generated from notebook: json_rev2.ipynb
# This file was auto-created to expose reusable code as a module.

import re, json, os
import re
import json
from typing import List, Dict, Any
import json, re
from collections import defaultdict
import copy
from typing import Dict, Any, List

base_dir = "data/FINAL/1C_0910"
names = []
QUESTION_ENDINGS = r"(?:하시오|설명하시오|서술하시오|쓰시오|논하시오|기술하시오|약술하시오)\."
PUNCT_BEFORE = r'[\.\"”\'’\)\]\}〉》」』>]'

def extract_qna(contents):
    """
    contents: {
        'page_contents': str,
        'page': int,
        'add_info': list   # 없으면 자동 생성
    }
    반환: contents (page_contents에 플레이스홀더 치환, add_info에 QNA 추가)
    """
    raw_text = contents.get('page_contents', '')
    if not raw_text:
        return contents

    # 이미 처리된 페이지면 (플레이스홀더가 있으면) 재처리 방지
    if '{q_' in raw_text:
        return contents

    # add_info 보장
    if 'add_info' not in contents or not isinstance(contents['add_info'], list):
        contents['add_info'] = []

    # 정답 맵 (예: "01 ④")
    answers = dict(re.findall(r'(\d{2})\s*([①②③④])', raw_text))

    # 문제 블록 매칭: 번호(2자리) 시작 ~ 해설 포함, 다음 번호 또는 문서 끝까지
    block_re = re.compile(r'(\d{2}\n.*?해설.*?)(?=\n\d{2}\n|$)', re.S)
    # 옵션 라인 정규식(해설 이전에서만 사용)
    option_line_re = re.compile(r'^[①②③④][^\n]*', re.M)

    out_parts = []
    last_idx = 0
    seq = 0

    for m in block_re.finditer(raw_text):
        seq += 1
        block = m.group(1)
        start, end = m.span(1)

        # 번호
        number_match = re.match(r'\s*(\d{2})', block)
        number = number_match.group(1) if number_match else f"{seq:02d}"

        # 질문/해설 분리(첫 '해설' 기준)
        split_pos = block.find('해설')
        before_expl = block[:split_pos]
        after_expl  = block[split_pos + len('해설'):]

        # ✅ 문제 끝에 붙은 코드(예: 19-1 21-2) 추출
        caption_matches = re.findall(r'(\d+-\d+)', before_expl.splitlines()[-1])
        captions = caption_matches if caption_matches else []

        # before_expl에서 caption 코드 제거
        if captions:
            before_expl = re.sub(r'(?:\d+-\d+\s*)+$', '', before_expl.strip())   

        # 옵션 추출: 해설 이전에서만 (줄 단위)
        raw_options = option_line_re.findall(before_expl)

        # 번호 뒤 공백 1칸 강제
        options = [re.sub(r'^([①②③④])\s*', r'\1 ', opt.strip())
                   for opt in raw_options]

        # 4개 초과 시 5번째 이후는 합치기
        if len(options) > 4:
            merged = "\n".join(options[4:])
            options = options[:4] + [merged]

        # 질문 텍스트 만들기: 번호 줄/옵션 줄 제거
        # 1) 번호줄 제거
        question_part = re.sub(r'^\s*\d{2}\s*\n', '', before_expl, count=1, flags=re.M)
        # 2) 옵션 줄 제거
        question_part = option_line_re.sub('', question_part)
        # 3) 공백 줄 정리
        question_text = "\n".join([ln for ln in question_part.splitlines() if ln.strip()])

        # 해설: 끝에 "nn ①" 패턴 있으면 제거(맨 끝에서만)
        explanation = after_expl.strip()
        # ✅ 해설 끝에 "01 ④ 02 ③" 처럼 2~3개 연속 정답이 있으면 한 번에 제거
        explanation = re.sub(r'(?:\s*\d{2}\s*[①②③④]){1,3}\s*$', '', explanation)
        # ✅ 해설 안의 ①②③④ 뒤에도 공백을 강제
        explanation = re.sub(r'([①②③④])(?!\s)', r'\1 ', explanation)

        # 정답
        answer = answers.get(number, "")

        # add_info 항목 생성
        tag = f"q_{contents['page']:04}_{seq:04}"
        contents['add_info'].append({
            'tag': tag,
            'type': "question",
            'description': {
                'number': number,
                'question': question_text,
                'options': options,
                'answer': answer,
                'explanation': explanation
            },
            'caption': captions,
            'file_path': 0,
            'bbox': 0
        })

        # 출력 텍스트 재조립: 블록 대신 플레이스홀더
        out_parts.append(raw_text[last_idx:start])
        out_parts.append("{"+tag+"}")
        last_idx = end

    # 남은 꼬리 붙이기
    out_parts.append(raw_text[last_idx:])
    contents['page_contents'] = "".join(out_parts)

    return contents
def _extract_number(line: str) -> str:
    """
    첫 줄에서 문제번호(숫자)만 추출. 없으면 빈 문자열 반환.
    예) '01 ...', '1) ...', '1. ...' 모두 지원.
    """
    m = NUM_RE.match(line or "")
    return (m.group(1).zfill(2)) if m else ""
def _split_by_answer_keyword(text: str) -> (str, str):
    """
    '모범답안' 기준으로 질문/답변 분리.
    - 첫 번째 '모범답안' 이전 = 질문 영역
    - 이후 전체 = 답변 영역 (선행 개행/공백 제거)
    - '모범답안'이 없으면: 질문=전체, 답변=""
    """
    parts = text.split("모범답안")
    if len(parts) == 1:
        return text.strip(), ""
    question_part, answer_part = parts[0], parts[1]
    # '모범답안' 다음에 남은 개행/공백/콜론 등을 정리
    # answer_part = answer_part.lstrip("\n\r :\t")
    return question_part.strip(), answer_part.strip()
def transform_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 페이지 dict를 목표 스키마로 변환
    입력 예:
      {
        "page": "0020",
        "chapter": "...",
        "page_contents": "...",
        "add_info": [...]
      }
    출력: 문제 1개 기준의 변환 구조
    """
    page = item.get("page", "").strip()
    chapter = item.get("chapter", "")
    raw = item.get("page_contents", "") or ""
    add_info = item.get("add_info", "")

    # 질문/답변 분리
    question_block, answer_block = _split_by_answer_keyword(raw)
    if ('{q' in raw) or (raw == "") or ('더 알아보기' in raw):
        return item
    else:
        # 질문문(첫 줄)과 문제번호 추출
        first_line = (question_block.splitlines() or [""])[0]
        number = _extract_number(first_line) or ""
        # 질문문은 "첫 줄에서 번호 제거한 나머지"로 구성
        question_text = question_block
        # 번호가 앞에 있으면 제거
        if number:
            # 맨 앞 숫자/구분문자 제거
            question_text = NUM_RE.sub("", question_text, count=1).strip()

        tag = f"q_{page}_0001"

        add_info.append({
                    "tag": tag,
                    "type": "question",
                    "description": {
                        "number": number,
                        "question": question_text,
                        "options": None,
                        "answer": answer_block,
                        "explanation": ""
                    },
                    "caption": [],
                    "file_path": None,
                    "bbox": None
                })

        return {
            "page": page,
            "chapter": chapter,
            "page_contents": "{" + tag + "}",
            "add_info": add_info
        }
def transform_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    여러 페이지를 일괄 변환.
    각 페이지당 1문항으로 가정하여 {q_<page>_0001} 형태로 변환.
    """
    return [transform_item(it) for it in items]
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

__all__ = ['PUNCT_BEFORE', 'QUESTION_ENDINGS', '_extract_number', '_split_by_answer_keyword', 'base_dir', 'build_big_text', 'clean_markers', 'convert_page_record', 'extract_qas_to_add_info', 'extract_qna', 'last_page_before', 'names', 'transform_item', 'transform_list']
