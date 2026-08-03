import pytest
from approvals import APPROVED, PENDING, REJECTED, create_request, decide, summary


def _store():
    return {}


def test_create_request_adds_entry():
    store = _store()
    rid = create_request(store, "Deploy v1.2", ["alice", "bob"])
    assert rid in store
    assert store[rid]["status"] == PENDING
    assert set(store[rid]["approvers"]) == {"alice", "bob"}


def test_create_request_requires_approvers():
    with pytest.raises(ValueError):
        create_request(_store(), "Deploy", [])


def test_approve_by_all_sets_approved():
    store = _store()
    rid = create_request(store, "Release", ["alice", "bob"])
    decide(store, rid, "alice", APPROVED)
    status = decide(store, rid, "bob", APPROVED)
    assert status == APPROVED


def test_single_rejection_sets_rejected():
    store = _store()
    rid = create_request(store, "Release", ["alice", "bob"])
    decide(store, rid, "alice", APPROVED)
    status = decide(store, rid, "bob", REJECTED)
    assert status == REJECTED


def test_partial_approval_stays_pending():
    store = _store()
    rid = create_request(store, "Release", ["alice", "bob"])
    status = decide(store, rid, "alice", APPROVED)
    assert status == PENDING


def test_decide_on_unknown_request_raises():
    with pytest.raises(KeyError):
        decide(_store(), "bad-id", "alice", APPROVED)


def test_decide_by_non_approver_raises():
    store = _store()
    rid = create_request(store, "Release", ["alice"])
    with pytest.raises(KeyError):
        decide(store, rid, "charlie", APPROVED)


def test_decide_on_closed_request_raises():
    store = _store()
    rid = create_request(store, "Release", ["alice"])
    decide(store, rid, "alice", APPROVED)
    with pytest.raises(RuntimeError):
        decide(store, rid, "alice", REJECTED)


def test_summary_counts_correctly():
    store = _store()
    r1 = create_request(store, "A", ["alice"])
    r2 = create_request(store, "B", ["bob"])
    decide(store, r1, "alice", APPROVED)
    decide(store, r2, "bob", REJECTED)
    r3 = create_request(store, "C", ["carol"])  # noqa: F841
    counts = summary(store)
    assert counts == {PENDING: 1, APPROVED: 1, REJECTED: 1}
