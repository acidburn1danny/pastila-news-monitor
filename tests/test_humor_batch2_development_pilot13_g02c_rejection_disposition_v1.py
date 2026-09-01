import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-g02c-rejection-disposition-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_g02c_rejection_is_nonpositive_and_non_authorizing():
    disposition = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(disposition); identity = core.pop("disposition_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_G02C_REJECTION_DISPOSITION_V1", core)
    assert disposition["disposition"] == "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE"
    assert disposition["earliest_failed_link"] == "P5_TO_L1"
    assert disposition["candidate_git_blob_oid_sha1"] == "9a643cff281455ee0b4c9772f9740175ab27753b"
    assert disposition["capability_state"] == "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION"
    assert disposition["candidate_bytes_modified"] is False and disposition["existing_identities_modified"] is False
    assert disposition["positive_coverage_eligible"] is False and disposition["g03_eligible"] is False
    assert disposition["candidate_level_failure_not_infrastructure_defect"] is True
    assert all(value is False for value in disposition["authority_matrix"].values())
