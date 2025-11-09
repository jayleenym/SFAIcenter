# Tools Arrange - 정리된 도구 모음

이 폴더는 `tools` 폴더의 코드들을 기능별로 정리하고 Class 기반으로 리팩토링한 구조입니다.

## 🚀 주요 개선사항

- **Class 기반 구조**: 모든 기능을 Class로 리팩토링하여 재사용성 향상
- **통합 파이프라인**: 하나의 메인 코드로 전체 프로세스 실행 가능
- **모듈화**: 비슷한 기능들을 통합하여 코드 중복 제거
- **확장성**: 새로운 기능 추가가 용이한 구조

## 📁 폴더 구조

```
tools_arrange/
├── core/                    # 핵심 유틸리티 및 공통 기능
│   ├── ProcessFiles.py     # Excel 데이터 처리, 파일 리스트 관리
│   ├── ProcessLv2.py       # JSON 데이터 포맷 변경, 텍스트 처리 유틸리티
│   └── QueryModels.py      # LLM 모델 쿼리 (OpenRouter, vLLM)
│
├── data_processing/         # 데이터 처리 및 정제
│   ├── cleanup_empty_pages.py  # JSON 파일에서 빈 페이지 제거
│   └── epubstats.py           # EPUB/PDF 통계 처리
│
├── qna/                     # Q&A 관련 처리
│   ├── extraction/         # Q&A 추출
│   │   ├── qna_extract.py      # Q&A 추출 메인 함수
│   │   └── ProcessQnA.py       # Q&A 도메인 분류
│   │
│   ├── processing/         # Q&A 처리 및 변환
│   │   ├── process_additional_tags.py  # 추가 태그 처리
│   │   ├── reclassify_qna_types.py     # Q&A 타입 재분류
│   │   └── verify_reclassification.py  # 재분류 검증
│   │
│   └── analysis/           # Q&A 분석
│       ├── analyze_additional_tags_grouped.py  # 추가 태그 분석
│       ├── analyze_qna_statistics.py           # Q&A 통계 분석
│       ├── check_real_duplicates.py            # 중복 검사
│       └── find_invalid_options.py              # 유효하지 않은 선지 찾기
│
└── evaluation/             # 평가 관련
    ├── multiple_eval_by_model.py      # LLM 평가 시스템 (O, X 문제 포함)
    ├── qna_subdomain_classifier.py    # Q&A 서브도메인 분류기
    ├── fill_multiple_choice_data.py   # 객관식 데이터 채우기
    ├── workbook_groupby_qtype.py       # 문제 타입별 그룹화
    ├── README_multiple_eval_by_model.md
    └── README_subdomain_classifier.md
```

## 📋 각 모듈 설명

### 🔧 core/ - 핵심 유틸리티

**ProcessFiles.py**
- Excel 데이터 읽기 및 병합
- 파일 리스트 관리
- 사이클별 데이터 경로 관리

**ProcessLv2.py**
- JSON 데이터 포맷 변경
- 텍스트 처리 유틸리티 (엔터 제거, 옵션 추출 등)
- 챕터 정보 채우기
- 문단 병합 처리

**QueryModels.py**
- OpenRouter API를 통한 LLM 쿼리
- vLLM을 통한 로컬 모델 쿼리
- 설정 파일 관리

### 📊 data_processing/ - 데이터 처리

**cleanup_empty_pages.py**
- JSON 파일에서 빈 페이지 제거
- 백업 파일 생성
- 통계 정보 제공

**epubstats.py**
- EPUB을 PDF로 변환
- PDF 페이지 수 확인
- Excel 파일에 통계 저장

### ❓ qna/ - Q&A 처리

#### extraction/ - 추출
- **qna_extract.py**: JSON 파일에서 Q&A 추출
- **ProcessQnA.py**: Q&A 도메인 분류 (금융기초/금융실무)

#### processing/ - 처리
- **process_additional_tags.py**: 추가 태그 처리 및 데이터 채우기
- **reclassify_qna_types.py**: Q&A 타입 재분류 (multiple-choice/short-answer/essay)
- **verify_reclassification.py**: 재분류 결과 검증

#### analysis/ - 분석
- **analyze_additional_tags_grouped.py**: 추가 태그 그룹 분석
- **analyze_qna_statistics.py**: Q&A 통계 분석 (도메인별, 타입별)
- **check_real_duplicates.py**: 중복 Q&A 검사
- **find_invalid_options.py**: 유효하지 않은 선지 찾기

### 📈 evaluation/ - 평가

