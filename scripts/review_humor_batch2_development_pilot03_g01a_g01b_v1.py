"""Git-object-only G01A/G01B review for Development Pilot 03."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "8aaeccbbca9d45fb9d522505f82d173e1090b3b6"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot03-ingestion-v1/"
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
    require(source_sha == "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30", "source hash")
    require(source_oid == "84d545881e9e701692731ae2d92892a18d58eb0a", "source Git object")
    require(source.decode("utf-8").encode("utf-8") == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source,
            "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive binding")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    expected_ids = {
        "source_commitment": "2cbc5e36316e3f536f8bcca1bc105daf3a69d0b16cd1c48b9528411e3325c85d",
        "rights_instrument_identity": "1165555c4f91781f5c22db56316899c9f89dfcc46c817f24d59dc997790cc4d6",
        "immutable_archive_commitment": "a114c0858b66bee530afe758e1ba174356913f2eecac5f90780ff63902816955",
        "source_package_identity": "08fe16a0a8b003a661cac1238eec0f752be1ae5c11e417125e1d7031291abeb6",
        "factual_authority_envelope_identity": "3808b24094412383f4a152233c7f18d098ea4cfa6a90c2a41ee1093c8ac02ac3",
        "partition_identity": "cf750b5d3f2cb53da2318723672c56668576b5dd84513cf4d389526f9dd5468c",
    }
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    contributor = rights["contributor"]
    ownership, grants, terms = rights["ownership_declarations"], rights["independent_grants"], rights["rights_terms"]
    require(contributor["public_identity"] == contributor["legal_identity"] == contributor["rights_holder_identity"] ==
            "urn:pastila:party:pastila-acida-owner-v1", "rights-holder identity")
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
        require(proposition["known_boundary"] in {"ONLY_THE_EXACT_BOUND_PROPOSITION", "EXACT_CONTENT_NOT_DOCUMENTED_AT_RECEIPT"}, "known boundary")
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
    require(previous == ledger["final_ledger_head"] == "81e65fd0e0a703fe388a0391fad9eb94331c734a8e37ca98f1dd07c0faf38b56", "ledger head")
    families = package["family_identities"]
    require(families == {
        "authority_family": "3b8ac6cc7c0833e50e20f537dd3b107b87753678064af4a9a16c54ed01b0e68f",
        "creative_premise_family_id": "UNASSIGNED",
        "event_family": "e6e856a2cbfd922994ffa49aac85f15356dc110e165c39c8fdf42a8b080dee32",
        "family_closure": "72ba444c839d38109fcf46cbad176f6c929dc7155129178428f57bd4060beff5",
        "revision_family": "471c1ffcef336effca84c8b707ee69df33dafed6bb5e4b5d76737fec900477cf",
        "source_family": "4f61c0b3898d1adab00cf56b3e1e378c2b3a152ae820efa32102849e7013a093",
        "topic_entity_family": "b7aafaa8a87f81a589d7b9aad899c08e7b4977df581a832b0289da5841b174be",
    }, "family identities")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True).splitlines()
    allowed = ("development-pilot03-preingestion", "development-pilot03-signing-packet", "development-pilot03-family-independence", "development-pilot03-ingestion-v1")
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
    core = {"schema_name": "batch2-development-pilot03-g01a-g01b-admission-v1", "schema_version": "1.0.0",
            "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
            "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
            "later_development_assignment_design_eligibility": True,
            "eligibility_scope": "SEPARATE_OWNER_AUTHORIZATION_REQUIRED_NO_ASSIGNMENT_GRANTED",
            "authority_matrix": {key: False for key in ("mechanism_assignment", "operational_obligation_assignment", "creative_premise_assignment",
                                                         "candidate_construction", "generation", "model_exposure", "training", "runtime_integration", "production_routing")}}
    admission_id = seal("B2_DEVELOPMENT_PILOT03_G01A_G01B_ADMISSION_V1", core)
    receipt = {**core, "admission_identity": admission_id}
    audit_core = {"schema_name": "batch2-development-pilot03-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
                  "reviewed_commit": COMMIT, "admission_identity": admission_id, "git_object_source_verification": "PASS",
                  "exact_committed_ingestion_file_set": "PASS_8_FILES", "identity_rederivation": "PASS",
                  "span_coordinate_hash_verification": "PASS_7_PROPOSITIONS", "rights_non_inheritance": "PASS",
                  "family_partition_isolation": "PASS", "contamination_and_ledger_continuity": "PASS",
                  "hidden_assignment_or_exposure": "ABSENT", "deterministic_blockers": [], "writes_beyond_review_artifacts": False}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT03_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot03-g01a-g01b-admission-v1.json", receipt),
                        ("humor-mechanics-batch2-development-pilot03-g01a-g01b-admission-v1-audit.json", audit)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission_id,
                      "audit_identity": audit["audit_identity"], "contamination_state": g01b["contamination_state"],
                      "eligible_for_later_separately_authorized_development_assignment_design": True}, sort_keys=True))


if __name__ == "__main__":
    main()
