import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# 1. Path Settings (Legacy Conversion)
# ==========================================
@dataclass
class PathSettings:
    BASE_DIR: Path = Path(__file__).resolve().parent
    LEGACY_BACKEND_DIR: Path = None
    LEGACY_FRONTEND_DIR: Path = None
    TARGET_OUTPUT_DIR: Path = None
    DOCS_DIR: Path = BASE_DIR.parent / "document" / "dev-note"
    
    # Multi-repo support: additional legacy directories
    LEGACY_DIRS: list[Path] = field(default_factory=list)

    def __post_init__(self):
        # Set defaults only if not provided via parameters
        if self.LEGACY_BACKEND_DIR is None:
            object.__setattr__(self, 'LEGACY_BACKEND_DIR', self.BASE_DIR.parent / "legacy" / "backend-api")
        if self.LEGACY_FRONTEND_DIR is None:
            object.__setattr__(self, 'LEGACY_FRONTEND_DIR', self.BASE_DIR.parent / "legacy" / "frontend-ui")
        if self.TARGET_OUTPUT_DIR is None:
            object.__setattr__(self, 'TARGET_OUTPUT_DIR', self.BASE_DIR.parent / "converted")

    def validate_paths(self):
        self.DOCS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.LEGACY_BACKEND_DIR.exists():
            logging.warning(f"Legacy backend not found at {self.LEGACY_BACKEND_DIR}")
        if not self.LEGACY_FRONTEND_DIR.exists():
            logging.warning(f"Legacy frontend not found at {self.LEGACY_FRONTEND_DIR}")
        self.TARGET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Validate multi-repo directories
        for i, legacy_dir in enumerate(self.LEGACY_DIRS):
            if not legacy_dir.exists():
                logging.warning(f"Legacy repo {i+1} not found at {legacy_dir}")


# ==========================================
# 2. LLM Settings
# ==========================================
@dataclass(frozen=True)
class LLMSettings:
    MODEL_NAME: str = "qwen/qwen3-32b"
    BASE_URL: str = "https://openrouter.ai/api/v1"
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 8192
    TOP_P: float = 0.95

    @property
    def api_key(self) -> str:
        key = os.getenv("OPENROUTER_API_KEY")
        if not key or key == "your-openrouter-api-key-here":
            logging.error("Critical: OPENROUTER_API_KEY is missing or invalid in .env")
            sys.exit(1)
        return key


# ==========================================
# 3. Agent & Loop Settings
# ==========================================
@dataclass(frozen=True)
class AgentSettings:
    MAX_RETRY_COUNT: int = 3
    CONTEXT_WINDOW_LIMIT: int = 32000
    ENABLE_DEBUG_LOGGING: bool = True


# ==========================================
# 4. Conversion Settings
# ==========================================
@dataclass(frozen=True)
class ConversionSettings:
    SOURCE_BACKEND_LANG: str = "javascript"
    TARGET_BACKEND_LANG: str = "java"
    SOURCE_FRONTEND_LANG: str = "javascript"
    TARGET_FRONTEND_LANG: str = "typescript"
    TARGET_BACKEND_FRAMEWORK: str = "spring-boot-3.3"
    TARGET_FRONTEND_ARCH: str = "fsd"
    TARGET_BACKEND_STYLE: str = "layered-domain"
    DOMAIN_NAME: str = "evaluation"


