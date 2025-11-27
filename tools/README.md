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
│       ├── step2_create_exams.py       # 2단계: 시험문제 만들기 (통합)
│       ├── step3_transform_questions.py # 3단계: 객관식 문제 변형
│       ├── step6_evaluate.py           # 6단계: 시험지 평가
│       └── step9_multiple_essay.py             # 9단계: 객관식 문제를 서술형 문제로 변환
│
├── statistics/              # 통계 저장 및 집계
│   ├── __init__.py
│   └── statistics_saver.py   # StatisticsSaver 클래스 (통계 저장/집계/로깅)
│
├── transformed/             # 문제 변형 관련 기능
│   ├── __init__.py
│   ├── multiple_change_question_and_options.py # 객관식 문제 변형 로직
│   ├── multiple_load_transformed_questions.py  # 변형된 문제 로드 유틸리티
│   ├── multiple_create_transformed_exam.py     # 변형된 시험지 생성 유틸리티
│   ├── essay_filter_full_explanation.py        # 1단계: 해설이 많은 문제 선별
│   ├── essay_classify_by_exam.py              # 2단계: 서술형 문제 시험별 분류
│   ├── essay_change_question_to_essay.py      # 3단계: 서술형 문제로 변환
│   ├── essay_extract_keywords.py              # 4단계: 키워드 추출
│   ├── essay_create_best_answers.py           # 5단계: 모범답안 생성
│   ├── essay_create_model_answers.py          # 모델 답변 생성
│   └── question_transformer.py                # 변형 오케스트레이터
│
├── exam/                    # 시험지 생성 및 검증
│   ├── __init__.py
│   ├── exam_create.py       # ExamMaker 클래스
│   ├── exam_plus_create.py  # ExamPlusMaker 클래스
│   └── exam_validator.py    # ExamValidator 클래스 (시험지 검증/업데이트)
│
├── core/                    # 핵심 유틸리티 및 공통 기능
│   ├── utils.py            # FileManager, TextProcessor, JSONHandler 클래스
│   ├── llm_query.py        # LLMQuery 클래스 (OpenRouter, vLLM)
│   ├── exam_config.py      # ExamConfig 클래스 (시험 설정 파일 로더)
│   └── logger.py           # 로깅 설정
│
├── data_processing/         # 데이터 처리 및 정제
│   ├── json_cleaner.py     # JSONCleaner 클래스 (빈 페이지 제거)
│   └── epubstats.py        # EPUB/PDF 통계 처리
│
├── qna/                     # Q&A 관련 처리
│   ├── qna_processor.py    # QnATypeClassifier, QnAExtractor, TagProcessor 클래스
│   ├── formatting.py       # Q&A 데이터 포맷화 유틸리티
│   ├── tag_processor.py    # 태그 처리 클래스
│   ├── make_extracted_qna.py # QnAMaker 클래스 (BatchExtractor 래퍼)
│   ├── classify_qna_type.py  # QnAClassifier 클래스
│   ├── fill_domain.py        # DomainFiller 클래스
│   ├── fill_multiple_choice_data.py # 객관식 데이터 채우기
│   ├── workbook_groupby_qtype.py    # 문제 타입별 그룹화
│   │
│   ├── extraction/         # Q&A 추출
│   │   └── batch_extractor.py # BatchExtractor 클래스
│   │
│   ├── processing/         # Q&A 처리 및 변환
│   │   ├── answer_type_classifier.py   # AnswerTypeClassifier (right/wrong/abcd 분류)
│   │   ├── qna_subdomain_classifier.py # QnASubdomainClassifier (도메인/서브도메인 분류)
│   │   ├── merger.py                   # QnAMerger 클래스
│   │   ├── tag_fixer.py                # TagFixer 클래스
│   │   ├── process_additional_tags.py  # (레거시)
│   │   ├── reclassify_qna_types.py     # (레거시)
│   │   └── verify_reclassification.py  # (레거시)
│   │
│   └── analysis/           # Q&A 분석
│       ├── statistics_analyzer.py              # QnAStatisticsAnalyzer 클래스
│       ├── analyze_qna_statistics.py           # 통계 분석 래퍼
│       ├── analyze_additional_tags_grouped.py  # 추가 태그 그룹 분석
│       ├── check_real_duplicates.py            # 중복 검사
│       └── find_invalid_options.py              # 유효하지 않은 선지 찾기
│
└── evaluation/             # 평가 관련
    ├── evaluate_essay_model.py      # 서술형 문제 평가 시스템
    ├── essay_utils.py               # 서술형 평가 유틸리티
    └── multiple_eval_by_model.py    # LLM 평가 시스템 (MultipleChoiceEvaluator)
```

## 📋 주요 모듈 변경 사항 (Refactoring)

### `tools/qna/`
- **Extraction**: `batch_extractor.py`로 추출 로직을 통합하고 `BatchExtractor` 클래스로 캡슐화했습니다. 기존 `process_qna.py` 등은 삭제되었습니다.
- **Processing**: `merger.py` (QnAMerger), `tag_fixer.py` (TagFixer) 등을 추가하여 역할을 분리했습니다.
- **Analysis**: `statistics_analyzer.py` (QnAStatisticsAnalyzer)를 추가하여 통계 분석 로직을 클래스화했습니다.
- **Interfaces**: `make_extracted_qna.py`, `analyze_qna_statistics.py` 등은 하위 호환성을 위해 새로운 클래스를 사용하는 래퍼로 유지됩니다.

### `tools/evaluation/`
- **Evaluation**: `multiple_eval_by_model.py`를 `MultipleChoiceEvaluator` 클래스 기반으로 리팩토링하여 상태 관리와 재사용성을 개선했습니다.

### `tools/exam/`
- **Creation**: `exam_create.py` (`ExamMaker`), `exam_plus_create.py` (`ExamPlusMaker`)로 클래스화하여 시험지 생성 로직을 체계화했습니다.

## 🔄 사용 흐름

### 전체 파이프라인 (권장)

```bash
# 전체 파이프라인 실행
python tools/main_pipeline.py --cycle 1
```

### 개별 단계 실행 예시

```bash
# 1단계(통합): Q&A 추출 및 Domain 분류
python tools/main_pipeline.py --steps extract_qna_w_domain --cycle 1

# 2단계: 시험문제 만들기 (일반)
python tools/main_pipeline.py --steps create_exam --num_sets 5

# 3단계: 객관식 문제 변형
python tools/main_pipeline.py --steps transform_questions --transform_wrong_to_right

# 6단계: 시험지 평가
python tools/main_pipeline.py --steps evaluate_exams

# 9단계: 서술형 변환 및 평가
python tools/main_pipeline.py --steps evaluate_essay
```

자세한 사용법과 옵션은 `main_pipeline.py --help`를 참고하거나 각 스크립트 상단의 주석을 확인하세요.
