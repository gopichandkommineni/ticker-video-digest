"""One way to ask Claude for structured data; two ways to reach Claude.

The pipeline needs the same thing everywhere: a prompt in, a validated pydantic
model out. How that request travels is a deployment detail, so it lives here
rather than in the three modules that make the calls.

**api** — the Anthropic SDK, with a forced tool call carrying the schema. Wants
credentials: ``ANTHROPIC_API_KEY``, or any other source the SDK resolves (an
``ant auth login`` profile counts).

**cli** — shells out to the Claude Code CLI in print mode, passing the same JSON
schema to ``--json-schema``. Wants no API key at all: it borrows whatever the
locally installed ``claude`` is already logged in as. Slower, and each call
carries the CLI's own tool definitions as prompt overhead — though a run's
calls share a prefix, so all but the first are cache reads.

Pick with ``TICKER_DIGEST_LLM_BACKEND=auto|api|cli``. ``api`` and ``cli`` are
commitments. The default, ``auto``, means "whatever works": the API when a key
is present *and accepted*, the CLI otherwise — including when a key is set but
turns out to be a placeholder, which is only discoverable on the first call.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from core.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_CLI_PATH,
    CLAUDE_CLI_TIMEOUT_SECONDS,
    LLM_BACKEND,
)

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# A model that ignores the schema and wraps its JSON in a code fence is wrong
# but recoverable; unwrapping costs nothing and saves a retry.
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class LLMError(RuntimeError):
    """Claude was reached but would not answer usefully.

    A per-call problem: the caller can skip this item and carry on.
    """


class LLMUnavailableError(LLMError):
    """Claude cannot be reached at all — no credentials, no CLI, a timeout.

    Every remaining call would fail the same way, so callers stop rather than
    working through the whole list discovering it once per item.
    """


@dataclass(frozen=True)
class StructuredCall:
    """One request for one validated object."""

    system: str
    user: str
    model: str
    response_model: type[BaseModel]
    tool_name: str
    tool_description: str
    max_tokens: int = 4096


class Backend(Protocol):
    name: str

    def run(self, call: StructuredCall) -> BaseModel: ...


def _retry_prompt(call: StructuredCall, error: ValidationError) -> str:
    return (
        f"{call.user}\n\n"
        "Your previous answer failed schema validation with these errors:\n"
        f"{error}\n\n"
        "Return the corrected data. Match the schema exactly."
    )


# ---------------------------------------------------------------------------
# Anthropic SDK
# ---------------------------------------------------------------------------


class ApiBackend:
    """The SDK, forcing a tool call so the schema is enforced server-side."""

    name = "api"

    def run(self, call: StructuredCall) -> BaseModel:
        client = anthropic.Anthropic()

        system = [
            {
                "type": "text",
                "text": call.system,
                # The system prompt and schema are identical across the videos
                # in a run, so this is the cheap half of every call after the
                # first.
                "cache_control": {"type": "ephemeral"},
            }
        ]
        tools = [
            {
                "name": call.tool_name,
                "description": call.tool_description,
                "input_schema": call.response_model.model_json_schema(),
            }
        ]
        messages: list[dict[str, Any]] = [{"role": "user", "content": call.user}]

        def _call(msgs: list[dict[str, Any]]) -> Any:
            return client.messages.create(
                model=call.model,
                max_tokens=call.max_tokens,
                system=system,  # type: ignore[arg-type]
                messages=msgs,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                tool_choice={"type": "tool", "name": call.tool_name},
            )

        response = _call(messages)
        payload = _tool_input(response, call.tool_name)

        try:
            return call.response_model.model_validate(payload)
        except ValidationError as exc:
            log.warning("%s failed validation, retrying once: %s", call.tool_name, exc)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": _retry_prompt(call, exc)})
            retried = _call(messages)
            return call.response_model.model_validate(
                _tool_input(retried, call.tool_name)
            )


def _tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input  # type: ignore[return-value]
    raise LLMError(f"No {tool_name!r} tool_use block in the response")


# ---------------------------------------------------------------------------
# Claude Code CLI
# ---------------------------------------------------------------------------


class ClaudeCliBackend:
    """``claude -p`` in print mode, with the schema on ``--json-schema``.

    The prompt goes in on stdin, not argv — a transcript is far longer than
    the command-line length limit on macOS.
    """

    name = "cli"

    # Claude Code prefers these over the claude.ai login it already holds, so a
    # stale or placeholder key in the environment would silently defeat the
    # whole point of this backend — and `.env` puts one there. Anyone who wants
    # the key used has TICKER_DIGEST_LLM_BACKEND=api for that.
    _SHADOWING_AUTH_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

    def __init__(self, executable: str = CLAUDE_CLI_PATH) -> None:
        self.executable = executable

    def _env(self) -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key not in self._SHADOWING_AUTH_VARS
        }

    def _argv(self, call: StructuredCall) -> list[str]:
        return [
            self.executable,
            "-p",
            "--output-format", "json",
            "--model", call.model,
            # Replaces Claude Code's own system prompt rather than appending to
            # it: this process is an extraction service, not a coding agent.
            "--system-prompt", call.system,
            "--json-schema", json.dumps(call.response_model.model_json_schema()),
            # Everything below keeps a user's local setup out of the request:
            # no MCP servers, no settings files, no skills, and no session
            # written to disk for what is a stateless call.
            "--strict-mcp-config",
            "--setting-sources", "",
            "--disable-slash-commands",
            "--no-session-persistence",
        ]

    def _invoke(self, call: StructuredCall, user: str) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                self._argv(call),
                input=user,
                capture_output=True,
                text=True,
                timeout=CLAUDE_CLI_TIMEOUT_SECONDS,
                check=False,
                env=self._env(),
            )
        except FileNotFoundError as exc:
            raise LLMUnavailableError(
                f"The Claude Code CLI was not found at {self.executable!r}.\n"
                "  Install it, put it on PATH, or set TICKER_DIGEST_CLAUDE_CLI to "
                "its full path.\n"
                "  Or set ANTHROPIC_API_KEY to use the API instead."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise LLMUnavailableError(
                f"The Claude Code CLI did not answer within "
                f"{CLAUDE_CLI_TIMEOUT_SECONDS}s ({call.tool_name})."
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip().splitlines()
            tail = stderr[-1] if stderr else "no error output"
            raise LLMUnavailableError(
                f"The Claude Code CLI exited {completed.returncode}: {tail}\n"
                "  If this is an authentication problem, run `claude` once "
                "interactively to log in."
            )

        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError(
                "Could not read the Claude Code CLI's response as JSON: "
                f"{completed.stdout[:200]!r}"
            ) from exc

        if envelope.get("is_error") or envelope.get("subtype") != "success":
            raise LLMUnavailableError(
                f"The Claude Code CLI reported a failure "
                f"({envelope.get('subtype', 'unknown')}): "
                f"{str(envelope.get('result'))[:300]}"
            )
        return envelope

    def run(self, call: StructuredCall) -> BaseModel:
        envelope = self._invoke(call, call.user)
        payload = _parse_result(envelope, call.tool_name)

        try:
            return call.response_model.model_validate(payload)
        except ValidationError as exc:
            log.warning("%s failed validation, retrying once: %s", call.tool_name, exc)
            retried = self._invoke(call, _retry_prompt(call, exc))
            return call.response_model.model_validate(
                _parse_result(retried, call.tool_name)
            )


def _parse_result(envelope: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Pull the model's JSON out of the CLI's result envelope."""
    result = envelope.get("result")
    if isinstance(result, dict):
        return result
    if not isinstance(result, str):
        raise LLMError(f"The CLI returned no result for {tool_name!r}")

    fenced = _FENCE.match(result)
    text = fenced.group(1) if fenced else result
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"The CLI's answer for {tool_name!r} was not JSON: {text[:200]!r}"
        ) from exc
    if not isinstance(parsed, dict):
        raise LLMError(f"The CLI's answer for {tool_name!r} was not an object")
    return parsed


