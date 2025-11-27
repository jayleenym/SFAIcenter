# Tools Arrange - 정리된 도구 모음

이 폴더는 `tools` 폴더의 코드들을 기능별로 정리하고 Class 기반으로 리팩토링한 구조입니다.

## 🚀 주요 개선사항

- **Class 기반 구조**: 모든 기능을 Class로 리팩토링하여 재사용성 향상
- **통합 파이프라인**: 하나의 메인 코드로 전체 프로세스 실행 가능
- **모듈화**: 비슷한 기능들을 통합하여 코드 중복 제거
- **확장성**: 새로운 기능 추가가 용이한 구조
- **단계별 분리**: 각 파이프라인 단계를 독립적인 모듈로 분리하여 유지보수성 향상
- **플랫폼 독립적 경로**: Windows와 macOS에서 자동으로 올바른 경로를 감지하고 사용
- **경로 자동화**: 하드코딩된 경로를 제거하고 플랫폼별 자동 감지 기능 추가
- **코드 간소화**: 변형 로직, 검증 로직 등을 별도 모듈로 분리하여 각 step 파일 간소화

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
│       ├── step1_extract_qna_w_domain.py # 1단계(통합): Q&A 추출 및 Domain 분류
│       ├── step5_create_exam.py        # 5단계: 시험문제 만들기
│       ├── step6_evaluate.py           # 6단계: 시험지 평가
│       ├── step7_transform_multiple_choice.py  # 7단계: 객관식 문제 변형
│       ├── step8_create_transformed_exam.py    # 8단계: 변형 문제를 포함한 시험지 생성
│       └── step9_multiple_essay.py             # 9단계: 객관식 문제를 서술형 문제로 변환
│
├── statistics/              # 통계 저장 및 집계
│   ├── __init__.py
│   └── statistics_saver.py   # StatisticsSaver 클래스 (통계 저장/집계/로깅)
│
├── transformed/             # 문제 변형 관련 기능
│   ├── __init__.py
│   ├── transform_multiple_choice.py    # MultipleChoiceTransformer 클래스 (객관식 변형)
│   ├── load_transformed_questions.py    # 변형된 문제 로드 유틸리티
│   ├── create_transformed_exam.py      # 변형된 시험지 생성 유틸리티
│   ├── essay_filter_full_explanation.py    # 1단계: 해설이 많은 문제 선별
│   ├── essay_classify_by_exam.py          # 2단계: 서술형 문제 시험별 분류
│   ├── essay_change_question_to_essay.py  # 3단계: 서술형 문제로 변환
│   ├── essay_extract_keywords.py          # 4단계: 키워드 추출
│   ├── essay_create_best_answers.py       # 5단계: 모범답안 생성
│   └── essay_create_model_answers.py      # 모델 답변 생성
│
├── exam/                    # 시험지 생성 및 검증
│   ├── __init__.py
│   └── exam_validator.py    # ExamValidator 클래스 (시험지 검증/업데이트)
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
│   ├── formatting.py       # Q&A 데이터 포맷화 유틸리티
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
    ├── evaluate_essay_model.py      # 서술형 문제 평가 시스템
    ├── essay_utils.py               # 서술형 평가 유틸리티 (모범답안 로드, API 키 설정)
    ├── multiple_eval_by_model.py    # LLM 평가 시스템 (O, X 문제 포함)
    ├── qna_subdomain_classifier.py  # Q&A 서브도메인 분류기
    ├── fill_multiple_choice_data.py # 객관식 데이터 채우기
    ├── workbook_groupby_qtype.py    # 문제 타입별 그룹화
    ├── README_multiple_eval_by_model.md
    └── README_subdomain_classifier.md
