# Tools Arrange - 정리된 도구 모음

이 폴더는 `tools` 폴더의 코드들을 기능별로 정리하고 Class 기반으로 리팩토링한 구조입니다.

## 🚀 주요 개선사항

- **Class 기반 구조**: 모든 기능을 Class로 리팩토링하여 재사용성 향상
- **통합 파이프라인**: 하나의 메인 코드로 전체 프로세스 실행 가능
- **모듈화**: 비슷한 기능들을 통합하여 코드 중복 제거
- **확장성**: 새로운 기능 추가가 용이한 구조
- **단계별 분리**: 각 파이프라인 단계를 독립적인 모듈로 분리하여 유지보수성 향상

## 📁 폴더 구조

```
tools/
├── main_pipeline.py        # 메인 파이프라인 엔트리 포인트
│
├── pipeline/                # 파이프라인 모듈
│   ├── __init__.py
│   ├── config.py            # 경로 설정 (ONEDRIVE_PATH, PROJECT_ROOT_PATH)
│   ├── base.py               # PipelineBase 기본 클래스
│   ├── main.py               # Pipeline 메인 클래스 (오케스트레이터)
│   └── steps/                # 각 단계별 모듈
│       ├── __init__.py
│       ├── step0_preprocessing.py      # 0단계: 텍스트 전처리
│       ├── step1_extract_basic.py      # 1단계: 기본 문제 추출
│       ├── step2_extract_full.py       # 2단계: 전체 문제 추출 (태그 대치)
│       ├── step3_classify.py           # 3단계: Q&A 타입별 분류
│       ├── step4_domain_subdomain.py   # 4단계: Domain/Subdomain 분류
│       ├── step5_create_exam.py        # 5단계: 시험문제 만들기
│       ├── step6_evaluate.py           # 6단계: 시험지 평가
│       └── step7_transform_multiple_choice.py  # 7단계: 객관식 문제 변형
│
├── core/                    # 핵심 유틸리티 및 공통 기능
│   ├── utils.py            # FileManager, TextProcessor, JSONHandler 클래스
│   ├── llm_query.py        # LLMQuery 클래스 (OpenRouter, vLLM)
│   ├── exam_config.py      # ExamConfig 클래스 (시험 설정 파일 로더)
│   └── README_exam_config.md  # exam_config.json 사용 가이드
│
├── data_processing/         # 데이터 처리 및 정제
│   ├── json_cleaner.py     # JSONCleaner 클래스 (빈 페이지 제거)
│   ├── cleanup_empty_pages.py  # (레거시)
│   └── epubstats.py           # EPUB/PDF 통계 처리
│
├── qna/                     # Q&A 관련 처리
│   ├── qna_processor.py    # QnATypeClassifier, QnAExtractor, TagProcessor 클래스
│   ├── extraction/         # Q&A 추출 (레거시)
│   │   ├── qna_extract.py      # Q&A 추출 메인 함수 (레거시)
│   │   └── process_qna.py      # Q&A 도메인 분류 (레거시)
│   │
│   ├── processing/         # Q&A 처리 및 변환
│   │   ├── answer_type_classifier.py   # AnswerTypeClassifier (right/wrong/abcd 분류)
│   │   ├── qna_subdomain_classifier.py # QnASubdomainClassifier (도메인/서브도메인 분류)
│   │   ├── process_additional_tags.py  # 추가 태그 처리 (레거시)
│   │   ├── reclassify_qna_types.py     # Q&A 타입 재분류 (레거시)
│   │   └── verify_reclassification.py  # 재분류 검증 (레거시)
│   │
│   └── analysis/           # Q&A 분석
│       ├── analyze_additional_tags_grouped.py  # 추가 태그 그룹 분석
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

### 🔄 pipeline/ - 파이프라인 모듈

**config.py** - 경로 설정
- `ONEDRIVE_PATH`: OneDrive 데이터 경로 설정
- `PROJECT_ROOT_PATH`: 프로젝트 루트 경로 설정
- 환경 변수로 오버라이드 가능

**base.py** - 파이프라인 기본 클래스
- `PipelineBase`: 모든 파이프라인 단계의 기본 클래스
- 공통 유틸리티 초기화 (FileManager, TextProcessor, JSONHandler, LLMQuery 등)
- 로깅 설정

**main.py** - 파이프라인 오케스트레이터
- `Pipeline`: 전체 파이프라인을 관리하는 메인 클래스
- 각 단계 인스턴스 생성 및 관리
- `run_full_pipeline()`: 전체 파이프라인 실행

**steps/** - 각 단계별 모듈
- `Step0Preprocessing`: 텍스트 전처리 (문장내 엔터 제거, 빈 챕터정보 채우기, 선지 텍스트 정규화)
- `Step1ExtractBasic`: 기본 문제 추출 (Lv2, Lv3_4)
- `Step2ExtractFull`: 전체 문제 추출 (Lv3, Lv3_4, Lv5) - 태그 대치 포함
- `Step3Classify`: Q&A 타입별 분류 (multiple-choice/short-answer/essay/etc)
- `Step4DomainSubdomain`: Domain/Subdomain 분류 (실패 항목 재처리 포함)
- `Step5CreateExam`: 시험문제 만들기 (exam_config.json 참고)
- `Step6Evaluate`: 시험지 평가 (모델별 답변 평가, 배치 처리, 시험지 경로 설정 가능)
- `Step7TransformMultipleChoice`: 객관식 문제 변형 (right/wrong/abcd 분류 및 변형)

### 🔧 core/ - 핵심 유틸리티

**utils.py** - 통합된 유틸리티 클래스
- `FileManager`: Excel 데이터 읽기 및 병합, 파일 리스트 관리, 사이클별 데이터 경로 관리
- `TextProcessor`: 텍스트 처리 유틸리티 (엔터 제거, 옵션 추출, 챕터 정보 채우기, 문단 병합 등)
- `JSONHandler`: JSON 파일 읽기/쓰기, 포맷 변환

**llm_query.py** - LLM 쿼리 클래스
- `LLMQuery`: OpenRouter API를 통한 LLM 쿼리, vLLM을 통한 로컬 모델 쿼리, 설정 파일 관리

**exam_config.py** - 시험 설정 파일 로더
- `ExamConfig`: exam_config.json 파일을 로드하고 기존 코드와의 호환성을 제공
- `get_exam_statistics()`: exam_statistics.json 형태로 가져오기
- `get_exam_hierarchy()`: exam_hierarchy.json 형태로 가져오기
- `get_domain_subdomain()`: domain_subdomain.json 형태로 가져오기
- 자세한 사용법은 `README_exam_config.md` 참고

### 📊 data_processing/ - 데이터 처리

**json_cleaner.py** - JSON 정리 클래스
- `JSONCleaner`: JSON 파일에서 빈 페이지 제거, 백업 파일 생성, 통계 정보 제공

**epubstats.py**
- EPUB을 PDF로 변환
- PDF 페이지 수 확인
- Excel 파일에 통계 저장

### ❓ qna/ - Q&A 처리

**qna_processor.py** - 통합된 Q&A 처리 클래스
- `QnATypeClassifier`: Q&A 타입 분류 (multiple-choice/short-answer/essay/etc)
- `QnAExtractor`: JSON 파일에서 Q&A 추출 및 태그 처리
- `TagProcessor`: 추가 태그 처리 및 데이터 채우기

#### extraction/ - 추출 (레거시)
- **qna_extract.py**: Q&A 추출 메인 함수 (레거시)
- **process_qna.py**: Q&A 도메인 분류 (레거시)
  - ⚠️ **주의**: 이 파일의 일부 함수는 `qna_processor.py`에 통합되었습니다:
    - `analyze_extracted_qna()` → `QnATypeClassifier.classify_qna_type()`
    - `replace_tags_in_text()`, `replace_tags_in_qna_data()` → `TagProcessor.replace_tags_in_text()`, `TagProcessor.replace_tags_in_qna_data()`

#### processing/ - 처리
- **answer_type_classifier.py**: AnswerTypeClassifier 클래스 - 객관식 문제를 right/wrong/abcd로 분류
- **qna_subdomain_classifier.py**: QnASubdomainClassifier 클래스 - Q&A 도메인/서브도메인 분류
- **process_additional_tags.py**: 추가 태그 처리 (레거시)
- **reclassify_qna_types.py**: Q&A 타입 재분류 (레거시)
- **verify_reclassification.py**: 재분류 결과 검증 (레거시)

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

### 전체 파이프라인 (권장)

```
main_pipeline.py → 전체 프로세스 실행
├── Step 0: 텍스트 전처리 (Lv2)
├── Step 1: 기본 문제 추출 (Lv2, Lv3_4)
├── Step 2: 전체 문제 추출 (Lv3, Lv3_4, Lv5) - 태그 대치
├── Step 3: Q&A 타입별 분류
├── Step 4: Domain/Subdomain 분류 (실패 항목 재처리)
├── Step 5: 시험문제 만들기
├── Step 6: 시험지 평가
└── Step 7: 객관식 문제 변형 (right/wrong/abcd 분류 및 변형)
```

### 개별 단계 실행

#### 1. 데이터 준비
```
pipeline/steps/step0_preprocessing.py → 텍스트 전처리
data_processing/json_cleaner.py → 빈 페이지 제거
```

#### 2. Q&A 추출 및 분류
```
pipeline/steps/step1_extract_basic.py → 기본 문제 추출
pipeline/steps/step2_extract_full.py → 전체 문제 추출 (태그 대치)
pipeline/steps/step3_classify.py → Q&A 타입별 분류
```

#### 3. Domain/Subdomain 분류
```
pipeline/steps/step4_domain_subdomain.py → Domain/Subdomain 분류
  ├── 기존 데이터로 빈칸 채우기
  ├── LLM을 통한 분류
  └── 실패 항목 재처리
