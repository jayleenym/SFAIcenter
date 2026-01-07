# Tools - 데이터 처리 도구 모음

이 폴더는 Q&A 추출, 시험지 생성, 평가 등의 데이터 처리 기능을 모듈화한 구조입니다.

## 🚀 주요 특징

- **Class 기반 구조**: 모든 기능을 클래스로 캡슐화하여 재사용성 향상
- **통합 파이프라인**: 하나의 메인 코드로 전체 프로세스 실행 가능
- **모듈화**: 비슷한 기능들을 통합하여 코드 중복 제거
- **플랫폼 독립적**: Windows/macOS에서 자동으로 올바른 경로 감지
- **단계별 분리**: 각 파이프라인 단계를 독립적인 모듈로 분리

## 📁 폴더 구조

```
tools/
├── __init__.py              # 경로 설정 (PathResolver)
├── main_pipeline.py         # 메인 파이프라인 엔트리 포인트
│
├── core/                    # 핵심 유틸리티
│   ├── __init__.py          # FileManager, LLMQuery 등 export
│   ├── utils.py             # FileManager, TextProcessor, JSONHandler
│   ├── llm_query.py         # LLMQuery (OpenRouter, vLLM)
│   ├── exam_config.py       # ExamConfig (시험 설정)
│   └── logger.py            # 로깅 설정
│
├── pipeline/                # 파이프라인 모듈
│   ├── __init__.py          # Pipeline, PipelineBase export
│   ├── base.py              # PipelineBase 기본 클래스
│   ├── main.py              # Pipeline 메인 클래스
│   └── steps/               # 각 단계별 모듈
│       ├── step1_extract_qna_w_domain.py  # Q&A 추출 및 Domain 분류
│       ├── step2_create_exams.py          # 시험문제 생성
│       ├── step3_transform_questions.py   # 객관식 문제 변형
│       ├── step6_evaluate.py              # 시험지 평가
│       └── step9_multiple_essay.py        # 서술형 변환
│
├── qna/                     # Q&A 관련 처리
│   ├── __init__.py          # QnAExtractor, TagProcessor 등 export
│   ├── extraction/          # Q&A 추출 (4개 파일)
│   │   ├── make_extracted_qna.py  # QnAMaker (step1 진입점)
│   │   ├── batch_extractor.py     # BatchExtractor (일괄 추출)
│   │   ├── qna_extractor.py       # QnAExtractor (Q&A 추출 핵심)
│   │   └── tag_processor.py       # TagProcessor (태그 처리)
│   ├── processing/          # Q&A 처리 및 변환 (8개 파일)
│   │   ├── organize_qna_by_type.py     # QnAOrganizer (타입별 분류)
│   │   ├── fill_domain.py              # DomainFiller (전체 흐름 관리)
│   │   ├── formatting.py               # 포맷화/필터링 유틸리티
│   │   ├── qna_type_classifier.py      # QnATypeClassifier
│   │   ├── qna_subdomain_classifier.py # QnASubdomainClassifier (API 호출)
│   │   ├── questions_info_manager.py   # QuestionsInfoManager (분류 캐시)
│   │   ├── process_additional_tags.py  # 추가 태그 처리
│   │   └── answer_type_classifier.py   # AnswerTypeClassifier
│   └── analysis/            # Q&A 분석
│       └── statistics_analyzer.py      # QnAStatisticsAnalyzer
│
├── exam/                    # 시험지 생성 및 검증 (4개 파일)
│   ├── __init__.py              # ExamMaker, ExamValidator export
│   ├── exam_create.py           # ExamMaker (일반 시험지)
│   ├── exam_plus_create.py      # ExamPlusMaker (변형 시험지)
│   ├── exam_validator.py        # ExamValidator (검증 유틸)
│   └── extract_exam_question_list.py  # 문제 번호 추출 도구
│
├── evaluation/              # 평가 관련 (3개 파일)
│   ├── __init__.py              # MultipleChoiceEvaluator 등 export
│   ├── multiple_eval_by_model.py    # 객관식 문제 평가
│   ├── evaluate_essay_model.py      # 서술형 문제 평가
│   └── essay_utils.py               # 서술형 평가 유틸리티
│
├── transformed/             # 문제 변형 관련 (11개 파일)
│   ├── __init__.py              # export
│   ├── common.py                # 공통 유틸리티 함수
│   ├── question_transformer.py  # QuestionTransformerOrchestrator (step3 진입점)
│   ├── multiple_change_question_and_options.py  # 객관식 변형
│   ├── multiple_load_transformed_questions.py   # 변형 문제 로드
│   ├── multiple_create_transformed_exam.py      # 변형 시험지 생성
│   ├── essay_filter_full_explanation.py    # 1단계: 문제 선별
│   ├── essay_classify_by_exam.py           # 2단계: 시험별 분류
│   ├── essay_change_question_to_essay.py   # 3단계: 서술형 변환
│   ├── essay_extract_keywords.py           # 4단계: 키워드 추출
│   ├── essay_create_best_answers.py        # 5단계: 모범답안 생성
│   └── essay_create_model_answers.py       # 모델 답변 생성
│
├── data_processing/         # 데이터 처리 및 정제
│   ├── __init__.py          # JSONCleaner export
│   └── json_cleaner.py      # JSONCleaner
│
└── statistics/              # 통계 저장 및 집계
    └── statistics_saver.py  # StatisticsSaver
```

