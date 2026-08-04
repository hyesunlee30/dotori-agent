# dotori-engine

![img.png](img.png)

> **"레거시 도토리를 모아 신뢰할 수 있는 차세대 시스템으로 가공하는 자동화 마이그레이션 제품"**
> **dotori-agent**는 복잡한 레거시 코드를 파악하고 명세서와 대조하여, 컴파일 및 테스트 검증까지 스스로 수행하는 **AI 기반 자가 수정(Self-Correction) 레거시 현대화 엔진**입니다.

---

## 개요

dotori-agent 는 레거시 Node.js/Express + React 코드를 AI(LLM) 를 활용하여 **Spring Boot 3.3 (Java) + React FSD (TypeScript)** 로 자동 변환합니다.

### 주요 기능

| 기능 | 설명 |
|------|------|
| **자동 파싱** | Express 라우트, Mongoose 스키마, React 컴포넌트를 Regex 기반으로 구조화 분석 |
| **AI 변환** | LangGraph 기반 상태 머신이 코드 생성을 수행 |
| **자가 수정** | 검증 실패 시 에러 피드백을 통해 최대 3 회까지 자체 수정 재시도 |
| **동시 비교** | 워크플로우(선형) 트랙과 에이전트(자가수정) 트랙을 병렬 실행하여 결과 비교 |

### 아키텍처 흐름

```
select_module → parse_legacy → inject_skills → convert → validate → self_reflect
                                                                         │
                                                                [passed?] ──yes──→ END
                                                                      │
                                                                     no
                                                                      │
                                                             (retry_count < 3?)
                                                                yes / no
                                                                │     │
                                                             correct  FAILED
                                                                │
                                                             convert (loop)
```

---

## 설치

### 1. 가상 환경 생성

```bash
python3 -m venv .venv
```

### 2. 가상 환경 활성화

```bash
source .venv/bin/activate   # macOS / Linux
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 폴더 구조 생성

```bash
mkdir -p dotori/parsers dotori/agent dotori/validators docs/performance
```

---

## 설정

`.env` 파일을 프로젝트 루트에 생성하고 OpenRouter API 키를 설정하세요:

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

### 설정 옵션

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `OPENROUTER_API_KEY` | *(필수)* | OpenRouter API 키 |
| `MODEL_NAME` | `qwen/qwen-3.6-35b-a3b` | 사용할 LLM 모델 |
| `BASE_URL` | `https://openrouter.ai/api/v1` | LLM API 엔드포인트 |
| `MAX_RETRY_COUNT` | `3` | 자가 수정 최대 재시도 횟수 |
| `CONTEXT_WINDOW_LIMIT` | `32000` | 세션당 토큰 제한 |
| `LEGACY_BACKEND_DIR` | `legacy/backend-api` | 레거시 Express.js 코드 경로 |
| `LEGACY_FRONTEND_DIR` | `legacy/frontend-ui` | 레거시 React 코드 경로 |
| `TARGET_OUTPUT_DIR` | `converted` | 변환 결과 출력 디렉토리 |

---

## 사용 방법

### 1. 워크플로우 파이프라인 실행 (선형 처리)

자가 수정 없이 한 번에 변환합니다:

```bash
python main.py workflow
```

결과: `converted/workflow/`

Python API:

```python
from pathlib import Path
from dotori.workflows.pipeline import run_workflow_pipeline

result = run_workflow_pipeline(
    legacy_dir=Path('legacy'),
    target_dir=Path('converted/workflow'),
)
print(f"Status: {result.status.value}")
```

### 2. AI 에이전트 실행 (자가 수정 포함)

검증 → 자기반성 → 수정의 사이클을 통해 자동으로 코드를 개선합니다:

```bash
python main.py agent
```

결과: `converted/agent/`

Python API:

```python
from pathlib import Path
from dotori.agent.graph import ConversionAgent

agent = ConversionAgent(
    legacy_backend_dir=Path('legacy/backend-api'),
    legacy_frontend_dir=Path('legacy/frontend-ui'),
    target_dir=Path('converted/agent'),
)
results = agent.convert_all(output_base=Path('converted/agent'))
for module, result in results.items():
    print(f"{module}: {result['status']} (retries: {result['retry_count']})")
```

### 3. 양쪽 트랙 비교 실행

워크플로우와 에이전트 결과를 병렬로 실행하고 비교합니다:

```bash
python main.py compare
```

결과: `converted/workflow/`, `converted/agent/`

Python API:

```python
from dotori.runners.compare import run_both_tracks

track_result = run_both_tracks(
    legacy_dir=Path('legacy'),
    target_dir=Path('converted'),
)
track_result.print_comparison()
```

---

## 디렉토리 구조

```
dotori-agent/
├── .env                          # 환경 변수 (API 키 등)
├── requirements.txt              # Python 의존성
├── document/                     # 문서 및 개발 노트
├── legacy/                       # 레거시 소스 코드 (입력)
│   └── backend-api/              # Express.js 백엔드
├── converted/                    # 변환된 코드 (출력)
├── plans/                        # 구현 계획
├── images/                       # 다이어그램
└── dotori/                       # 핵심 엔진
    ├── config.py                 # 중앙 설정
    ├── parsers/                  # 레거시 코드 파서
    │   ├── express_parser.py     # Express 라우트 파싱
    │   ├── mongoose_parser.py    # Mongoose 스키마 파싱
    │   └── react_parser.py       # React 컴포넌트 파싱
    ├── agent/                    # AI 에이전트
    │   ├── graph.py              # LangGraph 상태 머인
    │   ├── session.py            # 컨텍스트 관리
    │   └── sub_agent.py          # 서브에이전트 위임
    ├── validators/               # 코드 검증기
    │   └── base.py               # Java/FSD 검증 규칙
    ├── hooks/                    # 라이프사이클 훅
    ├── tools/                    # 유틸리티 (셸 빌드 도구)
    ├── workflows/                # DAG 파이프라인 오케스트레이터
    └── skills/                   # 변환 가이드 문서
```

---

## 변환 대상

| 레거시 | 목표 |
|--------|------|
| Express.js + Mongoose | Spring Boot 3.3 + JPA (Layered+Domain DDD) |
| React SPA (Ant Design) | React FSD (Feature-Sliced Design) + TypeScript |

백엔드 변환은 Entity, Repository, Service, Controller, DTO, Mapper 파일을 BeyondF 사내Coding 규약을 따라 생성합니다. 프론트엔드 변환은 FSD 구조에 맞춘 `.tsx` 파일, 네임드 익스포트, 번역 훅, 올바른 레이어 임포트를 생성합니다.