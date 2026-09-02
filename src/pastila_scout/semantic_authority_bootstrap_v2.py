"""Source-blind trust checks for future governed semantic-authority inputs.

This module validates envelopes only.  It cannot author, admit, persist, or
activate semantic content and is therefore safe to exercise with synthetic
non-family fixtures.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_identity(value: Mapping[str, Any], identity_field: str) -> str:
    body = {key: item for key, item in value.items() if key != identity_field}
    encoded = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def authority_content_identity(authority: Mapping[str, Any]) -> str:
    """Seal authority content without creating an authority/receipt hash cycle."""
    body = {
        key: item
        for key, item in authority.items()
        if key not in {"authority_identity", "admission_receipt"}
    }
    encoded = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_admitted_authority(
    authority: Mapping[str, Any],
    *,
    basis_identity: str,
    relation_class: str,
    evidence_kind: str,
    source_provenance_identity: str,
    candidate_author_identity: str,
    candidate_adjudicator_identity: str,
) -> None:
    """Fail closed unless an authority has an independent admission chain."""
    required = {
        "authority_identity",
        "kind",
        "basis_identity",
        "relation_class",
        "source_provenance_identity",
        "source_manifest",
        "admission_receipt",
        "canonical_semantic_content",
    }
    if required - authority.keys():
        raise ValueError("authority missing governed admission chain")
    if authority["authority_identity"] != authority_content_identity(authority):
        raise ValueError("authority identity mismatch")

    source = authority["source_manifest"]
    receipt = authority["admission_receipt"]
    if not isinstance(source, Mapping) or not isinstance(receipt, Mapping):
        raise ValueError("authority admission objects invalid")
    if source.get("source_identity") != canonical_identity(source, "source_identity"):
        raise ValueError("authority source identity mismatch")
    if receipt.get("admission_identity") != canonical_identity(
        receipt, "admission_identity"
    ):
        raise ValueError("authority admission identity mismatch")

    expected = {
        "basis_identity": basis_identity,
        "relation_class": relation_class,
        "kind": evidence_kind,
        "source_provenance_identity": source_provenance_identity,
    }
    for key, value in expected.items():
        if authority.get(key) != value:
            raise ValueError("authority binding mismatch")
    if source.get("provenance_identity") != source_provenance_identity:
        raise ValueError("authority source provenance mismatch")
    if receipt.get("source_identity") != source.get("source_identity"):
        raise ValueError("authority admission source mismatch")
    if receipt.get("authority_identity") != authority["authority_identity"]:
        raise ValueError("authority admission binding mismatch")
    if receipt.get("basis_identity") != basis_identity:
        raise ValueError("authority admission basis mismatch")
    if receipt.get("relation_class") != relation_class or receipt.get("kind") != evidence_kind:
        raise ValueError("authority admission class mismatch")
    if receipt.get("verdict") != "ADMITTED" or receipt.get("fail_closed") is not True:
        raise ValueError("authority not independently admitted")
    if source.get("origin") != "EXTERNAL_GOVERNED_GENERAL_SEMANTIC_SOURCE":
        raise ValueError("synthetic or internally derived authority source")
    if source.get("synthetic_qualification_fixture") is not False:
        raise ValueError("synthetic qualification authority prohibited")
    if receipt.get("candidate_identity") is not None:
        raise ValueError("candidate-dependent authority admission")

    owners = {
        source.get("source_owner"),
        receipt.get("verifier_identity"),
        candidate_author_identity,
        candidate_adjudicator_identity,
    }
    if None in owners or len(owners) != 4:
        raise ValueError("authority trust-domain collision")
    if authority.get("trust_domain_owner") != source.get("source_owner"):
        raise ValueError("authority owner assertion mismatch")
    if authority.get("independent") is not True:
        raise ValueError("authority independence flag absent")
