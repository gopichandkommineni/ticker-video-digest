"""Unit tests for the direct subreddit-metrics probe (mocked Arctic Shift)."""
from unittest.mock import patch

from core.social_media.reddit.subreddit_discovery import SubredditInfo
from casino_dashboard.jobs import subreddit_metrics as job


def test_clean_name_strips_prefixes():
    assert job._clean_name("RKLB") == "RKLB"
    assert job._clean_name("r/RKLB") == "RKLB"
    assert job._clean_name("/r/RocketLab") == "RocketLab"
    assert job._clean_name("  R/IonQStock  ") == "IonQStock"


def test_resolve_names_precedence(monkeypatch):
    assert job._resolve_names(["RKLB", "r/RocketLab"]) == ["RKLB", "RocketLab"]
    monkeypatch.setenv("SUBREDDIT_METRICS_NAMES", "RKLB, r/RKLB, IonQStock")
    # de-dupes (RKLB and r/RKLB collapse) and strips prefixes
    assert job._resolve_names([]) == ["RKLB", "IonQStock"]
    monkeypatch.delenv("SUBREDDIT_METRICS_NAMES")
    assert job._resolve_names([]) == job._DEFAULT_NAMES


def test_run_renders_metrics_table():
    info = SubredditInfo(
        name="RKLB", subscribers=15000, posts_7d=0,
        public_description="Rocket Lab RKLB investors", quarantined=False,
    )
    with patch.object(job, "fetch_about", return_value=info) as mock_about, \
         patch.object(job, "count_recent_posts", return_value=12) as mock_posts:
        lines = job.run(["r/RKLB"], sleep=False)

    text = "\n".join(lines)
    mock_about.assert_called_once_with("RKLB")   # prefix stripped before fetch
    mock_posts.assert_called_once_with("RKLB")
    assert "r/RKLB" in text
    assert "15,000" in text
    assert "| 12 |" in text                      # posts_7d overwritten from count
    assert "Rocket Lab RKLB investors" in text


def test_run_flags_not_found():
    with patch.object(job, "fetch_about", return_value=None), \
         patch.object(job, "count_recent_posts", return_value=0) as mock_posts:
        lines = job.run(["Nonexistent"], sleep=False)

    text = "\n".join(lines)
    assert "not found on Arctic Shift" in text
    mock_posts.assert_not_called()               # no metrics call when sub missing


def test_run_marks_quarantined_and_nsfw():
    info = SubredditInfo(name="Raw", subscribers=500, posts_7d=3,
                         over18=True, quarantined=True, public_description="")
    with patch.object(job, "fetch_about", return_value=info), \
         patch.object(job, "count_recent_posts", return_value=3):
        text = "\n".join(job.run(["Raw"], sleep=False))
    assert "NSFW" in text and "quarantined" in text
