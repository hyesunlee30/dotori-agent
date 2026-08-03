import logging
from dataclasses import dataclass, field
from pathlib import Path

from dotori.agent.session import Session
from dotori.config import config

logger = logging.getLogger(__name__)


@dataclass
class SubAgentResult:
    success: bool
    summary: str
    converted_files: dict = field(default_factory=dict)
    error: str = ""


class SubAgent:
    """Sub-agent with independent session for delegating complex conversion tasks.

    Keeps main session context below 50% by delegating complex modules
    to sub-agents that return only a final summary.
    """

    def __init__(self, name: str, parent_session: Session):
        self.name = name
        self.parent_session = parent_session
        self.session = Session(f"{parent_session.module}/{name}")
        self._max_context_ratio = 0.5

    def delegate(self, task: str, context: dict) -> SubAgentResult:
        """Delegate a conversion task to the sub-agent."""
        logger.info(f"Sub-agent '{self.name}' delegating task: {task}")

        self.session.add_message(
            role="user",
            content=f"[Sub-Agent Task]\n{task}\n\n[Context]\n{context}",
        )

        # Check if main session context is getting full
        parent_usage = self.parent_session.usage
        if parent_usage.used_ratio > self._max_context_ratio:
            logger.warning(
                f"Parent context at {parent_usage.used_ratio:.0%}, "
                f"delegating to sub-agent to keep context manageable"
            )

        # Simulate conversion work (in production, this would call LLM)
        try:
            result = self._execute_task(task, context)
            self.session.add_message(
                role="assistant",
                content=f"[Sub-Agent Result]\n{result.summary}",
            )

            # Return only summary to parent (keeps context small)
            return result

        except Exception as e:
            logger.error(f"Sub-agent '{self.name}' failed: {e}")
            return SubAgentResult(
                success=False,
                summary="",
                error=str(e),
            )

    def _execute_task(self, task: str, context: dict) -> SubAgentResult:
        """Execute the delegated conversion task."""
        # In production, this would:
        # 1. Parse the legacy code for this specific task
        # 2. Generate converted code using LLM
        # 3. Validate the output
        # 4. Return only the summary + file paths

        converted_files = {}
        summary_parts = []

        if "backend" in task.lower():
            summary_parts.append("Backend conversion planned: Entity, Repository, Service, Controller, DTO layers")
        if "frontend" in task.lower():
            summary_parts.append("Frontend conversion planned: FSD structure with features/entities/shared layers")

        summary = f"Sub-agent '{self.name}': {'; '.join(summary_parts)}"
        return SubAgentResult(
            success=True,
            summary=summary,
            converted_files=converted_files,
        )
