import json
from pathlib import Path

from pastila_scout.source_blind_rule_candidate_review_v1 import canonical_identity, review_catalog

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "docs/artifacts/humor-mechanics-batch2-v5-4-source-blind-rule-author-candidates-v1.json"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-v5-4-independent-causal-adversarial-review-v1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_review_is_complete_identity_bound_and_confers_no_authority():
    expected = review_catalog(load(CANDIDATES))
    evidence = load(EVIDENCE)
    assert evidence == expected
    assert evidence["evidence_identity"] == canonical_identity(evidence)
    assert evidence["candidate_catalog_identity"] == canonical_identity(load(CANDIDATES))
    assert evidence["reviewed_count"] == 88
    assert evidence["approved_for_adjudication_count"] == 0
    assert evidence["rejected_count"] == 88
    assert evidence["authority_limits"] == {
        "candidate_content_modified": False, "rules_admitted": 0, "rules_activated": 0,
        "rule_content_frozen": False, "coverage_computed": False,
    }


def test_every_candidate_has_two_independent_rejections_and_required_checks():
    evidence = load(EVIDENCE)
    reviews = evidence["reviews"]
    assert len({review["candidate_identity"] for review in reviews}) == 88
    assert evidence["reviewers"]["identities_distinct"] is True
    for review in reviews:
        assert review["causal_review"] == "REJECT"
        assert review["adversarial_review"] == "REJECT"
        assert "COUNTERFACTUAL_NOT_BOUND_TO_CONCRETE_PREDECESSOR_STATE" in review["reason_codes"]
        assert "NON_SUBSTITUTABILITY_ASSERTED_WITHOUT_CONTRAST_EVIDENCE" in review["reason_codes"]
        assert "TRANSITION_AND_RESULT_MAPPING_UNDER_SPECIFIED" in review["reason_codes"]


def test_non_anchor_terminal_privileged_and_abstract_findings_are_exact():
    evidence = load(EVIDENCE)
    counts = evidence["reason_counts"]
    assert counts["EXACT_PREDECESSOR_RESULT_SIGNATURE_NOT_DECLARED"] == 64
    assert counts["TERMINAL_PREDECESSOR_CONSUMPTION_NOT_EXACTLY_BOUND"] == 22
    assert counts["PRIVILEGED_AFFORDANCE_SAFETY_NOT_INDEPENDENTLY_ESTABLISHED"] == 16
    assert counts["CAUSAL_OR_LOGICAL_LICENSE_ASSUMED_IN_PRECONDITION"] == 11
