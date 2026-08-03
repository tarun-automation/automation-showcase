import json
from unittest.mock import Mock, patch

import pytest
import requests

from monitor import DOWN, UP, check_all, check_endpoint, summarise


def _resp(status_code=200):
    r = Mock()
    r.status_code = status_code
    return r


@patch("monitor.requests.get")
def test_check_endpoint_up_on_expected_status(mock_get):
    mock_get.return_value = _resp(200)
    r = check_endpoint("https://example.com")
    assert r["status"] == UP
    assert r["http_status"] == 200
    assert r["error"] is None
    assert isinstance(r["latency_ms"], float)


@patch("monitor.requests.get")
def test_check_endpoint_down_on_unexpected_status(mock_get):
    mock_get.return_value = _resp(503)
    r = check_endpoint("https://example.com")
    assert r["status"] == DOWN
    assert r["http_status"] == 503


@patch("monitor.requests.get")
def test_check_endpoint_down_on_connection_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("refused")
    r = check_endpoint("https://example.com")
    assert r["status"] == DOWN
    assert r["http_status"] is None
    assert "refused" in r["error"]


@patch("monitor.requests.get")
def test_check_endpoint_respects_expected_status(mock_get):
    mock_get.return_value = _resp(302)
    r = check_endpoint("https://example.com", expected_status=302)
    assert r["status"] == UP


@patch("monitor.requests.get")
def test_check_all_returns_one_result_per_endpoint(mock_get):
    mock_get.return_value = _resp(200)
    results = check_all([{"url": "https://a.com"}, {"url": "https://b.com"}])
    assert len(results) == 2


def test_summarise_counts_up_and_down():
    results = [
        {"status": UP,   "latency_ms": 100.0},
        {"status": UP,   "latency_ms": 200.0},
        {"status": DOWN, "latency_ms": 50.0},
    ]
    s = summarise(results)
    assert s == {"total": 3, "up": 2, "down": 1, "avg_latency_ms": 150.0}


def test_summarise_avg_latency_none_when_all_down():
    results = [{"status": DOWN, "latency_ms": 10.0}]
    assert summarise(results)["avg_latency_ms"] is None


def test_save_report_writes_json(tmp_path):
    from monitor import save_report
    report = {"checked_at": "2026-01-01T00:00:00+00:00", "summary": {}, "results": []}
    path = tmp_path / "report.json"
    save_report(report, path)
    assert json.loads(path.read_text()) == report