**multiple_eval_by_model.py**
- LLM을 사용한 객관식 문제 평가
- O, X 문제 지원
- 태그 대치 기능
- 모델별 정확도 분석

**qna_subdomain_classifier.py**
- Q&A 서브도메인 자동 분류
- 50문제 단위 배치 처리
- 도메인별 결과 저장

**fill_multiple_choice_data.py**
- 객관식 데이터에 서브도메인 정보 채우기
- file_id와 tag 기준 매칭

**workbook_groupby_qtype.py**
- 문제 타입별 그룹화 (multiple-choice/short-answer/essay)
- 필터링 및 정제

## 🔄 사용 흐름

### 1. 데이터 준비
```
core/ProcessFiles.py → Excel 데이터 읽기
core/ProcessLv2.py → JSON 포맷 변경
data_processing/cleanup_empty_pages.py → 빈 페이지 제거
```

### 2. Q&A 추출 및 분류
```
qna/extraction/qna_extract.py → Q&A 추출
qna/extraction/ProcessQnA.py → 도메인 분류
qna/processing/process_additional_tags.py → 태그 처리
qna/processing/reclassify_qna_types.py → 타입 재분류
```

### 3. Q&A 분석
```
qna/analysis/analyze_qna_statistics.py → 통계 분석
qna/analysis/check_real_duplicates.py → 중복 검사
qna/analysis/find_invalid_options.py → 유효성 검사
```

### 4. 평가
```
evaluation/workbook_groupby_qtype.py → 타입별 그룹화
evaluation/qna_subdomain_classifier.py → 서브도메인 분류
evaluation/fill_multiple_choice_data.py → 데이터 채우기
evaluation/multiple_eval_by_model.py → LLM 평가
```

## 🎯 사용 방법

### 메인 파이프라인 실행

```bash
# 전체 파이프라인 실행 (Cycle 1)
python tools_arrange/main_pipeline.py --cycle 1

# 특정 단계만 실행
python tools_arrange/main_pipeline.py --cycle 1 --steps cleanup extract

# 커스텀 경로 지정
python tools_arrange/main_pipeline.py --cycle 1 --base_path /path/to/data
```

### 개별 클래스 사용

```python
from tools_arrange.core import FileManager, TextProcessor, JSONHandler, LLMQuery
from tools_arrange.data_processing import JSONCleaner
from tools_arrange.qna import QnAExtractor, TagProcessor

# 파일 관리
file_manager = FileManager()
json_files = file_manager.get_filelist(cycle=1)

# JSON 정리
cleaner = JSONCleaner()
result = cleaner.cleanup_directory(Path('/path/to/json/files'))

# Q&A 추출
extractor = QnAExtractor(file_manager)
result = extractor.extract_from_file('/path/to/file.json', '/path/to/output.json')

# 태그 처리
tag_processor = TagProcessor()
tags_added, tags_empty, tags_found = tag_processor.fix_missing_tags(qna_data, source_data)

# LLM 쿼리
llm = LLMQuery()
response = llm.query_openrouter(system_prompt, user_prompt, model_name='openai/gpt-5')
```

## 📋 클래스 구조

### core/ - 핵심 유틸리티
- **FileManager**: 파일 및 경로 관리, Excel 데이터 처리
- **TextProcessor**: 텍스트 처리 (정규식, 태그 추출, 문단 병합 등)
- **JSONHandler**: JSON 파일 읽기/쓰기, 포맷 변경
- **LLMQuery**: LLM 쿼리 (OpenRouter, vLLM 지원)

### data_processing/ - 데이터 처리
- **JSONCleaner**: JSON 파일에서 빈 페이지 제거

### qna/ - Q&A 처리
- **QnAExtractor**: Q&A 추출 및 태그 처리
- **TagProcessor**: 추가 태그 처리 및 데이터 채우기
- **QnATypeClassifier**: Q&A 타입 분류 (multiple-choice/short-answer/essay)

## 📝 참고사항

- 각 클래스는 독립적으로 사용 가능하지만, 일부 클래스는 다른 클래스에 의존할 수 있습니다.
- `LLMQuery`는 LLM 관련 기능을 제공하므로 여러 모듈에서 공통으로 사용됩니다.
- 경로 설정은 `FileManager`에서 관리되며, OneDrive 경로를 기본으로 사용합니다.
- 메인 파이프라인은 전체 프로세스를 순차적으로 실행합니다.

## 🔗 원본 위치

이 파일들은 원래 `tools/` 폴더에 있었으며, 기능별로 재구성하고 Class 기반으로 리팩토링하여 `tools_arrange/` 폴더에 정리되었습니다.