# ==========================================
# 5. System Prompts (Legacy Conversion)
# ==========================================
@dataclass(frozen=True)
class PromptSettings:
    SYSTEM_ARCHITECT_ROLE: str = """
[System Role]
You are a 15-year veteran Enterprise System Legacy Modernization Architect.
Your sole mission is to analyze legacy Node.js/Express + React code and
perfectly convert it to Spring Boot 3.3 Layered+Domain DDD + React 18 FSD architecture.
    """

    CODING_GUIDELINES: str = """
[BeyondF Intranet Coding Rules - Strict Compliance]

1. Backend (Java / Spring Boot 3.3):
   - Style: Google Java Style Guide, 4-space indentation
   - Package structure: feature/{domain}/ with controller/, service/, mapper/, dto/, repository/, domain/
   - API Documentation: Separate into {Domain}ControllerApiDoc interface, implementation uses implements
   - DTO: Use Java record, group Request/Response inside top-level interface {Domain}Dto
   - Mapping: Use MapStruct (@Mapper(componentModel = "spring"))
   - Audit: Extend BaseEntity (registrar, modifier, createdAt, updatedAt)
   - Validation: @Valid + Bean Validation, use common ApiResponse format

2. Frontend (React / Ant Design / FSD):
   - Feature-Sliced Design (FSD) architecture strictly enforced
   - Use Named Export (export const), avoid export default
   - Styled Components + Flex components preferred
   - AntD: No Tag size prop, use Space.Compact, extract message/modal via App.useApp()
   - ag-Grid Community, distinguish valueGetter vs valueFormatter clearly
   - usePageTranslation hook required: {t("key", "Korean text")}

3. Common Principles:
   - No magic numbers: Extract constants as UPPER_SNAKE_CASE
   - No speculation: Do not add business logic not present in legacy code or specs
    """

    ERROR_CORRECTION_INSTRUCTION: str = """
[Self-Correction Guidelines]
Compilation, lint, or unit test failed in the previous converted code.
Analyze the provided StackTrace and validation error logs, identify the root cause,
and output the corrected full code that fully complies with
BeyondF Intranet architecture and coding conventions.
    """

    BACKEND_CONVERSION_GUIDE: str = """
[Node.js/Express to Spring Boot 3.3 Conversion Guide]

1. Express Router to Spring Controller:
   - GET /api/evaluations -> @GetMapping("/evaluations")
   - POST /api/evaluations -> @PostMapping("/evaluations")
   - PUT /api/evaluations/:id -> @PutMapping("/evaluations/{id}")
   - DELETE /api/evaluations/:id -> @DeleteMapping("/evaluations/{id}")
   - req.params.id -> @PathVariable String id
   - req.body -> @RequestBody EvaluationDto.Request
   - res.json({...}) -> ResponseEntity<ApiResponse<...>>

2. Mongoose Schema to JPA Entity:
   - type: String, required: true -> @Column(nullable = false)
   - type: Number, min: 1, max: 100 -> @Column + @Min(1) @Max(100)
   - enum: ['draft', 'submitted', 'completed'] -> @Enumerated(EnumType.STRING)
   - timestamps: true -> Extend BaseEntity
   - Schema.index({...}) -> Repository method or @Query

3. Controller Logic to Spring Service:
   - await Evaluation.find(...) -> evaluationRepository.findAll(...)
   - await Evaluation.findById(id) -> evaluationRepository.findById(id)
   - await new Evaluation(...).save() -> evaluationRepository.save(entity)
   - Model.aggregate([...]) -> @Query or QueryDSL

4. DTO Pattern:
   - JavaScript object -> Java interface container + record
   - interface EvaluationDto { interface Request { ... } interface Response { ... } }
    """

    FRONTEND_CONVERSION_GUIDE: str = """
[React SPA to FSD Architecture Conversion Guide]

1. FSD Folder Structure:
   src/
   ├── app/                    # App entry point
   ├── features/
   │   └── evaluations/
   │       ├── ui/             # EvaluationList, EvaluationForm, EvaluationStats
   │       ├── api/            # evaluationApi.ts
   │       ├── model/          # types.ts
   │       └── hooks/          # useEvaluations.ts
   ├── entities/
   │   └── evaluation/
   │       ├── model/types.ts
   │       └── ui/
   ├── shared/
   │   ├── api/axios.ts
   │   ├── ui/components/
   │   └── lib/dayjs.ts

2. Conversion Rules:
   - export default -> export const (Named Export)
   - Axios instance -> shared/api/axios.ts single instance
   - Page components -> features/evaluations/ui/
   - antd Form -> features internal form component
   - usePageTranslation hook required

3. AntD Notes:
   - No Tag size prop
   - Use Space.Compact instead of Input.Group
   - Extract message/modal via App.useApp() hook
    """


# ==========================================
# 6. Global Config Context (Singleton)
# ==========================================
@dataclass
class DotoriConfig:
    paths: PathSettings = None
    llm: LLMSettings = field(default_factory=LLMSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    conversion: ConversionSettings = field(default_factory=ConversionSettings)
    prompts: PromptSettings = field(default_factory=PromptSettings)

    def __post_init__(self):
        if self.paths is None:
            object.__setattr__(self, 'paths', PathSettings())

    def setup_logging(self):
        level = logging.DEBUG if self.agent.ENABLE_DEBUG_LOGGING else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# ==========================================
# 7. Config Factory (Parameter-Based)
# ==========================================
def create_config(
    legacy_backend_dir: Optional[Path] = None,
    legacy_frontend_dir: Optional[Path] = None,
    target_output_dir: Optional[Path] = None,
    legacy_dirs: Optional[list[Path]] = None,
) -> DotoriConfig:
    """Create a DotoriConfig with parameter-based paths.
    
    Args:
        legacy_backend_dir: Path to legacy backend code (e.g., /repos/legacy/backend-api)
        legacy_frontend_dir: Path to legacy frontend code (e.g., /repos/legacy/frontend-ui)
        target_output_dir: Path for migrated output (e.g., /repos/migrated/backend)
        legacy_dirs: Additional legacy repository directories to process
    
    Returns:
        Configured DotoriConfig instance
    """
    paths = PathSettings(
        LEGACY_BACKEND_DIR=legacy_backend_dir,
        LEGACY_FRONTEND_DIR=legacy_frontend_dir,
        TARGET_OUTPUT_DIR=target_output_dir,
        LEGACY_DIRS=legacy_dirs or [],
    )
    
    cfg = DotoriConfig(paths=paths)
    cfg.paths.validate_paths()
    cfg.setup_logging()
    
    return cfg


# Default global config (uses hardcoded defaults)
config = DotoriConfig()
config.paths.validate_paths()
config.setup_logging()
