"""Git-object-only G01A/G01B review for Development Pilot 12."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "fdff67f28483d42db86ab1e8edbc7d082351f599"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot12-ingestion-v1/"
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
    listed = subprocess.check_output(["git", "ls-tree", "--name-only", f"{COMMIT}:{PREFIX.rstrip('/')}"],
                                     cwd=ROOT, text=True).splitlines()
    require(set(listed) == expected_files, "exact committed file set")
    source = blob(PREFIX + "source.utf8.txt")
    rights, envelope, package = load("rights-instrument.json"), load("factual-authority-envelope.json"), load("source-package.json")
    archive, verification = load("archive-receipt.json"), load("custodial-verification.json")
    ledger, ingestion = load("access-ledger-segment.json"), load("ingestion-receipt.json")
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(source_sha == "8b87cef6b320d45d7594bc48919bae63442f51f1f7937b599575d435df69ea27", "source hash")
    require(source_oid == "7cb8282216f81cf1c774eab46081c57e490529a1", "source object")
    require(source.decode().encode() == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source, "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    expected_ids = {
        "source_commitment": "fb35495f96a10daadfdd6ed305318276c6e34311e27486ca19462745663c85e1",
        "rights_instrument_identity": "371f2bf02ad08467e4b38b2051b97049f298e71e7dd712f9a37085e22a442499",
        "immutable_archive_commitment": "0b0e10f21e45690a822f67d47cbc977a4e6e3eeb0e746fb43ad410ac980eb7c5",
        "source_package_identity": "24e76e7f17c28a093cddb9c8be355c1298030a17f4cec0cf126210c4a529e3b6",
        "factual_authority_envelope_identity": "f219f9188b7d35134f0271b40fe485c5525a4b094b72b8c7b51472385fa5a1f4",
        "partition_identity": "6e13be38955b1f45ccf55b78d49e8d16c028b3de10d1c09b09d9ac8ebfcc10c7",
    }
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    require(ingestion["ingestion_receipt_identity"] == "220fabdb6763ad7abd32acba0b61ff28ad79d53d487636033fd2c00ec295b823", "ingestion")
    require(verification["verification_identity"] == "7be8a56d33ce31301a54199ae6b3edd16139335c30105cd6b89f0450b401e1c4", "verification")
    require(archive["archive_receipt_identity"] == "e055a323ac7a946ba0ff4f5af2e0bc122534d4d6f78f6ba492b21080d090c292", "archive")
    require(ledger["ledger_segment_identity"] == "0a7e635952884330e01b6ecbfde6ac6b9c7a3951b1efb249a29172766543636d", "ledger")
    contributor, ownership = rights["contributor"], rights["ownership_declarations"]
    grants, terms = rights["independent_grants"], rights["rights_terms"]
    require(contributor["public_identity"] == contributor["legal_identity_commitment"] == contributor["rights_holder_identity"], "rights holder")
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity protection")
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "rights")
    require(all(ownership[key] is False for key in ownership if key.startswith("contains_")), "excluded material")
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "noninheritance")
    require(terms["expires_at"] == "NO_EXPIRY" and datetime.fromisoformat(terms["effective_at"]).tzinfo is not None, "rights terms")
    require(terms["correction_policy"] == "NEW_IMMUTABLE_REVISION_ONLY", "revision policy")
    text, proposition_results = source.decode(), []
    require(len(envelope["propositions"]) == 8, "proposition count")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE", "attribution")
        require(proposition["known_boundary"] and proposition["unknown_boundary"], "boundary")
        require(proposition["sensitive_protected_target_classification"] == "NONE_DECLARED_LOW_RISK_SYNTHETIC", "target")
        require(proposition["quotation_status"] == "NO_QUOTATION", "quotation")
        components = ["supporting_span", "subject", "predicate", "object"] + (["qualification"] if proposition["qualification"] else [])
        for component in components:
            item = proposition[component]
            cs, ce = item["character_coordinates"]
            bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode()
            require(value == source[bs:be], "coordinate span")
            require(hashlib.sha256(value).hexdigest() == item.get("sha256", item.get("span_sha256")), "span hash")
        proposition_results.append({"proposition_id": proposition["proposition_id"],
                                    "coordinates_and_hashes": "PASS",
                                    "modality_scope_attribution_boundaries": "PASS",
                                    "sufficiency_selection": "NOT_EVALUATED"})
    require(verification["verification_result"] == "PASS_8_OF_8" and verification["packet_consumed"] is True, "custody")
    require(len(verification["verified_responses"]) == len(set(verification["nonces_consumed"])) == 8, "nonce consumption")
    require(all(item["signature_verification"] == "PASS" for item in verification["verified_responses"]), "signatures")
    previous = ledger["previous_ledger_head"]
    require(previous == "1cc90a7a8a7ae0471411a75ad7a5d87c90c983c059fd27ae661d95bc894991b3", "prior ledger")
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "cc0493c97949a0426ff7ab9427a45fc23be468a0cac7ebd5732eaef5c96dcf1b", "ledger head")
    families = package["family_identities"]
    require(families["family_closure"] == "8d2800c73622e2eff44af4d30dcf75acd389be5e704272855928008a74757dba", "family closure")
    require(all(families[key] == "UNASSIGNED" for key in ("construction_revision_family_id", "creative_marker_family_id", "creative_premise_family_id")), "creative isolation")
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"],
                                         cwd=ROOT, text=True).splitlines()
    allowed = ("development-pilot12-preingestion", "development-pilot12-signing-packet",
               "development-pilot12-family-independence", "development-pilot12-ingestion-v1")
    require(references and all(any(fragment in ref for fragment in allowed) for ref in references), "family references")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    require(ingestion["proposition_bindings"] == "PASS_8_NOT_SELECTED" and ingestion["proposition_sufficiency_evaluated"] is False, "downstream")
    require(all(value is False for value in ingestion["authority_matrix"].values()), "authority matrix")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha,
            "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE",
            "immutable_capture_and_version": "PASS", "propositions": proposition_results,
            "proposition_binding_state": "PASS_8_NOT_SELECTED", "target_safety": "PASS_LOW_RISK_SYNTHETIC",
            "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED",
            "correction_revocation_supersession": "CURRENT_V1_NO_SUCCESSOR_OR_REVOCATION",
            "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS",
            "relationship_state": "FRESH_INDEPENDENT_FAMILY_NO_DUPLICATE_REVISION_SIBLING_OR_SAME_EVENT_RELATIVE",
            "partition": "DEVELOPMENT", "partition_isolation": "PASS",
            "contamination_ledger_head": ledger["final_ledger_head"],
            "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE",
            "creative_premise_family_id": "UNASSIGNED", "mechanism_assignment": "ABSENT",
            "operational_obligation_assignment": "ABSENT",
            "downstream_exposure": {key: False for key in ("constructor", "realizer", "candidate_emitter", "model", "training", "runtime", "production")}}
    authority_names = ("proposition_sufficiency_evaluation", "proposition_selection", "assignment", "semantic_role_planning",
                       "affordance_planning", "constructor_v5_3_1_source_compatibility_evaluation", "semantic_plan_evaluation",
                       "constructor_release", "constructor_invocation", "realization", "candidate_emission",
                       "coordinate_bound_semantic_conformance", "fragment_collision_evaluation", "g02", "g02c", "g03",
                       "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")
    core = {"schema_name": "batch2-development-pilot12-g01a-g01b-admission-v1", "schema_version": "1.0.0",
            "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
            "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
            "proposition_sufficiency_evaluated": False, "proposition_selected": False,
            "constructor_v5_3_1_compatibility_or_semantic_plan_evaluated": False,
            "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_POST_G01_PROPOSITION_SUFFICIENCY_GATE_ONLY",
            "authority_matrix": {key: False for key in authority_names}}
    admission = {**core, "admission_identity": seal("B2_DEVELOPMENT_PILOT12_G01A_G01B_ADMISSION_V1", core)}
    audit_core = {"schema_name": "batch2-development-pilot12-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
                  "reviewed_commit": COMMIT, "admission_identity": admission["admission_identity"],
                  "git_object_source_verification": "PASS", "exact_committed_ingestion_file_set": "PASS_8_FILES",
                  "identity_rederivation": "PASS", "span_coordinate_hash_verification": "PASS_8_PROPOSITIONS_NOT_SELECTED",
                  "rights_non_inheritance": "PASS", "family_partition_isolation": "PASS",
                  "contamination_and_ledger_continuity": "PASS", "proposition_sufficiency_evaluated": False,
                  "proposition_selected": False, "hidden_assignment_planning_or_exposure": "ABSENT",
                  "deterministic_blockers": []}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT12_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    outputs = (("humor-mechanics-batch2-development-pilot12-g01a-g01b-admission-v1.json", admission),
               ("humor-mechanics-batch2-development-pilot12-g01a-g01b-admission-v1-audit.json", audit))
    for name, value in outputs:
        path = OUT / name
        require(not path.exists(), "review exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission["admission_identity"],
                      "audit_identity": audit["audit_identity"], "proposition_bindings": "PASS_8_NOT_SELECTED",
                      "next_gate": "POST_G01_PROPOSITION_SUFFICIENCY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
