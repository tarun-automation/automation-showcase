import json

from processor import (
    clean_record,
    deduplicate,
    enrich_with_word_count,
    is_valid,
    process_records,
    read_records,
    write_records,
)


def test_clean_record_strips_whitespace():
    record = {"id": 1, "title": "  hello  ", "body": "world\n"}

    result = clean_record(record)

    assert result == {"id": 1, "title": "hello", "body": "world"}


def test_is_valid_true_when_required_fields_present():
    record = {"id": 1, "title": "t", "body": "b"}

    assert is_valid(record) is True


def test_is_valid_false_when_field_missing():
    record = {"id": 1, "title": "t"}

    assert is_valid(record) is False


def test_is_valid_false_when_field_empty():
    record = {"id": 1, "title": "", "body": "b"}

    assert is_valid(record) is False


def test_deduplicate_keeps_first_occurrence():
    records = [
        {"id": 1, "title": "first"},
        {"id": 2, "title": "second"},
        {"id": 1, "title": "duplicate"},
    ]

    result = deduplicate(records)

    assert result == [{"id": 1, "title": "first"}, {"id": 2, "title": "second"}]


def test_enrich_with_word_count():
    record = {"id": 1, "body": "one two three"}

    result = enrich_with_word_count(record)

    assert result["word_count"] == 3
    assert result["id"] == 1


def test_enrich_with_word_count_handles_missing_field():
    record = {"id": 1}

    result = enrich_with_word_count(record)

    assert result["word_count"] == 0


def test_process_records_end_to_end():
    records = [
        {"id": 1, "title": " hello ", "body": "one two"},
        {"id": 1, "title": "dup", "body": "should be dropped"},
        {"id": 2, "title": "", "body": "missing title"},
        {"id": 3, "title": "ok", "body": "three word body here"},
    ]

    result = process_records(records)

    assert [r["id"] for r in result] == [1, 3]
    assert result[0]["title"] == "hello"
    assert result[0]["word_count"] == 2
    assert result[1]["word_count"] == 4


def test_read_and_write_json_round_trip(tmp_path):
    records = [{"id": 1, "title": "t", "body": "b"}]
    path = tmp_path / "data.json"
    write_records(records, path)

    assert read_records(path) == records
    assert json.loads(path.read_text()) == records


def test_read_and_write_csv_round_trip(tmp_path):
    records = [{"id": "1", "title": "t", "body": "b"}]
    path = tmp_path / "data.csv"
    write_records(records, path)

    assert read_records(path) == records


def test_write_csv_handles_empty_records(tmp_path):
    path = tmp_path / "empty.csv"

    write_records([], path)

    assert path.read_text() == ""