```

#### 4. 시험문제 생성 및 평가
```
pipeline/steps/step5_create_exam.py → 시험문제 만들기
pipeline/steps/step6_evaluate.py → 시험지 평가
```

#### 5. 객관식 문제 변형
```
pipeline/steps/step7_transform_multiple_choice.py → 객관식 문제 변형
  ├── AnswerTypeClassifier로 문제 분류 (right/wrong/abcd)
  ├── wrong -> right 변형
  ├── right -> wrong 변형
  └── abcd 변형 (단일정답형 -> 복수정답형)
```

## 🎯 사용 방법

### 메인 파이프라인 실행

```bash
# 전체 파이프라인 실행 (Cycle 1)
python tools/main_pipeline.py --cycle 1

# 특정 단계만 실행
python tools/main_pipeline.py --cycle 1 --steps preprocess extract_basic extract_full

# 4단계: Domain/Subdomain 분류
python tools/main_pipeline.py --steps fill_domain --qna_type multiple --model x-ai/grok-4-fast

# 5단계: 시험문제 만들기
python tools/main_pipeline.py --steps create_exam --num_sets 5

# 6단계: 시험지 평가
python tools/main_pipeline.py --steps evaluate_exams --eval_models anthropic/claude-sonnet-4.5 google/gemini-2.5-flash