# ---------------------------------------------------------------------------
# Choosing one
# ---------------------------------------------------------------------------


def cli_available(executable: str = CLAUDE_CLI_PATH) -> bool:
    return shutil.which(executable) is not None


_NO_KEY_AT_ALL = (
    "No way to reach Claude.\n"
    "  Either set ANTHROPIC_API_KEY in .env,\n"
    "  or install the Claude Code CLI and log in by running `claude` once."
)


class AutoBackend:
    """Try the API, fall back to the CLI when the key turns out not to work.

    A key being *set* is not the same as a key being *valid*, and the
    difference only shows up on the first call. An invalid key is exactly the
    situation the CLI path exists for, so ``auto`` demotes to it rather than
    failing the run — once, and permanently for this instance, so a five-video
    digest doesn't collect five 401s on the way.
    """

    name = "auto"

    def __init__(self) -> None:
        self._backend: Backend = ApiBackend() if ANTHROPIC_API_KEY else ClaudeCliBackend()
        self._may_demote = bool(ANTHROPIC_API_KEY) and cli_available()
        if not ANTHROPIC_API_KEY:
            log.info(
                "No ANTHROPIC_API_KEY — using the Claude Code CLI at %s", CLAUDE_CLI_PATH
            )

    def run(self, call: StructuredCall) -> BaseModel:
        try:
            return self._backend.run(call)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            if not self._may_demote:
                raise LLMUnavailableError(
                    f"Claude rejected the API key: "
                    f"{getattr(exc, 'message', str(exc))}\n"
                    "  Check ANTHROPIC_API_KEY in .env is a real key, not a "
                    "placeholder.\n"
                    "  Or install the Claude Code CLI and log in — the digest can "
                    "run on that instead."
                ) from exc

            log.warning(
                "ANTHROPIC_API_KEY was rejected (%s). Falling back to the Claude "
                "Code CLI for the rest of this run.",
                getattr(exc, "message", exc),
            )
            self._backend = ClaudeCliBackend()
            self._may_demote = False
            return self._backend.run(call)


