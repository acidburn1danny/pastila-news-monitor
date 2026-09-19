from __future__ import annotations

import copy
import json

import pytest

import audit_production_core_v15_r4_readonly_adjudication_boundary as auditor
import materialize_production_core_v15_r4_readonly_adjudication_boundary as issuer


def test_fresh_boundary_audit_passes_and_emits_no_verdict():
    result = auditor.audit()
    assert result["verdict"] == "PASS + 0 BLOCKERS"
    assert result["adjudication_state"].endswith("NO_VERDICT")
    assert result["promotion"] is False


def test_boundary_is_exactly_r4_and_read_only():
    value = issuer.build()
    assert value["published_r4_commit"] == issuer.R4_COMMIT
    assert value["r4_evidence"]["row_count"] == 2400
    assert value["r4_evidence"]["structurally_valid_rows"] == 1986
    assert value["r4_evidence"]["structurally_failed_rows"] == 414
    assert value["attempt_mutation_authorized"] is False
    assert value["candidate_execution_authorized"] is False
    assert value["adjudication_performed"] is False
    assert value["adjudication_verdict"] is None
    assert value["promotion"] is False


@pytest.mark.parametrize("field", ["published_r4_commit", "r4_evidence", "adjudication_rule", "source_sha256"])
def test_signed_binding_rejects_boundary_substitution(field):
    value = issuer.build(); raw = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    expected = issuer.canonical(issuer.binding_for(value, raw))
    bad = copy.deepcopy(value)
    bad[field] = {} if field in ("r4_evidence", "source_sha256") else "x"
    bad_raw = json.dumps(bad, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    assert issuer.canonical(issuer.binding_for(bad, bad_raw)) != expected


def test_historical_v1_generation_cannot_substitute_for_r4():
    value = issuer.build()
    assert value["qualification_generation_identity"] != "cfa6c00b96430246755c7cdce4c59b52d67946b91c1635077890c317b9afcadf"


def test_boundary_binds_r4_as_publication_parent_not_mutable_head():
    value = issuer.build()
    assert value["published_r4_commit"] == issuer.R4_COMMIT
    assert value["published_r4_tree"] == issuer.R4_TREE
