"""Backend selection, and the Claude Code CLI path — no real subprocess, no API."""
import json
import subprocess
from typing import Literal

import pytest
from pydantic import BaseModel

from ticker_digest.llm import (
    ApiBackend,
    ClaudeCliBackend,
    LLMError,
    StructuredCall,
    resolve_backend,
)

from .digest_helpers import tool_response


class Answer(BaseModel):
    # A Literal, like the real models use — so the schema carries an enum and
    # the integration test below actually checks that the CLI honours it.
    sentiment: Literal["bullish", "bearish"]
    reason: str


def _call(user: str = "What did they say?") -> StructuredCall:
    return StructuredCall(
        system="You extract structured data.",
        user=user,
        model="claude-sonnet-4-6",
        response_model=Answer,
        tool_name="report_answer",
        tool_description="Report the answer.",
    )


def _envelope(result, *, is_error=False, subtype="success") -> str:
    payload = result if isinstance(result, str) else json.dumps(result)
    return json.dumps({"is_error": is_error, "subtype": subtype, "result": payload})


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=["claude"], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


def test_auto_prefers_the_api_when_a_key_is_present(mocker) -> None:
    mocker.patch("ticker_digest.llm.ANTHROPIC_API_KEY", "sk-real")
    assert resolve_backend("auto").name == "api"


def test_auto_falls_back_to_the_cli_when_there_is_no_key(mocker) -> None:
    mocker.patch("ticker_digest.llm.ANTHROPIC_API_KEY", "")
    mocker.patch("ticker_digest.llm.shutil.which", return_value="/usr/local/bin/claude")

    assert resolve_backend("auto").name == "cli"


def test_no_key_and_no_cli_explains_both_ways_out(mocker) -> None:
    mocker.patch("ticker_digest.llm.ANTHROPIC_API_KEY", "")
    mocker.patch("ticker_digest.llm.shutil.which", return_value=None)

    with pytest.raises(LLMError) as caught:
        resolve_backend("auto")

    message = str(caught.value)
    assert "ANTHROPIC_API_KEY" in message
    assert "Claude Code CLI" in message


def test_an_explicit_api_choice_does_not_consult_the_cli(mocker) -> None:
    mocker.patch("ticker_digest.llm.ANTHROPIC_API_KEY", "")
    which = mocker.patch("ticker_digest.llm.shutil.which")

    assert resolve_backend("api").name == "api"
    which.assert_not_called()


def test_an_explicit_cli_choice_without_the_cli_is_an_error(mocker) -> None:
    mocker.patch("ticker_digest.llm.shutil.which", return_value=None)

    with pytest.raises(LLMError, match="no Claude Code CLI was found"):
        resolve_backend("cli")


def test_an_unknown_backend_name_is_rejected() -> None:
    with pytest.raises(LLMError, match="Unknown TICKER_DIGEST_LLM_BACKEND"):
        resolve_backend("gpt")


# ---------------------------------------------------------------------------
# The CLI invocation
# ---------------------------------------------------------------------------


def test_a_clean_answer_is_validated_into_the_model(mocker) -> None:
    run = mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope({"sentiment": "bullish", "reason": "contract"})),
    )

    answer = ClaudeCliBackend().run(_call())

    assert isinstance(answer, Answer)
    assert answer.sentiment == "bullish"
    assert run.call_count == 1


def test_the_prompt_goes_on_stdin_not_the_command_line(mocker) -> None:
    """A transcript is longer than the argv limit on macOS."""
    run = mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope({"sentiment": "bullish", "reason": "x"})),
    )
    long_prompt = "word " * 50_000

    ClaudeCliBackend().run(_call(long_prompt))

    argv, kwargs = run.call_args.args[0], run.call_args.kwargs
    assert kwargs["input"] == long_prompt
    assert long_prompt not in argv


def test_the_schema_and_system_prompt_are_passed_through(mocker) -> None:
    run = mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope({"sentiment": "bullish", "reason": "x"})),
    )

    ClaudeCliBackend().run(_call())

    argv = run.call_args.args[0]
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert schema["properties"]["sentiment"]["enum"] == ["bullish", "bearish"]
    assert argv[argv.index("--system-prompt") + 1] == "You extract structured data."
    assert argv[argv.index("--model") + 1] == "claude-sonnet-4-6"
    assert argv[argv.index("--output-format") + 1] == "json"


def test_the_local_environment_is_kept_out_of_the_request(mocker) -> None:
    """No MCP servers, no settings files, no skills, no session on disk."""
    run = mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope({"sentiment": "bullish", "reason": "x"})),
    )

    ClaudeCliBackend().run(_call())

    argv = run.call_args.args[0]
    for flag in (
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
    ):
        assert flag in argv
    assert argv[argv.index("--setting-sources") + 1] == ""


def test_a_fenced_answer_is_unwrapped_rather_than_retried(mocker) -> None:
    fenced = '```json\n{"sentiment": "bearish", "reason": "burn"}\n```'
    run = mocker.patch(
        "ticker_digest.llm.subprocess.run", return_value=_completed(_envelope(fenced))
    )

    assert ClaudeCliBackend().run(_call()).sentiment == "bearish"
    assert run.call_count == 1


