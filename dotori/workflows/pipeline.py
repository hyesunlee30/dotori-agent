import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from dotori.config import config
from dotori.workflows.tasks import (
    Task,
    TaskResult,
    PipelineStatus,
    PipelineResult,
    ParseExpressRoutesTask,
    ParseMongooseSchemasTask,
    ParseReactComponentsTask,
    ExtractBusinessLogicTask,
    ConvertBackendTask,
    ConvertFrontendTask,
    ValidateJavaSyntaxTask,
    ValidateFSDStructureTask,
    RunBackendBuildTask,
    RunFrontendBuildTask,
    GenerateReportTask,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Simple Python DAG pipeline orchestrator.

    No external dependencies - just classes and functions.
    Tasks execute sequentially or in parallel based on dependencies.
    """

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._results: dict[str, TaskResult] = {}

    def add_task(self, task: Task, depends_on: list[str] = None):
        """Add a task with optional dependencies."""
        self.tasks[task.name] = task
        self._dependencies[task.name] = depends_on or []

    def _are_dependencies_met(self, task_name: str, completed: set[str]) -> bool:
        """Check if all dependencies for a task are completed."""
        deps = self._dependencies.get(task_name, [])
        return all(dep in completed for dep in deps)

    def execute(self, context: dict = None) -> PipelineResult:
        """Execute the full pipeline DAG."""
        start_time = time.time()
        context = context or {}
        completed: set[str] = set()
        failed_tasks: list[str] = []
        errors: list[str] = []

        logger.info("=" * 60)
        logger.info("WORKFLOW PIPELINE STARTED")
        logger.info("=" * 60)

        remaining = set(self.tasks.keys())

        while remaining:
            # Find tasks whose dependencies are all met
            ready = [
                name for name in remaining
                if self._are_dependencies_met(name, completed)
            ]

            if not ready:
                # Circular dependency or missing dependency
                errors.append(f"Cannot proceed: remaining tasks {remaining}")
                break

            # Execute ready tasks sequentially
            for task_name in ready:
                task = self.tasks[task_name]
                logger.info(f"[PIPELINE] Executing task: {task_name}")

                task_start = time.time()
                try:
                    result = task.execute(context)
                    task_duration = (time.time() - task_start) * 1000
                    result.duration_ms = task_duration

                    self._results[task_name] = result

                    if result.success:
                        logger.info(f"[PIPELINE] ✓ {task_name} completed ({task_duration:.0f}ms)")
                        completed.add(task_name)
                        remaining.discard(task_name)

                        # Pass results to next tasks via context
                        if result.data:
                            context.update(result.data)

                    else:
                        logger.error(f"[PIPELINE] ✗ {task_name} failed: {result.error}")
                        failed_tasks.append(task_name)
                        errors.append(f"{task_name}: {result.error}")
                        completed.add(task_name)
                        remaining.discard(task_name)

                except Exception as e:
                    task_duration = (time.time() - task_start) * 1000
                    logger.error(f"[PIPELINE] ✗ {task_name} exception: {e}", exc_info=True)
                    failed_tasks.append(task_name)
                    errors.append(f"{task_name}: {str(e)}")
                    completed.add(task_name)
                    remaining.discard(task_name)

        total_duration = (time.time() - start_time) * 1000

        # Determine pipeline status
        if not failed_tasks:
            status = PipelineStatus.COMPLETED
        elif completed:
            status = PipelineStatus.PARTIAL
        else:
            status = PipelineStatus.FAILED

        logger.info("=" * 60)
        logger.info(f"WORKFLOW PIPELINE {status.value.upper()} ({total_duration:.0f}ms)")
        logger.info(f"  Completed: {len(completed)}/{len(self.tasks)}")
        logger.info(f"  Failed: {len(failed_tasks)}")
        logger.info("=" * 60)

        return PipelineResult(
            status=status,
            duration_ms=total_duration,
            errors=errors,
        )

    def get_result(self, task_name: str) -> TaskResult | None:
        return self._results.get(task_name)


def build_backend_pipeline() -> Pipeline:
    """Build the backend conversion pipeline DAG."""
    pipeline = Pipeline()

    # Phase 1: Parse (sequential)
    pipeline.add_task(ParseExpressRoutesTask())
    pipeline.add_task(ParseMongooseSchemasTask())
    pipeline.add_task(ExtractBusinessLogicTask())

    # Phase 2: Convert (depends on parsing)
    pipeline.add_task(
        ConvertBackendTask(),
        depends_on=["parse_express_routes", "parse_mongoose_schemas", "extract_business_logic"]
    )

    # Phase 3: Validate (depends on conversion)
    pipeline.add_task(
        ValidateJavaSyntaxTask(),
        depends_on=["convert_backend_to_spring"]
    )

    # Phase 4: Build (depends on validation)
    pipeline.add_task(
        RunBackendBuildTask(),
        depends_on=["validate_java_syntax"]
    )

    return pipeline


def build_frontend_pipeline() -> Pipeline:
    """Build the frontend conversion pipeline DAG."""
    pipeline = Pipeline()

    # Phase 1: Parse
    pipeline.add_task(ParseReactComponentsTask())

    # Phase 2: Convert
    pipeline.add_task(
        ConvertFrontendTask(),
        depends_on=["parse_react_components"]
    )

    # Phase 3: Validate
    pipeline.add_task(
        ValidateFSDStructureTask(),
        depends_on=["convert_frontend_to_fsd"]
    )

    # Phase 4: Build
    pipeline.add_task(
        RunFrontendBuildTask(),
        depends_on=["validate_fsd_structure"]
    )

    return pipeline


def build_full_pipeline() -> Pipeline:
    """Build the full backend + frontend conversion pipeline."""
    pipeline = Pipeline()

    # Phase 1: Parse (all parsing tasks, no dependencies)
    pipeline.add_task(ParseExpressRoutesTask())
    pipeline.add_task(ParseMongooseSchemasTask())
    pipeline.add_task(ParseReactComponentsTask())
    pipeline.add_task(ExtractBusinessLogicTask())

    # Phase 2: Convert (depends on parsing)
    pipeline.add_task(
        ConvertBackendTask(),
        depends_on=["parse_express_routes", "parse_mongoose_schemas", "extract_business_logic"]
    )
    pipeline.add_task(
        ConvertFrontendTask(),
        depends_on=["parse_react_components"]
    )

    # Phase 3: Validate (depends on conversion)
    pipeline.add_task(
        ValidateJavaSyntaxTask(),
        depends_on=["convert_backend_to_spring"]
    )
    pipeline.add_task(
        ValidateFSDStructureTask(),
        depends_on=["convert_frontend_to_fsd"]
    )

    # Phase 4: Build (depends on validation)
    pipeline.add_task(
        RunBackendBuildTask(),
        depends_on=["validate_java_syntax"]
    )
    pipeline.add_task(
        RunFrontendBuildTask(),
        depends_on=["validate_fsd_structure"]
    )

    # Phase 5: Report (depends on everything)
    pipeline.add_task(
        GenerateReportTask(),
        depends_on=[
            "run_backend_build",
            "run_frontend_build",
        ]
    )

    return pipeline


def run_workflow_pipeline(
    legacy_dir: Path = None,
    target_dir: Path = None,
    llm_client: Any = None,
) -> PipelineResult:
    """Run the full workflow pipeline with convenient API.
    
    Args:
        legacy_dir: Path to legacy code directory (e.g., /repos/legacy)
        target_dir: Path for migrated output (e.g., /repos/migrated)
        llm_client: Optional LLM client for conversion
    
    Returns:
        PipelineResult with status and task results
    """
    legacy_dir = legacy_dir or config.paths.LEGACY_BACKEND_DIR.parent
    target_dir = target_dir or config.paths.TARGET_OUTPUT_DIR

    context = {
        "legacy_backend_dir": legacy_dir / "backend-api",
        "legacy_frontend_dir": legacy_dir / "frontend-ui",
        "target_backend_dir": target_dir / "backend",
        "target_frontend_dir": target_dir / "frontend",
        "system_prompt": config.prompts.SYSTEM_ARCHITECT_ROLE,
    }

    pipeline = build_full_pipeline()
    result = pipeline.execute(context)

    # Attach task results for easy access
    result.backend = pipeline.get_result("run_backend_build")
    result.frontend = pipeline.get_result("run_frontend_build")

    return result


def run_multi_repo_pipeline(
    legacy_dirs: list[Path],
    target_dir: Path,
    llm_client: Any = None,
) -> dict[str, PipelineResult]:
    """Run workflow pipeline for multiple legacy repositories.
    
    Args:
        legacy_dirs: List of paths to legacy repository directories
        target_dir: Base path for migrated output
        llm_client: Optional LLM client for conversion
    
    Returns:
        Dict mapping legacy dir name to PipelineResult
    """
    results = {}
    
    for legacy_dir in legacy_dirs:
        # Use repo name as output subdirectory
        repo_name = legacy_dir.name
        repo_target = target_dir / repo_name
        
        result = run_workflow_pipeline(
            legacy_dir=legacy_dir,
            target_dir=repo_target,
            llm_client=llm_client,
        )
        
        results[repo_name] = result
        logger.info(f"Pipeline result for {repo_name}: {result.status.value}")
        
        if result.errors:
            logger.warning(f"  Errors: {result.errors}")
    
    return results
