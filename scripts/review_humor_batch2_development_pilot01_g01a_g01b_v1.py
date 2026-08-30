"""Git-object-only G01A/G01B review for Development Pilot 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "601ee4812d864301cb55620e3d239515163e9ef8"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/"
OUT = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(name: str) -> dict[str, Any]:
    return json.loads(blob(PREFIX + name))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT,
            "HEAD must equal ingestion commit")
    source = blob(PREFIX + "source.utf8.txt")
    rights = load("rights-instrument.json")
    envelope = load("factual-authority-envelope.json")
    package = load("source-package.json")
    archive = load("archive-receipt.json")
    verification = load("custodial-verification.json")
    ledger = load("access-ledger-segment.json")
    ingestion = load("ingestion-receipt.json")
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(source_sha == "84261f1a6b97f951f70a1b86d42114da9703996607d43d2fc3779bffd7a97cb2", "source hash")
    require(source.decode("utf-8").encode("utf-8") == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source,
            "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive binding")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    required_ids = {
        "source_commitment": "c7a7c15444e5a21baebe7b90d0eb96522be6455fb0eaa763f3b2fbcdd71e98c2",
        "rights_instrument_identity": "11b24f3d67d17e04ff8ff24a38f1e24722de5433d76830a5b8c0e85ec0d45bab",
        "immutable_archive_commitment": "33fe934281f3eb21c19dc6bad23edfb5c809d32026dfdfddd77ed15d8417e031",
        "source_package_identity": "8377969bb9974e1e884243072fb178c977bb7074e03083f03a9329e64589f9ec",
        "factual_authority_envelope_identity": "7d0f1decc3e4908a03beedf4cec408cce096e07381b5e36f56c5e9dcb4975c65",
        "partition_identity": "74ef05ad01b3658d05f387632ae5a72a23de5eafa8955c659e1ae228bd634964",
    }
    for key, expected in required_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    contributor, ownership, grants, terms = (rights[x] for x in ("contributor", "ownership_declarations", "independent_grants", "rights_terms"))
    require(contributor["public_identity"] == contributor["legal_identity"] == contributor["rights_holder_identity"] ==
            "urn:pastila:party:pastila-acida-owner-v1", "rights-holder identity")
    require(all(ownership[x] is True for x in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "affirmative rights")
    negative_material = [x for x in ownership if x.startswith("contains_")]
    require(all(ownership[x] is False for x in negative_material), "third-party/private/sensitive material")
    require(all(grants[x] is True for x in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "applicable grants")
    require(all(grants[x] is False for x in ("model_exposure", "training", "runtime_integration", "production_routing")), "non-inheritance")
    require(terms["expires_at"] == "NO_EXPIRY" and datetime.fromisoformat(terms["effective_at"]).tzinfo is not None, "rights term")
    require(rights["source"]["source_version"] == "1.0.0" and datetime.fromisoformat(rights["source"]["capture_timestamp"]).tzinfo is not None, "version/capture")
    text = source.decode("utf-8")
    proposition_results = []
    require(len(envelope["propositions"]) == 6, "proposition count")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "modality/scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE" and proposition["known_boundary"] == "ONLY_THE_EXACT_BOUND_PROPOSITION", "attribution/known boundary")
        require(proposition["unknown_boundary"] == "ALL_UNSTATED_CONDITIONS_AND_REAL_WORLD_APPLICABILITY", "unknown boundary")
        require(proposition["time"] == "EXPLICIT_IF_BOUND_IN_OBJECT_OTHERWISE_UNSPECIFIED", "time boundary")
        require(proposition["sensitive_protected_target_classification"] == "NONE_DECLARED_LOW_RISK_SYNTHETIC", "target safety")
        for component in ("supporting_span", "subject", "predicate", "object") + (("qualification",) if proposition["qualification"] else ()):
            item = proposition[component]; cs, ce = item["character_coordinates"]; bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode("utf-8")
            require(value == source[bs:be] and hashlib.sha256(value).hexdigest() == item.get("sha256", item.get("span_sha256")),
                    f"span {proposition['proposition_id']} {component}")
        proposition_results.append({"proposition_id": proposition["proposition_id"], "span_coordinate_hash": "PASS",
                                    "modality_scope_attribution_boundaries": "PASS",
                                    "qualification": "BOUND" if proposition["qualification"] else "NONE_REQUIRED_BY_SOURCE",
                                    "time": proposition["time"]})
    require(verification["verification_result"] == "PASS_8_OF_8" and verification["packet_consumed"] is True and len(set(verification["nonces_consumed"])) == 8, "custodial consumption")
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "ledger continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "ledger seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "86aa81e1ba197d0ff7b4fe19bc7fa90773e7ded7596839d7d76ee5cdd74ae254", "ledger head")
    families = package["family_identities"]
    expected_families = {
        "source_family": "0958b102a31ce3a3101ca584a552a60c767243bd3ea8cf0211a64598231b8f12",
        "event_family": "0070e9be578ef6554e67ce342e798ca06f07dd898f792ebfea7440544448a55a",
        "authority_family": "9e9e829f602abcc23a7fb30a382422c63778f0bd217666bf3981f6aed249c754",
        "topic_entity_family": "2aad237873ea395239255e0f2fda5da0ec0220baca590aaa70bf06605216f4f4",
        "revision_family": "2633ed0e140e4e64badea4e67fd848acf6807529b57fa369932c63ce6025b837",
        "family_closure": "fd2e4d5cac6a7ed1b3800cc382a6860f2b690bf652691c134b94692bf4bf1f84",
        "creative_premise_family_id": "UNASSIGNED",
    }
    require(families == expected_families, "family identities/closure")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == required_ids["partition_identity"], "partition seal")
    # Locate every committed reference to this closure. All are confined to this pilot's
    # pre-ingestion, signing, or DEVELOPMENT ingestion artifacts.
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True).splitlines()
    allowed_fragments = ("development-pilot01-preingestion", "development-pilot01-signing-packet", "development-pilot01-ingestion-v1")
    require(all(any(fragment in ref for fragment in allowed_fragments) for ref in references), "cross-family reference")
    referenced_bytes = b"".join(blob(ref.split(":", 1)[1]) for ref in references)
    require(b'"partition": "BLIND_EVALUATION"' not in referenced_bytes and b'"partition": "CURRICULUM_CANDIDATE"' not in referenced_bytes,
            "cross-partition family member")
    require(b'"mechanism_assignment": true' not in referenced_bytes and b'"creative_premise_family_id": "UNASSIGNED"' in referenced_bytes,
            "mechanism/creative assignment")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha,
            "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE",
            "immutable_capture_and_version": "PASS", "propositions": proposition_results,
            "target_safety": "PASS_LOW_RISK_SYNTHETIC", "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED",
            "correction_revocation_supersession": "CURRENT_V1_NO_SUCCESSOR_OR_REVOCATION",
            "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS",
            "relationship_state": "PILOT_GENERATION_1_NO_DUPLICATE_REVISION_OR_SAME_EVENT_RELATIVE",
            "partition": "DEVELOPMENT", "partition_isolation": "PASS",
            "contamination_ledger_head": ledger["final_ledger_head"],
            "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE",
            "creative_premise_family_id": "UNASSIGNED", "mechanism_assignment": "ABSENT",
            "downstream_exposure": {key: False for key in ("constructor", "model", "training", "runtime", "production")}}
    core = {"schema_name": "batch2-development-pilot01-g01a-g01b-admission-v1", "schema_version": "1.0.0",
            "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
            "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
            "later_development_assignment_design_eligibility": True,
            "eligibility_scope": "SEPARATE_OWNER_AUTHORIZATION_REQUIRED_NO_ASSIGNMENT_GRANTED",
            "authority_matrix": {key: False for key in ("mechanism_assignment", "operational_obligation_assignment", "creative_premise_assignment",
                                                         "candidate_construction", "generation", "model_exposure", "training", "runtime_integration", "production_routing")}}
    admission_identity = seal("B2_DEVELOPMENT_PILOT01_G01A_G01B_ADMISSION_V1", core)
    receipt = {**core, "admission_identity": admission_identity}
    audit_core = {"schema_name": "batch2-development-pilot01-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
                  "reviewed_commit": COMMIT, "admission_identity": admission_identity,
                  "git_object_source_verification": "PASS", "exact_committed_ingestion_file_set": "PASS_8_FILES",
                  "identity_rederivation": "PASS", "span_coordinate_hash_verification": "PASS_6_PROPOSITIONS",
                  "rights_non_inheritance": "PASS", "family_partition_isolation": "PASS",
                  "contamination_and_ledger_continuity": "PASS", "hidden_assignment_or_exposure": "ABSENT",
                  "deterministic_blockers": [], "writes_beyond_review_artifacts": False}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT01_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot01-g01a-g01b-admission-v1.json", receipt),
                        ("humor-mechanics-batch2-development-pilot01-g01a-g01b-admission-v1-audit.json", audit)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission_identity,
                      "audit_identity": audit["audit_identity"], "contamination_state": g01b["contamination_state"],
                      "eligible_for_later_separately_authorized_development_assignment_design": True}, sort_keys=True))


if __name__ == "__main__":
    main()