```

## 📋 각 모듈 설명

### 🔄 pipeline/ - 파이프라인 모듈

**config.py** - 경로 설정

- `ONEDRIVE_PATH`: OneDrive 데이터 경로 설정 (플랫폼별 자동 감지)
- `PROJECT_ROOT_PATH`: 프로젝트 루트 경로 설정 (자동 감지)
- `SFAICENTER_PATH`: SFAICenter 디렉토리 경로 (자동 감지)
- `_find_onedrive_path()`: 플랫폼별 OneDrive 경로 자동 감지 함수
- 환경 변수로 오버라이드 가능 (`ONEDRIVE_PATH`, `PROJECT_ROOT_PATH`, `SFAICENTER_PATH`)

**base.py** - 파이프라인 기본 클래스

- `PipelineBase`: 모든 파이프라인 단계의 기본 클래스
- 공통 유틸리티 초기화 (FileManager, TextProcessor, JSONHandler, LLMQuery 등)
- 공통 로깅 메서드 (`_setup_step_logging`, `_remove_step_logging`)

**main.py** - 파이프라인 오케스트레이터

- `Pipeline`: 전체 파이프라인을 관리하는 메인 클래스
- 각 단계 인스턴스 생성 및 관리
- `run_full_pipeline()`: 전체 파이프라인 실행

**steps/** - 각 단계별 모듈

- `Step1ExtractQnAWDomain`: Q&A 추출 및 Domain 분류 (통합)
  - 기존 Step 2, 3, 4를 통합한 단계
  - Q&A 추출 -> 타입별 분류 -> Domain/Subdomain 채우기
  - Output: `eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json`
- `Step5CreateExam`: 시험문제 만들기 (exam_config.json 참고)
  - Output: `eval_data/4_multiple_exam/{set_name}/{exam_name}_exam.json`
  - `ExamValidator`를 사용하여 시험지 검증 및 업데이트
- `Step6Evaluate`: 시험지 평가 (모델별 답변 평가, 배치 처리, 시험지 경로 설정 가능)
  - Output: `eval_data/4_multiple_exam/exam_result/` 또는 `eval_data/8_multiple_exam_+/exam_+_result/`
- `Step7TransformMultipleChoice`: 객관식 문제 변형 (right/wrong/abcd 분류 및 변형)
  - Output: `eval_data/7_multiple_rw/` (answer_type_classified.json, pick_wrong/, pick_right/, pick_abcd/)
  - `MultipleChoiceTransformer`를 사용하여 변형 수행
- `Step8CreateTransformedExam`: 변형 문제를 포함한 시험지 생성 (1st~5th 세트 처리, 변형 문제와 원본 문제 결합)
  - Output: `eval_data/8_multiple_exam_+/{set_name}/` ({exam_name}_exam_transformed.json, {exam_name}_missing.json, STATS_{set_name}.md)
  - `load_transformed_questions`, `create_transformed_exam` 유틸리티 사용
- `Step9MultipleEssay`: 객관식 문제를 서술형 문제로 변환
  - 0단계: 해설이 많은 문제 선별 → `full_explanation.json`
  - 1단계: 해설이 많은 문제 선별 → `full_explanation.json`
  - 2단계: 시험별로 분류 → `questions/essay_questions_{round_folder}.json`
  - 3단계: 서술형 문제로 변환 → `questions/essay_questions_{round_folder}_서술형문제로변환.json`
  - 4단계: 키워드 추출 → `questions/essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json`
  - 5단계: 모범답안 생성 → `answers/best_ans_{round_folder}.json`
  - 모델 답변 생성 → `answers/{round_folder}/{model_name}_{round_number}.json`
  - `steps` 파라미터로 특정 단계만 선택 실행 가능 (예: [1, 2, 3] 또는 [4, 5])
  - 각 단계별로 독립적인 파일로 분리되어 있음
  - `models` 옵션이 있으면 `essay_create_model_answers.py`를 사용하여 모델 답변 생성

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

**formatting.py** - Q&A 데이터 포맷화 유틸리티

- `format_qna_item()`: Q&A 항목을 표준 형식으로 포맷화
- `should_include_qna_item()`: Q&A 항목이 필터링 조건을 만족하는지 확인

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

### 🔄 transformed/ - 문제 변형 관련 기능

**transform_multiple_choice.py** - 객관식 문제 변형 클래스

- `MultipleChoiceTransformer`: 객관식 문제 변형 클래스
  - `transform_wrong_to_right()`: wrong -> right 변형
  - `transform_right_to_wrong()`: right -> wrong 변형
  - `transform_abcd()`: abcd 변형 (단일정답형 -> 복수정답형)
  - 프롬프트 생성, API 호출, 결과 저장 로직 포함

**load_transformed_questions.py** - 변형된 문제 로드 유틸리티

- `load_transformed_questions()`: pick_right, pick_wrong, pick_abcd의 result.json 파일들을 로드하여 question_id를 키로 하는 딕셔너리로 반환

**create_transformed_exam.py** - 변형된 시험지 생성 유틸리티

- `create_transformed_exam()`: 원본 시험지의 각 문제에 대해 변형된 문제를 찾아서 새로운 시험지 생성

**essay_filter_full_explanation.py** - 1단계: 해설이 많은 문제 선별

- 옳지 않은 문제 중 해설이 모든 선지를 포함하는 문제 선별

**essay_classify_by_exam.py** - 2단계: 서술형 문제 시험별 분류

- 서술형 문제를 시험별로 분류하여 회차별 파일 생성

**essay_change_question_to_essay.py** - 3단계: 서술형 문제로 변환

- 객관식 문제를 서술형 문제로 변환

**essay_extract_keywords.py** - 4단계: 키워드 추출

- 서술형 답변 작성에 필요한 키워드 추출

**essay_create_best_answers.py** - 5단계: 모범답안 생성

- 키워드를 포함한 모범답안 생성

**essay_create_model_answers.py** - 모델 답변 생성

- 서술형 문제에 대한 모델 답변 생성

### 📝 exam/ - 시험지 생성 및 검증

**exam_validator.py** - 시험지 검증 및 업데이트 클래스

- `ExamValidator`: 시험지 검증 및 업데이트 클래스
  - `check_exam_meets_requirements()`: 기존 문제지가 exam_config 요구사항을 만족하는지 확인
  - `update_existing_exam()`: 기존 문제지를 exam_config 요구사항에 맞게 업데이트 (부족한 문제 추가, 불필요한 문제 제거)

### 📊 statistics/ - 통계 저장 및 집계

- **StatisticsSaver**: 통계 저장 및 집계 유틸리티 클래스
  - `save_statistics_markdown()`: 통계 정보를 마크다운 형식으로 저장
  - `aggregate_set_statistics()`: 여러 시험지의 통계를 집계
  - `log_statistics()`: 통계 정보를 로그로 출력

### 📈 evaluation/ - 평가

**evaluate_essay_model.py** - 서술형 문제 평가 시스템

- 서술형 문제에 대한 모델 평가
- 키워드 기반 점수 계산
- 통계 정보 생성

**essay_utils.py** - 서술형 평가 유틸리티

- `load_best_answers()`: 모범답안 로드
- `setup_llm_with_api_key()`: API 키 설정 및 LLM 인스턴스 생성

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
├── Step 1(통합): Q&A 추출 및 Domain 분류
│   └── Output: eval_data/2_subdomain/{qna_type}_subdomain_classified_ALL.json
├── Step 5: 시험문제 만들기
│   └── Output: eval_data/4_multiple_exam/{set_name}/{exam_name}_exam.json
├── Step 6: 시험지 평가
│   └── Output: eval_data/4_multiple_exam/exam_result/ 또는 eval_data/8_multiple_exam_+/exam_+_result/
├── Step 7: 객관식 문제 변형 (right/wrong/abcd 분류 및 변형)
│   └── Output: eval_data/7_multiple_rw/ (answer_type_classified.json, pick_wrong/, pick_right/, pick_abcd/)
├── Step 8: 변형 문제를 포함한 시험지 생성 (1st~5th 세트 처리)
│   └── Output: eval_data/8_multiple_exam_+/{set_name}/ ({exam_name}_exam_transformed.json, {exam_name}_missing.json, STATS_{set_name}.md)
└── Step 9: 객관식 문제를 서술형 문제로 변환
    ├── 0단계: 해설이 많은 문제 선별 → full_explanation.json
    ├── 1단계: 시험별로 분류 → questions/essay_questions_{round_folder}.json
    ├── 2단계: 키워드 추출 → questions/essay_questions_w_keyword_{round_folder}.json
    ├── 3단계: 모범답안 생성 → answers/best_ans_{round_folder}.json
    └── 4단계: 모델 답변 생성 → answers/{round_folder}/{model_name}_{round_number}.json
```

