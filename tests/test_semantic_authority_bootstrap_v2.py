from copy import deepcopy

import pytest

from pastila_scout.candidate_authoring_v2 import authority_identity
from pastila_scout.semantic_authority_bootstrap_v2 import (
    canonical_identity,
    verify_admitted_authority,
)


def admitted():
    source = {
        "origin": "EXTERNAL_GOVERNED_GENERAL_SEMANTIC_SOURCE",
        "source_owner": "SOURCE_OWNER",
        "provenance_identity": "provenance",
        "source_commitment": "commitment",
        "synthetic_qualification_fixture": False,
        "source_identity": "",
    }
    source["source_identity"] = canonical_identity(source, "source_identity")
    authority = {
        "kind": "semantic_authority",
        "basis_identity": "basis",
        "relation_class": "CAUSAL",
        "source_provenance_identity": "provenance",
        "trust_domain_owner": "SOURCE_OWNER",
        "independent": True,
        "source_manifest": source,
        "canonical_semantic_content": {"relation": "synthetic-test-only"},
        "admission_receipt": {},
        "authority_identity": "",
    }
    authority["authority_identity"] = authority_identity(authority)
    receipt = {
        "source_identity": source["source_identity"],
        "authority_identity": authority["authority_identity"],
        "basis_identity": "basis",
        "relation_class": "CAUSAL",
        "kind": "semantic_authority",
        "verdict": "ADMITTED",
        "fail_closed": True,
        "candidate_identity": None,
        "verifier_identity": "AUTHORITY_VERIFIER",
        "admission_identity": "",
    }
    receipt["admission_identity"] = canonical_identity(receipt, "admission_identity")
    authority["admission_receipt"] = receipt
    return authority


def verify(authority):
    verify_admitted_authority(
        authority,
        basis_identity="basis",
        relation_class="CAUSAL",
        evidence_kind="semantic_authority",
        source_provenance_identity="provenance",
        candidate_author_identity="CANDIDATE_AUTHOR",
        candidate_adjudicator_identity="RULE_ADJUDICATOR",
    )


def test_complete_non_circular_chain_is_accepted():
    verify(admitted())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda a: a.update(independent=False),
        lambda a: a["source_manifest"].update(origin="SYNTHETIC_FIXTURE"),
        lambda a: a["source_manifest"].update(synthetic_qualification_fixture=True),
        lambda a: a["admission_receipt"].update(candidate_identity="candidate"),
        lambda a: a["admission_receipt"].update(verdict="REJECTED"),
        lambda a: a["admission_receipt"].update(verifier_identity="CANDIDATE_AUTHOR"),
        lambda a: a.update(trust_domain_owner="ASSERTED_OTHER_OWNER"),
    ],
)
def test_resealed_adversarial_variants_fail(mutate):
    authority = admitted()
    mutate(authority)
    authority["source_manifest"]["source_identity"] = canonical_identity(
        authority["source_manifest"], "source_identity"
    )
    authority["authority_identity"] = authority_identity(authority)
    authority["admission_receipt"]["source_identity"] = authority["source_manifest"][
        "source_identity"
    ]
    authority["admission_receipt"]["authority_identity"] = authority[
        "authority_identity"
    ]
    authority["admission_receipt"]["admission_identity"] = canonical_identity(
        authority["admission_receipt"], "admission_identity"
    )
    with pytest.raises(ValueError):
        verify(authority)


def test_identity_graph_has_no_authority_receipt_hash_cycle():
    authority = admitted()
    changed = deepcopy(authority)
    changed["admission_receipt"]["verifier_identity"] = "OTHER_VERIFIER"
    assert authority_identity(changed) == authority["authority_identity"]
    assert canonical_identity(
        changed["admission_receipt"], "admission_identity"
    ) != authority["admission_receipt"]["admission_identity"]
