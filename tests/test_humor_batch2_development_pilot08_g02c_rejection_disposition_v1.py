"""Verify Pilot 08 non-positive G02C-rejection disposition."""

import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02c-rejection-disposition-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot08_g02c_rejection_is_nonpositive_and_non_authorizing():
    disposition = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(disposition)
    identity = core.pop("disposition_identity")
    assert seal("B2_DEVELOPMENT_PILOT08_G02C_REJECTION_DISPOSITION_V1", core) == identity
    assert disposition["disposition"] == "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE"
    assert disposition["g02c_verdict"] == "FAIL_UNBOUND_OPERAND_AND_INCOMPLETE_MULTI_LINK_CAUSAL_SPINE"
    assert disposition["earliest_failed_link"] == "FIRST_INVENTED_RELATION_TO_CONTROL_RETURN"
    assert disposition["candidate_git_blob_oid_sha1"] == "679ad8c85f55f002523657baf531587694f5f607"
    assert disposition["capability_state"] == "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION"
    assert disposition["candidate_bytes_modified"] is False
    assert disposition["positive_coverage_eligible"] is False
    assert disposition["g03_eligible"] is False
    assert all(value is False for value in disposition["authority_matrix"].values())
