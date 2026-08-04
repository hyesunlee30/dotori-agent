import time
import logging
from pathlib import Path
from typing import Any

from dotori.config import config
from dotori.workflows.pipeline import run_workflow_pipeline, PipelineResult
from dotori.agent.graph import ConversionAgent, ModuleType

logger = logging.getLogger(__name__)


class AgentResult:
    """Result from the agent (LangGraph) track."""

    def __init__(self, result: dict):
        self.success = result.get("success", False)
        self.status = result.get("status", "unknown")
        self.module = result.get("module", "")
        self.retry_count = result.get("retry_count", 0)
        self.validation = result.get("validation_result", {})
        self.error = result.get("error", "")
        self.duration_ms = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "status": self.status,
            "module": self.module,
            "retry_count": self.retry_count,
            "validation": self.validation,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class TrackResult:
    """Comparison result between workflow and agent tracks."""

    def __init__(self):
        self.workflow: PipelineResult | None = None
        self.agent_backend: AgentResult | None = None
        self.agent_frontend: AgentResult | None = None
        self.duration_ms: float = 0

    def print_comparison(self):
        """Print a comparison table between the two tracks."""
        print("\n" + "=" * 80)
        print("WORKFLOW vs AGENT - COMPARISON")
        print("=" * 80)

        # Workflow result
        wf = self.workflow
        print(f"\n[WORKFLOW TRACK]")
        print(f"  Status:      {wf.status.value if wf else 'N/A'}")
        print(f"  Duration:    {wf.duration_ms:.0f}ms" if wf else "  Duration:    N/A")
        if wf:
            print(f"  Errors:      {len(wf.errors)}")
            for err in wf.errors[:5]:
                print(f"    - {err}")

        # Agent results
        print(f"\n[AGENT TRACK]")

        ab = self.agent_backend
        print(f"  Backend:")
        print(f"    Status:      {ab.status if ab else 'N/A'}")
        print(f"    Retries:     {ab.retry_count if ab else 'N/A'}")
        print(f"    Success:     {ab.success if ab else 'N/A'}")
        if ab and ab.error:
            print(f"    Error:       {ab.error[:200]}")

        af = self.agent_frontend
        print(f"  Frontend:")
        print(f"    Status:      {af.status if af else 'N/A'}")
        print(f"    Retries:     {af.retry_count if af else 'N/A'}")
        print(f"    Success:     {af.success if af else 'N/A'}")
        if af and af.error:
            print(f"    Error:       {af.error[:200]}")

        # Key differences
        print(f"\n[KEY DIFFERENCES]")
        print(f"  Workflow:    Linear DAG, fixed retry (3x), no self-reflection")
        print(f"  Agent:       State machine, self-reflection loop, context management")
        print(f"  Workflow:    LLM call: 2x (backend + frontend)")
        print(f"  Agent:       LLM call: 2x+ (retry loop on validation failure)")
        print(f"  Workflow:    Cost: lower")
        print(f"  Agent:       Cost: higher (potential multiple LLM calls)")
        print(f"  Workflow:    Quality: standard conversion")
        print(f"  Agent:       Quality: adaptive (error analysis + correction)")

        print("\n" + "=" * 80)


def run_both_tracks(
    legacy_dir: Path = None,
    target_dir: Path = None,
    llm_client: Any = None,
) -> TrackResult:
    """Run both workflow and agent tracks and return comparison result."""
    start_time = time.time()
    result = TrackResult()

    legacy_dir = legacy_dir or config.paths.LEGACY_BACKEND_DIR.parent
    target_dir = target_dir or config.paths.TARGET_OUTPUT_DIR

    # ===== Track 1: Workflow Pipeline =====
    logger.info("=" * 60)
    logger.info("TRACK 1: WORKFLOW PIPELINE")
    logger.info("=" * 60)
    wf_start = time.time()

    try:
        wf_result = run_workflow_pipeline(
            legacy_dir=legacy_dir,
            target_dir=target_dir,
            llm_client=llm_client,
        )
        result.workflow = wf_result
    except Exception as e:
        logger.error(f"Workflow track failed: {e}", exc_info=True)
        result.workflow = PipelineResult(
            status=PipelineStatus.FAILED,
            duration_ms=(time.time() - wf_start) * 1000,
            errors=[str(e)],
        )

    wf_duration = (time.time() - wf_start) * 1000
    logger.info(f"Workflow track completed in {wf_duration:.0f}ms")

    # ===== Track 2: Agent Pipeline =====
    logger.info("=" * 60)
    logger.info("TRACK 2: AGENT PIPELINE")
    logger.info("=" * 60)
    agent_start = time.time()

    agent = ConversionAgent()

    # Backend conversion
    try:
        backend_result = agent.convert("backend-api", ModuleType.BACKEND, output_base=target_dir / "agent" / "backend")
        result.agent_backend = AgentResult(backend_result)
    except Exception as e:
        logger.error(f"Agent backend failed: {e}", exc_info=True)
        result.agent_backend = AgentResult({
            "success": False,
            "status": "failed",
            "module": "backend-api",
            "error": str(e),
        })

    # Frontend conversion
    try:
        frontend_result = agent.convert("frontend-ui", ModuleType.FRONTEND, output_base=target_dir / "agent" / "frontend")
        result.agent_frontend = AgentResult(frontend_result)
    except Exception as e:
        logger.error(f"Agent frontend failed: {e}", exc_info=True)
        result.agent_frontend = AgentResult({
            "success": False,
            "status": "failed",
            "module": "frontend-ui",
            "error": str(e),
        })

    agent_duration = (time.time() - agent_start) * 1000
    logger.info(f"Agent track completed in {agent_duration:.0f}ms")

    result.duration_ms = (time.time() - start_time) * 1000

    return result
