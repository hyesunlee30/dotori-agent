1. 모델 및 파라미터 세팅
   - Temperature 0.1 고정 (동일한 레거시 입력에 대해 항상 일관되고 정확한 코드)
2. 에이전트 시스템 페르소나 및 스킹
   - Qwen 계열 모델은 System Prompt로 역할, 제약사항, 출력 형식을 명확히 정의해 줄 때 성능이 극대화된다. 

```
[System Role]
당신은 15년 경력의 Enterprise System Legacy Modernization Architect입니다. 
당신의 유일한 임무는 레거시 코드와 명세서를 분석하여 최신 아키텍처 코드로 완벽히 변환하는 것입니다.

[Core Rules]
1. 추측하여 코드를 작성하지 마십시오. 명세서나 기존 코드에 없는 비즈니스 로직은 임의로 추가하지 않습니다.
2. 코드는 반드시 컴파일 가능해야 하며, 단위 테스트를 통과해야 합니다.
3. 결과를 출력할 때는 잡담(Explanaion)을 최소화하고, [변환된 코드] 및 [변경 요약] 형식만 엄격히 준수하십시오.
4. 검증 도구 실행 결과 에러(StackTrace)가 발생하면, 이전 코드의 오류 원인을 정적 분석하여 완벽히 수정한 코드만 다시 제출하십시오.
```

3. 도구 구성 전략 - 도구를 많이 주면 환각에 빠지기 쉽다. 도구는 딱 3가지
   - read_legacy_spec_and_code(조회 도구) : 특정 모듈의 명세서(Markdown)와 레거시 소스 코드를 읽어 오는 도구
   - run_sandbox_compiler_and_test(검증 도구) : 반환된 코드를 실제 Target 저장소 디렉터리에 적용하고, 로컬에서 컴파일/테스트 실행 결과를 받아오는 도구
   - read_test_failure_log(디버깅 도구) : 테스트 실패 시 상세한 StackTrace 및 린트 에러 메시지를 수집하는 도구 
4. 세션 및 컨텍스트 윈도우 관리 전략 : 레거시 마이그레이션에서 가장 쉽게 터지는 문제가 LLM 토큰 초과 및 이전 대화 오염. 세션은 아래 원칙으로 넘겨야 한다.
   - 단위(Unit/Class)별 세션 격리 
   - 메시지 히스토리 슬라이딩(Context Window Trimming) : 최초 프롬프트 + 최후에 변환된 코드 + 가장 최근 에러 로그만 남기고 중간 과정 삭제
5. 실습 및 적용을 위한 기본 세팅 클래스 스켈레톤 작성

