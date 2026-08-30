"""Verify the content-free internally owned acquisition-channel qualification."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name: str) -> tuple[dict, str]:
    raw = (ART / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: dict, field: str) -> str:
    body = dict(value)
    body.pop(field)
    return hashlib.sha256(canonical({"namespace": namespace, "value": body})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    declaration, declaration_sha = load("humor-mechanics-batch2-internally-owned-rights-declaration-template-v1.json")
    archive, archive_sha = load("humor-mechanics-batch2-immutable-archive-qualification-v1.json")
    roles, roles_sha = load("humor-mechanics-batch2-custodial-role-matrix-v1.json")
    fixtures, fixtures_sha = load("humor-mechanics-batch2-internally-owned-metadata-conformance-v1.json")
    registry, registry_sha = load("humor-mechanics-batch2-approved-channel-registry-v1.json")
    audit, _ = load("humor-mechanics-batch2-internally-owned-channel-qualification-v1-audit.json")
    false_matrix = {key: False for key in [
        "source_acquisition", "content_ingestion", "mechanism_assignment", "candidate_construction",
        "surface_generation", "model_exposure", "training", "runtime_integration", "production_routing"]}
    require(declaration["template_identity"] == seal("B2_INTERNALLY_OWNED_DECLARATION_TEMPLATE_V1",
                                                     declaration, "template_identity"), "declaration seal")
    require(archive["archive_spec_identity"] == seal("B2_IMMUTABLE_ARCHIVE_QUALIFICATION_V1",
                                                    archive, "archive_spec_identity"), "archive seal")
    require(roles["role_matrix_identity"] == seal("B2_CUSTODIAL_ROLE_MATRIX_V1",
                                                 roles, "role_matrix_identity"), "role seal")
    require(fixtures["fixture_suite_identity"] == seal("B2_INTERNALLY_OWNED_METADATA_FIXTURES_V1",
                                                       fixtures, "fixture_suite_identity"), "fixture seal")
    require(registry["registry_identity"] == seal("B2_APPROVED_CHANNEL_REGISTRY_V1",
                                                  registry, "registry_identity"), "registry seal")
    qualified = registry["channels"]["INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE"]
    require(qualified["qualification"] == "QUALIFIED_PROTOCOL_DESIGN_ONLY", "internal lane not qualified")
    require(not qualified["source_acquisition_enabled"] and not qualified["content_ingestion_enabled"],
            "qualified lane accidentally operational")
    require(qualified["qualification_artifacts"] == {
        "declaration_template_sha256": declaration_sha, "archive_spec_sha256": archive_sha,
        "role_matrix_sha256": roles_sha, "metadata_fixture_sha256": fixtures_sha}, "artifact binding mismatch")
    for name in ("AFFIRMATIVELY_LICENSED_EXTERNAL_MATERIAL",
                 "COMPATIBLE_PUBLIC_DOMAIN_OR_OPEN_LICENSE_MATERIAL"):
        require(registry["channels"][name]["qualification"] == "NOT_YET_QUALIFIED", f"{name} promoted")
        require(not registry["channels"][name]["source_acquisition_enabled"], f"{name} enabled")
    require(registry["current_authority"] == audit["authority_matrix"] == declaration["current_grant"] ==
            false_matrix, "authority widened")
    require(declaration["not_a_grant_until_completed_and_sealed"], "template acts as grant")
    require(set(item["value"] for item in declaration["independent_grants"].values()) == {"UNSELECTED"},
            "template contains grant selection")
    probe = archive["qualification_readback"]
    committed = subprocess.check_output(["git", "show", f"{probe['commit']}:{probe['path']}"], cwd=ROOT)
    require(hashlib.sha256(committed).hexdigest() == probe["expected_sha256"],
            "qualified Git archive readback mismatch")
    require(archive["production_archive_selected"] and
            archive["qualified_backend"] == "REPOSITORY_GIT_OBJECT_DATABASE" and
            not archive["archive_write_authorized"] and not archive["content_ingestion_authorized"],
            "archive qualification or write boundary invalid")
    require(roles["appointments"] == "UNASSIGNED_REQUIRES_SEPARATE_OWNER_APPOINTMENT" and
            not roles["credentials_provisioned"] and not roles["operational_access_enabled"],
            "custodial access activated")
    require(not fixtures["contains_source_content"] and
            fixtures["actions_performed"] == {"sources_acquired": 0, "content_ingested": 0,
                                               "content_bytes_created": 0, "blind_surfaces_read": 0,
                                               "model_calls": 0}, "content-free boundary violated")
    require(all(value == "REJECTED" for key, value in fixtures["cases"].items()
                if key != "VALID_COMPLETE_TEMPLATE_SHAPE"), "negative fixture fail-open")
    require(audit["bindings"]["registry_sha256"] == registry_sha, "audit registry hash")
    require(audit["verdict"] == "PASS_CONTENT_FREE_CHANNEL_QUALIFICATION" and
            not audit["deterministic_defects_remaining"] and
            set(audit["checks"].values()) == {"PASS"}, "audit not clean")
    require(audit["next_phase"] == "SEPARATE_CONTENT_FREE_CUSTODIAL_APPOINTMENT_AND_SIGNING_READINESS",
            "next phase improperly includes acquisition")
    print(json.dumps({"verdict": audit["verdict"], "registry_identity": registry["registry_identity"],
                      "internally_owned_lane": "QUALIFIED_PROTOCOL_DESIGN_ONLY",
                      "source_acquisition_enabled": False, "content_ingestion_enabled": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()
