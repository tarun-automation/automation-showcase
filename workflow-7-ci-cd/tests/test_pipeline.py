import json
from unittest.mock import patch, MagicMock

import pytest

from pipeline import FAIL, PASS, SKIP, run_pipeline, run_step


def _step(name, cmd):
    return {"name": name, "cmd": cmd}


def _proc(returncode, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


@patch("pipeline.subprocess.run")
def test_run_step_pass_on_zero_exit(mock_run):
    mock_run.return_value = _proc(0, stdout="ok")
    r = run_step("lint", ["echo", "ok"])
    assert r["status"] == PASS
    assert r["stdout"] == "ok"


@patch("pipeline.subprocess.run")
def test_run_step_fail_on_nonzero_exit(mock_run):
    mock_run.return_value = _proc(1, stderr="error")
    r = run_step("test", ["false"])
    assert r["status"] == FAIL
    assert r["stderr"] == "error"


@patch("pipeline.subprocess.run")
def test_run_pipeline_all_pass(mock_run):
    mock_run.return_value = _proc(0)
    steps = [_step("lint", ["echo"]), _step("test", ["echo"])]
    report = run_pipeline(steps)
    assert report["status"] == PASS
    assert all(s["status"] == PASS for s in report["steps"])


@patch("pipeline.subprocess.run")
def test_run_pipeline_stops_on_fail_by_default(mock_run):
    mock_run.return_value = _proc(1)
    steps = [_step("lint", ["false"]), _step("test", ["echo"]), _step("build", ["echo"])]
    report = run_pipeline(steps)
    assert report["status"] == FAIL
    assert report["steps"][0]["status"] == FAIL
    assert report["steps"][1]["status"] == SKIP
    assert report["steps"][2]["status"] == SKIP


@patch("pipeline.subprocess.run")
def test_run_pipeline_continues_when_stop_on_fail_false(mock_run):
    mock_run.side_effect = [_proc(1), _proc(0), _proc(0)]
    steps = [_step("lint", ["false"]), _step("test", ["echo"]), _step("build", ["echo"])]
    report = run_pipeline(steps, stop_on_fail=False)
    assert report["status"] == FAIL
    assert report["steps"][1]["status"] == PASS
    assert report["steps"][2]["status"] == PASS


@patch("pipeline.subprocess.run")
def test_elapsed_time_is_recorded(mock_run):
    mock_run.return_value = _proc(0)
    r = run_step("build", ["echo"])
    assert isinstance(r["elapsed_s"], float)
    assert r["elapsed_s"] >= 0


def test_run_step_missing_command_returns_fail():
    r = run_step("bad", ["__nonexistent_command_xyz__"])
    assert r["status"] == FAIL


@patch("pipeline.subprocess.run")
def test_save_report_writes_json(mock_run, tmp_path):
    from pipeline import save_report
    mock_run.return_value = _proc(0)
    report = run_pipeline([_step("lint", ["echo"])])
    path = tmp_path / "report.json"
    save_report(report, path)
    loaded = json.loads(path.read_text())
    assert loaded["status"] == PASS
