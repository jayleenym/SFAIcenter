# 신체손해사정사
import re, os, json
from typing import List, Dict, Any

NUM_RE = re.compile(r"^\s*(\d{1,3})[.)]?\s*")

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

# def transform_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """
#     여러 페이지를 일괄 변환.
#     각 페이지당 1문항으로 가정하여 {q_<page>_0001} 형태로 변환.
#     """
#     return [transform_item(it) for it in items]


def main(INPUT_PATH) -> None:
    BACKUP_PATH = INPUT_PATH + ".bak"
    
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(INPUT_PATH)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    contents: List[Dict[str, Any]] = data.get("contents", [])
    data["contents"] = transform_item(contents)

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)