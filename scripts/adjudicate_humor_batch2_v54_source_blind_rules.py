"""Create non-operational V5.4 adjudication artifacts from the author catalog.

The runner intentionally reads only the frozen design inputs and the source-blind
candidate catalog. It never reads holdouts, Pilot material, coverage, or mechanisms.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"
SOURCE = ARTIFACTS / "humor-mechanics-batch2-v5-4-source-blind-rule-author-candidates-v1.json"
INDEPENDENT_REVIEW = ARTIFACTS / "humor-mechanics-batch2-v5-4-independent-causal-adversarial-review-v1.json"
DISPOSITIONS = ARTIFACTS / "humor-mechanics-batch2-v5-4-rule-adjudication-dispositions-v1.json"
EVIDENCE = ARTIFACTS / "humor-mechanics-batch2-v5-4-rule-adjudication-batch-evidence-v1.json"
CATALOG = ARTIFACTS / "humor-mechanics-batch2-v5-4-proposed-admitted-rule-catalog-v1.json"

ADJUDICATOR = "RULE_ADJUDICATOR_V54_01"
AUTHOR = "RULE_AUTHOR_V54_01"
FROZEN_INPUTS = (
    "humor-mechanics-batch2-v5-4-general-semantic-ontology-design-v1.json",
    "humor-mechanics-batch2-v5-4-general-predicate-taxonomy-v1.json",
    "humor-mechanics-batch2-v5-4-trusted-semantic-rule-contract-v1.json",
    "humor-mechanics-batch2-v5-4-rule-admission-governance-v1.json",
    "humor-mechanics-batch2-v5-4-semantic-rule-admission-schema-v1.json",
    "humor-mechanics-batch2-v5-4-rule-composition-model-v1.json",
    "humor-mechanics-batch2-v5-4-predetermined-rule-population-curriculum-v1.json",
)


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seal(value: dict) -> dict:
    value["artifact_identity"] = canonical_hash(value)
    return value


def main() -> None:
    frozen = {name: json.loads((ARTIFACTS / name).read_text(encoding="utf-8")) for name in FROZEN_INPUTS}
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    independent_review = json.loads(INDEPENDENT_REVIEW.read_text(encoding="utf-8"))
    if source["author_identity"] != AUTHOR or source["curriculum_execution"]["total_candidates"] != 88:
        raise ValueError("unexpected author catalog identity or candidate count")
    if frozen[FROZEN_INPUTS[3]]["mandatory_separation"]["same_identity_forbidden"] is not True:
        raise ValueError("frozen separation invariant missing")
    review_identity = independent_review["evidence_identity"]
    review_payload = {key: value for key, value in independent_review.items() if key != "evidence_identity"}
    if canonical_hash(review_payload) != review_identity:
        raise ValueError("independent-review identity mismatch")
    if independent_review["candidate_catalog_identity"] != canonical_hash(source):
        raise ValueError("independent review is not bound to this candidate catalog")
    reviewers = independent_review["reviewers"]
    if not reviewers["identities_distinct"] or ADJUDICATOR in reviewers.values() or AUTHOR in reviewers.values():
        raise ValueError("reviewer independence invariant failed")
    review_by_candidate = {row["candidate_identity"]: row for row in independent_review["reviews"]}
    if len(review_by_candidate) != 88:
        raise ValueError("independent review is not complete")

    dispositions = []
    batch_rows: dict[int, list[dict]] = defaultdict(list)
    for item in source["candidates"]:
        semantic = item["semantic_content"]
        batch = int(semantic["curriculum_cell"][1:3])
        external = review_by_candidate[item["candidate_identity"]]
        if external["curriculum_cell"] != semantic["curriculum_cell"]:
            raise ValueError("independent review curriculum-cell mismatch")
        reasons = list(external["reason_codes"])
        disposition = (
            "PROPOSED_ADMITTED_NOT_ACTIVE"
            if external["causal_review"] == external["adversarial_review"] == "PASS"
            else "REJECT_NOT_ADMITTED_NOT_ACTIVE"
        )
        row = {
            "candidate_identity": item["candidate_identity"],
            "curriculum_cell": semantic["curriculum_cell"],
            "batch": batch,
            "predicate_family": semantic["predicate_family"],
            "author_identity": semantic["author_identity"],
            "adjudicator_identity": ADJUDICATOR,
            "independent_review_identity": review_identity,
            "causal_reviewer_identity": reviewers["causal"],
            "adversarial_reviewer_identity": reviewers["adversarial"],
            "disposition": disposition,
            "reason_codes": reasons,
            "proposed_rule_identity": None,
            "adjudication_receipt": None,
        }
        dispositions.append(row)
        batch_rows[batch].append(row)

    batch_evidence = []
    for batch in sorted(batch_rows):
        rows = batch_rows[batch]
        reason_counts = Counter(reason for row in rows for reason in row["reason_codes"])
        batch_evidence.append({
            "batch": batch,
            "candidate_count": len(rows),
            "proposed_admitted_count": 0,
            "rejected_count": len(rows),
            "semantic_actor_patient_affordance_review": "NO_ADDITIONAL_CATALOG_WIDE_CLASS_OR_ROLE_SHAPE_BLOCKER_FOUND",
            "causal_counterfactual_non_substitutability_review": "INDEPENDENT_REVIEW_COMPLETE_REJECT",
            "adversarial_overbreadth_review": "INDEPENDENT_REVIEW_COMPLETE_REJECT",
            "composition_review": "INDEPENDENT_REVIEW_COMPLETE_WITH_DECLARED_SIGNATURE_BLOCKERS",
            "reason_counts": dict(sorted(reason_counts.items())),
        })

    disposition_artifact = seal({
        "schema": "V5_4_RULE_ADJUDICATION_DISPOSITIONS_V1",
        "status": "FINAL_ADVISORY_DISPOSITIONS_NOT_ACTIVATION_AUTHORITY",
        "adjudicator_identity": ADJUDICATOR,
        "author_identity": AUTHOR,
        "identity_separation": True,
        "source_catalog_identity": canonical_hash(source),
        "independent_review_identity": review_identity,
        "frozen_input_identities": {name: canonical_hash(value) for name, value in frozen.items()},
        "forbidden_material_accessed": False,
        "total_candidates": len(dispositions),
        "proposed_admitted": 0,
        "rejected": len(dispositions),
        "operationally_activated": 0,
        "dispositions": dispositions,
    })
    evidence_artifact = seal({
        "schema": "V5_4_RULE_ADJUDICATION_BATCH_EVIDENCE_V1",
        "status": "FINAL_REVIEW_COMPLETE_ALL_CANDIDATES_REJECTED",
        "adjudicator_identity": ADJUDICATOR,
        "review_policy": {
            "semantic_adjudicator_may_impersonate_causal_reviewer": False,
            "semantic_adjudicator_may_impersonate_adversarial_reviewer": False,
            "absence_of_required_independent_evidence_is_rejection": True,
        },
        "independent_review_identity": review_identity,
        "causal_reviewer_identity": reviewers["causal"],
        "adversarial_reviewer_identity": reviewers["adversarial"],
        "batches": batch_evidence,
        "review_dimensions": [
            "SEMANTIC_DIRECTION", "ACTOR_PATIENT_TYPING", "ROLE_BINDING",
            "AFFORDANCE_AUTHORITY", "CAUSAL_NECESSITY", "COUNTERFACTUAL_DEPENDENCY",
            "CONSEQUENCE_NON_SUBSTITUTABILITY", "COMPOSITION_COMPATIBILITY",
            "ADVERSARIAL_OVERBREADTH",
        ],
    })
    catalog_artifact = seal({
        "schema": "V5_4_PROPOSED_ADMITTED_RULE_CATALOG_V1",
        "status": "IMMUTABLE_EMPTY_NO_RULES_ADMITTED_NO_RULES_ACTIVE",
        "adjudicator_identity": ADJUDICATOR,
        "source_disposition_identity": disposition_artifact["artifact_identity"],
        "canonical_identity_method": "SHA256_RFC8785_COMPATIBLE_CANONICAL_JSON",
        "proposed_admitted_rule_count": 0,
        "operational_rule_count": 0,
        "rules": [],
    })
    for path, value in ((DISPOSITIONS, disposition_artifact), (EVIDENCE, evidence_artifact), (CATALOG, catalog_artifact)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
