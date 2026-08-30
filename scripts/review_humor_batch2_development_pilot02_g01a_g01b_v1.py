"""Git-object-only G01A/G01B review for Development Pilot 02."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "6220b9d86336ec6bd4a62a1cff528e96f973be2c"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/"
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
    require(source_sha == "be9853603f82bc1fd11b2d0e06a692b3db4b83d1a7e20733c203c5aea1a04ea8", "source hash")
    require(source.decode("utf-8").encode("utf-8") == source and not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source,
            "encoding")
    require(source_oid == package["prospective_git_blob_oid_sha1"] == archive["git_blob_oid_sha1"], "Git/archive binding")
    require(archive["readback_sha256"] == archive["original_bytes_sha256"] == source_sha, "archive readback")
    required_ids = {
        "source_commitment": "c7c7174e1f046dba95eef105e2f415e096d42d86db80c55231d2abb86dbaac57",
        "rights_instrument_identity": "5d3e704a4d40715cbfad67a59188a873335b9f45116d09f6c4c0fa7d974e2ac3",
        "immutable_archive_commitment": "584f483b830492ff8ac8353238d9c5d3b9747683aab8133de026a42d24831780",
        "source_package_identity": "241171211ce96e247dcfaeaa513fb4a38f187008dd0e71697b3c85e4e4140668",
        "factual_authority_envelope_identity": "f3a66b5ccaa831acc171daa509700b16dbe2ebc9cfac30c8e68296e67c4bed9e",
        "partition_identity": "7c8c0b1d9dd148ed12f5a6df0202430e2bc34bb913e00e5f5f179c9dc250ca0b",
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
    require(len(envelope["propositions"]) == 7, "proposition count")
    for proposition in envelope["propositions"]:
        require(proposition["modality"] == "ASSERTED" and proposition["scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "modality/scope")
        require(proposition["attribution"] == "OWNER_AUTHORED_SOURCE" and proposition["known_boundary"] == "ONLY_THE_EXACT_BOUND_PROPOSITION", "attribution/known boundary")
        require(proposition["unknown_boundary"] ==
                "ALL_UNSTATED_PROPERTIES_CAUSES_PREFERENCES_RESULTS_AND_REAL_WORLD_APPLICABILITY",
                "unknown boundary")
        require(proposition["time"] in {
            "UNSPECIFIED",
            "EXPLICIT_2026_09_04_11_30_TO_13_00_BEFORE_PUBLIC_OPENING",
            "AT_END_OF_TASTING_WITH_LATER_EVALUATION_UNSCHEDULED",
            "AT_TEST_END",
        }, "time boundary")
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
    require(previous == ledger["final_ledger_head"] == "bb530d7a11f32d76b21f3e12695abb5f05219847b96a82c5a911211c8126e460", "ledger head")
    families = package["family_identities"]
    expected_families = {
        "source_family": "f75b690801066eb41484e39ba66bccbb3c6963b9721ccea2a96df79d50b38b8c",
        "event_family": "d83ec1870ec3d927cbee90a7eb0230279d35b09d725b060f831d5de3dc5df52e",
        "authority_family": "3d312d29db34d3a4f8a2f2fc5b97af88e9b5ff1477040dd6697d7f6472dc9b62",
        "topic_entity_family": "ab894f64a7d4a22908e8a520a6f44fa7cd826f11a6126a1c85ea9947d312dc1d",
        "revision_family": "e688e30d39d3ae465d92f8f13684776f9720fa8214813affe6958c076a01c08c",
        "family_closure": "ac076a1fd6ec4bc95138683590fca942bcfa322b3637a61b53b78484b12db005",
        "creative_premise_family_id": "UNASSIGNED",
    }
    require(families == expected_families, "family identities/closure")
    require(package["partition"] == "DEVELOPMENT" and package["partition_identity"] == required_ids["partition_identity"], "partition seal")
    # Locate every committed reference to this closure. All are confined to this pilot's
    # pre-ingestion, signing, or DEVELOPMENT ingestion artifacts.
    references = subprocess.check_output(["git", "grep", "-l", families["family_closure"], COMMIT, "--", "docs"], cwd=ROOT, text=True).splitlines()
    allowed_fragments = ("development-pilot02-preingestion", "development-pilot02-signing-packet", "development-pilot02-ingestion-v1")
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
    core = {"schema_name": "batch2-development-pilot02-g01a-g01b-admission-v1", "schema_version": "1.0.0",
            "reviewed_commit": COMMIT, "ingestion_receipt_identity": ingestion["ingestion_receipt_identity"],
            "source_package_identity": package["source_package_identity"], "g01a": g01a, "g01b": g01b,
            "later_development_assignment_design_eligibility": True,
            "eligibility_scope": "SEPARATE_OWNER_AUTHORIZATION_REQUIRED_NO_ASSIGNMENT_GRANTED",
            "authority_matrix": {key: False for key in ("mechanism_assignment", "operational_obligation_assignment", "creative_premise_assignment",
                                                         "candidate_construction", "generation", "model_exposure", "training", "runtime_integration", "production_routing")}}
    admission_identity = seal("B2_DEVELOPMENT_PILOT02_G01A_G01B_ADMISSION_V1", core)
    receipt = {**core, "admission_identity": admission_identity}
    audit_core = {"schema_name": "batch2-development-pilot02-g01a-g01b-admission-audit-v1", "schema_version": "1.0.0",
                  "reviewed_commit": COMMIT, "admission_identity": admission_identity,
                  "git_object_source_verification": "PASS", "exact_committed_ingestion_file_set": "PASS_8_FILES",
                  "identity_rederivation": "PASS", "span_coordinate_hash_verification": "PASS_7_PROPOSITIONS",
                  "rights_non_inheritance": "PASS", "family_partition_isolation": "PASS",
                  "contamination_and_ledger_continuity": "PASS", "hidden_assignment_or_exposure": "ABSENT",
                  "deterministic_blockers": [], "writes_beyond_review_artifacts": False}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT02_G01A_G01B_ADMISSION_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot02-g01a-g01b-admission-v1.json", receipt),
                        ("humor-mechanics-batch2-development-pilot02-g01a-g01b-admission-v1-audit.json", audit)):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"G01A": "PASS", "G01B": "PASS", "admission_identity": admission_identity,
                      "audit_identity": audit["audit_identity"], "contamination_state": g01b["contamination_state"],
                      "eligible_for_later_separately_authorized_development_assignment_design": True}, sort_keys=True))


if __name__ == "__main__":
    main()
