"""Verify Pilot 10's non-positive G02C-rejection disposition."""

import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02c-rejection-disposition-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_g02c_rejection_is_nonpositive_and_non_authorizing():
    disposition = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(disposition); identity = core.pop("disposition_identity")
    assert seal("B2_DEVELOPMENT_PILOT10_G02C_REJECTION_DISPOSITION_V1", core) == identity
    assert disposition["disposition"] == "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE"
    assert disposition["g02c_verdict"] == "FAIL_TERMINAL_EDGE_NON_ARBITRARY_CAUSAL_CONTINUITY"
    assert disposition["earliest_failed_link"] == "L2_TO_TERMINAL_RESULT"
    assert disposition["candidate_git_blob_oid_sha1"] == "8dfbc43c94190e5b0fca48d6bcd28adf55c21391"
    assert disposition["material_realization"] == {"nodes": "3_OF_3", "edges": "2_OF_2", "terminal_result_witnesses": 1}
    assert disposition["semantic_necessity"]["valid_necessary_edges"] == "2_OF_3"
    assert disposition["capability_state"] == "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION"
    assert disposition["candidate_bytes_modified"] is False
    assert disposition["positive_coverage_eligible"] is False
    assert disposition["g03_eligible"] is False
    assert all(value is False for value in disposition["authority_matrix"].values())
