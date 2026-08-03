from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HookContext:
    """Hook execution context passed through the hook chain."""
    module: str = ""
    step: str = ""
    state: dict = field(default_factory=dict)
    error: Exception | None = None


class Hook(ABC):
    """Abstract base class for all hooks."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def before(self, ctx: HookContext) -> HookContext:
        """Execute before the main operation."""
        ...

    @abstractmethod
    def after(self, ctx: HookContext) -> HookContext:
        """Execute after the main operation."""
        ...


class OnRequestHook(Hook):
    """Rewrites prompts when receiving user input for legacy conversion."""

    @property
    def name(self) -> str:
        return "OnRequestHook"

    def before(self, ctx: HookContext) -> HookContext:
        if "prompt" in ctx.state:
            prompt = ctx.state["prompt"]
            module = ctx.module or "unknown"
            ctx.state["prompt"] = (
                f"[Module: {module}] {prompt}"
            )
        return ctx

    def after(self, ctx: HookContext) -> HookContext:
        return ctx


class BeforeSendHook(Hook):
    """Checks token usage before sending, compresses context at 50-80%."""

    def __init__(self, token_tracker: Any = None, compression_threshold: float = 0.5,
                 max_threshold: float = 0.8):
        self.token_tracker = token_tracker
        self.compression_threshold = compression_threshold
        self.max_threshold = max_threshold

    @property
    def name(self) -> str:
        return "BeforeSendHook"

    def before(self, ctx: HookContext) -> HookContext:
        if self.token_tracker is None:
            return ctx
        usage = self.token_tracker.get_usage()
        if usage is None:
            return ctx
        if usage.used_ratio >= self.max_threshold:
            ctx.state["needs_compression"] = True
            ctx.state["compression_ratio"] = self.max_threshold
        elif usage.used_ratio >= self.compression_threshold:
            ctx.state["warning"] = "Token usage high, consider compressing context"
        return ctx

    def after(self, ctx: HookContext) -> HookContext:
        return ctx


class OnToolCallHook(Hook):
    """Guards tool call arguments before execution."""

    @property
    def name(self) -> str:
        return "OnToolCallHook"

    def before(self, ctx: HookContext) -> HookContext:
        tool_name = ctx.state.get("tool_name", "")
        tool_args = ctx.state.get("tool_args", {})
        if not tool_name:
            ctx.error = ValueError("Tool call missing tool_name")
            return ctx
        if ctx.module and ctx.state.get("module") != ctx.module:
            ctx.state["module_mismatch"] = True
        return ctx

    def after(self, ctx: HookContext) -> HookContext:
        return ctx


class OnToolResultHook(Hook):
    """Detects repeated tool calls (3+ times triggers a reminder)."""

    def __init__(self):
        self._call_counts: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "OnToolResultHook"

    def before(self, ctx: HookContext) -> HookContext:
        return ctx

    def after(self, ctx: HookContext) -> HookContext:
        tool_name = ctx.state.get("tool_name", "unknown")
        self._call_counts[tool_name] = self._call_counts.get(tool_name, 0) + 1
        count = self._call_counts[tool_name]
        if count >= 3:
            ctx.state["repeated_tool_warning"] = (
                f"Tool '{tool_name}' called {count} times. "
                "Consider reviewing the approach."
            )
        return ctx


class HookRegistry:
    """Manages hook registration and execution."""

    def __init__(self):
        self._hooks: dict[str, list[Hook]] = {}

    def register(self, hook: Hook):
        self._hooks.setdefault(hook.name, []).append(hook)

    def unregister(self, hook_name: str):
        self._hooks.pop(hook_name, None)

    def execute_before(self, ctx: HookContext) -> HookContext:
        for hooks in self._hooks.values():
            for hook in hooks:
                ctx = hook.before(ctx)
                if ctx.error:
                    return ctx
        return ctx

    def execute_after(self, ctx: HookContext) -> HookContext:
        for hooks in self._hooks.values():
            for hook in reversed(hooks):
                ctx = hook.after(ctx)
        return ctx

    def execute(self, ctx: HookContext) -> HookContext:
        ctx = self.execute_before(ctx)
        if ctx.error:
            return self.execute_after(ctx)
        ctx = self.execute_after(ctx)
        return ctx
