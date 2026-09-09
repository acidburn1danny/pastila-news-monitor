from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ARTIFACT = Path("docs/artifacts/production-core-comparative-qualification-ordinal8-audit-v1.json")
ARTIFACT_SHA256 = "17c403ae347c209e0d7217ab5af57b3d191a39c4f7c571393adc29d883174ac2"
AUDIT_IDENTITY = "c749b7d08a43dc1358a6da781265dec98dcec0dcf6bd0dfc193aa7501be6d9b1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def test_ordinal8_audit_is_self_bound_and_fail_closed() -> None:
    raw = ARTIFACT.read_bytes()
    assert raw.startswith(b"{") and raw.endswith(b"}\n")
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    value = json.loads(raw)
    assert set(value) == {
        "schema", "schema_version", "authority_commit", "authority_tree",
        "qualification_generation_identity", "attempt_ordinal", "attempt_identity",
        "completion_identity", "completion_artifact_sha256", "private_artifact_root",
        "private_artifact_count", "private_artifact_hash_mismatches",
        "private_evidence_availability", "batch_count", "case_execution_count", "matrix",
        "raw_output_count", "observation_count", "execution_receipt_count",
        "raw_observation_receipt_identity_mismatches", "unique_execution_receipt_identities",
        "unique_observation_identities", "deterministic_alias_case_groups",
        "deterministic_alias_case_groups_with_one_raw_sha256", "structural_result",
        "resource_verification", "network_verification", "stderr_verification",
        "blind_exports", "audit_verdict", "hard_gate", "retry_or_redraw_authorized",
        "promotion_effect", "new_execution_or_infrastructure_blockers", "audit_identity",
    }
    core = dict(value)
    identity = core.pop("audit_identity")
    assert identity == AUDIT_IDENTITY
    assert identity == hashlib.sha256(_canonical(core)).hexdigest()
    assert value["schema"] == "pastila-production-core-comparative-qualification-execution-audit"
    assert type(value["schema_version"]) is int and value["schema_version"] == 1
    assert value["authority_commit"] == "90c6d137310bb0d8347240ac21299aeeefd71844"
    assert value["authority_tree"] == "1aa24c4bc7d5a4885a331a3612974d5ace327fcd"
    assert value["qualification_generation_identity"] == "bbcfa148c1eaf58b5dda2f2f87297b7a573f660020c0d6af3e849cfed137a8b5"
    assert value["attempt_identity"] == "c25992af719a0e601ca40f184bf4da500b2af56ec87c744b9f4c86778671e459"
    assert value["completion_identity"] == "ec17f7b07615d410d712a3d9a5aa3d2e5b8a1aa810130df4a2e3a923d37606b7"
    assert value["completion_artifact_sha256"] == "b2a97ec671ac2148009862bb2d9772f8e92da60ff3a3ca92489c198eb749cfc0"
    assert value["private_artifact_root"] == "6d3cd925949876b706e6acd7ca3843282df174d28ca46d3837146c9bdc4523cf"
    integer_fields = {
        "attempt_ordinal": 8, "private_artifact_count": 7249,
        "private_artifact_hash_mismatches": 0, "batch_count": 12,
        "case_execution_count": 2400, "raw_output_count": 2400,
        "observation_count": 2400, "execution_receipt_count": 2400,
        "raw_observation_receipt_identity_mismatches": 0,
        "unique_execution_receipt_identities": 2400, "unique_observation_identities": 2400,
        "deterministic_alias_case_groups": 400,
        "deterministic_alias_case_groups_with_one_raw_sha256": 400,
        "new_execution_or_infrastructure_blockers": 0,
    }
    for field, expected in integer_fields.items():
        assert type(value[field]) is int and value[field] == expected
    nested_integer_paths = (
        ("matrix", "materializations"),
        ("matrix", "repetitions_per_materialization"),
        ("matrix", "cases"),
        ("matrix", "candidates"),
        ("structural_result", "pass"),
        ("structural_result", "fail"),
        ("structural_result", "failure_classification", "not_one_bare_utf8_json_object"),
        ("structural_result", "failure_classification", "bare_json_violates_structured_response_contract"),
        ("structural_result", "candidate_alias_results", "CANDIDATE-A", "pass"),
        ("structural_result", "candidate_alias_results", "CANDIDATE-A", "fail"),
        ("structural_result", "candidate_alias_results", "CANDIDATE-A", "valid_repetitions_per_case"),
        ("structural_result", "candidate_alias_results", "CANDIDATE-B", "pass"),
        ("structural_result", "candidate_alias_results", "CANDIDATE-B", "fail"),
        ("structural_result", "candidate_alias_results", "CANDIDATE-B", "valid_repetitions_per_case"),
        *(("resource_verification", field) for field in value["resource_verification"]),
        ("network_verification", "batch_network_log_count"),
        ("blind_exports", "packet_count_per_adjudicator"),
    )
    for path in nested_integer_paths:
        nested = value
        for part in path:
            nested = nested[part]
        assert type(nested) is int
    assert value["matrix"] == {"materializations": 2, "repetitions_per_materialization": 3, "cases": 200, "candidates": 2}
    assert value["structural_result"] == {
        "pass": 12,
        "fail": 2388,
        "failure_classification": {
            "not_one_bare_utf8_json_object": 2316,
            "bare_json_violates_structured_response_contract": 72,
        },
        "candidate_alias_results": {
            "CANDIDATE-A": {"pass": 12, "fail": 1188, "structurally_valid_case_ids": ["pcq-eos-001", "pcq-eos-010"], "valid_repetitions_per_case": 6},
            "CANDIDATE-B": {"pass": 0, "fail": 1200, "structurally_valid_case_ids": [], "valid_repetitions_per_case": 0},
        },
    }
    assert value["resource_verification"] == {
        "maximum_input_tokens": 1568, "input_token_ceiling": 1924,
        "maximum_output_tokens": 279, "output_token_ceiling": 6268,
        "maximum_load_plus_generation_wall_ns": 36347004020,
        "wall_time_ceiling_ns": 600000000000,
        "maximum_peak_rss_bytes": 15652958208,
        "peak_rss_ceiling_bytes": 16106127360, "terminal_eos_false_count": 0,
    }
    assert value["network_verification"] == {
        "batch_network_log_count": 12,
        "common_network_log_sha256": "abbd3cb07265e3479beab667bccc060088d55b016efd5262cafdf0ae52d34c4c",
        "policy": "DENY_ALL_NEW_CHILD_NAMESPACE", "result": "PASS",
    }
    assert value["stderr_verification"] == {
        "candidate_output_contamination": False,
        "warning_bytes_committed_or_content_attested": False,
        "claim": "CHANNEL_SEPARATION_ONLY",
    }
    assert value["blind_exports"] == {
        "packet_count_per_adjudicator": 2400,
        "common_packets_root": "8afb38f745b9c219f1ffec063567f4309fc386a76c23d6faf4b5787b1787a059",
        "adjudicator_a_custody_identity": "4f7ba6f298e4aa1a82d22bd73b189cb07d8d524b556c487b24f23c7896d589b0",
        "adjudicator_b_custody_identity": "32efd7760b6c8a0671281a38e1e6e1d1ac4f19c569d02f92e9b2abd43b719320",
        "distributed": False, "distribution_authorized": False,
        "structurally_valid_subset_distribution_requires_separate_owner_authority": True,
    }
    assert value["audit_verdict"] == "PASS_EXECUTION_EVIDENCE_INTEGRITY"
    assert value["hard_gate"] == {
        "rule": "100_PERCENT_EACH_RUN_NO_COMPENSATION",
        "CANDIDATE-A": "FAIL_STRUCTURAL_GATE_NOT_PROMOTABLE",
        "CANDIDATE-B": "FAIL_STRUCTURAL_GATE_NOT_PROMOTABLE",
        "aggregate_compensation_permitted": False, "automatic_promotion_permitted": False,
        "semantic_adjudication_of_structural_failures_permitted": False,
    }
    assert value["private_evidence_availability"] == "LOCAL_PRIVATE_NOT_COMMITTED"
    assert value["retry_or_redraw_authorized"] is False
    assert value["promotion_effect"] is False


def test_ordinal8_audit_does_not_commit_private_execution_or_blind_packets() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "-z", ".pastila-runtime/production-core-qualification-v1"],
        check=True,
        capture_output=True,
    ).stdout
    assert tracked == b""
    value = json.loads(ARTIFACT.read_bytes())
    assert value["private_evidence_availability"] == "LOCAL_PRIVATE_NOT_COMMITTED"
    assert value["blind_exports"]["structurally_valid_subset_distribution_requires_separate_owner_authority"] is True