def resolve_backend(preference: str | None = None) -> Backend:
    """Return the backend to use, or explain why none is usable.

    ``api`` and ``cli`` are commitments — an explicit choice is not silently
    overridden. ``auto`` means "whatever works": the API when a key is present
    and accepted, the CLI otherwise.
    """
    choice = (preference or LLM_BACKEND or "auto").strip().lower()

    if choice == "api":
        return ApiBackend()
    if choice == "cli":
        if not cli_available():
            raise LLMUnavailableError(
                f"TICKER_DIGEST_LLM_BACKEND=cli, but no Claude Code CLI was found "
                f"at {CLAUDE_CLI_PATH!r}."
            )
        return ClaudeCliBackend()
    if choice != "auto":
        raise LLMUnavailableError(
            f"Unknown TICKER_DIGEST_LLM_BACKEND {choice!r}. Use auto, api or cli."
        )

    if not ANTHROPIC_API_KEY and not cli_available():
        raise LLMUnavailableError(_NO_KEY_AT_ALL)
    return AutoBackend()


# Resolved once per process. The point is not speed: AutoBackend remembers that
# an API key was rejected, and that memory is worthless if every call rebuilds
# it from scratch.
_BACKEND: Backend | None = None


def get_backend() -> Backend:
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = resolve_backend()
    return _BACKEND


def reset_backend() -> None:
    """Forget the resolved backend. For tests, and for changing env mid-process."""
    global _BACKEND
    _BACKEND = None


def ask(call: StructuredCall, backend: Backend | None = None) -> Any:
    """Run one structured call through the resolved backend."""
    return (backend or get_backend()).run(call)
