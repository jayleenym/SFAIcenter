# QnA 도메인 병렬처리 스크립트

`merged_extracted_qna_Lv2345.json` 파일에서 처리되지 않은 데이터를 찾아서 `add_qna_domain` 함수를 병렬로 실행하는 스크립트입니다.

## 파일 설명

### 1. `process_remaining_qna.py` (완전한 버전)
- 처리되지 않은 데이터를 정확히 식별
- 상세한 로깅과 오류 처리
- 설정 가능한 배치 크기와 워커 수
- 임시 파일 자동 정리

### 2. `simple_parallel_qna.py` (간단한 버전)
- 간단하고 빠른 처리
- 최소한의 설정으로 실행 가능
- 기본 설정: 배치당 20개, 워커 3개

## 사용 방법

### 간단한 실행 (권장)
```bash
cd /Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter
python simple_parallel_qna.py
```

### 완전한 실행
```bash
cd /Users/yejin/Desktop/Desktop_AICenter✨/SFAIcenter
python process_remaining_qna.py
```

## 설정 변경

### simple_parallel_qna.py 설정
```python
batch_size = 20  # 각 배치당 처리할 데이터 개수
max_workers = 3  # 병렬 처리 워커 수
model = "grok-beta/grok-2-1212"  # 사용할 모델
```

### process_remaining_qna.py 설정
```python
chunk_size = 50  # 각 묶음당 처리할 데이터 개수
max_workers = 4  # 병렬 처리 워커 수
model = "grok-beta/grok-2-1212"  # 사용할 모델
```

## 출력 파일

- `merged_extracted_qna_domain_Lv2345_final.json` (simple 버전)
- `merged_extracted_qna_domain_Lv2345_completed.json` (완전한 버전)

## 주의사항

1. **API 제한**: OpenRouter API의 제한을 고려하여 워커 수를 조정하세요
2. **메모리 사용량**: 배치 크기가 클수록 메모리를 더 사용합니다
3. **네트워크 안정성**: 네트워크가 불안정한 경우 워커 수를 줄이세요
4. **백업**: 실행 전 원본 파일을 백업하는 것을 권장합니다

## 문제 해결

### 메모리 부족 오류
- 배치 크기를 줄이세요 (20 → 10)
- 워커 수를 줄이세요 (3 → 2)

### API 제한 오류
- 워커 수를 줄이세요 (3 → 1)
- 배치 크기를 줄이세요

### 네트워크 오류
- 스크립트를 다시 실행하면 처리되지 않은 부분만 다시 처리됩니다
- 중간 결과 파일들이 보존되므로 안전합니다