```
import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# .env 파일 명시적 로드
load_dotenv()

# ==========================================
# 1. Path Settings (경로 관리)
# ==========================================
@dataclass(frozen=True)
class PathSettings:
    """엔진 내 모든 파일 읽기/쓰기 기준 경로를 안전하게 관리"""
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DOCS_DIR: Path = BASE_DIR / "docs" / "performance"
    TARGET_REPO_DIR: Path = BASE_DIR.parent / "performance-eval-service"
    
    def validate_paths(self):
        """실행 전 필수 디렉터리 존재 여부를 검증합니다."""
        self.DOCS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.TARGET_REPO_DIR.exists():
            logging.warning(f"Target repository not found at {self.TARGET_REPO_DIR}. Directory will be created.")
            self.TARGET_REPO_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# 2. LLM Settings (모델 파라미터 제어)
# ==========================================
@dataclass(frozen=True)
class LLMSettings:
    """환각(Hallucination)을 막기 위한 보수적인 모델 하이퍼파라미터 설정"""
    MODEL_NAME: str = "qwen/qwen-3.6-35b-a3b"
    BASE_URL: str = "https://openrouter.ai/api/v1"
    TEMPERATURE: float = 0.0  # 정밀한 코드 변환을 위한 0.0 고정
    MAX_TOKENS: int = 8192    # 대규모 클래스 및 StackTrace 처리를 위한 여유 공간
    TOP_P: float = 0.95
    
    @property
    def api_key(self) -> str:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key or key == "your-openrouter-api-key-here":
            logging.error("Critical: OPENROUTER_API_KEY is missing or invalid in .env")
            sys.exit(1)
        return key

# ==========================================
# 3. Agent & Loop Settings (에이전트 제어)
# ==========================================
@dataclass(frozen=True)
class AgentSettings:
    """자가 수정(Self-Correction) 루프의 무한 반복을 막는 안전장치"""
    MAX_RETRY_COUNT: int = 3
    CONTEXT_WINDOW_LIMIT: int = 32000  # Qwen3.6의 컨텍스트 한도 내에서 슬라이딩 윈도우 기준점
    ENABLE_DEBUG_LOGGING: bool = True

# ==========================================
# 4. System Prompts (표준화된 페르소나 및 코드 가이드라인) - 각 프로젝트에 맞게 변경하여 사용
# ==========================================
@dataclass(frozen=True)
class PromptSettings:

    SYSTEM_ARCHITECT_ROLE: str = """
    당신은 15년 경력의 Enterprise System Legacy Modernization Architect입니다. 
    당신의 임무는 레거시 코드를 분석하여 BeyondF Intranet 프로젝트 표준(Backend: Spring Boot 3.3 Layered+Domain DDD, Frontend: React 18 FSD)에 맞춰 완벽한 코드로 변환하는 것입니다.
    """
    
    CODING_GUIDELINES: str = """
    [BeyondF Intranet 코딩 규칙 - 엄격 준수]
    
    1. 공통 및 백엔드 (Java / Spring Boot 3.3):
       - 코딩 스타일: Google Java Style Guide를 준수하며, 백엔드 들여쓰기는 반드시 4-space를 적용합니다.
       - 패키지 및 디렉터리 구조: 모든 비즈니스 코드는 도메인 단위로 분리하며, `feature/{도메인}` 구조 하위에 아래의 세부 패키지 및 폴더 레이아웃을 엄격히 준수하여 구성합니다.
         ```text
         feature/{도메인}/
         ├── controller/
         │   └── {Domain}Controller.java (+ {Domain}ControllerApiDoc 인터페이스 분리)
         ├── service/
         │   ├── {Domain}Service.java (인터페이스)
         │   └── impl/
         │       └── {Domain}ServiceImpl.java (구현체)
         ├── mapper/
         │   └── {Domain}Mapper.java (MapStruct)
         ├── dto/
         │   └── {Domain}Dto.java (최상위 interface 컨테이너 및 내부 Request/Response record)
         ├── repository/
         │   ├── {Domain}Repository.java (JpaRepository + QueryRepository 인터페이스 상속)
         │   ├── {Domain}QueryRepository.java (QueryDSL 인터페이스)
         │   └── impl/
         │       └── {Domain}RepositoryImpl.java (QueryDSL 구현체)
         └── domain/
             └── {Domain}.java (JPA Entity, BaseEntity 상속)
         ```
       - API 문서화 분리 패턴: 컨트롤러의 순수 비즈니스 로직 가독성을 높이기 위해, API 문서화 어노테이션(Swagger/OpenAPI)은 `{Domain}ControllerApiDoc` 인터페이스에 집중시키고, 실제 `{Domain}Controller` 구현체는 이 인터페이스를 구현(implements)합니다. **컨트롤러 구현체 클래스 내부에 문서화 어노테이션을 직접 작성하지 않습니다.**
       - DTO 패턴: DTO는 불변성을 보장하는 Java `record`를 사용하며, 최상위 컨테이너 `interface`(예: `EmployeeDto`) 내부에 `interface Request`, `interface Response`로 그룹화하여 선언합니다. (`new` 연산자 차단을 위해 반드시 interface 사용)
       - 매핑 및 감사(Audit): 객체 간 변환 시 MapStruct(`@Mapper(componentModel = "spring")`)를 적극 활용합니다. Entity는 BaseEntity(등록자, 수정자, 등록일시, 수정일시 자동 관리)를 상속받으며, 래퍼 클래스만을 사용합니다.
       - 예외 및 유효성: `@Valid`와 Bean Validation을 사용하며, 응답은 공통 `ApiResponse` 포맷을 따릅니다.
       
    2. 프론트엔드 (React / Ant Design / FSD):
       - 패키지 및 린트: `pnpm` 환경을 기준으로 하며, Feature-Sliced Design (FSD) 아키텍처 규칙을 엄격히 준수합니다 (하위 레이어는 상위 레이어를 import 불가).
       - 컴포넌트 & 스타일: `export default`를 지양하고 **Named Export(`export const`)**를 사용합니다. 스타일은 Styled Component 방식을 사용하며, 컴포넌트 간격은 `Flex` 컴포넌트를 우선 사용합니다.
       - AntD 주의사항: `<Tag />`의 `size` prop 사용 금지, `Input.Group` 대신 `Space.Compact` 사용, `message`/`modal`은 반드시 `App.useApp()` 훅을 통해 추출하여 사용합니다.
       - 그리드: ag-Grid Community를 사용하며, 셀 내부에 AntD 컴포넌트 결합 시 `valueGetter`와 `valueFormatter`의 역할을 명확히 구분합니다. `AgGridReact` 사용 시 `theme` 객체와 `className`을 동시에 지정하지 않습니다.
       - 다국어: `usePageTranslation` 훅을 사용해 `{t("key", "한국어")}` 형식을 필수 적용합니다.
       
    3. 공통 원칙:
       - 매직 넘버 금지: 비즈니스 로직 내의 상수는 의미 있는 이름의 UPPER_SNAKE_CASE 상수로 추출합니다.
       - 조작 금지: 주어진 레거시 코드와 명세서에 존재하지 않는 비즈니스 로직을 임의로 추론하거나 추가하지 않습니다.
    """
    
    ERROR_CORRECTION_INSTRUCTION: str = """
    [자가 수정(Self-Correction) 지침]
    이전 변환 코드에서 컴파일, 린트 또는 단위 테스트 실패가 발생했습니다.
    제공된 StackTrace와 검증 에러 로그를 분석하여 원인을 파악하고, BeyondF Intranet의 프로젝트 아키텍처 및 코딩 컨벤션을 완벽히 준수한 상태로 수정된 전체 코드를 다시 출력하십시오.
    """

# ==========================================
# 5. Global Config Context (싱글톤)
# ==========================================
@dataclass(frozen=True)
class DotoriConfig:
    """전역에서 접근 가능한 설정 객체 컨테이너입니다."""
    paths: PathSettings = field(default_factory=PathSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    prompts: PromptSettings = field(default_factory=PromptSettings)
    
    def setup_logging(self):
        """엔진 구동을 위한 글로벌 로깅 포맷을 설정합니다."""
        level = logging.DEBUG if self.agent.ENABLE_DEBUG_LOGGING else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

# 프로젝트 내에서 사용할 싱글톤 인스턴스
config = DotoriConfig()

# 초기화 시점에 경로 검증 및 로깅 세팅 실행
config.paths.validate_paths()
config.setup_logging()
```