## 🔄 파이프라인 단계

| Step | 이름 | 설명 |
|------|------|------|
| 1 | `extract_qna_w_domain` | Q&A 추출 및 Domain/Subdomain 분류 |
| 2 | `create_exam` | 일반 시험지 생성 (5세트) |
| 3 | `transform_questions` | 객관식 문제 변형 (right↔wrong, ABCD) |
| 4 | `create_transformed_exam` | 변형 시험지 생성 |
| 5 | `evaluate_exams` | 시험지 평가 (객관식) |
| 6 | `evaluate_essay` | 서술형 문제 변환 및 평가 |

### Step 1: extract_qna_w_domain 실행 흐름

```
Step1ExtractQnAWDomain.execute()
    │
    ├─ 1. Q&A 추출 (QnAMaker.process_cycle)
    │      └─ extraction/batch_extractor.py (BatchExtractor)
    │              └─ extraction/qna_extractor.py (QnAExtractor)
    │                      ├─ extraction/tag_processor.py (태그 추출)
    │                      └─ processing/qna_type_classifier.py (타입 분류)
    │
    ├─ 2-3. 타입별 분류 및 저장 (QnAOrganizer.classify_and_save)
    │      └─ processing/organize_qna_by_type.py
    │              ├─ processing/formatting.py (포맷화, 필터링)
    │              └─ processing/qna_type_classifier.py (타입 분류)
    │
    └─ 4-5. Domain/Subdomain 채우기 (DomainFiller.fill_domain)
           └─ processing/fill_domain.py
                   ├─ processing/questions_info_manager.py (캐시 조회)
                   └─ processing/qna_subdomain_classifier.py (LLM API 호출)
```

### Step 2: create_exam 실행 흐름

```
Step2CreateExams.execute()
    │
    ├─ 일반 시험지 생성 (transformed=False)
    │   └─ ExamMaker.create_exams() - exam/exam_create.py
    │           └─ qna/extraction/tag_processor.py (태그 대치)
    │
    └─ 변형 시험지 생성 (transformed=True)
        └─ ExamPlusMaker.create_transformed_exams() - exam/exam_plus_create.py
                ├─ transformed/multiple_load_transformed_questions.py
                └─ transformed/multiple_create_transformed_exam.py
```

### Step 3: transform_questions 실행 흐름

```
Step3TransformQuestions.execute()
    └─ QuestionTransformerOrchestrator - question_transformer.py
            │
            ├─ 분류 (run_classify=True일 때)
            │   └─ qna/processing/answer_type_classifier.py (right/wrong/abcd 분류)
            │
            └─ 변형
                └─ multiple_change_question_and_options.py
                        ├─ wrong → right 변형
                        ├─ right → wrong 변형
                        └─ abcd 변형
```

### Step 6: evaluate_exams 실행 흐름

```
Step6Evaluate.execute()
    │
    ├─ 객관식 평가
    │   └─ evaluation/multiple_eval_by_model.py
    │           ├─ run_eval_pipeline() (LLM 호출)
    │           └─ save_combined_results_to_excel() (결과 저장)
    │
    └─ 서술형 평가 (essay=True일 때)
        └─ evaluation/evaluate_essay_model.py
                └─ evaluation/essay_utils.py (유틸리티)
```

### Step 9: evaluate_essay 실행 흐름

