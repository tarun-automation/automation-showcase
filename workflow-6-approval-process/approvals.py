"""Routes approval requests through a chain of approvers and tracks their decisions."""

import argparse
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PENDING  = "pending"
APPROVED = "approved"
REJECTED = "rejected"


def _now():
    return datetime.now(timezone.utc).isoformat()


def load_store(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def save_store(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2))


def create_request(store, title, approvers):
    if not approvers:
        raise ValueError("At least one approver is required")
    rid = str(uuid.uuid4())[:8]
    store[rid] = {
        "id": rid, "title": title, "created_at": _now(),
        "approvers": {a: PENDING for a in approvers},
        "status": PENDING,
    }
    logger.info("Created request %s: %s (approvers: %s)", rid, title, ", ".join(approvers))
    return rid


def decide(store, rid, approver, decision):
    if rid not in store:
        raise KeyError(f"Request {rid!r} not found")
    req = store[rid]
    if req["status"] != PENDING:
        raise RuntimeError(f"Request {rid} is already {req['status']}")
    if approver not in req["approvers"]:
        raise KeyError(f"{approver!r} is not an approver for {rid}")
    if decision not in (APPROVED, REJECTED):
        raise ValueError(f"Decision must be '{APPROVED}' or '{REJECTED}'")

    req["approvers"][approver] = decision
    logger.info("%s %s request %s", approver, decision, rid)

    votes = list(req["approvers"].values())
    if any(v == REJECTED for v in votes):
        req["status"] = REJECTED
    elif all(v == APPROVED for v in votes):
        req["status"] = APPROVED

    return req["status"]


def summary(store):
    counts = {PENDING: 0, APPROVED: 0, REJECTED: 0}
    for req in store.values():
        counts[req["status"]] += 1
    return counts


def build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="output/approvals.json")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create")
    c.add_argument("title")
    c.add_argument("--approvers", required=True, help="Comma-separated list")

    d = sub.add_parser("decide")
    d.add_argument("request_id")
    d.add_argument("approver")
    d.add_argument("decision", choices=[APPROVED, REJECTED])

    sub.add_parser("list")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    store = load_store(args.store)

    if args.command == "create":
        approvers = [a.strip() for a in args.approvers.split(",")]
        rid = create_request(store, args.title, approvers)
        print(f"Created request: {rid}")
    elif args.command == "decide":
        status = decide(store, args.request_id, args.approver, args.decision)
        print(f"Request {args.request_id} is now: {status}")
    elif args.command == "list":
        print(json.dumps(store, indent=2))
        print(summary(store))

    save_store(store, args.store)


if __name__ == "__main__":
    main()