# 6단계: 시험지 평가 (1세트만 평가)
python tools/main_pipeline.py --steps evaluate_exams --eval_sets 1

# 6단계: 시험지 평가 (여러 세트 지정: 1, 2, 3세트만 평가)
python tools/main_pipeline.py --steps evaluate_exams --eval_sets 1 2 3

# 6단계: 시험지 평가 (커스텀 시험지 경로 지정)
python tools/main_pipeline.py --steps evaluate_exams --eval_exam_dir /path/to/exam/directory

# 6단계: 시험지 평가 (상대 경로로 시험지 경로 지정)
python tools/main_pipeline.py --steps evaluate_exams --eval_exam_dir evaluation/custom_exam_dir

# 커스텀 경로 지정
python tools/main_pipeline.py --cycle 1 --onedrive_path /path/to/onedrive --project_root_path /path/to/project
```

### main_pipeline.py 명령행 옵션

#### 기본 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--cycle` | 사이클 번호 (1, 2, 3) - 0, 1, 2, 3단계에서만 필요 | None |
| `--steps` | 실행할 단계 목록 (공백으로 구분) | None (전체 실행) |
| | | 가능한 값: `preprocess`, `extract_basic`, `extract_full`, `classify`, `fill_domain`, `create_exam`, `evaluate_exams`, `transform_multiple_choice` |
| `--base_path` | 기본 데이터 경로 | None (ONEDRIVE_PATH 사용) |
| `--config_path` | LLM 설정 파일 경로 | None (PROJECT_ROOT_PATH/llm_config.ini 사용) |
| `--onedrive_path` | OneDrive 경로 | None (자동 감지) |
| `--project_root_path` | 프로젝트 루트 경로 | None (자동 감지) |
| `--debug` | 디버그 로그 활성화 | False |

