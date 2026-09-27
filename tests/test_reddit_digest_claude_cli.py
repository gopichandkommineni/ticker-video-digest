"""Tests for the Claude Code CLI digest client (subprocess faked — no CLI runs)."""
import json
import subprocess
from unittest.mock import patch

import pytest

from core.social_media.reddit.digest import (
    ClaudeCliClient,
    LLMError,
    LLMFatal,
    MissingKey,
    QuotaExhausted,
)
from core.social_media.reddit.digest.claude_cli import _plain_schema

_RUN = "core.social_media.reddit.digest.claude_cli.subprocess.run"
_WHICH = "core.social_media.reddit.digest.claude_cli.shutil.which"


def _done(envelope=None, stdout=None, stderr="", code=0):
    out = stdout if stdout is not None else json.dumps(envelope)
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=out, stderr=stderr)


def _ok(**extra):
    return {"type": "result", "subtype": "success", "is_error": False, **extra}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("REDDIT_DIGEST_CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("REDDIT_DIGEST_CLAUDE_CLI", raising=False)
    with patch(_WHICH, return_value="/usr/bin/claude"):
        yield ClaudeCliClient()


def test_missing_cli_is_missing_key():
    with patch(_WHICH, return_value=None), pytest.raises(MissingKey, match="not installed"):
        ClaudeCliClient()


def test_model_defaults_to_haiku_and_can_be_set(client, monkeypatch):
    assert client.cli_model == "haiku" and client.model == "claude-haiku"
    monkeypatch.setenv("REDDIT_DIGEST_CLAUDE_MODEL", "sonnet")
    with patch(_WHICH, return_value="/usr/bin/claude"):
        assert ClaudeCliClient().model == "claude-sonnet"
        assert ClaudeCliClient(model="claude-sonnet-5").model == "claude-sonnet-5"


def test_call_shape_no_tools_prompt_on_stdin_and_no_api_key(client, monkeypatch):
    """Answer-only (no tools), prompt via stdin, and never an API key — so the
    call runs on the subscription, not API billing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-real-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth")
    schema = {"type": "OBJECT", "properties": {"summary": {"type": "STRING"}}}
    with patch(_RUN, return_value=_done(_ok(structured_output={"summary": "hi"}))) as run:
        out = client.generate_json("SYS", "POSTS", schema)
    assert out == {"summary": "hi"}
    argv, kw = run.call_args.args[0], run.call_args.kwargs
    assert argv[:2] == ["claude", "-p"]
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--model") + 1] == "haiku"
    assert argv[argv.index("--system-prompt") + 1] == "SYS"
    assert json.loads(argv[argv.index("--json-schema") + 1]) == {
        "type": "object", "properties": {"summary": {"type": "string"}}}
    assert "--setting-sources" in argv and "--strict-mcp-config" in argv
    assert kw["input"] == "POSTS" and "POSTS" not in argv
    assert "ANTHROPIC_API_KEY" not in kw["env"] and "ANTHROPIC_AUTH_TOKEN" not in kw["env"]
    assert kw["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "oauth"


@pytest.mark.parametrize("result", ['{"summary": "x"}', '```json\n{"summary": "x"}\n```'])
def test_falls_back_to_the_text_result(client, result):
    with patch(_RUN, return_value=_done(_ok(result=result))):
        assert client.generate_json("s", "p", {}) == {"summary": "x"}


def test_non_json_answer_is_a_per_stock_error(client):
    with patch(_RUN, return_value=_done(_ok(result="Sorry, I can't."))):
        with pytest.raises(LLMError) as err:
            client.generate_json("s", "p", {})
    assert not isinstance(err.value, LLMFatal)


@pytest.mark.parametrize("message", [
    "Claude AI usage limit reached|1759000000",
    "You've hit your limit · resets 3pm",
])
def test_plan_limit_stops_the_run(client, message):
    env = {"type": "result", "subtype": "success", "is_error": True, "result": message}
    with patch(_RUN, return_value=_done(env, code=1)), pytest.raises(QuotaExhausted):
        client.generate_json("s", "p", {})


@pytest.mark.parametrize("message", [
    "Invalid API key · Please run /login",
    "OAuth token has expired. Please obtain a new token or refresh your existing token.",
])
def test_sign_in_problems_are_fatal(client, message):
    env = {"type": "result", "subtype": "success", "is_error": True, "result": message}
    with patch(_RUN, return_value=_done(env, code=1)), pytest.raises(LLMFatal) as err:
        client.generate_json("s", "p", {})
    assert not isinstance(err.value, QuotaExhausted)


def test_other_reported_errors_are_per_stock(client):
    env = {"type": "result", "subtype": "error_during_execution", "is_error": True,
           "result": "API Error: 529 Overloaded"}
    with patch(_RUN, return_value=_done(env)), pytest.raises(LLMError) as err:
        client.generate_json("s", "p", {})
    assert not isinstance(err.value, LLMFatal)


def test_no_envelope_at_all_is_fatal(client):
    """A crash or bad flag gives no JSON: it would repeat for every stock."""
    bad = _done(stdout="", stderr="error: unknown option '--tools'", code=1)
    with patch(_RUN, return_value=bad), pytest.raises(LLMFatal, match="exited 1"):
        client.generate_json("s", "p", {})


def test_timeout_is_a_per_stock_error(client):
    with patch(_RUN, side_effect=subprocess.TimeoutExpired("claude", 300)):
        with pytest.raises(LLMError, match="no answer within") as err:
            client.generate_json("s", "p", {})
    assert not isinstance(err.value, LLMFatal)


def test_plain_schema_lowercases_types_only():
    gem = {"type": "ARRAY", "items": {"type": "STRING", "enum": ["BULLISH", "neutral"]}}
    assert _plain_schema(gem) == {"type": "array",
                                  "items": {"type": "string", "enum": ["BULLISH", "neutral"]}}
