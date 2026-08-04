# Dotori Agent - 단일 기능 검증 가이드

## 목적

복잡한 전체 마이그레이션 파이프라인 대신, **단일 기능(평가 CRUD)** 으로만 전체 워크플로우의 변환 품질을 검증하는 가이드입니다.

## 1. 검증 철학

```
전체 기능 검증 = 단일 기능(평가) 완전 변환 + 빌드 통과 + 검증 통과
```

- **평가(Evaluation)** 은 레거시 코드의 모든 패턴을 포함하는 대표 기능
  - Express Router (GET/POST/PUT/DELETE)
  - Mongoose Schema (필드 타입, enum, min/max, timestamps)
  - Controller CRUD 로직
  - React 페이지 (목록 + 폼)
- 이 하나만 완벽하면 다른 기능도 동일 패턴으로 변환 가능

## 2. 검증 단계

### Step 1: 파싱 검증 (5분)

```bash
# 레거시 코드 파싱 확인
python3 -c "
from dotori.parsers.express_parser import parse_express_routes
from dotori.parsers.mongoose_parser import parse_mongoose_schema
from dotori.parsers.react_parser import parse_react_component
from pathlib import Path

# 1) Express 라우트 파싱
routes = parse_express_routes(Path('legacy/backend-api/routes/evaluations.js'))
print(f'라우트 수: {len(routes.routes)}')
for r in routes.routes:
    print(f'  {r.method} {r.path} -> {r.handler}')

# 2) Mongoose 스키마 파싱
schema = parse_mongoose_schema(Path('legacy/backend-api/models/Evaluation.js'))
print(f'필드 수: {len(schema.fields)}')
for f in schema.fields:
    print(f'  {f.name}: {f.type} required={f.required}')

# 3) React 컴포넌트 파싱
comp = parse_react_component(Path('legacy/frontend-ui/src/pages/EvaluationList.jsx'))
print(f'컴포넌트: {comp.name}')
print(f'  API 호출: {comp.api_calls}')
print(f'  폼 필드: {len(comp.form_fields)}')
"
```

**검증 항목:**
- [ ] Express 라우트 4개 발견 (GET, POST, PUT, DELETE)
- [ ] Mongoose 필드 8개 발견 (title, category, score, status, evaluator, evaluatee, createdAt, updatedAt)
- [ ] React 컴포넌트 2개 발견 (EvaluationList, EvaluationForm)

### Step 2: 에이전트 변환 실행 (10분)

```bash
# 단일 기능 평가 변환 - 파라미터 기반
python3 -c "
from pathlib import Path
from dotori.workflows.pipeline import run_workflow_pipeline

result = run_workflow_pipeline(
    legacy_dir=Path('legacy'),        # 레거시 코드 위치
    target_dir=Path('converted'),     # 출력 위치
)

print(f'상태: {result.status.value}')
print(f'오류: {result.errors}')
print(f'백엔드: {result.backend}')
print(f'프론트엔드: {result.frontend}')
"
```

**검증 항목:**
- [ ] 파싱 단계 성공
- [ ] 변환 단계 성공 (LLM 호출)
- [ ] 검증 단계 통과

### Step 3: 생성 코드 확인 (5분)

```bash
# 생성된 백엔드 구조 확인
find converted/backend -name "*.java" | head -20

# 생성된 프론트엔드 구조 확인
find converted/frontend -name "*.tsx" | head -20
```

**백엔드 필수 파일:**
- [ ] `Evaluation.java` (Entity)
- [ ] `EvaluationRepository.java` (Repository)
- [ ] `EvaluationService.java` (Service)
- [ ] `EvaluationController.java` (Controller)
- [ ] `EvaluationDto.java` (DTO)
- [ ] `EvaluationMapper.java` (Mapper)

**프론트엔드 필수 파일:**
- [ ] `features/evaluations/ui/EvaluationList.tsx`
- [ ] `features/evaluations/ui/EvaluationForm.tsx`
- [ ] `features/evaluations/api/evaluationApi.ts`
- [ ] `features/evaluations/model/types.ts`
- [ ] `shared/api/axios.ts`

### Step 4: 빌드 검증 (10분)

```bash
# 백엔드 빌드
cd converted/backend && ./gradlew build -x test

# 프론트엔드 빌드
cd converted/frontend && pnpm build
```

**검증 항목:**
- [ ] 백엔드 컴파일 에러 없음
- [ ] 프론트엔드 빌드 에러 없음
- [ ] 타입 에러 없음

### Step 5: 검증 규칙 통과 확인

```bash
python3 -c "
from dotori.validators.base import JavaValidator, FrontendValidator

# Java 검증
validator = JavaValidator()

# Entity 검증
with open('converted/backend/Evaluation.java') as f:
    result = validator.validate_syntax(f.read())
    print(f'Entity 문법: {result.passed}')
    print(f'  에러: {result.errors}')

# Controller 검증
with open('converted/backend/EvaluationController.java') as f:
    result = validator.validate_structure(f.read(), 'EvaluationController')
    print(f'Controller 구조: {result.passed}')
    print(f'  에러: {result.errors}')

# Frontend 검증
from dotori.validators.base import FrontendValidator
fv = FrontendValidator()

with open('converted/frontend/EvaluationList.tsx') as f:
    result = fv.validate_named_export(f.read(), 'EvaluationList')
    print(f'Named Export: {result.passed}')
    print(f'  에러: {result.errors}')
"
```