```
Step9MultipleEssay.execute()
    │
    ├─ 1단계: 해설이 많은 문제 선별
    │   └─ essay_filter_full_explanation.py
    │
    ├─ 2단계: 시험별로 분류
    │   └─ essay_classify_by_exam.py
    │
    ├─ 3단계: 서술형 문제로 변환
    │   └─ essay_change_question_to_essay.py
    │
    ├─ 4단계: 키워드 추출
    │   └─ essay_extract_keywords.py
    │
    ├─ 5단계: 모범답안 생성
    │   └─ essay_create_best_answers.py
    │
    └─ 모델 답변 생성 (models 지정 시)
        └─ essay_create_model_answers.py
```

## 📦 Q&A 처리 모듈 (qna/)

### extraction/ - Q&A 추출

| 모듈 | 클래스 | 역할 |
|------|--------|------|
| `make_extracted_qna.py` | `QnAMaker` | step1 진입점, BatchExtractor 상속 |
| `batch_extractor.py` | `BatchExtractor` | 일괄 추출 로직, 재개(resume) 기능 지원 |
| `qna_extractor.py` | `QnAExtractor` | JSON에서 Q&A 태그 추출 핵심 로직 |
| `tag_processor.py` | `TagProcessor` | 태그 추출/대치 유틸리티 |

### processing/ - Q&A 처리 및 변환

| 모듈 | 클래스 | 역할 |
|------|--------|------|
| `organize_qna_by_type.py` | `QnAOrganizer` | 타입별 분류: multiple-choice, short-answer, essay, etc |
| `fill_domain.py` | `DomainFiller` | **전체 흐름 관리**: 기존 분류 활용 → API 호출 → is_table 추가 → 저장 → 원본 삭제 |
| `formatting.py` | - | 포맷화/필터링 유틸리티 함수 |
| `qna_type_classifier.py` | `QnATypeClassifier` | 문제 유형 분류 (multiple-choice/short-answer/essay/etc) |
| `qna_subdomain_classifier.py` | `QnASubdomainClassifier` | **API 호출만**: domain/subdomain/is_calculation 분류 |
| `questions_info_manager.py` | `QuestionsInfoManager` | 분류 결과 캐시 관리 (questions_info.json) |
| `process_additional_tags.py` | - | 추가 태그 처리 (tb, f, note 태그) |
| `answer_type_classifier.py` | `AnswerTypeClassifier` | 답변 유형 분류 (transformed에서 사용) |

### 출력 파일 필드 순서

```json
{
  "file_id": "...",
  "tag": "...",
  "title": "...",
  "cat1_domain": "...",
  "cat2_sub": "...",
  "cat3_specific": "...",
  "chapter": "...",
  "page": "...",
  "qna_type": "multiple-choice",
  "domain": "금융일반",
  "subdomain": "금융시장",
  "is_calculation": false,
  "is_table": false,
  "classification_reason": "...",
  "question": "...",
  "options": ["①...", "②...", "③...", "④..."],
  "answer": "...",
  "explanation": "..."
}
```

- `is_table`: `question`에 `{tb_` 패턴이 있으면 `true`

## 💻 사용법

### 전체 파이프라인 실행

```bash
python tools/main_pipeline.py --cycle 1
```

### 개별 단계 실행

```bash
# 1단계: Q&A 추출 및 Domain 분류
python tools/main_pipeline.py --steps extract_qna_w_domain --cycle 1
python tools/main_pipeline.py --steps extract_qna_w_domain --cycle 1 --levels Lv2 Lv3_4

# 2단계: 시험문제 만들기 (랜덤 모드)
python tools/main_pipeline.py --steps create_exam --random --num_sets 5

# 3단계: 문제 변형
python tools/main_pipeline.py --steps transform_questions --transform_data /path/to/classified.json
python tools/main_pipeline.py --steps transform_questions \
  --transform_classify --transform_input /path/to/input.json \
  --transform_types wrong_to_right right_to_wrong

# 4단계: 변형 시험지 생성
python tools/main_pipeline.py --steps create_transformed_exam --transformed_sets 1 2 3

# 5단계: 시험지 평가 (기본)
python tools/main_pipeline.py --steps evaluate_exams --eval_models gpt-4

# 5단계: 시험지 평가 (vLLM 서버 모드, 변형 시험지)
python tools/main_pipeline.py --steps evaluate_exams \
  --eval_exam_dir /path/to/exam \
  --eval_models /path/to/model \
  --eval_use_server_mode \
  --eval_batch_size 1 \
  --transformed

# 6단계: 서술형 변환 (전체 단계)
python tools/main_pipeline.py --steps evaluate_essay

# 6단계: 서술형 변환 (특정 단계만)
python tools/main_pipeline.py --steps evaluate_essay --essay_steps 1 2 3 --essay_sets 1 2
```

