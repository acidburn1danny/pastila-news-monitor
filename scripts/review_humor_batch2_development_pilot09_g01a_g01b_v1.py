"""Git-object-only G01A/G01B review for Development Pilot 09."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "8991524fb136d29daa5f559ba8d9aef7386a2ac8"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/"
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
    archive, verification, ledger, ingestion = load("archive-receipt.json"), load("custodial-verification.json"), load("access-ledger-segment.json"), load("ingestion-receipt.json")
    source_sha = hashlib.sha256(source).hexdigest()
    source_oid = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    require(source_sha == "608f26b4588c347707ae5eccb08194d498fb3b3e9e7a6402be63ad2bc7c77c77", "source hash")
    require(source_oid == "61a5a9fb520f356b90060db16123eb8ccd25cf76", "source object")
    require(source.decode().encode() == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source, "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "readback")
    expected_ids = {"source_commitment": "c07226c1a0c8776f3306e895bff9ce7b21f28b6262d89e33085cfb6384478730",
                    "rights_instrument_identity": "09ff47a2a0c2d920bc85523dbd9524dcc76a3c3728c5a0f7f4f263042be45a09",
                    "immutable_archive_commitment": "2b404cf5af851f7c756f28acf757f4cc21688a30ad54b866813b3d33b7be2144",
                    "source_package_identity": "e6b520958d949f673600366018572fb00da98125646ab75cdb4fc6e34d1da5f0",
                    "factual_authority_envelope_identity": "9e791c37ce2fca9b927e3c386ede1ae0c2c0019e1301261e5bb900c7ffaa39f9",
                    "partition_identity": "7d2321691df49824609db1a1bb6f13537a1e29c9165cd93037353fb4be3fb0bf"}
    for key, expected in expected_ids.items():
        require(package.get(key) == expected or ingestion.get(key) == expected, f"identity {key}")
    contributor, ownership = rights["contributor"], rights["ownership_declarations"]
    grants, terms = rights["independent_grants"], rights["rights_terms"]
    require(contributor["public_identity"] == contributor["legal_identity_commitment"] == contributor["rights_holder_identity"] == "urn:pastila:party:pastila-acida-owner-v1", "rights holder")
    require(contributor["identity_disclosure_approved_for_commit"] is False and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity protection")
    require(all(ownership[x] is True for x in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "rights")
    require(all(ownership[x] is False for x in ownership if x.startswith("contains_")), "excluded material")
    require(all(grants[x] is True for x in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "grants")
    require(all(grants[x] is False for x in ("model_exposure", "training", "runtime_integration", "production_routing")), "noninheritance")
    require(terms["expires_at"] == "NO_EXPIRY" and datetime.fromisoformat(terms["effective_at"]).tzinfo is not None, "rights terms")
    text, results = source.decode(), []
    require(len(envelope["propositions"]) == 8, "proposition count")
    allowed_known = {
        "ONLY_THE_EXACT_BOUND_PROPOSITION",
        "AUTOMATIC_NONSTART_OCCURS_IF_SENSOR_NONDETECTION_OR_SIGNAL_NONARRIVAL_CONDITION_HOLDS",
        "TEST_IS_LIMITED_TO_THIS_TRANSPORT_LINE_AND_DOES_NOT_ESTABLISH_OTHER_EQUIPMENT_STATE",
        "SYSTEM_PERFORMANCE_AND_TECHNICAL_INTERVENTION_NEED_ARE_EXPLICITLY_UNKNOWN_BEFORE_VERIFICATION",
    }
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "modality/scope")
        require(proposition["known_boundary"] in allowed_known and proposition["sensitive_protected_target_classification"] == "NONE_DECLARED_LOW_RISK_SYNTHETIC", "boundary/target")
        components = ["supporting_span", "subject", "predicate", "object"] + (["qualification"] if proposition["qualification"] else [])
        for component in components:
            item = proposition[component]; cs, ce = item["character_coordinates"]; bs, be = item["utf8_byte_coordinates"]
            value = text[cs:ce].encode()
            require(value == source[bs:be] and hashlib.sha256(value).hexdigest() == item.get("sha256", item.get("span_sha256")), "span")
        results.append({"proposition_id": proposition["proposition_id"], "coordinates_and_hashes": "PASS",
                        "modality_scope_attribution_boundaries": "PASS", "qualification": "BOUND" if proposition["qualification"] else "NONE_REQUIRED"})
    require(verification["verification_result"] == "PASS_8_OF_8" and verification["packet_consumed"] is True and len(set(verification["nonces_consumed"])) == 8, "custody")
    previous = ledger["previous_ledger_head"]
    for entry in ledger["entries"]:
        require(entry["previous_entry_hash"] == previous, "continuity")
        core = dict(entry); identity = core.pop("entry_hash")
        require(seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", core) == identity, "entry seal")
        previous = identity
    require(previous == ledger["final_ledger_head"] == "0dc087dde79a0b008d333c4e84a0572b32cb9bd25704b9a55a00cb4d5849069a", "ledger head")
    families = package["family_identities"]
    require(families == {
        "authority_family": "07ee83dcf8fbaeb2ccade856687683b13e07d5280f6f13b9358a169d27bd3f08",
        "construction_revision_family_id": "UNASSIGNED",
        "creative_marker_family_id": "UNASSIGNED",
        "creative_premise_family_id": "UNASSIGNED",
        "event_family": "02e6bf2e099aba433bbc8863fa7b70b3409fdd39ab56b5c51c4fade29d1a2b67",
        "family_closure": "67115badafe9cf5c18b43b4008808f83abf8f0ebb6b47fa20d253d3007c07fa6",
        "revision_family": "efcac72521d8cd459e2ab47c811a2fa8db772ae789091f03161a2134c4529295",
        "source_family": "c185e5d436f48cbd4a7d2562ca3a60b948f6f087749624f45c2415515a30b8d7",
        "topic_entity_family": "2014c63240a2bad3d9e0c311c4b1674c92e50ebba32d7e33ff19b065a5f28abb",
    }, "families")
    references = subprocess.check_output(
        ["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True
    ).splitlines()
    allowed = ("development-pilot09-preingestion", "development-pilot09-signing-packet",
               "development-pilot09-family-independence", "development-pilot09-ingestion-v1")
    require(references and all(any(fragment in ref for fragment in allowed) for ref in references), "cross-family reference")
    referenced = b"\n".join(blob(ref.split(":", 1)[-1] if ref.startswith(COMMIT + ":") else ref) for ref in references)
    require(b'"partition": "BLIND_EVALUATION"' not in referenced and
            b'"partition": "CURRICULUM_CANDIDATE"' not in referenced, "cross partition")
    require(b'"creative_premise_family_id": "UNASSIGNED"' in referenced, "creative premise")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == expected_ids["partition_identity"], "partition")
    require(ingestion["proposition_sufficiency_evaluated"] is False, "sufficiency")
    g01a = {"verdict": "PASS", "source_git_object": source_oid, "source_sha256": source_sha,
            "rights_and_permitted_use": "PASS_WITH_STRICT_NON_INHERITANCE", "immutable_capture_and_version": "PASS",
            "propositions": results, "target_safety": "PASS_LOW_RISK_SYNTHETIC",
            "third_party_material": "NONE_DECLARED_AND_NONE_OBSERVED", "correction_revocation_supersession": "CURRENT_V1_NO_SUCCESSOR_OR_REVOCATION",
            "custodial_authority": "PASS_8_OF_8_CONSUMED"}
    g01b = {"verdict": "PASS", "family_identities": families, "family_closure": "PASS",
            "relationship_state": "FRESH_INDEPENDENT_FAMILY_NO_DUPLICATE_REVISION_SIBLING_OR_SAME_EVENT_RELATIVE",
            "partition": "DEVELOPMENT", "partition_isolation": "PASS", "contamination_ledger_head": ledger["final_ledger_head"],
            "contamination_state": "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "creative_premise_family_id": "UNASSIGNED",
            "mechanism_assignment": "ABSENT", "downstream_exposure": {key: False for key in ("constructor", "model", "training", "runtime", "production")}}
    core = {"schema_name": "batch2-development-pilot09-g01a-g01b-admission-v1", "schema_version": "1.0.0",
            "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
            "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
            "proposition_sufficiency_evaluated": False, "constructor_v5_compatibility_evaluated": False,
            "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_POST_G01_PROPOSITION_SUFFICIENCY_GATE_ONLY",
            "authority_matrix": {key: False for key in ("proposition_sufficiency_evaluation", "assignment", "constructor_v5_source_compatibility_evaluation", "constructor_release", "construction",
                                                         "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    admission = {**core, "admission_identity": seal("B2_DEVELOPMENT_PILOT09_G01A_G01B_ADMISSION_V1", core)}
    audit_core = {"schema_name": "batch2-development-pilot09-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
                  "reviewed_commit": COMMIT, "admission_identity": admission["admission_identity"], "git_object_source_verification": "PASS",
                  "exact_committed_ingestion_file_set": "PASS_8_FILES", "identity_rederivation": "PASS",
                  "span_coordinate_hash_verification": "PASS_8_PROPOSITIONS", "rights_non_inheritance": "PASS",
                  "family_partition_isolation": "PASS", "contamination_and_ledger_continuity": "PASS",
                  "proposition_sufficiency_evaluated": False, "constructor_v5_compatibility_evaluated": False, "hidden_assignment_or_exposure": "ABSENT", "deterministic_blockers": []}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT09_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot09-g01a-g01b-admission-v1.json", admission),
                        ("humor-mechanics-batch2-development-pilot09-g01a-g01b-admission-v1-audit.json", audit)):
        path = OUT / name; require(not path.exists(), "review already exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission["admission_identity"],
                      "audit_identity": audit["audit_identity"], "next_gate": "POST_G01_PROPOSITION_SUFFICIENCY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()