### 개별 단계 실행

#### 1. Q&A 추출 및 분류 (통합)

```
pipeline/steps/step1_extract_qna_w_domain.py → Q&A 추출 및 Domain 분류
  - Q&A 추출 -> 타입별 분류 -> Domain/Subdomain 채우기
  - cycle=None이면 모든 사이클 자동 처리
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
  ├── MultipleChoiceTransformer로 변형 수행
  ├── wrong -> right 변형
  ├── right -> wrong 변형
  └── abcd 변형 (단일정답형 -> 복수정답형)
```

#### 6. 변형 문제를 포함한 시험지 생성

```
pipeline/steps/step8_create_transformed_exam.py → 변형 문제를 포함한 시험지 생성
  ├── load_transformed_questions()로 변형된 문제 로드
  ├── create_transformed_exam()로 변형된 시험지 생성
  ├── 4_multiple_exam의 각 세트(1st~5th) 시험지 로드
  ├── pick_right, pick_wrong, pick_abcd의 변형 문제 매칭
  ├── 변형된 문제로 question, options, answer 교체
  ├── 원본 explanation을 original_explanation으로 저장
  ├── 변형된 explanation을 explanation으로 저장
  └── 변형되지 않은 문제는 별도 파일(_missing.json)로 저장
```

#### 7. 객관식 문제를 서술형 문제로 변환

```
pipeline/steps/step9_multiple_essay.py → 객관식 문제를 서술형 문제로 변환
  ├── 1단계: filter_full_explanation - 해설이 많은 문제 선별
  │   └── Output: full_explanation.json
  ├── 2단계: classify_essay_by_exam - 시험별로 분류
  │   └── Output: questions/essay_questions_{round_folder}.json
  ├── 3단계: change_question_to_essay - 서술형 문제로 변환
  │   └── Output: questions/essay_questions_{round_folder}_서술형문제로변환.json
  ├── 4단계: extract_keywords - 키워드 추출
  │   └── Output: questions/essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json
  ├── 5단계: create_best_answers - 모범답안 생성
  │   └── Output: answers/best_ans_{round_folder}.json
  └── 모델 답변 생성: process_essay_questions (models 옵션이 있을 때만)
      └── Output: answers/{round_folder}/{model_name}_{round_number}.json
```

## 🎯 사용 방법

### 메인 파이프라인 실행

