"""Canonically repair the duplicated Pilot 05 prior-family suffix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
TEMPLATE = ART / "humor-mechanics-batch2-development-pilot05-owner-declaration-template-v1.json"
REQUEST = ART / "humor-mechanics-batch2-development-pilot05-owner-input-request-v1.json"
AUDIT = ART / "humor-mechanics-batch2-development-pilot05-owner-input-request-audit-v1.json"
OWNER_DECLARATION = ROOT / "owner-declaration-pilot05-v1.json"
OLD_TEMPLATE_ID = "0ec4d2d2b3b344d7c984d912483bf5a49374ed5d25789df0547945a0d6d3d426"
OLD_REQUEST_ID = "ddf080ac6938162c067b475ad371b98e909b30cb77b4755d99828905cdab2ca5"
OLD_AUDIT_ID = "4850ad69ae0a2f40a57649bbd56251a880d3a98347de55c76c5a50118a8b6396"
OLD_DECLARATION_SHA = "acff7c3ffd4124c6c0d8921e3887811259f4192ef35e7fc40d51e8bcad7fe71c"
OLD_REUSE = "source_does_not_reuse_pilots_01_02_03_04_04_wording_entities_events_or_creative_structures"
NEW_REUSE = "source_does_not_reuse_pilots_01_02_03_04_wording_entities_events_or_creative_structures"
OLD_RELATION = "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04_04"
NEW_RELATION = "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def replace_keys(value: dict[str, Any]) -> None:
    declarations = value["source_status_declarations"]
    if OLD_REUSE not in declarations or OLD_RELATION not in declarations:
        raise SystemExit("expected duplicated Pilot 05 keys are absent")
    if NEW_REUSE in declarations or NEW_RELATION in declarations:
        raise SystemExit("corrected Pilot 05 keys already exist")
    declarations[NEW_REUSE] = declarations.pop(OLD_REUSE)
    declarations[NEW_RELATION] = declarations.pop(OLD_RELATION)


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    template = load(TEMPLATE)
    request = load(REQUEST)
    audit = load(AUDIT)
    raw_declaration = OWNER_DECLARATION.read_bytes()
    if hashlib.sha256(raw_declaration).hexdigest() != OLD_DECLARATION_SHA:
        raise SystemExit("owner declaration SHA-256 mismatch")
    if template.pop("template_identity") != OLD_TEMPLATE_ID:
        raise SystemExit("template predecessor mismatch")
    if request.pop("owner_input_request_identity") != OLD_REQUEST_ID:
        raise SystemExit("request predecessor mismatch")
    if audit.pop("audit_identity") != OLD_AUDIT_ID:
        raise SystemExit("audit predecessor mismatch")

    declaration = json.loads(raw_declaration)
    replace_keys(template)
    replace_keys(declaration)
    template_id = seal("B2_DEVELOPMENT_PILOT05_OWNER_DECLARATION_TEMPLATE_V1", template)
    template["template_identity"] = template_id

    request["declaration_template_identity"] = template_id
    request["template_repair"] = {
        "predecessor_template_identity": OLD_TEMPLATE_ID,
        "repair": "REMOVE_DUPLICATED_04_SUFFIX_FROM_TWO_PRIOR_FAMILY_DECLARATION_KEYS",
        "owner_values_preserved": True,
        "owner_source_bytes_modified": False,
    }
    request_id = seal("B2_DEVELOPMENT_PILOT05_OWNER_INPUT_REQUEST_V1", request)
    request["owner_input_request_identity"] = request_id

    audit["owner_input_request_identity"] = request_id
    audit["template_schema_repair"] = "PASS_CANONICAL_KEY_RENAME_VALUES_PRESERVED"
    audit["predecessor_audit_identity"] = OLD_AUDIT_ID
    audit_id = seal("B2_DEVELOPMENT_PILOT05_OWNER_INPUT_REQUEST_AUDIT_V1", audit)
    audit["audit_identity"] = audit_id

    canonical_declaration = canonical(declaration) + b"\n"
    canonical_declaration_sha = hashlib.sha256(canonical_declaration).hexdigest()
    declaration_identity = seal("B2_DEVELOPMENT_PILOT05_CANONICAL_OWNER_DECLARATION_V1", declaration)
    canonical_path = ART / "humor-mechanics-batch2-development-pilot05-owner-declaration-canonical-v1.json"
    canonical_path.write_bytes(canonical_declaration)

    repair_core = {
        "schema_name": "batch2-development-pilot05-template-schema-repair-v1",
        "schema_version": "1.0.0",
        "defect": "DUPLICATED_04_SUFFIX_IN_TWO_SOURCE_STATUS_DECLARATION_KEYS",
        "predecessor": {"template_identity": OLD_TEMPLATE_ID, "request_identity": OLD_REQUEST_ID, "audit_identity": OLD_AUDIT_ID, "owner_declaration_sha256": OLD_DECLARATION_SHA},
        "successor": {"template_identity": template_id, "request_identity": request_id, "audit_identity": audit_id, "canonical_declaration_sha256": canonical_declaration_sha, "canonical_declaration_identity": declaration_identity},
        "source_sha256_preserved": "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc",
        "owner_values_preserved": True,
        "rights_or_authority_changed": False,
        "operational_authority_granted": False,
        "repair_verdict": "PASS_CANONICAL_DIRECTLY_SCOPED_REPAIR",
    }
    repair = {**repair_core, "repair_identity": seal("B2_DEVELOPMENT_PILOT05_TEMPLATE_SCHEMA_REPAIR_V1", repair_core)}
    write(TEMPLATE, template)
    write(REQUEST, request)
    write(AUDIT, audit)
    write(ART / "humor-mechanics-batch2-development-pilot05-template-schema-repair-v1.json", repair)
    print(json.dumps(repair["successor"], sort_keys=True))


if __name__ == "__main__":
    main()