#### 단계별 옵션

**4단계 (Domain/Subdomain 분류)**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--qna_type` | QnA 타입 (multiple, short, essay) | 'multiple' |
| `--model` | 사용할 모델 | 'x-ai/grok-4-fast' |

**5단계 (시험문제 만들기)**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--num_sets` | 시험 세트 개수 | 5 |

**6단계 (시험지 평가)**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--eval_models` | 평가할 모델 목록 (공백으로 구분) | None (자동 설정) |
| `--eval_batch_size` | 평가 배치 크기 | 10 |
| `--eval_use_ox_support` | O, X 문제 지원 활성화 | True |
| `--eval_use_server_mode` | vLLM 서버 모드 사용 | False |
| `--eval_exam_dir` | 시험지 디렉토리 경로 (단일 JSON 파일 또는 디렉토리) | None (기본 경로 사용) |
| `--eval_sets` | 평가할 세트 번호 (1, 2, 3, 4, 5 중 선택, 공백으로 구분) | None (모든 세트 평가) |

**7단계 (객관식 문제 변형)**
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--transform_classify` | 분류 단계 실행 여부 | False |
| `--transform_classified_data_path` | 이미 분류된 데이터 파일 경로 (--transform_classify가 False일 때, None이면 기본 경로 사용) | None |
| `--transform_input_data_path` | 입력 데이터 파일 경로 (--transform_classify가 True일 때만 사용) | None |
| `--transform_classify_model` | 분류에 사용할 모델 (--transform_classify가 True일 때만 사용) | 'openai/gpt-5' |
| `--transform_classify_batch_size` | 분류 배치 크기 (--transform_classify가 True일 때만 사용) | 10 |
| `--transform_model` | 변형에 사용할 모델 | 'openai/o3' |
| `--transform_wrong_to_right` | wrong -> right 변형 수행 여부 | False |
| `--transform_right_to_wrong` | right -> wrong 변형 수행 여부 | False |
| `--transform_abcd` | abcd 변형 수행 여부 | False |

**참고:**
- `--transform_classify`가 False이고 `--transform_classified_data_path`가 None이면 기본 경로(`evaluation/eval_data/7_multiple_rw/answer_type_classified.json`)를 자동으로 사용합니다.
- 변형 옵션(`--transform_wrong_to_right`, `--transform_right_to_wrong`, `--transform_abcd`)은 기본값이 False이므로, 원하는 변형을 명시적으로 활성화해야 합니다.

#### 실행 가능한 단계 목록

`--steps` 옵션에 사용할 수 있는 단계 이름:
- `preprocess`: 0단계 - 텍스트 전처리
- `extract_basic`: 1단계 - 기본 문제 추출
- `extract_full`: 2단계 - 전체 문제 추출 (태그 대치)
- `classify`: 3단계 - Q&A 타입별 분류
- `fill_domain`: 4단계 - Domain/Subdomain 분류
- `create_exam`: 5단계 - 시험문제 만들기
- `evaluate_exams`: 6단계 - 시험지 평가
- `transform_multiple_choice`: 7단계 - 객관식 문제 변형

#### 사용 예제

