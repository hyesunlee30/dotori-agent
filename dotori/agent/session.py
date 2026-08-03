import logging
from dataclasses import dataclass, field
from typing import Any

from dotori.config import config

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    limit: int = 32000

    @property
    def used_ratio(self) -> float:
        if self.limit == 0:
            return 0.0
        return self.total_tokens / self.limit

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.total_tokens)


class TokenTracker:
    """Tracks context token usage for a session."""

    def __init__(self, limit: int = 32000):
        self.limit = limit
        self._prompt_tokens = 0
        self._completion_tokens = 0

    def update(self, prompt_tokens: int, completion_tokens: int):
        self._prompt_tokens += prompt_tokens
        self._completion_tokens += completion_tokens
        logger.debug(
            "Token update: prompt=%d, completion=%d, total=%d/%d",
            prompt_tokens, completion_tokens,
            self.total, self.limit
        )

    @property
    def total(self) -> int:
        return self._prompt_tokens + self._completion_tokens

    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self._completion_tokens

    def get_usage(self) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            total_tokens=self.total,
            limit=self.limit,
        )


@dataclass
class Message:
    role: str
    content: str
    tokens: int = 0


class ContextWindowManager:
    """Manages sliding context window for a session.

    Keeps only: first prompt + latest converted code + most recent error logs.
    Removes intermediate conversation history to stay within token limits.
    """

    def __init__(self, limit: int = 32000):
        self.limit = limit
        self._messages: list[Message] = []
        self._first_prompt: Message | None = None
        self._latest_code: Message | None = None
        self._latest_error: Message | None = None

    def add(self, message: Message):
        self._messages.append(message)
        if self._first_prompt is None and message.role == "user":
            self._first_prompt = message
        if message.role == "assistant" and "```" in message.content:
            self._latest_code = message
        if "error" in message.content.lower() or "traceback" in message.content.lower():
            self._latest_error = message

    def trim(self) -> list[Message]:
        """Return trimmed message list keeping only essential messages."""
        essential: list[Message] = []
        if self._first_prompt:
            essential.append(self._first_prompt)
        if self._latest_code:
            essential.append(self._latest_code)
        if self._latest_error:
            essential.append(self._latest_error)
        remaining = [m for m in self._messages if m not in essential]
        if remaining:
            essential.extend(remaining[-5:])
        self._messages = essential
        logger.debug("Context window trimmed to %d messages", len(self._messages))
        return essential

    def get_messages(self) -> list[Message]:
        return list(self._messages)

    def clear(self):
        self._messages.clear()
        self._first_prompt = None
        self._latest_code = None
        self._latest_error = None

    @property
    def message_count(self) -> int:
        return len(self._messages)


class Session:
    """Isolated session per module (backend-api, frontend-ui)."""

    def __init__(self, module: str):
        self.module = module
        self.token_tracker = TokenTracker(limit=config.agent.CONTEXT_WINDOW_LIMIT)
        self.context_window = ContextWindowManager(limit=config.agent.CONTEXT_WINDOW_LIMIT)
        self._metadata: dict[str, Any] = {}
        self._created_at: str = ""

    def add_message(self, role: str, content: str, tokens: int = 0):
        msg = Message(role=role, content=content, tokens=tokens)
        self.context_window.add(msg)
        self.token_tracker.update(
            prompt_tokens=tokens if role == "user" else 0,
            completion_tokens=tokens if role == "assistant" else 0,
        )

    def get_context(self) -> list[Message]:
        usage = self.token_tracker.get_usage()
        if usage.used_ratio > 0.8:
            return self.context_window.trim()
        return self.context_window.get_messages()

    def reset(self):
        self.context_window.clear()
        self.token_tracker = TokenTracker(limit=self.token_tracker.limit)
        self._metadata.clear()

    @property
    def usage(self) -> TokenUsage:
        return self.token_tracker.get_usage()
