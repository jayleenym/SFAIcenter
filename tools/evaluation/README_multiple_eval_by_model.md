# LLM 평가 시스템

O, X 문제를 포함한 객관식 문제 평가를 위한 통합 시스템입니다.

## 주요 기능

- **O, X 문제 지원**: O, X 형태의 문제도 정확하게 처리
- **태그 대치 지원**: `{f_0000_0000}` 형태의 태그를 실제 내용으로 대치
- **진행상황 표시**: 실시간 진행바와 상세한 로깅
- **에러 핸들링**: API 호출 실패 시 자동 재시도
- **데이터 품질 검사**: 빈 문제, 중복 문제 등 자동 감지
- **상세한 결과 분석**: 모델별 정확도, O/X 문제 vs 일반 객관식 비교
- **다양한 출력 형식**: Excel, CSV 로그 파일

## 설치 요구사항

```bash
pip install pandas numpy tqdm openpyxl
```

## 사용법

### 기본 사용법

```bash
python tools/evaluation/llm_evaluation_system.py --data_path /path/to/your/data --sample_size 100
```

### O, X 문제 지원 활성화

```bash
python tools/evaluation/llm_evaluation_system.py --data_path /path/to/your/data --sample_size 100 --use_ox_support
```

### 태그 대치 비활성화

```bash
python tools/evaluation/llm_evaluation_system.py --data_path /path/to/your/data --sample_size 100 --no_tag_replacement
```

### 모든 옵션 사용

```bash
python tools/evaluation/llm_evaluation_system.py \
    --data_path /path/to/your/data \
    --sample_size 200 \
    --batch_size 20 \
    --models anthropic/claude-sonnet-4.5 google/gemini-2.5-flash \
    --use_ox_support \
    --seed 123
```

## 명령행 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--data_path` | 데이터 디렉토리 경로 | 필수 |
| `--sample_size` | 샘플 크기 | 100 |
| `--batch_size` | 배치 크기 | 10 |
| `--models` | 평가할 모델 목록 | ['anthropic/claude-sonnet-4.5'] |
| `--use_ox_support` | O, X 문제 지원 활성화 | False |
| `--apply_tag_replacement` | 태그 대치 적용 (기본값: True) | True |
| `--no_tag_replacement` | 태그 대치 비활성화 | False |
| `--seed` | 랜덤 시드 (기본값: 42) | 42 |

## 출력 파일

### Excel 파일
- `evaluation_results_YYYY-MM-DD_HHMMSS.xlsx`
  - `전체데이터`: 모든 문제 데이터
  - `모델별예측`: 모델별 예측 결과 (와이드 포맷)
  - `정확도`: 모델별 정확도 요약

### CSV 로그 파일
- `evaluation_predictions_YYYY-MM-DD_HHMMSS.csv`: 상세 예측 로그
- `evaluation_model_stats_YYYY-MM-DD_HHMMSS.csv`: 모델별 통계

### 로그 파일
- `evaluation.log`: 상세 실행 로그

## 데이터 형식

입력 데이터는 다음 형식의 JSON 파일들이어야 합니다:

```json
[
  {
    "file_id": "SS0001",
    "qna_type": "multiple-choice",
    "qna_data": {
      "tag": "q_0001_0001",
      "type": "question",
      "description": {
        "number": "1",
        "question": "문제 내용",
        "options": ["선지1", "선지2", "선지3", "선지4", "선지5"],
        "answer": "①",
        "explanation": "해설"
      }
    },
    "additional_tags_found": ["{f_0001_0001}"],
    "additional_tag_data": [
      {
        "tag": "{f_0001_0001}",
        "data": {
          "content": "실제 수식 내용"
        }
      }
    ]
  }
]
```

## O, X 문제 지원

O, X 문제는 다음과 같이 처리됩니다:

- **자동 감지**: 선지가 2개 이하이고 O/X 형태인 경우 자동으로 O, X 문제로 인식
- **정답 변환**: O → 1번, X → 2번으로 변환
- **별도 분석**: O, X 문제와 일반 객관식 문제의 정확도를 별도로 분석

## 태그 대치 기능

시스템은 자동으로 다음 태그들을 실제 내용으로 대치합니다:

- `{f_0000_0000}`: 수식 태그
- `{tb_0000_0000}`: 표 태그  
- `{note_0000_0000}`: 노트 태그

태그 대치는 `additional_tag_data` 필드의 내용을 사용하여 수행됩니다.

## 예제 실행

```bash
# 기본 실행
python tools/evaluation/llm_evaluation_system.py --data_path ./data/FIN_workbook --sample_size 50

# O, X 문제 포함 실행
python tools/evaluation/llm_evaluation_system.py --data_path ./data/FIN_workbook --sample_size 100 --use_ox_support

# 태그 대치 비활성화
python tools/evaluation/llm_evaluation_system.py --data_path ./data/FIN_workbook --sample_size 50 --no_tag_replacement
```

## 문제 해결

### API 호출 오류
- `tools.Openrouter` 모듈이 필요한 경우, 해당 모듈을 설치
- API 키 설정 확인

### 메모리 부족
- `sample_size`를 줄여서 실행
- `batch_size`를 줄여서 실행

### 데이터 형식 오류
- JSON 파일 형식 확인
- `qna_type`이 "multiple-choice"인지 확인

### 태그 대치 오류
- `additional_tag_data` 필드가 올바르게 설정되어 있는지 확인
- 태그 형식이 `{f_0000_0000}` 형태인지 확인

## 로그 확인

실행 중 상세한 로그는 `evaluation.log` 파일에서 확인할 수 있습니다:

```bash
tail -f evaluation.log
```

## 성능 최적화

- **배치 크기 조정**: `--batch_size` 옵션으로 API 호출 빈도 조절
- **샘플 크기 조정**: `--sample_size` 옵션으로 처리할 문제 수 조절
- **태그 대치 비활성화**: `--no_tag_replacement` 옵션으로 처리 속도 향상

