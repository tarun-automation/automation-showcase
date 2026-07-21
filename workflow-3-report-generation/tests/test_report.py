import json

from report import compute_summary, read_records, render_markdown_report, write_report

SAMPLE_RECORDS = [
    {"id": 1, "title": "Short", "body": "one two"},
    {"id": 2, "title": "Long", "body": "one two three four five six"},
    {"id": 3, "title": "Medium", "word_count": 4},
]


def test_compute_summary_counts_and_average():
    summary = compute_summary(SAMPLE_RECORDS)

    assert summary["total_records"] == 3
    assert summary["min_word_count"] == 2
    assert summary["max_word_count"] == 6
    assert summary["average_word_count"] == round((2 + 6 + 4) / 3, 2)


def test_compute_summary_uses_existing_word_count_field():
    summary = compute_summary([{"id": 3, "title": "Medium", "word_count": 4, "body": "ignored text here"}])

    assert summary["min_word_count"] == 4
    assert summary["max_word_count"] == 4


def test_compute_summary_top_records_sorted_descending():
    summary = compute_summary(SAMPLE_RECORDS, top_n=2)

    assert len(summary["top_records"]) == 2
    assert summary["top_records"][0]["id"] == 2
    assert summary["top_records"][1]["id"] == 3


def test_compute_summary_handles_empty_records():
    summary = compute_summary([])

    assert summary["total_records"] == 0
    assert summary["average_word_count"] == 0
    assert summary["top_records"] == []


def test_render_markdown_report_includes_summary_and_top_records():
    summary = compute_summary(SAMPLE_RECORDS)

    report = render_markdown_report(summary, generated_at="2026-01-01T00:00:00+00:00")

    assert "# Data Processing Report" in report
    assert "Generated: 2026-01-01T00:00:00+00:00" in report
    assert "| Total records | 3 |" in report
    assert "| 2 | Long | 6 |" in report


def test_render_markdown_report_handles_no_records():
    summary = compute_summary([])

    report = render_markdown_report(summary, generated_at="2026-01-01T00:00:00+00:00")

    assert "No records to display." in report


def test_read_records_json(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(SAMPLE_RECORDS[:2]))

    assert read_records(path) == SAMPLE_RECORDS[:2]


def test_write_report_writes_file(tmp_path):
    path = tmp_path / "nested" / "report.md"

    write_report("# Hello", path)

    assert path.read_text() == "# Hello"