### 주요 옵션

#### 기본 옵션
| 옵션 | 설명 |
|------|------|
| `--steps` | 실행할 단계 선택 (미지정시 전체 실행) |
| `--cycle` | 사이클 번호 (1, 2, 3) - 1단계에서 사용 |
| `--debug` | 디버그 모드 활성화 |
| `--config_path` | LLM 설정 파일 경로 |
| `--base_path` | 기본 데이터 경로 |

#### Q&A 추출 (1단계)
| 옵션 | 설명 |
|------|------|
| `--levels` | 처리할 레벨 (Lv2, Lv3_4, Lv5 중 선택, 미지정시 전체) |
| `--model` | 도메인 분류에 사용할 LLM 모델 (기본값: x-ai/grok-4-fast) |

#### 시험 생성 (2단계)
| 옵션 | 설명 |
|------|------|
| `--num_sets` | 시험 세트 개수 (기본값: 5) |
| `--random` | 랜덤 모드 (새로 문제 뽑기) |

#### 문제 변형 (3단계)
| 옵션 | 설명 |
|------|------|
| `--transform_data` | 분류된 데이터 파일 경로 |
| `--transform_classify` | 분류 단계 실행 |
| `--transform_input` | 변형 입력 데이터 경로 (--transform_classify 사용시) |
| `--transform_types` | 수행할 변형 종류 (wrong_to_right, right_to_wrong, abcd) |
| `--transform_classify_model` | 분류에 사용할 모델 (기본값: openai/gpt-5) |
| `--transform_classify_batch_size` | 분류 배치 크기 (기본값: 10) |
| `--transform_model` | 변형에 사용할 모델 (기본값: openai/o3) |
| `--transform_seed` | 랜덤 시드 (기본값: 42) |

#### 변형 시험지 생성 (4단계)
| 옵션 | 설명 |
|------|------|
| `--transformed_sets` | 생성할 세트 번호 (1-5, 미지정시 전체) |

#### 시험 평가 (5단계)
| 옵션 | 설명 |
|------|------|
| `--eval_models` | 평가할 모델 목록 |
| `--eval_sets` | 평가할 세트 번호 (1-5) |
| `--eval_transformed`, `--transformed` | 변형 시험지 평가 모드 |
| `--eval_server_mode`, `--eval_use_server_mode` | vLLM 서버 모드 |
| `--eval_exam_dir` | 시험지 디렉토리/파일 경로 |
| `--eval_batch_size` | 평가 배치 크기 (기본값: 10) |
| `--eval_use_ox_support` | O, X 문제 지원 활성화 (기본값: True) |
| `--eval_no_ox_support` | O, X 문제 지원 비활성화 |
| `--eval_essay` | 서술형 평가도 함께 수행 |

#### 서술형 평가 (6단계)
| 옵션 | 설명 |
|------|------|
| `--essay_models` | 서술형 평가 모델 목록 |
| `--essay_sets` | 처리할 세트 번호 (1-5) |
| `--essay_server_mode` | vLLM 서버 모드 |
| `--essay_steps` | 실행할 단계 번호 (1: 문제선별, 2: 시험분류, 3: 서술형변환, 4: 키워드추출, 5: 모범답안생성) |

### Python에서 직접 사용

```python
from tools.pipeline import Pipeline

# 파이프라인 인스턴스 생성
pipeline = Pipeline()

# 개별 단계 실행
results = pipeline.run_full_pipeline(
    steps=['create_exam'],
    num_sets=5,
    random_mode=True
)

print(results)
```

### 개별 클래스 사용

```python
from tools.core import FileManager, LLMQuery, JSONHandler
from tools.qna import QnAExtractor, TagProcessor
from tools.exam import ExamMaker, ExamValidator

# FileManager 사용
fm = FileManager()
json_files = fm.get_json_file_list(cycle=1)

# LLMQuery 사용
llm = LLMQuery()
response = llm.query_openrouter(
    system_prompt="You are a helpful assistant.",
    user_prompt="What is the capital of France?",
    model_name="openai/gpt-4"
)
```

## 📝 경로 설정

경로는 자동으로 감지되지만, 환경 변수로 오버라이드할 수 있습니다:

```bash
export ONEDRIVE_PATH="/path/to/onedrive"
export PROJECT_ROOT_PATH="/path/to/project"
export SFAICENTER_PATH="/path/to/sfaicenter"
```