```bash
# 전체 파이프라인 실행 (Cycle 1)
python tools/main_pipeline.py --cycle 1

# 특정 단계만 실행
python tools/main_pipeline.py --cycle 1 --steps preprocess extract_basic

# 4단계만 실행 (객관식 문제, 특정 모델 사용)
python tools/main_pipeline.py --steps fill_domain --qna_type multiple --model openai/gpt-5

# 5단계만 실행 (3세트 생성)
python tools/main_pipeline.py --steps create_exam --num_sets 3

# 6단계만 실행 (특정 모델들로 평가)
python tools/main_pipeline.py --steps evaluate_exams --eval_models openai/gpt-5 google/gemini-2.5-pro

# 6단계만 실행 (1세트만 평가, 배치 크기 20)
python tools/main_pipeline.py --steps evaluate_exams --eval_sets 1 --eval_batch_size 20

# 6단계만 실행 (여러 세트 지정: 1, 2, 3세트만 평가)
python tools/main_pipeline.py --steps evaluate_exams --eval_sets 1 2 3

# 6단계만 실행 (커스텀 시험지 경로 지정)
python tools/main_pipeline.py --steps evaluate_exams --eval_exam_dir /path/to/exam/directory

# 6단계만 실행 (단일 JSON 파일 평가)
python tools/main_pipeline.py --steps evaluate_exams --eval_exam_dir /path/to/exam.json

# 6단계만 실행 (vLLM 서버 모드 사용)
python tools/main_pipeline.py --steps evaluate_exams --eval_use_server_mode

# 7단계만 실행 (기본 경로의 answer_type_classified.json 사용)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_wrong_to_right

# 7단계만 실행 (분류 단계 포함)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_classify --transform_input_data_path /path/to/data.json --transform_wrong_to_right

# 7단계만 실행 (특정 분류된 파일 사용)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_classified_data_path /path/to/classified.json --transform_wrong_to_right

# 7단계만 실행 (여러 변형 수행)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_wrong_to_right --transform_right_to_wrong --transform_abcd

# 디버그 모드로 실행
python tools/main_pipeline.py --cycle 1 --debug
```

### 파이프라인 모듈 직접 사용

```python
from pipeline import Pipeline

# 파이프라인 생성
pipeline = Pipeline(
    onedrive_path="/path/to/onedrive",
    project_root_path="/path/to/project"
)

# 전체 파이프라인 실행
results = pipeline.run_full_pipeline(
    cycle=1,
    steps=['preprocess', 'extract_basic', 'extract_full', 'classify']
)

# 6단계만 실행 (시험지 경로 지정)
results = pipeline.run_full_pipeline(
    steps=['evaluate_exams'],
    eval_exam_dir="/path/to/exam/directory"
)

# 6단계만 실행 (1세트만 평가)
results = pipeline.run_full_pipeline(
    steps=['evaluate_exams'],
    eval_sets=[1]
)

# 6단계만 실행 (여러 세트 지정: 1, 2, 3세트만 평가)
results = pipeline.run_full_pipeline(
    steps=['evaluate_exams'],
    eval_sets=[1, 2, 3]
)

# 개별 단계 실행
result = pipeline.step0.execute(cycle=1)
result = pipeline.step4.execute(qna_type='multiple', model='x-ai/grok-4-fast')
result = pipeline.step5.execute(num_sets=5)
result = pipeline.step6.execute(exam_dir="/path/to/exam/directory")  # 시험지 경로 지정
result = pipeline.step6.execute(sets=[1])  # 1세트만 평가
result = pipeline.step6.execute(sets=[1, 2, 3])  # 1, 2, 3세트만 평가
result = pipeline.step7.execute(
    classified_data_path="/path/to/classified.json",  # 또는 None (기본 경로 사용)
    run_classify=False,  # True면 분류 단계 실행
    transform_model='openai/o3',
    transform_wrong_to_right=True
)  # 7단계: 객관식 문제 변형

# 분류 단계 포함 실행
result = pipeline.step7.execute(
    input_data_path="/path/to/data.json",
    run_classify=True,
    classify_model='openai/gpt-5',
    transform_model='openai/o3',
    transform_wrong_to_right=True
)  # 7단계: 객관식 문제 변형 (분류 포함)
```

