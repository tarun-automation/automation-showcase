"""Runs a CI/CD pipeline — lint, test, build, deploy — and reports a pass/fail result."""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PASS = "pass"
FAIL = "fail"
SKIP = "skip"


def _now():
    return datetime.now(timezone.utc).isoformat()


def run_step(name, cmd, *, cwd=None, stop_on_fail=True):
    """Run a shell command and return a result dict."""
    logger.info("[%s] running: %s", name, " ".join(cmd))
    start = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        status = PASS if proc.returncode == 0 else FAIL
    except FileNotFoundError as exc:
        proc = None
        status = FAIL
        logger.error("[%s] command not found: %s", name, exc)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    result = {
        "step": name,
        "status": status,
        "elapsed_s": round(elapsed, 2),
        "stdout": proc.stdout.strip() if proc else "",
        "stderr": proc.stderr.strip() if proc else str(exc),
    }
    symbol = "✓" if status == PASS else "✗"
    logger.info("[%s] %s  (%.2fs)", name, symbol, elapsed)
    if status == FAIL:
        logger.error("[%s] stderr: %s", name, result["stderr"])
    return result


def run_pipeline(steps, *, cwd=None, stop_on_fail=True):
    """Run a list of ``{name, cmd}`` steps in order."""
    results = []
    failed = False
    for step in steps:
        if failed and stop_on_fail:
            results.append({"step": step["name"], "status": SKIP, "elapsed_s": 0, "stdout": "", "stderr": ""})
            continue
        r = run_step(step["name"], step["cmd"], cwd=cwd)
        results.append(r)
        if r["status"] == FAIL:
            failed = True
    overall = FAIL if any(r["status"] == FAIL for r in results) else PASS
    return {"status": overall, "started_at": _now(), "steps": results}


def save_report(report, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2))
    logger.info("Report written to %s", path)


def build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None, help="JSON file with [{name, cmd}] step list")
    p.add_argument("--report", default="output/pipeline_report.json")
    p.add_argument("--no-stop-on-fail", action="store_true")
    p.add_argument("--cwd", default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    return p


DEFAULT_STEPS = [
    {"name": "lint",   "cmd": ["python", "-m", "flake8", "--max-line-length=120", "."]},
    {"name": "test",   "cmd": ["python", "-m", "pytest", "--tb=short", "-q"]},
    {"name": "build",  "cmd": ["python", "-m", "build", "--wheel", "--outdir", "dist/"]},
]


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    steps = DEFAULT_STEPS
    if args.config:
        steps = json.loads(Path(args.config).read_text())

    report = run_pipeline(steps, cwd=args.cwd, stop_on_fail=not args.no_stop_on_fail)
    save_report(report, args.report)
    print(f"Pipeline {report['status'].upper()}")
    sys.exit(0 if report["status"] == PASS else 1)


if __name__ == "__main__":
    main()
