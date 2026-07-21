from unittest.mock import Mock, patch

import pytest
import requests

from notifier import build_message, read_text, send_console, send_file, send_webhook


def test_read_text_returns_file_contents(tmp_path):
    path = tmp_path / "report.md"
    path.write_text("# Report\n\nHello")

    assert read_text(path) == "# Report\n\nHello"


def test_build_message_passes_through_short_text():
    assert build_message("hello world") == "hello world"


def test_build_message_truncates_long_text():
    text = "a" * 600

    message = build_message(text, max_length=100)

    assert len(message) == 103
    assert message.endswith("...")


def test_build_message_strips_surrounding_whitespace():
    assert build_message("  hello  \n") == "hello"


def test_send_console_prints_message(capsys):
    send_console("hello world")

    captured = capsys.readouterr()
    assert "hello world" in captured.out


def test_send_file_appends_timestamped_entry(tmp_path):
    output_path = tmp_path / "notifications.log"

    send_file("first message", output_path)
    send_file("second message", output_path)

    lines = output_path.read_text().splitlines()
    assert len(lines) == 2
    assert "first message" in lines[0]
    assert "second message" in lines[1]


def _mock_response(status_ok=True):
    response = Mock()
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("boom")
    return response


@patch("notifier.requests.post")
def test_send_webhook_success(mock_post):
    mock_post.return_value = _mock_response()

    result = send_webhook("hello", "https://hooks.example.com/webhook")

    assert result is True
    mock_post.assert_called_once_with(
        "https://hooks.example.com/webhook", json={"text": "hello"}, timeout=10
    )


@patch("notifier.time.sleep", return_value=None)
@patch("notifier.requests.post")
def test_send_webhook_retries_then_succeeds(mock_post, mock_sleep):
    mock_post.side_effect = [requests.ConnectionError("down"), _mock_response()]

    result = send_webhook("hello", "https://hooks.example.com/webhook", max_retries=3)

    assert result is True
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@patch("notifier.time.sleep", return_value=None)
@patch("notifier.requests.post")
def test_send_webhook_raises_after_exhausting_retries(mock_post, mock_sleep):
    mock_post.side_effect = requests.ConnectionError("down")

    with pytest.raises(requests.ConnectionError):
        send_webhook("hello", "https://hooks.example.com/webhook", max_retries=2)

    assert mock_post.call_count == 2