**검증 항목:**
- [ ] Java 괄호/브라켓 매칭
- [ ] Entity에 `@Entity`, `@Id` 존재
- [ ] Controller에 `@RestController`, `@RequestMapping` 존재
- [ ] 프론트엔드 `export const` 사용 (export default 아님)
- [ ] FSD import 규칙 준수

## 3. 전체 파이프라인 흐름도

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 파싱 (Parsing)                                               │
│    Express Routes ──┐                                            │
│    Mongoose Schema ─┼──> Structured Data ──> LLM Prompt          │
│    React Pages  ────┘                                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 변환 (Conversion)                                             │
│    LLM (Self-Correction Loop)                                   │
│    Parse ──> Convert ──> Validate ──> Self-Reflect ──> Fix      │
│                                    │         │                   │
│                                    ▼         │                   │
│                              Complete      Retry (max 3)         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 검증 (Validation)                                             │
│    Java Syntax ──> Structure ──> Build ──> FSD Rules            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 출력 (Output)                                                 │
│    converted/backend/  (Spring Boot 3.3)                        │
│    converted/frontend/ (React FSD)                              │
└─────────────────────────────────────────────────────────────────┘
```

## 4. 파라미터 기반 실행

### 기본 실행 (디폴트 경로)

```bash
python3 -c "
from pathlib import Path
from dotori.workflows.pipeline import run_workflow_pipeline

result = run_workflow_pipeline(
    legacy_dir=Path('legacy'),        # 레거시 코드 위치
    target_dir=Path('converted'),     # 출력 위치
)
print(f'상태: {result.status.value}')
"
```

### 파라미터 기반 실행 (사용자 정의 경로)

```bash
python3 -c "
from pathlib import Path
from dotori.config import create_config
from dotori.workflows.pipeline import run_workflow_pipeline

# 파라미터로 경로 지정
config = create_config(
    legacy_backend_dir=Path('/repos/legacy/backend-api'),
    legacy_frontend_dir=Path('/repos/legacy/frontend-ui'),
    target_output_dir=Path('/repos/migrated'),
)

result = run_workflow_pipeline(
    legacy_dir=Path('/repos/legacy'),
    target_dir=Path('/repos/migrated'),
)
print(f'상태: {result.status.value}')
"
```

### 에이전트 기반 실행 (제품 레벨)

```bash
python3 -c "
from pathlib import Path
from dotori.agent.graph import ConversionAgent

# 파라미터로 경로 지정
agent = ConversionAgent(
    legacy_backend_dir=Path('/repos/legacy/backend-api'),
    legacy_frontend_dir=Path('/repos/legacy/frontend-ui'),
    target_dir=Path('/repos/migrated'),
)

# 전체 변환 실행 (backend + frontend)
results = agent.convert_all()
for module, result in results.items():
    print(f'{module}: {result[\"status\"]} (retries: {result[\"retry_count\"]})')
"
```

### 다중 레거시 레포 실행

```bash
python3 -c "
from pathlib import Path
from dotori.workflows.pipeline import run_multi_repo_pipeline

# 여러 레거시 레포 위치
legacy_dirs = [
    Path('/repos/project-a'),
    Path('/repos/project-b'),
    Path('/repos/project-c'),
]

target_dir = Path('/repos/migrated')

results = run_multi_repo_pipeline(
    legacy_dirs=legacy_dirs,
    target_dir=target_dir,
)

for repo_name, result in results.items():
    print(f'{repo_name}: {result.status.value}')
    if result.errors:
        print(f'  Errors: {result.errors}')
"
```

### 다중 레포 + 에이전트 조합

```bash
python3 -c "
from pathlib import Path
from dotori.agent.graph import ConversionAgent

# 각 레포별로 에이전트 생성
repos = {
    'project-a': Path('/repos/project-a'),
    'project-b': Path('/repos/project-b'),
}

output_base = Path('/repos/migrated')

for repo_name, legacy_dir in repos.items():
    agent = ConversionAgent(
        legacy_backend_dir=legacy_dir / 'backend-api',
        legacy_frontend_dir=legacy_dir / 'frontend-ui',
        target_dir=output_base / repo_name,
    )
    results = agent.convert_all()
    print(f'{repo_name}: {results}')
"
```

## 5. 실패 시 디버깅

| 증상 | 원인 | 해결 |
|------|------|------|
| 파싱 실패 | 레거시 파일 구조 다름 | `parsers/` 수정 |
| 변환 에러 | LLM 응답 포맷 안좋음 | 프롬프트 개선 |
| 검증 실패 | 코딩 규칙 위반 | `skills/` 가이드 확인 |
| 빌드 실패 | 의존성 누락 | `pom.xml`/`build.gradle` 확인 |

## 6. 성공 기준 체크리스트

- [ ] Step 1: 파싱 - 모든 파일 구조 추출 완료
- [ ] Step 2: 변환 - LLM 응답 수신, self-reflection 루프 동작
- [ ] Step 3: 생성 코드 - 모든 필수 파일 생성됨
- [ ] Step 4: 빌드 - 컴파일 에러 없음
- [ ] Step 5: 검증 - 모든 규칙 통과
- [ ] 최종: `converted/` 폴더에 완성된 프로젝트 존재