```bash
# 1단계(통합): Q&A 추출 및 Domain 분류
python tools/main_pipeline.py --steps extract_qna_w_domain --cycle 1

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

# 6단계: 기본 시험지 평가
python tools/main_pipeline.py --steps evaluate_exams

# 6단계: 변형 시험지 평가 (--eval_transformed 플래그 사용)
python tools/main_pipeline.py --steps evaluate_exams --eval_transformed

# 6단계: 서술형 문제 평가 (--eval_essay 플래그 사용)
python tools/main_pipeline.py --steps evaluate_exams --eval_essay

# 6단계: 변형 시험지 평가 + 서술형 문제 평가
python tools/main_pipeline.py --steps evaluate_exams --eval_transformed --eval_essay

# 6단계: 변형 시험지 평가 (특정 세트만 평가)
python tools/main_pipeline.py --steps evaluate_exams --eval_transformed --eval_sets 1 2 3

# 7단계: 객관식 문제 변형 (기본 경로의 answer_type_classified.json 사용)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_wrong_to_right

# 7단계: 객관식 문제 변형 (분류 단계 포함)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_classify --transform_input_data_path /path/to/data.json --transform_wrong_to_right

# 7단계: 객관식 문제 변형 (여러 변형 수행)
python tools/main_pipeline.py --steps transform_multiple_choice --transform_wrong_to_right --transform_right_to_wrong --transform_abcd

# 8단계: 변형 문제를 포함한 시험지 생성 (1st~5th 모두 처리)
python tools/main_pipeline.py --steps create_transformed_exam

# 8단계: 변형 문제를 포함한 시험지 생성 (특정 세트만 처리: 1, 2, 3세트)
python tools/main_pipeline.py --steps create_transformed_exam --create_transformed_exam_sets 1 2 3

# 9단계: 객관식 문제를 서술형 문제로 변환 (모든 단계 실행)
python tools/main_pipeline.py --steps evaluate_essay

# 9단계: 0-2단계만 실행 (해설 선별, 시험별 분류, 키워드 추출)
python tools/main_pipeline.py --steps evaluate_essay --essay_steps 0 1 2

# 9단계: 3단계만 실행 (모범답안 생성)
python tools/main_pipeline.py --steps evaluate_essay --essay_steps 3

# 9단계: 서술형 문제 변환 + 모델 답변 생성 (모든 단계)
python tools/main_pipeline.py --steps evaluate_essay --essay_models google/gemini-2.5-pro openai/gpt-5 --essay_sets 1 2 3

# 9단계: 서술형 문제 변환 + 모델 답변 생성 (특정 세트만)
python tools/main_pipeline.py --steps evaluate_essay --essay_models google/gemini-2.5-pro openai/gpt-5

# 커스텀 경로 지정
python tools/main_pipeline.py --cycle 1 --onedrive_path /path/to/onedrive --project_root_path /path/to/project
```

### main_pipeline.py 명령행 옵션

#### 기본 옵션