### 개별 클래스 사용

```python
from core import FileManager, TextProcessor, JSONHandler, LLMQuery, ExamConfig
from data_processing import JSONCleaner
from qna import QnAExtractor, TagProcessor
from qna.processing import AnswerTypeClassifier, QnASubdomainClassifier

# 파일 관리
file_manager = FileManager()
json_files = file_manager.get_json_file_list(cycle=1)
excel_data = file_manager.load_excel_metadata(cycle=1)

# JSON 정리
cleaner = JSONCleaner()
result = cleaner.cleanup_directory(Path('/path/to/json/files'))

# Q&A 추출
extractor = QnAExtractor(file_manager)
result = extractor.extract_from_file('/path/to/file.json', '/path/to/output.json')

# 태그 처리
tag_processor = TagProcessor()
tags_added, tags_empty, tags_found = tag_processor.add_missing_tags(qna_data, source_data)
filled_count, total_empty = tag_processor.fill_empty_tag_data(qna_data, source_data)

# LLM 쿼리
llm = LLMQuery()
response = llm.query_openrouter(system_prompt, user_prompt, model_name='openai/gpt-5')

# 시험 설정 로드
config = ExamConfig()
stats = config.get_exam_statistics()
hierarchy = config.get_exam_hierarchy()
domain_subdomain = config.get_domain_subdomain()

# Answer Type 분류
classifier = AnswerTypeClassifier()
classified = classifier.classify_questions(questions, model='openai/gpt-5')

# 도메인/서브도메인 분류
subdomain_classifier = QnASubdomainClassifier(mode='multiple')
classified = subdomain_classifier.classify_questions(questions, model='x-ai/grok-4-fast')
```
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
read_file

## 📋 클래스 구조

### core/ - 핵심 유틸리티
- **FileManager**: 파일 및 경로 관리, Excel 메타데이터 로드, 파일 리스트 관리
  - `load_excel_metadata()`: Excel에서 도서 메타데이터 읽기
  - `get_json_file_list()`: JSON 파일 리스트 가져오기
  - `organize_files_by_level()`: 레벨별 파일 분류 및 이동
- **TextProcessor**: 텍스트 처리 유틸리티
  - `remove_inline_newlines()`: 문장 내 엔터 제거
  - `split_text_with_newline_removal()`: 엔터 제거 후 텍스트 분리 (remove_inline_newlines 재사용)
  - `extract_choice_options()`: 선택지(①~⑤) 추출
  - `normalize_option_text()`: 선지 텍스트 정규화
  - `convert_to_circle_number()`: 숫자를 원형 숫자로 변환
  - `fill_missing_chapters()`: 빈 챕터 정보 채우기
  - `merge_broken_paragraphs()`: 끊어진 문단 병합
- **JSONHandler**: JSON 파일 읽기/쓰기, 포맷 변환
  - `load()`: JSON 파일 로드
  - `save()`: JSON 파일 저장
  - `convert_json_format()`: JSON 데이터 구조 변환
- **LLMQuery**: LLM 쿼리 (OpenRouter, vLLM 지원)
  - `query_openrouter()`: OpenRouter API 쿼리
  - `load_vllm_model()`: vLLM 모델 로드
  - `query_vllm()`: vLLM 모델 쿼리
- **ExamConfig**: 시험 설정 파일 로더
  - `get_exam_statistics()`: exam_statistics.json 형태로 가져오기
  - `get_exam_hierarchy()`: exam_hierarchy.json 형태로 가져오기
  - `get_domain_subdomain()`: domain_subdomain.json 형태로 가져오기
  - `get_exam_domains()`: 특정 시험의 도메인 리스트 가져오기
  - `get_domain_info()`: 특정 도메인 정보 가져오기
  - `get_subdomain_count()`: 서브도메인 문제 개수 가져오기
  - `get_subdomain_description()`: 서브도메인 설명 가져오기

### data_processing/ - 데이터 처리
- **JSONCleaner**: JSON 파일에서 빈 페이지 제거