def test_an_invalid_answer_is_retried_once_with_the_errors(mocker) -> None:
    run = mocker.patch(
        "ticker_digest.llm.subprocess.run",
        side_effect=[
            _completed(_envelope({"sentiment": "bullish"})),  # missing 'reason'
            _completed(_envelope({"sentiment": "bullish", "reason": "contract"})),
        ],
    )

    assert ClaudeCliBackend().run(_call()).reason == "contract"
    assert run.call_count == 2
    assert "failed schema validation" in run.call_args.kwargs["input"]


def test_a_second_invalid_answer_gives_up(mocker) -> None:
    mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope({"sentiment": "bullish"})),
    )

    with pytest.raises(Exception):  # noqa: B017 — pydantic's ValidationError
        ClaudeCliBackend().run(_call())


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_a_missing_cli_names_both_remedies(mocker) -> None:
    mocker.patch("ticker_digest.llm.subprocess.run", side_effect=FileNotFoundError())

    with pytest.raises(LLMError) as caught:
        ClaudeCliBackend().run(_call())

    message = str(caught.value)
    assert "TICKER_DIGEST_CLAUDE_CLI" in message
    assert "ANTHROPIC_API_KEY" in message


def test_a_nonzero_exit_suggests_logging_in(mocker) -> None:
    mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(stderr="Invalid API key · Please run /login", returncode=1),
    )

    with pytest.raises(LLMError) as caught:
        ClaudeCliBackend().run(_call())

    assert "log in" in str(caught.value)
    assert "Please run /login" in str(caught.value)


def test_a_timeout_says_how_long_it_waited(mocker) -> None:
    mocker.patch(
        "ticker_digest.llm.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=600),
    )

    with pytest.raises(LLMError, match="did not answer within"):
        ClaudeCliBackend().run(_call())


def test_an_error_envelope_is_surfaced(mocker) -> None:
    mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope("usage limit reached", is_error=True,
                                          subtype="error_during_execution")),
    )

    with pytest.raises(LLMError) as caught:
        ClaudeCliBackend().run(_call())

    assert "usage limit reached" in str(caught.value)


def test_unparseable_stdout_is_reported_as_such(mocker) -> None:
    mocker.patch(
        "ticker_digest.llm.subprocess.run", return_value=_completed("not json at all")
    )

    with pytest.raises(LLMError, match="Could not read"):
        ClaudeCliBackend().run(_call())


def test_a_non_json_result_is_reported_as_such(mocker) -> None:
    mocker.patch(
        "ticker_digest.llm.subprocess.run",
        return_value=_completed(_envelope("I'm afraid I can't do that")),
    )

    with pytest.raises(LLMError, match="was not JSON"):
        ClaudeCliBackend().run(_call())


# ---------------------------------------------------------------------------
# The API backend still behaves as it did
# ---------------------------------------------------------------------------


def test_the_api_backend_forces_the_tool_and_caches_the_system_prompt(mocker) -> None:
    client = mocker.MagicMock()
    client.messages.create.return_value = tool_response(
        "report_answer", {"sentiment": "bullish", "reason": "contract"}
    )
    mocker.patch("ticker_digest.llm.anthropic.Anthropic", return_value=client)

    assert ApiBackend().run(_call()).sentiment == "bullish"

    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["tool_choice"] == {"type": "tool", "name": "report_answer"}
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["tools"][0]["input_schema"]["properties"]["reason"]["type"] == "string"


def test_the_api_backend_retries_once_on_a_bad_shape(mocker) -> None:
    client = mocker.MagicMock()
    client.messages.create.side_effect = [
        tool_response("report_answer", {"sentiment": "bullish"}),
        tool_response("report_answer", {"sentiment": "bullish", "reason": "contract"}),
    ]
    mocker.patch("ticker_digest.llm.anthropic.Anthropic", return_value=client)

    assert ApiBackend().run(_call()).reason == "contract"
    assert client.messages.create.call_count == 2


def test_a_response_without_the_tool_block_is_an_llm_error(mocker) -> None:
    empty = mocker.MagicMock()
    empty.content = []
    client = mocker.MagicMock()
    client.messages.create.return_value = empty
    mocker.patch("ticker_digest.llm.anthropic.Anthropic", return_value=client)

    with pytest.raises(LLMError, match="tool_use block"):
        ApiBackend().run(_call())


# ---------------------------------------------------------------------------
# Against the real binary — excluded by default
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_the_real_cli_accepts_these_flags_and_returns_the_schema() -> None:
    """The one thing mocks cannot prove: that this flag combination works.

    Needs a `claude` on PATH that is already logged in, and spends a little
    of that account's usage. Run with: pytest -m integration
    """
    import shutil as _shutil

    if _shutil.which("claude") is None:
        pytest.skip("no claude CLI on PATH")

    answer = ClaudeCliBackend().run(
        StructuredCall(
            system="You extract structured data from short statements.",
            user="The speaker said the company won a large contract and raised guidance.",
            model="claude-haiku-4-5",
            response_model=Answer,
            tool_name="report_answer",
            tool_description="Report the answer.",
        )
    )

    # Reaching this line at all means the CLI honoured the schema's enum:
    # pydantic would reject anything outside it.
    assert isinstance(answer, Answer)
    assert answer.sentiment == "bullish"
    assert answer.reason
