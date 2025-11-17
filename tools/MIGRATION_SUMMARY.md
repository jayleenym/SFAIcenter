# exam_config.json 마이그레이션 완료

## 마이그레이션된 파일

### 1. `tools/pipeline/steps/step5_create_exam.py`
- **변경 전**: `exam_statistics.json` 파일을 직접 로드
- **변경 후**: `ExamConfig` 클래스를 사용하여 `exam_config.json`에서 통계 정보 로드
- **변경 내용**:
  - `ExamConfig` import 추가
  - 파일 직접 로드 코드를 `ExamConfig(onedrive_path=self.onedrive_path).get_exam_statistics()`로 변경
  - 에러 처리 개선

### 2. `tools/qna/processing/qna_subdomain_classifier.py`
- **변경 전**: `domain_subdomain.json` 파일을 직접 로드
- **변경 후**: `ExamConfig` 클래스를 사용하여 `exam_config.json`에서 도메인-서브도메인 매핑 로드
- **변경 내용**:
  - `ExamConfig` import 추가
  - `load_domain_subdomain()` 메서드를 `ExamConfig`를 사용하도록 수정
  - 하위 호환성을 위해 기존 파일 로드 방식 fallback 유지

### 3. `tools/core/exam_config.py`
- **개선 사항**: `onedrive_path` 파라미터 지원 추가
  - `ExamConfig` 클래스와 모든 편의 함수에 `onedrive_path` 파라미터 추가
  - OneDrive 경로를 우선적으로 사용하도록 개선

## 사용 방법

### step5_create_exam.py에서
```python
# 기존 코드는 자동으로 exam_config.json을 사용합니다
exam_config = ExamConfig(onedrive_path=self.onedrive_path)
stats = exam_config.get_exam_statistics()
```

### qna_subdomain_classifier.py에서
```python
# 기존 코드는 자동으로 exam_config.json을 사용합니다
# exam_config.json이 없으면 기존 domain_subdomain.json을 fallback으로 사용
exam_config = ExamConfig(onedrive_path=self.onedrive_path)
domain_subdomain = exam_config.get_domain_subdomain()
```

## 하위 호환성

- `qna_subdomain_classifier.py`는 `exam_config.json`을 찾을 수 없을 경우 기존 `domain_subdomain.json` 파일을 fallback으로 사용합니다.
- 기존 3개 파일(`exam_statistics.json`, `exam_hierarchy.json`, `domain_subdomain.json`)은 그대로 유지되므로 기존 코드와의 호환성이 보장됩니다.

## 다음 단계

1. 테스트: 마이그레이션된 코드가 정상적으로 작동하는지 확인
2. 점진적 전환: 다른 파일들도 필요시 마이그레이션
3. 문서화: README 업데이트 (선택사항)