| 옵션                    | 설명                                                                                                | 기본값                                                                                                                                                                                                            |
| ----------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--cycle`             | 사이클 번호 (1, 2, 3) - 0, 1단계에서는 필수, 2, 3단계에서는 선택적 (None이면 모든 사이클 자동 처리) | None                                                                                                                                                                                                              |
| `--steps`             | 실행할 단계 목록 (공백으로 구분)                                                                    | None (전체 실행)                                                                                                                                                                                                  |
|                         |                                                                                                     | 가능한 값:`extract_qna_w_domain`, `create_exam`, `evaluate_exams`, `transform_multiple_choice`, `create_transformed_exam`, `evaluate_essay` |
| `--levels`            | 처리할 레벨 목록 (2단계에서 사용, 예: Lv2 Lv3_4)                                                    | None (기본값: Lv2, Lv3_4, Lv5)                                                                                                                                                                                    |
| `--base_path`         | 기본 데이터 경로                                                                                    | None (ONEDRIVE_PATH 사용)                                                                                                                                                                                         |
| `--config_path`       | LLM 설정 파일 경로                                                                                  | None (PROJECT_ROOT_PATH/llm_config.ini 사용)                                                                                                                                                                      |
| `--onedrive_path`     | OneDrive 경로                                                                                       | None (자동 감지)                                                                                                                                                                                                  |
| `--project_root_path` | 프로젝트 루트 경로                                                                                  | None (자동 감지)                                                                                                                                                                                                  |
| `--debug`             | 디버그 로그 활성화                                                                                  | False                                                                                                                                                                                                             |

#### 단계별 옵션

**1단계(통합) (Q&A 추출 및 Domain 분류)**

| 옵션           | 설명                              | 기본값             |
| -------------- | --------------------------------- | ------------------ |
| `--levels`     | 처리할 레벨 목록 (공백으로 구분)  | Lv2 Lv3_4 Lv5      |
| `--qna_type`   | QnA 타입 (multiple, short, essay) | 'multiple'         |
| `--model`      | 사용할 모델                       | 'x-ai/grok-4-fast' |

**5단계 (시험문제 만들기)**

| 옵션           | 설명           | 기본값 |
| -------------- | -------------- | ------ |
| `--num_sets` | 시험 세트 개수 | 5      |

**6단계 (시험지 평가)**

| 옵션                       | 설명                                                                                | 기본값                |
| -------------------------- | ----------------------------------------------------------------------------------- | --------------------- |
| `--eval_models`          | 평가할 모델 목록 (공백으로 구분)                                                    | None (자동 설정)      |
| `--eval_batch_size`      | 평가 배치 크기                                                                      | 10                    |
| `--eval_use_ox_support`  | O, X 문제 지원 활성화                                                               | True                  |
| `--eval_use_server_mode` | vLLM 서버 모드 사용                                                                 | False                 |
| `--eval_exam_dir`        | 시험지 디렉토리 경로 (단일 JSON 파일 또는 디렉토리)                                 | None (기본 경로 사용) |
| `--eval_sets`            | 평가할 세트 번호 (1, 2, 3, 4, 5 중 선택, 공백으로 구분)                             | None (모든 세트 평가) |
| `--eval_transformed`     | 변형 시험지 평가 모드 (True면 8_multiple_exam_+ 사용, False면 4_multiple_exam 사용) | False                 |
| `--eval_essay`           | 서술형 문제 평가 모드 (True면 9_multiple_to_essay 평가 수행)                        | False                 |

**7단계 (객관식 문제 변형)**

| 옵션                                 | 설명                                                                                      | 기본값         |
| ------------------------------------ | ----------------------------------------------------------------------------------------- | -------------- |
| `--transform_classify`             | 분류 단계 실행 여부                                                                       | False          |
| `--transform_classified_data_path` | 이미 분류된 데이터 파일 경로 (--transform_classify가 False일 때, None이면 기본 경로 사용) | None           |
| `--transform_input_data_path`      | 입력 데이터 파일 경로 (--transform_classify가 True일 때만 사용)                           | None           |
| `--transform_classify_model`       | 분류에 사용할 모델 (--transform_classify가 True일 때만 사용)                              | 'openai/gpt-5' |
| `--transform_classify_batch_size`  | 분류 배치 크기 (--transform_classify가 True일 때만 사용)                                  | 10             |
| `--transform_model`                | 변형에 사용할 모델                                                                        | 'openai/o3'    |
| `--transform_wrong_to_right`       | wrong -> right 변형 수행 여부                                                             | False          |
| `--transform_right_to_wrong`       | right -> wrong 변형 수행 여부                                                             | False          |
| `--transform_abcd`                 | abcd 변형 수행 여부                                                                       | False          |

**8단계 (변형 문제를 포함한 시험지 생성)**

| 옵션                               | 설명                                                           | 기본값               |
| ---------------------------------- | -------------------------------------------------------------- | -------------------- |
| `--create_transformed_exam_sets` | 변형 시험지 생성할 세트 번호 리스트 (공백으로 구분, 예: 1 2 3) | None (1~5 모두 처리) |

**9단계 (객관식 문제를 서술형 문제로 변환)**

| 옵션                        | 설명                                                                        | 기본값               |
| --------------------------- | --------------------------------------------------------------------------- | -------------------- |
| `--essay_models`          | 모델 답변 생성할 모델 목록 (공백으로 구분, None이면 답변 생성 안 함)        | None                 |
| `--essay_sets`            | 처리할 세트 번호 리스트 (공백으로 구분, 예: 1 2 3, models가 있을 때만 사용) | None (1~5 모두 처리) |
| `--essay_use_server_mode` | vLLM 서버 모드 사용 (models가 있을 때만 사용)                               | False                |
| `--essay_steps`            | 실행할 단계 리스트 (공백으로 구분, 예: 0 1 2 또는 3). None이면 모든 단계 실행 (0-4) | None (모든 단계 실행) |

**참고:**

- `--transform_classify`가 False이고 `--transform_classified_data_path`가 None이면 기본 경로(`evaluation/eval_data/7_multiple_rw/answer_type_classified.json`)를 자동으로 사용합니다.
- 변형 옵션(`--transform_wrong_to_right`, `--transform_right_to_wrong`, `--transform_abcd`)은 기본값이 False이므로, 원하는 변형을 명시적으로 활성화해야 합니다.

#### 실행 가능한 단계 목록

`--steps` 옵션에 사용할 수 있는 단계 이름:

- `extract_qna_w_domain`: 1단계(통합) - Q&A 추출 및 Domain 분류
- `create_exam`: 5단계 - 시험문제 만들기
- `evaluate_exams`: 6단계 - 시험지 평가
- `transform_multiple_choice`: 7단계 - 객관식 문제 변형
- `create_transformed_exam`: 8단계 - 변형 문제를 포함한 시험지 생성
- `evaluate_essay`: 9단계 - 객관식 문제를 서술형 문제로 변환

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
result = pipeline.step1_domain.execute(cycle=1, levels=['Lv2', 'Lv3_4'], model='x-ai/grok-4-fast')
result = pipeline.step5.execute(num_sets=5)
result = pipeline.step6.execute(exam_dir="/path/to/exam/directory")
result = pipeline.step7.execute(
    classified_data_path=None,  # 기본 경로 사용
    run_classify=False,
    transform_model='openai/o3',
    transform_wrong_to_right=True
)
result = pipeline.step8.execute(sets=[1, 2, 3])
result = pipeline.step9.execute(
    models=['google/gemini-2.5-pro', 'openai/gpt-5'],
    sets=[1, 2, 3],
    use_server_mode=False,
    steps=[0, 1, 2, 3, 4]  # None이면 모든 단계 실행
)
```

### 개별 모듈 사용