## 🛠️ 개발 가이드

### 새 단계 추가하기

1. `pipeline/steps/` 에 새 step 파일 생성
2. `PipelineBase` 를 상속받아 클래스 정의
3. `execute()` 메서드 구현
4. `pipeline/steps/__init__.py` 에 export 추가
5. `pipeline/main.py` 의 `run_full_pipeline()` 에 새 단계 추가

### Import 패턴

```python
# 권장: tools 패키지에서 import
from tools.core import FileManager, LLMQuery
from tools.qna import QnAExtractor
from tools.exam import ExamMaker

# 상대 import (같은 패키지 내에서만)
from .utils import FileManager
from ..base import PipelineBase
```

## 📋 변경 이력

### v1.4.0 (리팩토링)
- **FileManager 경로 중복 제거**: `tools/__init__.py`의 `PathResolver`를 사용하도록 통합
  - 기존: FileManager에서 플랫폼별 OneDrive 경로 직접 탐지
  - 변경: `from tools import ONEDRIVE_PATH` 사용
- **JSONHandler/TextProcessor 클래스 참조 변경**: 모든 메서드가 `@staticmethod`이므로 인스턴스 생성 불필요
  - `PipelineBase`에서 인스턴스 대신 클래스 참조로 변경
- **Pipeline step lazy initialization**: 필요할 때만 step 인스턴스 생성
  - `__init__`에서 모든 step 인스턴스 생성 → `_get_step()` 메서드로 필요시 생성
- **Step6Evaluate 리팩토링**: 600줄의 `execute()` 메서드 개선
  - 클래스 상수 추가: `SET_NAMES`, `DEFAULT_MODELS`
  - 헬퍼 메서드 추출: `_get_api_key()`, `_get_exam_directories()`, `_make_models_filename()`
  - 중복 코드 제거
- **import 경로 통일**: `from core.xxx` → `from tools.core.xxx`
  - `exam/exam_create.py`, `exam/exam_plus_create.py`
  - `qna/processing/qna_subdomain_classifier.py`, `answer_type_classifier.py`
  - `transformed/question_transformer.py`, `multiple_change_question_and_options.py`, `multiple_load_transformed_questions.py`
  - `evaluation/essay_utils.py`

### v1.3.0 (코드 정리)
- `qna/processing/` 미사용 파일 삭제 (5개):
  - `reclassify_qna_types.py` - 일회성 재분류 스크립트
  - `verify_reclassification.py` - 재분류 검증 스크립트
  - `merger.py` - 미사용 병합 클래스
  - `tag_fixer.py` - 미사용 태그 대치 클래스
  - `workbook_groupby_qtype.py` - organize_qna_by_type.py와 중복
- `evaluation/` 미사용 파일 삭제 (1개):
  - `check_all_exams_shortage.py` - 미사용 분석 스크립트
- `transformed/` 미사용 파일 삭제 (1개):
  - `multiple_process_missing_questions.py` - 어디서도 import되지 않음
- `questions_info_manager.py` 추가: 분류 결과 캐시 관리
- 각 스텝별 실행 흐름도 README에 추가
- 폴더 구조 문서화 정비

### v1.2.0 (Domain 분류 모듈 정리)
- 출력 파일명 변경: `~_subdomain_classified_ALL.json` → `~_DST.json`
- `qna_subdomain_classifier.py`: API 호출만 담당하도록 단순화
  - `classify_questions(questions, batch_size, model)` → `(updated, failed)` 반환
  - 파일 저장/삭제 로직 제거
- `fill_domain.py`: 전체 흐름 관리
  - 기존 분류 파일에서 domain/subdomain 채우기
  - 빈 항목만 API 호출 (classifier 사용)
  - 실패 항목 재시도
  - `is_table` 필드 추가 (`question`에 `{tb_` 패턴 있으면 True)
  - 결과 저장 및 원본 파일 삭제
  - 통계 파일 자동 생성 (`STATS_{qna_type}_DST.md`)

### v1.1.0 (리팩토링)
- `PathResolver` 클래스로 경로 관리 통합
- 중복된 `sys.path` 조작 제거
- `transformed/common.py` 로 유틸리티 분리
- 모든 `__init__.py` 파일에 docstring 및 `__all__` 정리
- import 패턴 통일 (`tools.xxx` 형태)

### v1.0.0 (초기 버전)
- Class 기반 구조로 리팩토링
- 통합 파이프라인 구현
- 모듈화 및 분리
