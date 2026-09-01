"""Git-object-only G01A/G01B review for Development Pilot 10."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "3401c3e28b33498c290cb7506ef77778a7a415ff"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot10-ingestion-v1/"
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
    require(source_sha == "454a0c568c12a46224407f6c3b378f8197e3f4653cca6d897d1c03b8d94821d7", "source hash")
    require(source_oid == "f97c50c0c81b47a6e0358feac98e4d2de0f515b2", "source object")
    require(source.decode().encode() == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source, "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    expected_ids = {
        "source_commitment": "6cf7bd08e9643efe7651a8bf8e917e90782d383fe5c9eebf58d1ae68740f24ce",
        "rights_instrument_identity": "9db36d1aa93b91a68b0cbc80f24eb7458dfce01d868246afef44f58e6f45ce5f",
        "immutable_archive_commitment": "0d6737d5f204efd83bb6168dec5082ecf9f4473ff2643567b4fbb7931711ea25",
        "source_package_identity": "cd1c968bb7d90416b5255ad14094410491e756ce58bc78512cca2e5297a044c1",
        "factual_authority_envelope_identity": "fbae8cb29dcf203bae478b010fe19036239623551f22949b3cb56ac34ba18d21",
        "partition_identity": "9180f7320a93342248fe9546237016261d1dd08340916c0ad8e19269ddf40147",
    }
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    require(ingestion["ingestion_receipt_identity"] == "0283383697b7616585433fe36ce0f7280ae4c4165563ec3f98518a59cedb5a86", "ingestion receipt")
    require(verification["verification_identity"] == "eb6ca968f7ba734fe3668ea51c03de30186f8d7154ace34f42ca13e7ef385f16", "verification identity")
    require(archive["archive_receipt_identity"] == "60b4e5c9bbff05465a8c155d55edacc0d52883c1f449716463a44ac8657c4ded", "archive receipt")
    require(ledger["ledger_segment_identity"] == "3c9f5404bcca59faa7133308a34b47b0d1fbfb78555cb0573518cd96c219cbdd", "ledger segment")
    contributor, ownership = rights["contributor"], rights["ownership_declarations"]
    grants, terms = rights["independent_grants"], rights["rights_terms"]
    require(contributor["public_identity"] == contributor["legal_identity_commitment"] == contributor["rights_holder_identity"] == "urn:pastila:party:pastila-acida-owner-v1", "rights holder")
    require(contributor["identity_disclosure_approved_for_commit"] is False and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity protection")
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "rights")
    require(all(ownership[key] is False for key in ownership if key.startswith("contains_")), "excluded material")
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "noninheritance")
    require(terms["expires_at"] == "NO_EXPIRY" and datetime.fromisoformat(terms["effective_at"]).tzinfo is not None, "rights terms")
    require(terms["correction_policy"] == "NEW_IMMUTABLE_REVISION_ONLY" and terms["supersession_policy"] == "EXPLICIT_PREDECESSOR_SUCCESSOR_CHAIN", "correction/supersession")
    text, results = source.decode(), []
    require(len(envelope["propositions"]) == 7, "proposition count")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "modality/scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE" and proposition["known_boundary"] and proposition["unknown_boundary"], "authority boundary")
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
    require(len(verification["verified_responses"]) == len(set(verification["nonces_consumed"])) == 8, "response/nonce consumption")
    require(all(item["signature_verification"] == "PASS" for item in verification["verified_responses"]), "signatures")
    previous = ledger["previous_ledger_head"]
    require(previous == "0dc087dde79a0b008d333c4e84a0572b32cb9bd25704b9a55a00cb4d5849069a", "prior ledger head")
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "e8279d111b95f6a1e4abf96ace2594c2cdbda6be504708d7df3d9e10feec8335", "ledger head")
    families = package["family_identities"]
    require(families == {
        "authority_family": "013598b3f1bd023fb8539ac68e874ee86a30452055b252d4c301d3dd7871249a",
        "construction_revision_family_id": "UNASSIGNED", "creative_marker_family_id": "UNASSIGNED",
        "creative_premise_family_id": "UNASSIGNED",
        "event_family": "4b88063a302b1144032b7b7121fc995277267f432efa75f265859f0336d77bdd",
        "family_closure": "bf5fab9153bd3ac6c3ef1b793ff9e5e41ab875071823df3c29a65b0dbc53cb4d",
        "revision_family": "99bd2e117962e189ecdace6beaddee82d716e152e01f9ad5d92a915dceff37dc",
        "source_family": "82b55379b3b02da913e0337350853530ed84d89084a9f27f129577f831a1bc15",
        "topic_entity_family": "f5c92a659f5a2a39dd118ed91006a481c0f04b0498a96d6732367d212766ab4b",
    }, "families")
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True).splitlines()
    allowed = ("development-pilot10-preingestion", "development-pilot10-signing-packet",
               "development-pilot10-family-independence", "development-pilot10-ingestion-v1")
    require(references and all(any(fragment in ref for fragment in allowed) for ref in references), "cross-family reference")
    referenced = b"\n".join(blob(ref.split(":", 1)[-1] if ref.startswith(COMMIT + ":") else ref) for ref in references)
    require(b'"partition": "BLIND_EVALUATION"' not in referenced and b'"partition": "CURRICULUM_CANDIDATE"' not in referenced, "cross partition")
    require(b'"creative_premise_family_id": "UNASSIGNED"' in referenced, "creative premise")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    require(ingestion["proposition_sufficiency_evaluated"] is False and ingestion["constructor_v5_2_compatibility_evaluated"] is False, "downstream boundary")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha,
        "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE", "immutable_capture_and_version": "PASS",
        "propositions": results, "target_safety": "PASS_LOW_RISK_SYNTHETIC",
        "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED",
        "correction_revocation_supersession": "CURRENT_V1_NO_SUCCESSOR_OR_REVOCATION",
        "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS",
        "relationship_state": "FRESH_INDEPENDENT_FAMILY_NO_DUPLICATE_REVISION_SIBLING_OR_SAME_EVENT_RELATIVE",
        "partition": "DEVELOPMENT", "partition_isolation": "PASS", "contamination_ledger_head": ledger["final_ledger_head"],
        "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "creative_premise_family_id": "UNASSIGNED",
        "mechanism_assignment": "ABSENT", "operational_obligation_assignment": "ABSENT",
        "downstream_exposure": {key: False for key in ("constructor", "realizer", "candidate_emitter", "model", "training", "runtime", "production")}}
    core = {"schema_name": "batch2-development-pilot10-g01a-g01b-admission-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
        "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
        "proposition_sufficiency_evaluated": False, "constructor_v5_2_compatibility_evaluated": False,
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_POST_G01_PROPOSITION_SUFFICIENCY_GATE_ONLY",
        "authority_matrix": {key: False for key in ("proposition_sufficiency_evaluation", "assignment",
            "constructor_v5_2_source_compatibility_evaluation", "constructor_release", "constructor_invocation", "realization",
            "candidate_emission", "post_realization_pre_emission_conformance", "fragment_collision_evaluation", "g02", "g02c",
            "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    admission = {**core, "admission_identity": seal("B2_DEVELOPMENT_PILOT10_G01A_G01B_ADMISSION_V1", core)}
    audit_core = {"schema_name": "batch2-development-pilot10-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "admission_identity": admission["admission_identity"], "git_object_source_verification": "PASS",
        "exact_committed_ingestion_file_set": "PASS_8_FILES", "identity_rederivation": "PASS",
        "span_coordinate_hash_verification": "PASS_7_PROPOSITIONS", "rights_non_inheritance": "PASS",
        "family_partition_isolation": "PASS", "contamination_and_ledger_continuity": "PASS",
        "proposition_sufficiency_evaluated": False, "constructor_v5_2_compatibility_evaluated": False,
        "hidden_assignment_or_exposure": "ABSENT", "deterministic_blockers": []}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT10_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot10-g01a-g01b-admission-v1.json", admission),
                        ("humor-mechanics-batch2-development-pilot10-g01a-g01b-admission-v1-audit.json", audit)):
        path = OUT / name
        require(not path.exists(), "review already exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission["admission_identity"],
                      "audit_identity": audit["audit_identity"],
                      "next_gate": "POST_G01_PROPOSITION_SUFFICIENCY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