```python
from transformed import MultipleChoiceTransformer, load_transformed_questions, create_transformed_exam
from exam import ExamValidator
from evaluation.essay_utils import load_best_answers, setup_llm_with_api_key
from qna.formatting import format_qna_item, should_include_qna_item

# 객관식 문제 변형
transformer = MultipleChoiceTransformer(llm_query, onedrive_path, logger)
result = transformer.transform_wrong_to_right(questions, model, seed)

# 변형된 문제 로드
transformed_questions = load_transformed_questions(onedrive_path, json_handler, logger)

# 변형된 시험지 생성
new_exam, missing, stats = create_transformed_exam(original_exam, transformed_questions)

# 시험지 검증
meets_requirements, actual_counts = ExamValidator.check_exam_meets_requirements(
    exam_data, exam_name, stats
)

# 시험지 업데이트
updated_exam = ExamValidator.update_existing_exam(
    existing_exam_data, exam_name, stats, all_data, used_questions, logger
)

# 모범답안 로드
best_answers = load_best_answers(best_ans_file, logger)

# LLM 설정
llm = setup_llm_with_api_key(project_root_path, logger)

# Q&A 포맷화
formatted_item = format_qna_item(qna_item)
should_include = should_include_qna_item(qna_item, qna_type)
```

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

### transformed/ - 문제 변형

- **MultipleChoiceTransformer**: 객관식 문제 변형 클래스
  - `transform_wrong_to_right()`: wrong -> right 변형
  - `transform_right_to_wrong()`: right -> wrong 변형
  - `transform_abcd()`: abcd 변형
  - `_sample_questions_by_answer_count()`: 정답 개수별 문제 샘플링
  - `_transform_batch()`: 배치 변형 처리
  - `_call_api_and_save()`: API 호출 및 결과 저장
  - `_create_wrong_to_right_prompt()`: wrong -> right 프롬프트 생성
  - `_create_right_to_wrong_prompt()`: right -> wrong 프롬프트 생성

### exam/ - 시험지 검증

- **ExamValidator**: 시험지 검증 및 업데이트 클래스
  - `check_exam_meets_requirements()`: 시험지 요구사항 검증
  - `update_existing_exam()`: 시험지 업데이트 (부족한 문제 추가, 불필요한 문제 제거)

### evaluation/ - 평가

- **essay_utils**: 서술형 평가 유틸리티
  - `load_best_answers()`: 모범답안 로드
  - `setup_llm_with_api_key()`: API 키 설정 및 LLM 인스턴스 생성

### qna/ - Q&A 처리

- **formatting**: Q&A 데이터 포맷화 유틸리티
  - `format_qna_item()`: Q&A 항목 포맷화
  - `should_include_qna_item()`: 필터링 조건 확인

## 📝 참고사항

### 파이프라인 구조

- **모듈화**: 각 단계가 독립적인 파일로 분리되어 유지보수가 용이합니다.
- **재사용성**: 각 단계 클래스를 독립적으로 사용할 수 있습니다.
- **확장성**: 새로운 단계를 추가하려면 `pipeline/steps/`에 새 파일을 추가하면 됩니다.
- **코드 간소화**: 변형 로직, 검증 로직 등을 별도 모듈로 분리하여 각 step 파일이 간결해졌습니다.

### 경로 설정

경로 설정은 `pipeline/config.py`에서 중앙 관리되며, **플랫폼별 자동 감지 기능**을 지원합니다.

#### 플랫폼별 OneDrive 경로 자동 감지

시스템이 자동으로 플랫폼을 감지하여 올바른 OneDrive 경로를 찾습니다:

- **Windows**:

  - `C:\Users\<username>\OneDrive\데이터L\selectstar`
  - `C:\Users\<username>\OneDrive - 개인\데이터L\selectstar`
  - 환경 변수 `OneDrive` 또는 `OneDriveConsumer`에서 경로 확인
- **macOS**:

  - `~/Library/CloudStorage/OneDrive-개인/데이터L/selectstar`
  - `~/Library/CloudStorage/OneDrive/데이터L/selectstar`
- **Linux**:

  - `~/OneDrive/데이터L/selectstar`

#### 경로 설정 방법

1. **자동 감지 (권장)**: 별도 설정 없이 자동으로 올바른 경로를 찾습니다.
2. **환경 변수로 오버라이드**:
   ```bash
   # Windows (PowerShell)
   $env:ONEDRIVE_PATH="C:\Users\Jin\OneDrive\데이터L\selectstar"

   # macOS/Linux
   export ONEDRIVE_PATH="/path/to/onedrive/데이터L/selectstar"
   ```
3. **코드에서 직접 설정**: `pipeline/config.py`의 `_find_onedrive_path()` 함수를 수정

#### 경로 관련 개선사항

- ✅ **플랫폼 독립적 경로**: 모든 경로가 `os.path.join()`을 사용하여 플랫폼 독립적으로 동작합니다.
- ✅ **슬래시 경로 제거**: 하드코딩된 슬래시(`/`) 경로를 모두 `os.path.join()` 인수로 분리했습니다.
- ✅ **자동 플랫폼 감지**: Windows와 macOS에서 자동으로 올바른 OneDrive 경로를 찾습니다.
- ✅ **환경 변수 지원**: 환경 변수로 경로를 오버라이드할 수 있습니다.

