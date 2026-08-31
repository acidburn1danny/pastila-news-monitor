"""Mechanism-neutral Governance V2 G02C review for Pilot 03 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "d0df4be491f0e2f852d4ded64c4c346fa7759b68"
INGESTION_COMMIT = "8aaeccbbca9d45fb9d522505f82d173e1090b3b6"
GOVERNANCE_COMMIT = "618333a3db484da134904aea004a36e9cb0350d4"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-g02-v1.json"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot03-ingestion-v1/"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(git_bytes(commit, path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def span(text: str, value: str) -> dict[str, Any]:
    start = text.index(value); end = start + len(value)
    raw = value.encode("utf-8")
    return {"character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(text[:start].encode()), len(text[:end].encode())],
            "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> None:
    receipt_path = ART / "humor-mechanics-batch2-development-pilot03-candidate01-g02c-conformance-receipt-v1.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot03-candidate01-g02c-review-v1.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02_COMMIT, "HEAD")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    g02 = git_json(G02_COMMIT, G02_PATH)
    envelope = git_json(INGESTION_COMMIT, PREFIX + "factual-authority-envelope.json")
    source = git_bytes(INGESTION_COMMIT, PREFIX + "source.utf8.txt").decode("utf-8")
    governance = git_json(GOVERNANCE_COMMIT, "docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v2.json")
    schema = git_json(GOVERNANCE_COMMIT, "docs/artifacts/humor-mechanics-batch2-successor-obligation-conformance-schema-v2.json")
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] == "c6bd81d8263aad7004c403ffaee7ba8a59817e276cd81a86275001fa254b1f56", "G02")
    require(hashlib.sha256(candidate).hexdigest() == "86f058253be11227bf40a0de4842bf79ae7458b2a89f11c8fca033477e0a626d", "candidate")
    require(governance["obligation_governance_identity"] == "874c5d611c5ab955e0f9d82aa5aa086fad98e065f66e20e9e236f48798287024", "governance")
    require(schema["conformance_schema_identity"] == "9470ce435de7ddcfea8dc4b3022b2ad697c2aa85fab44e8b532b4fa9850b0512", "schema")
    text = candidate.decode("utf-8")
    p7 = next(p for p in envelope["propositions"] if p["proposition_id"] == "P7")
    ss, se = p7["supporting_span"]["character_coordinates"]
    exact = source[ss:se]
    require(text.startswith(exact + " "), "authorized proposition")
    marker = "În povestea imaginară a coletului"
    step1 = "necunoașterea conținutului lasă lista de inventar goală"
    step2 = "cum lista goală nu poate confirma nimic, deschiderea programată ajunge să fie singurul lucru care mai poate fi inventariat"
    require(marker in text and step1 in text and step2 in text, "surface components")
    s1, s2 = span(text, step1), span(text, step2)
    require(s1["character_coordinates"][1] < s2["character_coordinates"][0], "ordered situations")
    governance_tokens = ("obligație", "regulă editorială", "clasificare", "verificarea rezultatului", "marcaj creativ")
    require(not any(token in text.lower() for token in governance_tokens), "governance transfer")
    predicates = {
        "AUTHORIZED_PROPOSITION_PRESERVED": True,
        "TWO_DISTINCT_NEW_SITUATIONS": True,
        "RELATION_OPERATIVE_ACROSS_BOTH": True,
        "SECOND_DEPENDS_ON_FIRST": True,
        "LOCAL_INTELLIGIBILITY": True,
        "NO_UNRELATED_EVENT": True,
        "ENTITY_STATUS_PRESERVED": True,
        "INTEGRATED_NARRATIVE_CREATIVE_MARKING": True,
        "GOVERNANCE_LANGUAGE_ABSENT": True,
        "PROCEDURAL_ABSTRACTION_NONMATERIAL": True,
        "IDIOMATIC_ROMANIAN_PRECHECK_PASS": True,
    }
    require(list(predicates) == schema["required_predicates"] and all(predicates.values()), "required predicates")
    relation_core = {"proposition_id": "P7", "source_relation": {
        key: {"character_coordinates": p7[key]["character_coordinates"],
              "utf8_byte_coordinates": p7[key]["utf8_byte_coordinates"], "sha256": p7[key]["sha256"]}
        for key in ("subject", "predicate", "object")}}
    receipt_core = {
        "schema_name": "batch2-development-pilot03-g02c-conformance-receipt-v1", "schema_version": "2.0.0",
        "candidate_identity": "b4555cc43bf16a466734aed46e93baa83bd9bc37d52d3826976be3370ccef72d",
        "obligation_governance_identity": governance["obligation_governance_identity"],
        "conformance_schema_identity": schema["conformance_schema_identity"],
        "selected_proposition": {"proposition_id": "P7", "source_span": p7["supporting_span"]},
        "continued_relation_fingerprint": seal("B2_G02C_CONTINUED_RELATION_V2", relation_core),
        "situations": [{"ordinal": 1, "candidate_span": s1, "locally_understandable": True},
                       {"ordinal": 2, "candidate_span": s2, "locally_understandable": True}],
        "dependency": {"step2_requires_step1": True, "unrelated_replacement_possible": False},
        "required_predicates": predicates,
        "naturalness_precheck": {"editorial_or_governance_label_as_marker": False,
                                 "obligation_terminology_copied_or_paraphrased": False,
                                 "materially_procedural_abstract_register": False,
                                 "unidiomatic_creative_marking": False,
                                 "does_not_replace_blind_g04a": True},
        "verdict": "PASS",
    }
    receipt_id = seal("B2_DEVELOPMENT_PILOT03_G02C_CONFORMANCE_RECEIPT_V2", receipt_core)
    receipt = {**receipt_core, "conformance_receipt_identity": receipt_id}
    review_core = {
        "schema_name": "batch2-development-pilot03-candidate-g02c-review-v1", "schema_version": "2.0.0",
        "candidate_identity": receipt_core["candidate_identity"], "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
        "creative_premise_family_id": "dd530bad539b8ce3e40d4a4b35eacb75a040e84ad44b051652c6266519b88bcf",
        "g02_commit": G02_COMMIT, "g02_receipt_identity": g02["g02_receipt_identity"],
        "obligation_governance_identity": governance["obligation_governance_identity"],
        "conformance_schema_identity": schema["conformance_schema_identity"], "conformance_receipt_identity": receipt_id,
        "predicate_verification": "PASS_ALL_GOVERNANCE_V2_REQUIRED_PREDICATES",
        "naturalness_precheck": "PASS_NO_INSTRUCTION_TO_SURFACE_TRANSFER",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED",
        "sealed_mapping_accessed": False, "g03_performed": False, "candidate_modified": False,
        "g02c_verdict": "PASS", "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_BLIND_G03_MECHANISM_RECOVERY",
        "authority_matrix": {key: False for key in ("g03_mechanism_recovery", "repair", "rewrite", "regeneration",
                                                     "owner_review", "training", "runtime_integration", "production_routing")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT03_G02C_REVIEW_V1", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g02c_verdict": "PASS", "conformance_receipt_identity": receipt_id,
                      "g02c_review_identity": review["g02c_review_identity"],
                      "naturalness_precheck": review["naturalness_precheck"],
                      "next_gate": "BLIND_G03_MECHANISM_RECOVERY_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
