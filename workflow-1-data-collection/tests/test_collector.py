import json
from unittest.mock import Mock, patch

import pytest
import requests

from collector import fetch_data, save_csv, save_json

SAMPLE_RECORDS = [
    {"id": 1, "title": "First post", "body": "Hello world"},
    {"id": 2, "title": "Second post", "body": "Another entry"},
]


def _mock_response(json_data, status_ok=True):
    response = Mock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("boom")
    return response


@patch("collector.requests.get")
def test_fetch_data_returns_json_on_success(mock_get):
    mock_get.return_value = _mock_response(SAMPLE_RECORDS)

    result = fetch_data("https://example.com/posts")

    assert result == SAMPLE_RECORDS
    mock_get.assert_called_once()


@patch("collector.time.sleep", return_value=None)
@patch("collector.requests.get")
def test_fetch_data_retries_then_succeeds(mock_get, mock_sleep):
    mock_get.side_effect = [
        requests.ConnectionError("network down"),
        _mock_response(SAMPLE_RECORDS),
    ]

    result = fetch_data("https://example.com/posts", max_retries=3)

    assert result == SAMPLE_RECORDS
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


@patch("collector.time.sleep", return_value=None)
@patch("collector.requests.get")
def test_fetch_data_raises_after_exhausting_retries(mock_get, mock_sleep):
    mock_get.side_effect = requests.ConnectionError("network down")

    with pytest.raises(requests.ConnectionError):
        fetch_data("https://example.com/posts", max_retries=2)

    assert mock_get.call_count == 2


def test_save_json_writes_records(tmp_path):
    output_path = tmp_path / "nested" / "data.json"

    save_json(SAMPLE_RECORDS, output_path)

    assert json.loads(output_path.read_text()) == SAMPLE_RECORDS


def test_save_csv_writes_header_and_rows(tmp_path):
    output_path = tmp_path / "data.csv"

    save_csv(SAMPLE_RECORDS, output_path)

    lines = output_path.read_text().splitlines()
    assert lines[0] == "id,title,body"
    assert len(lines) == 1 + len(SAMPLE_RECORDS)


def test_save_csv_handles_empty_data(tmp_path):
    output_path = tmp_path / "empty.csv"

    save_csv([], output_path)

    assert output_path.read_text() == ""
