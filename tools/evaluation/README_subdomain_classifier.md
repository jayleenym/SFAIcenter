# Q&A 서브도메인 분류기

금융 시험 문제를 도메인별로 세부 분류하는 자동화 도구입니다.

## 주요 기능

- **50문제 단위 배치 처리**: API 호출을 50문제씩 나누어 처리하여 안정성 확보
- **자동 JSON 파싱**: API 응답을 자동으로 파싱하여 `qna_subdomain` 필드 업데이트
- **도메인별 결과 저장**: 각 도메인별로 분류된 문제들을 별도 JSON 파일로 저장
- **오류 처리 및 로깅**: 상세한 로그와 오류 처리로 안정적인 실행
- **중간 결과 저장**: 5배치마다 중간 결과를 저장하여 진행 상황 추적

## 파일 구조

```
SFAIcenter/
├── qna_subdomain_classifier.py    # 메인 분류기 클래스
├── run_subdomain_classification.py # 실행 스크립트
├── llm_config.ini                 # API 설정 파일
├── evaluation/eval_data/
│   ├── domain_subdomain.json      # 도메인-서브도메인 매핑
│   └── subdomain_results/         # 분류 결과 저장 폴더
│       ├── 경제_subdomain_classified.json
│       ├── 경영_subdomain_classified.json
│       ├── all_domains_subdomain_classified.json
│       └── classification_statistics.json
```

## 사용 방법

### 1. 기본 실행

```bash
python run_subdomain_classification.py
```

### 2. 커스텀 설정으로 실행

```bash
python qna_subdomain_classifier.py \
    --data_path /path/to/your/data \
    --model "x-ai/grok-4-fast" \
    --batch_size 50 \
    --config ./llm_config.ini
```

### 3. 프로그래밍 방식으로 사용

```python
from qna_subdomain_classifier import QnASubdomainClassifier

# 분류기 초기화
classifier = QnASubdomainClassifier()

# 특정 도메인만 처리
domain_questions = [...]  # 도메인별 문제 리스트
results = classifier.process_domain_batch(
    domain="경제", 
    questions=domain_questions,
    batch_size=50,
    model="x-ai/grok-4-fast"
)

# 전체 도메인 처리
all_results = classifier.process_all_domains(
    data_path="/path/to/data",
    model="x-ai/grok-4-fast",
    batch_size=50
)
```

## 설정 파일 (llm_config.ini)

```ini
[OPENROUTER]
key = your_api_key_here
url = https://openrouter.ai/api/v1

[PARAMS]
temperature = 0.1
frequency_penalty = 0.0
presence_penalty = 0.0
top_p = 0.9
```

## 도메인-서브도메인 매핑

현재 지원하는 도메인과 서브도메인:

- **경제**: 미시경제학, 거시경제학, 국제경제학, 경제정책 및 시사경제
- **경영**: 경영학원론 및 조직관리, 재무관리 및 기업가치평가, 마케팅 및 영업전략, 경영컨설팅 및 기술평가, 경영윤리 및 ESG
- **통계**: 기초통계학, 추론통계학, 응용통계 및 시계열분석, 데이터조사 및 분석활용
- **영업**: 금융상품영업, 고객상담 및 민원관리, 영업윤리 및 법규준수, 세일즈커뮤니케이션
- **자산운용**: 투자분석 및 포트폴리오이론, 펀드운용, 파생상품, 연금·대체투자
- **세무**: 소득세·법인세, 상속세·증여세, 부가가치세 및 원천징수, 세무회계 및 재정정책
- **보험계약**: 보험법 및 계약이론, 보험상품구조, 언더라이팅 및 재보험, 보험회계 및 공시
- **내부통제**: 컴플라이언스 및 법규, 소비자보호, 자금세탁방지 및 AML, 윤리경영 및 내부감사
- **리스크관리**: 리스크기초이론, 금융리스크측정기법, 보험리스크관리, 통합리스크관리
- **보상처리**: 손해사정실무, 보험금심사, 분쟁조정 및 금융소비자보호
- **노무**: 근로기준법 및 인사관리, 노동법 및 사회보험, 노사관계 및 분쟁조정, 조직문화 및 인재육성
- **회계**: 재무회계, 관리회계, 세무회계, 회계기준 및 감사
- **디지털**: 디지털금융, 데이터분석 및 인공지능, 핀테크 및 블록체인, 정보보호 및 시스템관리

## 출력 결과

### 1. 도메인별 분류 결과
각 도메인별로 `{도메인명}_subdomain_classified.json` 파일이 생성됩니다.

```json
[
  {
    "file_id": "SS0000",
    "title": "책 제목",
    "chapter": "챕터명",
    "qna_id": "SS0000_q_0000_0000",
    "qna_domain": "경제",
    "qna_subdomain": "미시경제학",
    "qna_subdomain_reason": "수요·공급 이론 관련 문제",
    "qna_question": "문제 내용",
    "qna_answer": "정답",
    "qna_options": ["선지1", "선지2", "선지3", "선지4"],
    "qna_explanation": "해설"
  }
]
```

### 2. 통합 결과
모든 도메인의 결과를 하나로 합친 `all_domains_subdomain_classified.json` 파일이 생성됩니다.

### 3. 통계 정보
분류 결과의 통계 정보가 `classification_statistics.json` 파일에 저장됩니다.

```json
{
  "경제": {
    "total_questions": 150,
    "subdomain_distribution": {
      "미시경제학": 45,
      "거시경제학": 38,
      "국제경제학": 32,
      "경제정책 및 시사경제": 35
    }
  }
}
```

## 로그 파일

실행 과정은 `qna_classification.log` 파일에 상세히 기록됩니다.

## 주의사항

1. **API 키 설정**: `llm_config.ini` 파일에 올바른 API 키를 설정해야 합니다.
2. **데이터 경로**: 데이터 파일 경로가 올바른지 확인하세요.
3. **배치 크기**: 메모리와 API 제한에 따라 배치 크기를 조정할 수 있습니다.
4. **중간 저장**: 5배치마다 중간 결과가 저장되므로 중단되어도 이어서 실행할 수 있습니다.

## 문제 해결

### API 호출 실패
- API 키가 올바른지 확인
- 네트워크 연결 상태 확인
- API 사용량 제한 확인

### JSON 파싱 오류
- API 응답 형식 확인
- 로그 파일에서 상세 오류 내용 확인

### 메모리 부족
- 배치 크기를 줄여서 실행 (예: `--batch_size 25`)
