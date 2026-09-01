"""Git-object-only G01A/G01B review for Development Pilot 13."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "34a39ae37563d923f55549fb620601a46e4f9d63"
PREPARATION_COMMIT = "9424ded3c53b0155febc6993254ec52cf79bd81a"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot13-ingestion-v1/"
OUT = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str, commit: str = COMMIT) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


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
    independence = json.loads(blob("docs/artifacts/humor-mechanics-batch2-development-pilot13-family-independence-v1.json", PREPARATION_COMMIT))
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(source_sha == "9d79b45d06fba5b950f97e7d09f38450177b7ff7d5cbf962a9e4f7af452b6a76", "source hash")
    require(source_oid == "e3631174edc2adb56b1f28b803eafb9ceba487ff", "source object")
    require(source.decode().encode() == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source, "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    expected_ids = {
        "source_commitment": "8886fa5ee7f13af2ab7eca004c4838b9af83d0b31671f1df9a8d98426fdf7ff9",
        "rights_instrument_identity": "bd784d0cdbc1e0452c6a66ac2f8dfd6a0a94394e892e9500228fbadee6b8ead9",
        "immutable_archive_commitment": "a3f32d4f29ccf03f4a2547ab4e7a885c9952ac4219d753b984491538242774e6",
        "source_package_identity": "3acf18889454e8fdd8397e0a41f6f96216cd6be98f6ab2b54131acff1e7c31a0",
        "factual_authority_envelope_identity": "509b2472a28a2f6ce3b514a05820f13be29d60df98464af0b1e25d1bb1cb3af9",
        "partition_identity": "710267f2d079966d1de2a1912bd9ef73deee60d38ecb97914ad4e7bd3cd6fced",
    }
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    require(ingestion["ingestion_receipt_identity"] == "ecc1252846d30658e3adee1cac4de52d69ec9b0c7e68e0b4e3763401fe3cd4c6", "ingestion")
    require(verification["verification_identity"] == "8d766a103b929e8e437dc998863656de86791380aa829963518326c25bda5dc5", "verification")
    require(archive["archive_receipt_identity"] == "d2fef97efead557c2a65285f7a700ea63a4d5b479ee246193d046599a90734a6", "archive")
    require(ledger["ledger_segment_identity"] == "88235bf972667cde211b4dec63ef60f28066f390938af6d57a61a91aeb7cb9d2", "ledger")
    contributor, ownership, grants = rights["contributor"], rights["ownership_declarations"], rights["independent_grants"]
    require(contributor["public_identity"] == contributor["legal_identity_commitment"] == contributor["rights_holder_identity"], "rights holder")
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity protection")
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "rights")
    require(all(ownership[key] is False for key in ownership if key.startswith("contains_")), "excluded material")
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "noninheritance")
    require(rights["owner_confirmation"]["confirmed"] is True and rights["trial_role"] == "LEGITIMATE_END_TO_END_MECHANISM_TRIAL", "owner confirmation")
    text, proposition_results = source.decode(), []
    require(len(envelope["propositions"]) == 8 and envelope["proposition_selection"] == "NOT_PERFORMED", "proposition count/selection")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE" and proposition["known_boundary"] and proposition["unknown_boundary"], "authority boundaries")
        require(proposition["sensitive_protected_target_classification"] == "NONE_DECLARED_LOW_RISK_SYNTHETIC" and proposition["quotation_status"] == "NO_QUOTATION", "target/quotation")
        components = ["supporting_span", "subject", "predicate", "object"] + (["qualification"] if proposition["qualification"] else [])
        for component in components:
            item = proposition[component]
            cs, ce = item["character_coordinates"]
            bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode()
            require(value == source[bs:be] and hashlib.sha256(value).hexdigest() == item.get("sha256", item.get("span_sha256")), "span")
        proposition_results.append({"proposition_id": proposition["proposition_id"], "coordinates_and_hashes": "PASS", "modality_scope_attribution_boundaries": "PASS", "sufficiency_selection": "NOT_EVALUATED"})
    require(verification["verification_result"] == "PASS_8_OF_8" and verification["packet_consumed"] is True, "custody")
    require(len(verification["verified_responses"]) == len(set(verification["nonces_consumed"])) == 8, "nonces")
    require(all(item["signature_verification"] == "PASS" for item in verification["verified_responses"]), "signatures")
    previous = ledger["previous_ledger_head"]
    require(previous == "cc0493c97949a0426ff7ab9427a45fc23be468a0cac7ebd5732eaef5c96dcf1b", "prior ledger")
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "a97d53ffe4ce3eedd3438e3551b9ee94b67f2f515e016783359efe290b93a72a", "ledger head")
    require(independence["family_independence_identity"] == "f37e392607eb53190b98434a777207a66426fced35d550dede87f96d1bb69125", "independence identity")
    require(independence["result"] == "PASS_FRESH_FAMILY_INDEPENDENCE" and independence["source_hash_distinct"] and independence["git_blob_distinct"], "family independence")
    require(not independence["exact_prior_line_reuse"] and not independence["source_event_topic_revision_sibling_syndication_same_event_relation"] and not independence["prior_downstream_or_expected_result_shaping"] and not independence["blind_family_access"], "contamination")
    families = package["family_identities"]
    require(families["family_closure"] == "eb3c3a116fd30596e1b606051a8da8da1aaa9b4ca33eff21bbd94b051928b8b2", "family closure")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    require(ingestion["proposition_bindings"] == "PASS_8_NOT_SELECTED" and ingestion["proposition_sufficiency_evaluated"] is False, "downstream")
    require(all(value is False for value in ingestion["authority_matrix"].values()), "authority matrix")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha, "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE", "immutable_capture_and_version": "PASS", "propositions": proposition_results, "proposition_binding_state": "PASS_8_NOT_SELECTED", "target_safety": "PASS_LOW_RISK_SYNTHETIC", "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED", "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS", "relationship_state": "FRESH_INDEPENDENT_FAMILY_NO_DUPLICATE_REVISION_SIBLING_OR_SAME_EVENT_RELATIVE", "partition": "DEVELOPMENT", "partition_isolation": "PASS", "contamination_ledger_head": ledger["final_ledger_head"], "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "creative_premise_family_id": "UNASSIGNED", "mechanism_assignment": "ABSENT", "operational_obligation_assignment": "ABSENT", "downstream_exposure": {key: False for key in ("constructor", "provider", "emitter", "model", "training", "runtime", "production")}}
    authority_names = ("proposition_sufficiency_evaluation", "proposition_selection", "assignment", "semantic_role_planning", "affordance_planning", "constructor_v5_3_3_compatibility", "semantic_plan", "constructor_release", "constructor_invocation", "realization", "candidate_emission", "semantic_conformance", "fragment_collision", "g02", "g02c", "g03", "g03b", "g03c", "romanian_naturalness", "voice", "owner_review", "g04b", "model_exposure", "training", "runtime_integration", "production_routing")
    core = {"schema_name": "batch2-development-pilot13-g01a-g01b-admission-v1", "schema_version": "1.0.0", "pilot_role": "LEGITIMATE_END_TO_END_MECHANISM_TRIAL", "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"], "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b, "proposition_sufficiency_evaluated": False, "proposition_selected": False, "constructor_v5_3_3_compatibility_or_semantic_plan_evaluated": False, "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_POST_G01_PROPOSITION_SUFFICIENCY_GATE_ONLY", "authority_matrix": {key: False for key in authority_names}}
    admission = {**core, "admission_identity": seal("B2_DEVELOPMENT_PILOT13_G01A_G01B_ADMISSION_V1", core)}
    audit_core = {"schema_name": "batch2-development-pilot13-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0", "reviewed_commit": COMMIT, "admission_identity": admission["admission_identity"], "git_object_source_verification": "PASS", "exact_committed_ingestion_file_set": "PASS_8_FILES", "identity_rederivation": "PASS", "span_coordinate_hash_verification": "PASS_8_PROPOSITIONS_NOT_SELECTED", "rights_non_inheritance": "PASS", "family_partition_isolation": "PASS", "contamination_and_ledger_continuity": "PASS", "proposition_sufficiency_evaluated": False, "proposition_selected": False, "hidden_assignment_planning_or_exposure": "ABSENT", "deterministic_blockers": []}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT13_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot13-g01a-g01b-admission-v1.json", admission), ("humor-mechanics-batch2-development-pilot13-g01a-g01b-admission-v1-audit.json", audit)):
        path = OUT / name
        require(not path.exists(), "review exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission["admission_identity"], "audit_identity": audit["audit_identity"], "proposition_bindings": "PASS_8_NOT_SELECTED", "next_gate": "POST_G01_PROPOSITION_SUFFICIENCY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
