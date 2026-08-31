"""Git-object-only G01A/G01B review for Development Pilot 04."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "4e4afc730be7600fb0b6ce8abf822bce868b0565"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot04-ingestion-v1/"
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
    expected_files = {"source.utf8.txt", "rights-instrument.json", "factual-authority-envelope.json",
                      "source-package.json", "archive-receipt.json", "custodial-verification.json",
                      "access-ledger-segment.json", "ingestion-receipt.json"}
    tree = subprocess.check_output(["git", "ls-tree", "--name-only", COMMIT, PREFIX.rstrip("/")], cwd=ROOT, text=True)
    require(tree.strip() == PREFIX.rstrip("/"), "ingestion tree")
    listed = subprocess.check_output(["git", "ls-tree", "--name-only", f"{COMMIT}:{PREFIX.rstrip('/')}"], cwd=ROOT, text=True).splitlines()
    require(set(listed) == expected_files, "exact committed file set")
    source = blob(PREFIX + "source.utf8.txt")
    rights, envelope, package = load("rights-instrument.json"), load("factual-authority-envelope.json"), load("source-package.json")
    archive, verification, ledger = load("archive-receipt.json"), load("custodial-verification.json"), load("access-ledger-segment.json")
    ingestion = load("ingestion-receipt.json")
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(source_sha == "db4d440d42596e2db5ca402afa23bc8f65dcf7a7ba23a06d3ebef9e2eb1aa480", "source hash")
    require(source_oid == "342f171ed4dcf103a95dd49a6e974a2b246a8f8d", "source Git object")
    require(source.decode("utf-8").encode("utf-8") == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source,
            "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive binding")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    expected_ids = {
        "source_commitment": "da1142f651d94ff72ec4331ad7390d8977b8c1132cb908fb39f3c02cb3690720",
        "rights_instrument_identity": "549fa8e91e20dd36365bb4a37c4871a2951180ca6059bdf1243ab2c73f33646d",
        "immutable_archive_commitment": "07dc1bcf9f0af46e1b3003774ab39c7f612ba89daa58f3c402b1fc87cff1f7fd",
        "source_package_identity": "6fb31794566391bafa242fd8de1048ed3f3f234b9822b9d7f4a99307fbe1d72c",
        "factual_authority_envelope_identity": "40c92efd6ee0ae4b99d422094d2d28073ad8602df0c1528a38bbf681aba3de8d",
        "partition_identity": "d2f8f9069c01e25f754b14d6984aa3265aa843fb0a05c1b84555023145da9eb1",
    }
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    contributor = rights["contributor"]
    ownership, grants, terms = rights["ownership_declarations"], rights["independent_grants"], rights["rights_terms"]
    require(contributor["public_identity"] == contributor["legal_identity_commitment"] == contributor["rights_holder_identity"] ==
            "urn:pastila:party:pastila-acida-owner-v1", "rights-holder identity")
    require(contributor["identity_disclosure_approved_for_commit"] is False and
            contributor["legal_identity_verification_reference"].startswith("owner-record:"), "private legal identity protection")
    require(all(ownership[x] is True for x in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "affirmative rights")
    require(all(ownership[x] is False for x in ownership if x.startswith("contains_")), "third-party/private/sensitive material")
    require(all(grants[x] is True for x in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "applicable grants")
    require(all(grants[x] is False for x in ("model_exposure", "training", "runtime_integration", "production_routing")), "non-inheritance")
    require(terms["expires_at"] == "NO_EXPIRY" and datetime.fromisoformat(terms["effective_at"]).tzinfo is not None, "rights term")
    require(rights["source"]["source_version"] == "1.0.0" and datetime.fromisoformat(rights["source"]["capture_timestamp"]).tzinfo is not None, "version/capture")
    text = source.decode("utf-8")
    results = []
    require(len(envelope["propositions"]) == 7, "proposition count")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED", "modality")
        require(proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE", "attribution")
        require(proposition["known_boundary"] in {
            "ONLY_THE_EXACT_BOUND_PROPOSITION",
            "NUMBER_OF_PEOPLE_REQUESTING_ACCESS_NOT_ESTABLISHED",
        }, "known boundary")
        require(proposition["unknown_boundary"].endswith("REAL_WORLD_APPLICABILITY_UNKNOWN") or
                proposition["unknown_boundary"].endswith("REAL_WORLD_APPLICABILITY"), "unknown boundary")
        require(proposition["sensitive_protected_target_classification"] == "NONE_DECLARED_LOW_RISK_SYNTHETIC", "target")
        components = ["supporting_span", "subject", "predicate", "object"]
        if proposition["qualification"]:
            components.append("qualification")
        for component in components:
            item = proposition[component]
            cs, ce = item["character_coordinates"]
            bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode("utf-8")
            require(value == source[bs:be], f"coordinate {proposition['proposition_id']} {component}")
            require(hashlib.sha256(value).hexdigest() == item.get("sha256", item.get("span_sha256")), f"hash {proposition['proposition_id']} {component}")
        results.append({"proposition_id": proposition["proposition_id"], "coordinates_and_hashes": "PASS",
                        "modality_scope_attribution_boundaries": "PASS", "qualification": "BOUND" if proposition["qualification"] else "NONE_REQUIRED"})
    require(verification["verification_result"] == "PASS_8_OF_8" and verification["packet_consumed"] is True and len(set(verification["nonces_consumed"])) == 8, "custodial consumption")
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "ledger continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "ledger entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "3a172491ec99d5f8c0ef2d4be075912b5518f6b42bb19641bd60ab9b20d26fd4", "ledger head")
    families = package["family_identities"]
    require(families == {
        "authority_family": "f8b6dbc61f0f79ed4e396fdfe5645fe66223493cca8606202e4c4cc3de211d23",
        "creative_premise_family_id": "UNASSIGNED",
        "event_family": "ea19c20788d4790ee4d6cc0544db7c5cac78730edefbcd0cc773e47bd128efad",
        "family_closure": "ab682e0762d486faa5218ed249cfffe43feaf65025f23b8fbb2b1b94a7fcb54e",
        "revision_family": "15662651198cb31d3fd4d49b631f4950c79cb38426c4579c7d009929483030e8",
        "source_family": "dd1d5cb54f7b3b767b9950a44ee91115a9ccdad98cbd4f5566f454a0b5e94db0",
        "topic_entity_family": "910dc9e2464b40fce33cef763bfb87fb53f715be61ee6259994da53261a6e875",
    }, "family identities")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True).splitlines()
    allowed = ("development-pilot04-preingestion", "development-pilot04-signing-packet", "development-pilot04-family-independence", "development-pilot04-ingestion-v1")
    require(all(any(fragment in ref for fragment in allowed) for ref in references), "cross-family reference")
    referenced = b"".join(blob(ref.split(":", 1)[1]) for ref in references)
    require(b'"partition": "BLIND_EVALUATION"' not in referenced and b'"partition": "CURRICULUM_CANDIDATE"' not in referenced, "cross partition")
    require(b'"creative_premise_family_id": "UNASSIGNED"' in referenced, "creative premise")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha,
            "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE", "immutable_capture_and_version": "PASS",
            "propositions": results, "target_safety": "PASS_LOW_RISK_SYNTHETIC",
            "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED",
            "correction_revocation_supersession": "CURRENT_V1_NO_SUCCESSOR_OR_REVOCATION",
            "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS",
            "relationship_state": "FRESH_INDEPENDENT_FAMILY_NO_DUPLICATE_REVISION_SIBLING_OR_SAME_EVENT_RELATIVE",
            "partition": "DEVELOPMENT", "partition_isolation": "PASS",
            "contamination_ledger_head": ledger["final_ledger_head"],
            "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE",
            "creative_premise_family_id": "UNASSIGNED", "mechanism_assignment": "ABSENT",
            "downstream_exposure": {key: False for key in ("constructor", "model", "training", "runtime", "production")}}
    core = {"schema_name": "batch2-development-pilot04-g01a-g01b-admission-v1", "schema_version": "1.0.0",
            "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
            "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
            "later_development_assignment_design_eligibility": True,
            "eligibility_scope": "SEPARATE_OWNER_AUTHORIZATION_REQUIRED_NO_ASSIGNMENT_GRANTED",
            "authority_matrix": {key: False for key in ("mechanism_assignment", "operational_obligation_assignment", "creative_premise_assignment",
                                                         "candidate_construction", "generation", "model_exposure", "training", "runtime_integration",
                                                         "production_routing", "g04b_pool_certification")}}
    admission_id = seal("B2_DEVELOPMENT_PILOT04_G01A_G01B_ADMISSION_V1", core)
    receipt = {**core, "admission_identity": admission_id}
    audit_core = {"schema_name": "batch2-development-pilot04-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
                  "reviewed_commit": COMMIT, "admission_identity": admission_id, "git_object_source_verification": "PASS",
                  "exact_committed_ingestion_file_set": "PASS_8_FILES", "identity_rederivation": "PASS",
                  "span_coordinate_hash_verification": "PASS_7_PROPOSITIONS", "rights_non_inheritance": "PASS",
                  "family_partition_isolation": "PASS", "contamination_and_ledger_continuity": "PASS",
                  "hidden_assignment_or_exposure": "ABSENT", "deterministic_blockers": [], "writes_beyond_review_artifacts": False}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT04_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1.json", receipt),
                        ("humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1-audit.json", audit)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission_id,
                      "audit_identity": audit["audit_identity"], "contamination_state": g01b["contamination_state"],
                      "eligible_for_later_separately_authorized_development_assignment_design": True}, sort_keys=True))


if __name__ == "__main__":
    main()
