"""Digest client that runs the Claude Code CLI on a Claude subscription.

`claude -p` (print mode) answers once and exits, so a program can call it. It
runs on whatever the CLI is signed in as:
- locally, the account you log in with when you run `claude`;
- in GitHub Actions, `CLAUDE_CODE_OAUTH_TOKEN`, the token `claude setup-token`
  prints.

Either way the calls count against the subscription's usage limits (Pro, Max),
not per-token API billing. To make sure of that, the API-key variables are
removed from the CLI's environment: Claude Code prefers an `ANTHROPIC_API_KEY`
over the subscription when one is set, and the workflow sets one for other jobs.

Reddit posts are untrusted text, so the CLI runs with no tools (`--tools ""`):
it can only answer, never read files or run commands. The user's own settings,
MCP servers and slash commands are kept out too.
"""
import json
import logging
import os
import re
import shutil
import subprocess

from core.social_media.reddit.digest.errors import LLMError, LLMFatal, MissingKey, QuotaExhausted

logger = logging.getLogger(__name__)

# Lighter model by default, to go easy on the plan's usage limits.
# Override with REDDIT_DIGEST_CLAUDE_MODEL (e.g. "sonnet").
DEFAULT_MODEL = "haiku"

# Variables that would make the CLI bill an API account instead of the plan.
_API_AUTH_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

_LIMIT = re.compile(r"usage limit|limit reached|hit your limit|out of (extra )?usage|quota",
                    re.IGNORECASE)
_AUTH = re.compile(r"/login|log ?in|not logged|authenticat|oauth|invalid api key|"
                   r"unauthori[sz]ed|token (has )?expired|credit balance|\b40[13]\b",
                   re.IGNORECASE)
_BAD_MODEL = re.compile(r"model.{0,40}(not found|not available|invalid|unknown)|not_found_error",
                        re.IGNORECASE)
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def _classify(message: str) -> LLMError:
    """The right error for what the CLI said went wrong."""
    text = message.strip()[:300] or "no details"
    if _LIMIT.search(text):
        return QuotaExhausted(f"Claude plan usage limit reached: {text}")
    if _AUTH.search(text):
        return LLMFatal(f"Claude CLI isn't signed in to a subscription: {text}")
    if _BAD_MODEL.search(text):
        return LLMFatal(f"Claude CLI rejected the model: {text}")
    return LLMError(f"Claude CLI call failed: {text}")


class ClaudeCliClient:
    """generate_json(system, prompt, schema) → parsed dict, via `claude -p`."""

    # The CLI waits out its own limits; no pacing needed between stocks.
    call_delay = 0.0

    def __init__(
        self,
        model: str | None = None,
        executable: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.executable = executable or os.environ.get("REDDIT_DIGEST_CLAUDE_CLI", "").strip() or "claude"
        if shutil.which(self.executable) is None:
            raise MissingKey(f"the Claude Code CLI ({self.executable!r}) is not installed")
        self.cli_model = (model or os.environ.get("REDDIT_DIGEST_CLAUDE_MODEL", "").strip()
                          or DEFAULT_MODEL)
        # What the page and report show: "claude-haiku", or a full ID as given.
        self.model = self.cli_model if self.cli_model.startswith("claude") else f"claude-{self.cli_model}"
        self.timeout = timeout

    def _argv(self, system: str, schema: dict) -> list[str]:
        return [
            self.executable, "-p",
            "--output-format", "json",
            "--model", self.cli_model,
            "--system-prompt", system,
            "--json-schema", json.dumps(schema),
            "--tools", "",                 # answer only: no files, no commands
            "--strict-mcp-config",         # no MCP servers
            "--setting-sources", "",       # no user or project settings
            "--disable-slash-commands",
            "--no-session-persistence",
        ]

    @staticmethod
    def _env() -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if k not in _API_AUTH_VARS}

    def generate_json(self, system: str, prompt: str, schema: dict) -> dict:
        try:
            done = subprocess.run(
                self._argv(system, _plain_schema(schema)),
                input=prompt,               # stdin: posts are too long for argv
                capture_output=True, text=True, timeout=self.timeout,
                check=False, env=self._env(),
            )
        except FileNotFoundError as exc:
            raise MissingKey(f"the Claude Code CLI ({self.executable!r}) is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise LLMError(f"Claude CLI gave no answer within {self.timeout:.0f}s") from exc

        try:
            envelope = json.loads(done.stdout)
        except json.JSONDecodeError:
            envelope = None
        if not isinstance(envelope, dict):
            # No result at all: a bad flag, a crash, or a sign-in problem.
            # Whatever it is will happen again for the next stock.
            err = _classify(done.stderr or done.stdout)
            raise err if isinstance(err, LLMFatal) else LLMFatal(
                f"Claude CLI exited {done.returncode}: {str(err)[:250]}")
        if envelope.get("is_error") or envelope.get("subtype") != "success":
            raise _classify(str(envelope.get("result") or envelope.get("subtype") or done.stderr))
        return _payload(envelope)


def _payload(envelope: dict) -> dict:
    """The model's JSON: `structured_output` when --json-schema was honoured,
    else the text result parsed (tolerating a code fence)."""
    structured = envelope.get("structured_output")
    if isinstance(structured, dict):
        return structured
    result = envelope.get("result")
    if isinstance(result, dict):
        return result
    if not isinstance(result, str):
        raise LLMError("Claude CLI returned no result")
    fenced = _FENCE.match(result)
    try:
        parsed = json.loads(fenced.group(1) if fenced else result)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Claude CLI's answer was not JSON: {result[:200]!r}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("Claude CLI's answer was not a JSON object")
    return parsed


def _plain_schema(schema: dict) -> dict:
    """The digest schema is written in Gemini's dialect (type names in capitals,
    "OBJECT", "STRING"…). Standard JSON Schema, which the CLI takes, wants them
    lower-case; everything else is the same."""
    if isinstance(schema, dict):
        return {k: (v.lower() if k == "type" and isinstance(v, str) else _plain_schema(v))
                for k, v in schema.items()}
    if isinstance(schema, list):
        return [_plain_schema(v) for v in schema]
    return schema
