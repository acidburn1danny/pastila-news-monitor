import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"


def load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def identity(value):
    payload = {key: item for key, item in value.items() if key != "artifact_identity"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_all_candidates_have_fail_closed_dispositions_and_no_activation():
    artifact = load("humor-mechanics-batch2-v5-4-rule-adjudication-dispositions-v1.json")
    assert artifact["artifact_identity"] == identity(artifact)
    assert artifact["adjudicator_identity"] == "RULE_ADJUDICATOR_V54_01"
    assert artifact["author_identity"] == "RULE_AUTHOR_V54_01"
    assert artifact["total_candidates"] == artifact["rejected"] == 88
    assert artifact["proposed_admitted"] == artifact["operationally_activated"] == 0
    assert artifact["independent_review_identity"] == "91f40b488ec61ee8fa90343c99ce469d61554bf1d5cbdc4acb2ec2f552034a8a"
    assert len({row["candidate_identity"] for row in artifact["dispositions"]}) == 88
    assert all(row["proposed_rule_identity"] is None for row in artifact["dispositions"])


def test_batch_evidence_preserves_frozen_batch_counts_and_independence():
    artifact = load("humor-mechanics-batch2-v5-4-rule-adjudication-batch-evidence-v1.json")
    assert artifact["artifact_identity"] == identity(artifact)
    assert [row["candidate_count"] for row in artifact["batches"]] == [16, 20, 16, 20, 16]
    assert all(row["proposed_admitted_count"] == 0 for row in artifact["batches"])
    assert artifact["review_policy"]["absence_of_required_independent_evidence_is_rejection"] is True
    assert artifact["status"] == "FINAL_REVIEW_COMPLETE_ALL_CANDIDATES_REJECTED"


def test_proposed_catalog_is_immutable_empty_and_non_operational():
    artifact = load("humor-mechanics-batch2-v5-4-proposed-admitted-rule-catalog-v1.json")
    assert artifact["artifact_identity"] == identity(artifact)
    assert artifact["proposed_admitted_rule_count"] == artifact["operational_rule_count"] == 0
    assert artifact["rules"] == []
