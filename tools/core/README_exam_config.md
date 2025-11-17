# exam_config.json 사용 가이드

3개의 설정 파일(`exam_statistics.json`, `exam_hierarchy.json`, `domain_subdomain.json`)을 하나의 `exam_config.json`으로 통합했습니다.

## 파일 구조

```
exam_config.json
├── exams: 시험별 상세 정보
│   ├── 금융일반
│   │   ├── domains: ["경제", "경영"]
│   │   └── domain_details
│   │       ├── 경제
│   │       │   ├── exam_questions: 125
│   │       │   └── subdomains
│   │       │       ├── 미시경제학
│   │       │       │   ├── count: 32
│   │       │       │   └── description: "수요·공급, 소비자·생산자이론..."
│   │       │       └── ...
│   │       └── ...
│   └── ...
└── all_domains: 모든 도메인별 서브도메인 리스트 (기존 domain_subdomain.json과 동일)
```

## 사용 방법

### 1. ExamConfig 클래스 사용 (권장)

```python
from tools.core.exam_config import ExamConfig

# 기본 경로에서 자동으로 찾기
config = ExamConfig()

# 또는 직접 경로 지정
config = ExamConfig('/path/to/exam_config.json')

# 기존 코드와 호환: exam_statistics.json 형태로 가져오기
stats = config.get_exam_statistics()
# {
#     "금융일반": {
#         "경제": {
#             "exam_questions": 125,
#             "exam_subdomain_distribution": {
#                 "미시경제학": 32,
#                 ...
#             }
#         }
#     }
# }

# 기존 코드와 호환: exam_hierarchy.json 형태로 가져오기
hierarchy = config.get_exam_hierarchy()
# {
#     "금융일반": ["경제", "경영"],
#     ...
# }

# 기존 코드와 호환: domain_subdomain.json 형태로 가져오기
domain_subdomain = config.get_domain_subdomain()
# {
#     "경제": [
#         "미시경제학 (수요·공급, 소비자·생산자이론, 시장이론, 후생경제)",
#         ...
#     ]
# }

# 새로운 기능: 특정 정보만 가져오기
domains = config.get_exam_domains("금융일반")  # ["경제", "경영"]
domain_info = config.get_domain_info("금융일반", "경제")
count = config.get_subdomain_count("금융일반", "경제", "미시경제학")  # 32
description = config.get_subdomain_description("금융일반", "경제", "미시경제학")
```

### 2. 편의 함수 사용 (기존 코드와 호환)

```python
from tools.core.exam_config import (
    load_exam_statistics,
    load_exam_hierarchy,
    load_domain_subdomain
)

# 기존 코드를 수정하지 않고도 사용 가능
stats = load_exam_statistics()
hierarchy = load_exam_hierarchy()
domain_subdomain = load_domain_subdomain()
```

### 3. 직접 JSON 로드 (기존 방식 유지 가능)

```python
import json
import os

config_path = os.path.join(onedrive_path, 'evaluation/eval_data/exam_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 직접 접근
exams = config['exams']
all_domains = config['all_domains']
```

## 기존 코드 마이그레이션

### Before (기존 방식)
```python
# 3개 파일을 각각 로드
with open('exam_statistics.json', 'r', encoding='utf-8') as f:
    stats = json.load(f)

with open('exam_hierarchy.json', 'r', encoding='utf-8') as f:
    hierarchy = json.load(f)

with open('domain_subdomain.json', 'r', encoding='utf-8') as f:
    domain_subdomain = json.load(f)
```

### After (새로운 방식)
```python
from tools.core.exam_config import ExamConfig

config = ExamConfig()
stats = config.get_exam_statistics()
hierarchy = config.get_exam_hierarchy()
domain_subdomain = config.get_domain_subdomain()
```

## 장점

1. **단일 파일 관리**: 3개 파일 대신 1개 파일로 관리
2. **데이터 일관성**: 모든 정보가 한 곳에 있어 일관성 보장
3. **타입 안정성**: ExamConfig 클래스로 안전한 접근
4. **하위 호환성**: 기존 코드 수정 없이 사용 가능
5. **확장성**: 새로운 정보 추가가 쉬움
6. **검증**: 파일 경로 자동 검색 및 오류 처리

## 예제: step5_create_exam.py 마이그레이션

### 기존 코드
```python
stats_file = os.path.join(
    self.onedrive_path,
    'evaluation/eval_data/exam_statistics.json'
)
with open(stats_file, 'r', encoding='utf-8') as f:
    stats = json.load(f)
```

### 새로운 코드
```python
from tools.core.exam_config import ExamConfig

config = ExamConfig()
stats = config.get_exam_statistics()
```

## 예제: qna_subdomain_classifier.py 마이그레이션

### 기존 코드
```python
domain_subdomain_path = os.path.join(
    self.onedrive_path, 
    'evaluation/eval_data/domain_subdomain.json'
)
with open(domain_subdomain_path, 'r', encoding='utf-8') as f:
    return json.load(f)
```

### 새로운 코드
```python
from tools.core.exam_config import ExamConfig

config = ExamConfig()
return config.get_domain_subdomain()
```