### 의존성

- 각 클래스는 독립적으로 사용 가능하지만, 일부 클래스는 다른 클래스에 의존할 수 있습니다.
- `LLMQuery`는 LLM 관련 기능을 제공하므로 여러 모듈에서 공통으로 사용됩니다.
- `PipelineBase`는 모든 단계 클래스의 기본 클래스입니다.
- 변형 로직은 `transformed` 폴더에 모듈화되어 재사용 가능합니다.
- 검증 로직은 `exam` 폴더에 모듈화되어 재사용 가능합니다.

### 파일 저장 방식

- **Step 2 (전체 문제 추출)**: 기존 `_extracted_qna.json` 파일이 있으면 덮어쓰기합니다 (중복 체크 없음). 내용이 비어있으면 파일을 저장하지 않습니다.
- **Step 3 (타입별 분류)**: 기존 분류 파일(`multiple-choice.json` 등)이 있으면 자동으로 병합합니다. `file_id`와 `tag` 기준으로 중복을 제거하고 새 항목만 추가합니다.
- **Step 4 (Domain/Subdomain 분류)**:
  - 기존 파일이 있으면 `.bak` 파일로 백업한 후 새 결과와 병합합니다.
  - `multiple_classification_Lv234.json` 저장 시에도 기존 파일이 있으면 병합합니다.
  - 모든 병합은 `file_id`와 `tag` 기준으로 중복을 제거합니다.

### 특수 경로 처리

- **2단계 (전체 문제 추출)**: `--cycle`과 `--levels`를 함께 사용하면 `evaluation/workbook_data/{cycle_path}/{level}/` 경로에 저장됩니다 (예: `--cycle 1 --levels Lv2 Lv3_4` → `workbook_data/1C/Lv2/`, `workbook_data/1C/Lv3_4/`).
- **multiple_classification_Lv234.json**: Step 4에서 `qna_type=multiple`이고 Lv2 또는 Lv3_4 경로가 존재하면 자동으로 `evaluation/eval_data/2_subdomain/multiple_classification_Lv234.json`에도 저장합니다.

### 실패 항목 재처리

- 4단계(Domain/Subdomain 분류)에서 실패한 항목은 자동으로 감지되어 재처리됩니다.
- 실패 항목은 `evaluation/eval_data/2_subdomain/{qna_type}_failed_items.json`에 저장됩니다.

### API 키 설정

**6단계 (시험지 평가)**

- 6단계에서 OpenRouter API를 사용할 때는 `llm_config.ini`의 `key_evaluate`를 사용합니다.
- `key_evaluate`가 설정 파일에 없으면 에러가 발생합니다.
- vLLM 서버 모드(`--eval_use_server_mode`)를 사용할 때는 API 키가 필요 없습니다.

**9단계 (서술형 문제 모델 평가)**

- 9단계에서 OpenRouter API를 사용할 때는 `llm_config.ini`의 `key_evaluate`를 우선 사용하고, 없으면 `key`를 사용합니다.
- `essay_utils.setup_llm_with_api_key()`를 통해 자동으로 설정됩니다.

### 6단계 (시험지 평가) 저장 경로 및 파일명

**기본 객관식 평가 모드 (`--eval_transformed` 없음)**

- 입력 디렉토리: `evaluation/eval_data/4_multiple_exam/`
- 출력 디렉토리: `evaluation/eval_data/4_multiple_exam/exam_result/`
- 저장 구조:
  - Excel 파일: `exam_result/{set_name}/{set_name}_evaluation_{모델이름}.xlsx`
    - 예: `exam_result/1st/1st_evaluation_gpt-5_gemini-2.5-pro.xlsx`
  - `model_output`: `exam_result/model_output/`
  - `timing_stats`: `exam_result/timing_stats/`
  - `invalid_responses`: `exam_result/invalid_responses/`

**변형 객관식 평가 모드 (`--eval_transformed` 있음)**

- 입력 디렉토리: `evaluation/eval_data/8_multiple_exam_+/`
- 출력 디렉토리: `evaluation/eval_data/8_multiple_exam_+/exam_+_result/`
- 저장 구조:
  - Excel 파일: `exam_+_result/{set_name}_evaluation_{모델이름}_transformed.xlsx`
    - 예: `exam_+_result/1st_evaluation_gpt-5_gemini-2.5-pro_transformed.xlsx`
  - `model_output`: `exam_+_result/model_output/`
  - `timing_stats`: `exam_+_result/timing_stats/`
  - `invalid_responses`: `exam_+_result/invalid_responses/`

**참고:**

- 기본 모드는 세트별로 폴더를 생성하여 저장합니다 (`exam_result/1st/`, `exam_result/2nd/`, ...).
- 변형 모드는 `exam_+_result/` 폴더에 직접 파일을 저장합니다 (폴더 구조 없음).
- 변형 모드의 파일명은 기본 모드와 동일하지만 `_transformed` 접미사가 추가됩니다.

**서술형 평가 모드 (`--eval_essay` 있음)**

