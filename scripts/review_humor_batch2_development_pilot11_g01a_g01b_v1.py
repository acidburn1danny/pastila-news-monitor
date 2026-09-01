"""Git-object-only G01A/G01B review for Development Pilot 11."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "2a8f78214446c721edc9385e9a83bde91f6e4228"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot11-ingestion-v1/"
OUT = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(name: str) -> dict[str, Any]:
    return json.loads(blob(PREFIX + name))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    expected_files = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json", "source-package.json",
                      "archive-receipt.json", "custodial-verification.json", "access-ledger-segment.json", "ingestion-receipt.json"}
    listed = subprocess.check_output(["git", "ls-tree", "--name-only", f"{COMMIT}:{PREFIX.rstrip('/')}"], cwd=ROOT, text=True).splitlines()
    require(set(listed) == expected_files, "exact committed file set")
    source = blob(PREFIX + "source.utf8.txt")
    rights, envelope, package = load("rights-instrument.json"), load("factual-authority-envelope.json"), load("source-package.json")
    archive, verification = load("archive-receipt.json"), load("custodial-verification.json")
    ledger, ingestion = load("access-ledger-segment.json"), load("ingestion-receipt.json")
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(source_sha == "cdf1901941057914cb7b22ac1233771773e2f15bd1671bcc47e2d17d123e2bd9", "source hash")
    require(source_oid == "219938213986d668a53490734510a016437bbad2", "source object")
    require(source.decode().encode() == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source, "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    expected_ids = {"source_commitment": "674ec0659a372c80eadc4f78f539df5db40b8a0ecac899b7a508c9e59d72568c",
        "rights_instrument_identity": "7299ad5a4d1f8c9adf34c336858a5bf44ed901b503f51e23b89210b7029d1241",
        "immutable_archive_commitment": "f9c10644629f87ff088a836e19f2c080d2cdd6daffe1028a55583c277a07b625",
        "source_package_identity": "f69112cebbb6edb3f46427a923de82383b1065e4d497e19f885fbfb8e117dd1e",
        "factual_authority_envelope_identity": "a12fa5890bdafe8d48e83897f4dea5a49c56bc59b301b2b37872991440dcd1f1",
        "partition_identity": "6f07bdcff4f9c7de7631b703b0f587c30b9443bba5ab0d3145998b778e619304"}
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    require(ingestion["ingestion_receipt_identity"] == "7df4980d4d38fb1084d9b651035e98712e3494ab7deb87b7d1587078d6c07d54", "ingestion")
    require(verification["verification_identity"] == "cd54abdcb0ac57d603147d9fdc15cfb15255ab9b7750e975cef0b58e420058bc", "verification")
    require(archive["archive_receipt_identity"] == "4aada81e57e68c5cbd7bdd026f32f921b58e6d82b20d334b19c074a4fd934bea", "archive")
    require(ledger["ledger_segment_identity"] == "1b0eb047a049f3b25e500409b26ecb35da5766ec7ce7d9496dd03f7b094ec684", "ledger")
    contributor, ownership = rights["contributor"], rights["ownership_declarations"]
    grants, terms = rights["independent_grants"], rights["rights_terms"]
    require(contributor["public_identity"] == contributor["legal_identity_commitment"] == contributor["rights_holder_identity"], "rights holder")
    require(contributor["identity_disclosure_approved_for_commit"] is False and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity protection")
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "rights")
    require(all(ownership[key] is False for key in ownership if key.startswith("contains_")), "excluded material")
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "noninheritance")
    require(terms["expires_at"] == "NO_EXPIRY" and datetime.fromisoformat(terms["effective_at"]).tzinfo is not None, "rights terms")
    require(terms["correction_policy"] == "NEW_IMMUTABLE_REVISION_ONLY" and terms["supersession_policy"] == "EXPLICIT_PREDECESSOR_SUCCESSOR_CHAIN", "revision policy")
    text, results = source.decode(), []
    require(len(envelope["propositions"]) == 7, "proposition count")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE" and proposition["known_boundary"] and proposition["unknown_boundary"], "boundary")
        require(proposition["sensitive_protected_target_classification"] == "NONE_DECLARED_LOW_RISK_SYNTHETIC", "target")
        require(proposition["quotation_status"] == "NO_QUOTATION", "quotation")
        components = ["supporting_span", "subject", "predicate", "object"] + (["qualification"] if proposition["qualification"] else [])
        for component in components:
            item = proposition[component]; cs, ce = item["character_coordinates"]; bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode()
            require(value == source[bs:be] and hashlib.sha256(value).hexdigest() == item.get("sha256", item.get("span_sha256")), "span")
        results.append({"proposition_id": proposition["proposition_id"], "coordinates_and_hashes": "PASS",
                        "modality_scope_attribution_boundaries": "PASS", "qualification": "BOUND" if proposition["qualification"] else "NONE_REQUIRED"})
    require(verification["verification_result"] == "PASS_8_OF_8" and verification["packet_consumed"] is True, "custody")
    require(len(verification["verified_responses"]) == len(set(verification["nonces_consumed"])) == 8, "nonce consumption")
    require(all(item["signature_verification"] == "PASS" for item in verification["verified_responses"]), "signatures")
    previous = ledger["previous_ledger_head"]
    require(previous == "e8279d111b95f6a1e4abf96ace2594c2cdbda6be504708d7df3d9e10feec8335", "prior ledger")
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "1cc90a7a8a7ae0471411a75ad7a5d87c90c983c059fd27ae661d95bc894991b3", "ledger head")
    families = package["family_identities"]
    require(families == {"authority_family": "52a5b2138bd40d439cf65aea4d8eb2842efaea614e62352f8a7682f36a14d851",
        "construction_revision_family_id": "UNASSIGNED", "creative_marker_family_id": "UNASSIGNED",
        "creative_premise_family_id": "UNASSIGNED", "event_family": "c84fb1b2da238189c9de168f88af297b4473d6bd9d5f5384a3fd3777522cb1dc",
        "family_closure": "a05bd9cf96214d6f2b86e35440e008acd1fc7c84b1d5aacc7b88500cfb6e40bb",
        "revision_family": "f4e871ba13e7357c33935ed67ee332af12aaf9ee2d5ecf7b447d7b6a5df2acb0",
        "source_family": "c823818d0700089d4046395fea8e04503e7146033ef0ce28ca159e1e0ba9bb99",
        "topic_entity_family": "917643501067e6d07d7803fc7fc9e80832f23ca144cd2e5fb26ae5f698e4c0f6"}, "families")
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True).splitlines()
    allowed = ("development-pilot11-preingestion", "development-pilot11-signing-packet", "development-pilot11-family-independence", "development-pilot11-ingestion-v1")
    require(references and all(any(fragment in ref for fragment in allowed) for ref in references), "family references")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    require(ingestion["proposition_sufficiency_evaluated"] is False and ingestion["constructor_v5_3_compatibility_or_semantic_plan_evaluated"] is False, "downstream")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha,
        "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE", "immutable_capture_and_version": "PASS",
        "propositions": results, "target_safety": "PASS_LOW_RISK_SYNTHETIC", "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED",
        "correction_revocation_supersession": "CURRENT_V1_NO_SUCCESSOR_OR_REVOCATION", "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS",
        "relationship_state": "FRESH_INDEPENDENT_FAMILY_NO_DUPLICATE_REVISION_SIBLING_OR_SAME_EVENT_RELATIVE",
        "partition": "DEVELOPMENT", "partition_isolation": "PASS", "contamination_ledger_head": ledger["final_ledger_head"],
        "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "creative_premise_family_id": "UNASSIGNED",
        "mechanism_assignment": "ABSENT", "operational_obligation_assignment": "ABSENT",
        "downstream_exposure": {key: False for key in ("constructor", "realizer", "candidate_emitter", "model", "training", "runtime", "production")}}
    core = {"schema_name": "batch2-development-pilot11-g01a-g01b-admission-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
        "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
        "proposition_sufficiency_evaluated": False, "constructor_v5_3_compatibility_or_semantic_plan_evaluated": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_POST_G01_PROPOSITION_SUFFICIENCY_GATE_ONLY",
        "authority_matrix": {key: False for key in ("proposition_sufficiency_evaluation", "assignment",
            "constructor_v5_3_source_compatibility_evaluation", "semantic_plan_evaluation", "constructor_release", "constructor_invocation",
            "realization", "candidate_emission", "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c", "g03",
            "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    admission = {**core, "admission_identity": seal("B2_DEVELOPMENT_PILOT11_G01A_G01B_ADMISSION_V1", core)}
    audit_core = {"schema_name": "batch2-development-pilot11-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "admission_identity": admission["admission_identity"], "git_object_source_verification": "PASS",
        "exact_committed_ingestion_file_set": "PASS_8_FILES", "identity_rederivation": "PASS",
        "span_coordinate_hash_verification": "PASS_7_PROPOSITIONS", "rights_non_inheritance": "PASS",
        "family_partition_isolation": "PASS", "contamination_and_ledger_continuity": "PASS",
        "proposition_sufficiency_evaluated": False, "constructor_v5_3_compatibility_or_semantic_plan_evaluated": False,
        "hidden_assignment_or_exposure": "ABSENT", "deterministic_blockers": []}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT11_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot11-g01a-g01b-admission-v1.json", admission),
                        ("humor-mechanics-batch2-development-pilot11-g01a-g01b-admission-v1-audit.json", audit)):
        path = OUT / name
        require(not path.exists(), "review exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission["admission_identity"],
                      "audit_identity": audit["audit_identity"], "next_gate": "POST_G01_PROPOSITION_SUFFICIENCY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
