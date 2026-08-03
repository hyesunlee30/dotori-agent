# Dotori Agent - 3단계 구현 계획

## 구현 파일 구조

```
dotori/
├── __init__.py
├── config.py              # Phase 0: 설정 클래스 (setting.md 기반)
├── hooks/
│   ├── __init__.py
│   └── base.py            # Phase 1: 훅 기반 생명주기 제어
├── agent/
│   ├── __init__.py
│   ├── session.py         # Phase 1: 세션 및 컨텍스트 윈도우 관리
│   ├── graph.py           # Phase 1+3: LangGraph 에이전트 루프 + 자아성찰
│   └── sub_agent.py       # Phase 3: 서브에이전트 위임 패턴
├── tools/
│   ├── __init__.py
│   └── shell.py           # Phase 2: 범용 도구 + 스킬 구조
├── skills/
│   └── __init__.py        # Phase 2: 스킬 문서 로딩
├── parsers/
│   └── __init__.py
└── validators/
    └── __init__.py
```

## Phase 1: 기본 구조 (Turn-Iteration-Session + 훅)

### 1. hooks/base.py - 훅 기반 생명주기 제어
- `Hook` 추상 베이스 클래스
- `OnRequestHook`: 사용자 입력 전달 시 프롬프트 리라이팅
- `BeforeSendHook`: 전송 직전 토큰 사용량 체크 (50-80% 시 압축)
- `OnToolCallHook`: 도구 실행 전 인자 가드레일 검사
- `OnToolResultHook`: 동일 도구 연속 호출 감지 (3회 이상 시 리마인더)
- `HookRegistry`: 훅 등록 및 실행 관리

### 2. agent/session.py - 세션 및 컨텍스트 윈도우 관리
- `Session`: 단위(Unit/Class)별 세션 격리
- `ContextWindowManager`: 메시지 히스토리 슬라이딩 (최초 프롬프트 + 최신 코드 + 최근 에러만 유지)
- `TokenTracker`: 컨텍스트 토큰 사용량 추적

### 3. agent/graph.py - LangGraph 에이전트 루프
- `AgentState`: LangGraph 상태 정의 (messages, tools, retry_count, etc.)
- `create_agent_graph(): 상태 머신 그래프 구축
- 훅 통합: `before_send`, `on_tool_result` 노드
- 턴/이터레이션/세션 구조 구현

## Phase 2: 범용 도구 + 스킬 구조

### 4. tools/shell.py - 범용 Shell 도구
- `ShellTool`: Terminal/Shell 기본 프로세스 실행 도구 1개
- 실행 결과 비동기 반환
- 타임아웃 및 에러 처리

### 5. skills/__init__.py - 스킬 문서 로딩
- `Skill`: 마크다운 기반 스킬 정의
- `SkillLoader`: 스킬 문서 동적 로딩
- 모델이 필요할 때 스킬 컨텍스트 주입

## Phase 3: 심화 패턴

### 6. agent/sub_agent.py - 서브에이전트 위임 패턴
- `SubAgent`: 독립 세션 가진 서브에이전트
- 메인 세션 컨텍스트 50% 이하 유지
- 최종 요약 결과만 메인 세션 반환

### 7. agent/graph.py - Goal 자아성찰 루프
- `SelfReflectionNode`: 턴 종료 시 자아성찰 상태 검사
- "테스트 통과?", "조건 충족?" 판정
- 미달성 시 새 프롬프트 생성 → 요청 큐 삽입 → 다음 턀

## 구현 순서
1. config.py (기반 설정)
2. hooks/base.py (훅 아키텍처)
3. agent/session.py (세션 관리)
4. agent/graph.py (에이전트 루프 Phase 1)
5. tools/shell.py (범용 도구 Phase 2)
6. skills/__init__.py (스킬 로딩 Phase 2)
7. agent/sub_agent.py (서브에이전트 Phase 3)
8. agent/graph.py (자아성찰 루프 Phase 3 추가)