### qna/ - Q&A 처리
- **QnAExtractor**: Q&A 추출 및 태그 처리
  - `extract_qna_from_json()`: JSON 데이터에서 Q&A 추출
  - `extract_from_file()`: 파일에서 Q&A 추출
- **TagProcessor**: 추가 태그 처리 및 데이터 채우기
  - `extract_tags_from_qna_content()`: Q&A 내용에서 태그 추출
  - `extract_page_from_tag()`: 태그에서 페이지 번호 추출
  - `find_tag_data_in_add_info()`: add_info에서 태그 데이터 찾기
  - `add_missing_tags()`: 누락된 태그 추가
  - `fill_empty_tag_data()`: 빈 태그 데이터 채우기
- **QnATypeClassifier**: Q&A 타입 분류
  - `classify_qna_type()`: Q&A 타입 분류 (multiple-choice/short-answer/essay/etc)
- **AnswerTypeClassifier**: 객관식 문제 Answer Type 분류 (qna/processing/)
  - `classify_questions()`: 객관식 문제를 right/wrong/abcd로 분류
- **QnASubdomainClassifier**: Q&A 도메인/서브도메인 분류 (qna/processing/)
  - `classify_questions()`: Q&A 도메인/서브도메인 분류

## 📝 참고사항

### 파이프라인 구조
- **모듈화**: 각 단계가 독립적인 파일로 분리되어 유지보수가 용이합니다.
- **재사용성**: 각 단계 클래스를 독립적으로 사용할 수 있습니다.
- **확장성**: 새로운 단계를 추가하려면 `pipeline/steps/`에 새 파일을 추가하면 됩니다.

### 경로 설정
- 경로 설정은 `pipeline/config.py`에서 중앙 관리됩니다.
- `ONEDRIVE_PATH`와 `PROJECT_ROOT_PATH`만 수정하면 모든 경로가 자동으로 설정됩니다.
- 환경 변수로 오버라이드 가능: `export ONEDRIVE_PATH=/path/to/onedrive`

### 의존성
- 각 클래스는 독립적으로 사용 가능하지만, 일부 클래스는 다른 클래스에 의존할 수 있습니다.
- `LLMQuery`는 LLM 관련 기능을 제공하므로 여러 모듈에서 공통으로 사용됩니다.
- `PipelineBase`는 모든 단계 클래스의 기본 클래스입니다.

### 실패 항목 재처리
- 4단계(Domain/Subdomain 분류)에서 실패한 항목은 자동으로 감지되어 재처리됩니다.
- 실패 항목은 `evaluation/eval_data/2_subdomain/{qna_type}_failed_items.json`에 저장됩니다.

### API 키 설정

**6단계 (시험지 평가)**
- 6단계에서 OpenRouter API를 사용할 때는 `llm_config.ini`의 `key_evaluate`를 사용합니다.
- `key_evaluate`가 설정 파일에 없으면 에러가 발생합니다.
- vLLM 서버 모드(`--eval_use_server_mode`)를 사용할 때는 API 키가 필요 없습니다.

**7단계 (객관식 문제 변형)**
- 7단계는 `AnswerTypeClassifier`를 사용하여 문제를 분류하고, LLM을 사용하여 문제를 변형합니다.
- `--transform_classify` 옵션을 사용하여 분류 단계를 실행할 수 있습니다 (기본값: False).
- `--transform_classify`가 False일 때:
  - `--transform_classified_data_path`를 지정하면 해당 파일을 사용합니다.
  - `--transform_classified_data_path`가 None이면 기본 경로(`evaluation/eval_data/7_multiple_rw/answer_type_classified.json`)를 자동으로 사용합니다.
- 분류 단계와 변형 단계에서 서로 다른 모델을 사용할 수 있습니다 (기본값: `openai/gpt-5`로 분류, `openai/o3`로 변형).
- 변형 옵션: `wrong -> right`, `right -> wrong`, `abcd` 변형을 개별적으로 활성화/비활성화할 수 있습니다 (기본값: 모두 False).

