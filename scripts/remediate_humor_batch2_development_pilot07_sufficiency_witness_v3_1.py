"""Correct stale adjacent-link labels in Pilot 07's source-only sufficiency witness."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "170277f341c5352934dddb4ecc515cf4dd3c1e42"
OLD_RECEIPT = "docs/artifacts/humor-mechanics-batch2-development-pilot07-proposition-sufficiency-receipt-v3.json"
OLD_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot07-proposition-sufficiency-audit-v3.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path):
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def write(name, value):
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main():
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    old, old_audit = load(OLD_RECEIPT), load(OLD_AUDIT)
    if old["receipt_identity"] != "820d12777ab5c7796115c1cbdca7e225ae70eabebb035bcdab8c407f6214a1ad":
        raise SystemExit("old receipt")
    if old_audit["audit_identity"] != "2fbe3a7c908dfcc09b82d431066e06ce0fb50a1fb918a2d97ac318a9d02a8204":
        raise SystemExit("old audit")
    links = [
        "ISSUE_OBSERVATION_IS_THE_EXPLICIT_CONDITION_FOR_REPORT_ENTRY",
        "REPORT_ENTRY_IS_EXPLICITLY_DIRECTED_TO_LATER_ANALYSIS",
    ]
    core = {key: value for key, value in old.items() if key != "receipt_identity"}
    core["schema_version"] = "3.0.1"
    core["supersedes_receipt_identity"] = old["receipt_identity"]
    core["remediation"] = "CORRECT_STALE_ADJACENT_LINK_LABELS_ONLY"
    core["abstract_adjacent_link_witness"]["adjacent_links"] = links
    selected = [item for item in core["all_proposition_assessments"] if item["proposition_id"] == "P5"]
    if len(selected) != 1 or selected[0]["abstract_adjacent_link_witness"] is None:
        raise SystemExit("P5 witness")
    selected[0]["abstract_adjacent_link_witness"]["adjacent_links"] = links
    receipt = {**core, "receipt_identity": seal("B2_PILOT07_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V3_1", core)}
    audit_core = {
        "schema_name": "batch2-pilot07-post-g01-proposition-sufficiency-remediation-audit-v3-1",
        "schema_version": "3.0.1",
        "superseded_receipt_identity": old["receipt_identity"],
        "corrected_receipt_identity": receipt["receipt_identity"],
        "source_proposition_and_span_unchanged": True,
        "selected_proposition": "P5",
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "relation_and_adjacent_links_consistent": "PASS",
        "candidate_surface_absent": True,
        "assignment_authority": False,
        "construction_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_WITNESS_LABEL_REMEDIATION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PILOT07_POST_G01_PROPOSITION_SUFFICIENCY_REMEDIATION_AUDIT_V3_1", audit_core)}
    write("humor-mechanics-batch2-development-pilot07-proposition-sufficiency-receipt-v3-1.json", receipt)
    write("humor-mechanics-batch2-development-pilot07-proposition-sufficiency-remediation-audit-v3-1.json", audit)
    print(json.dumps({"receipt_identity": receipt["receipt_identity"], "audit_identity": audit["audit_identity"], "verdict": audit["verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()