- 입력: `9_multiple_to_essay/questions/essay_questions_{세트명}.json`
- 평가 함수: `evaluate_essay_model.evaluate_single_model()`
- 출력 경로: `9_multiple_to_essay/evaluation_results/`
- 출력 파일:
  - `{모델명}_set{세트번호}_detailed_results.json`: 상세 평가 결과
  - `{모델명}_set{세트번호}_statistics.json`: 통계 정보
- 서술형 평가는 객관식 평가와 독립적으로 실행되며, `--eval_transformed`와 함께 사용할 수 있습니다.

**7단계 (객관식 문제 변형)**

- 7단계는 `AnswerTypeClassifier`를 사용하여 문제를 분류하고, `MultipleChoiceTransformer`를 사용하여 문제를 변형합니다.
- `--transform_classify` 옵션을 사용하여 분류 단계를 실행할 수 있습니다 (기본값: False).
- `--transform_classify`가 False일 때:
  - `--transform_classified_data_path`를 지정하면 해당 파일을 사용합니다.
  - `--transform_classified_data_path`가 None이면 기본 경로(`evaluation/eval_data/7_multiple_rw/answer_type_classified.json`)를 자동으로 사용합니다.
- 분류 단계와 변형 단계에서 서로 다른 모델을 사용할 수 있습니다 (기본값: `openai/gpt-5`로 분류, `openai/o3`로 변형).
- 변형 옵션: `wrong -> right`, `right -> wrong`, `abcd` 변형을 개별적으로 활성화/비활성화할 수 있습니다 (기본값: 모두 False).

**8단계 (변형 문제를 포함한 시험지 생성)**

- 8단계는 4_multiple_exam의 각 세트(1st~5th) 시험지에서 변형된 문제를 찾아 새로운 시험지를 생성합니다.
- `load_transformed_questions()`를 사용하여 `pick_right`, `pick_wrong`, `pick_abcd`의 result.json 파일에서 변형된 문제를 로드합니다.
- `create_transformed_exam()`를 사용하여 변형된 시험지를 생성합니다.
- 변형 규칙:
  - 기존 시험지의 `question`, `options`, `answer`를 변형된 문제의 것으로 교체
  - 기존 시험지의 `explanation`을 `original_explanation`으로 키 이름 변경
  - 변형된 문제의 `explanation`을 `explanation` 키에 저장
- 변형되지 않은 문제는 `{시험지명}_missing.json` 파일로 별도 저장됩니다.
- 결과는 `evaluation/eval_data/8_multiple_exam_+/{세트명}/` 폴더에 저장됩니다.
- `--create_transformed_exam_sets` 옵션으로 특정 세트만 처리할 수 있습니다 (None이면 1~5 모두 처리).

**9단계 (객관식 문제를 서술형 문제로 변환)**

- 9단계는 옳지 않은 객관식 문제를 서술형 문제로 변환합니다.
- **1단계**: `essay_filter_full_explanation.py` - 해설이 모든 선지를 포함하는 문제만 선별
  - 입력: `7_multiple_rw/answer_type_classified.json` (answer_type='wrong'인 문제)
  - 출력: `9_multiple_to_essay/full_explanation.json`
- **2단계**: `essay_classify_by_exam.py` - 시험별로 분류
  - 입력: `9_multiple_to_essay/full_explanation.json`
  - 출력: `9_multiple_to_essay/questions/essay_questions_{round_folder}.json` (1st, 2nd, 3rd, 4th, 5th)
- **3단계**: `essay_change_question_to_essay.py` - 서술형 문제로 변환
  - 입력: `9_multiple_to_essay/questions/essay_questions_{round_folder}.json`
  - 출력: `9_multiple_to_essay/questions/essay_questions_{round_folder}_서술형문제로변환.json`
- **4단계**: `essay_extract_keywords.py` - 키워드 추출
  - 입력: `9_multiple_to_essay/questions/essay_questions_{round_folder}_서술형문제로변환.json`
  - 출력: `9_multiple_to_essay/questions/essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json`
- **5단계**: `essay_create_best_answers.py` - 모범답안 생성
  - 입력: `9_multiple_to_essay/questions/essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json`
  - 출력: `9_multiple_to_essay/answers/best_ans_{round_folder}.json`
- **모델 답변 생성**: `essay_create_model_answers.py` - 모델 답변 생성 (`--essay_models` 옵션이 있을 때만)
  - 입력: `9_multiple_to_essay/questions/essay_questions_w_keyword_{round_folder}_서술형답변에서키워드추출.json`
  - 출력: `9_multiple_to_essay/answers/{round_folder}/{model_name}_{round_number}.json`
- `--essay_steps` 옵션으로 특정 단계만 선택 실행 가능 (예: `--essay_steps 1 2 3` 또는 `--essay_steps 4 5`)
- 결과는 `evaluation/eval_data/9_multiple_to_essay/` 디렉토리에 저장됩니다.
- 서술형 문제 평가는 6단계에서 `--eval_essay` 옵션을 사용할 때 수행됩니다.
- `--eval_essay`는 `--eval_transformed`와 독립적으로 사용할 수 있으며, 함께 사용할 수도 있습니다.
