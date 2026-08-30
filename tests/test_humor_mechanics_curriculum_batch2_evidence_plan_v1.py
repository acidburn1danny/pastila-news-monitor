from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = ROOT / "docs/artifacts/humor-mechanics-curriculum-v1.manifest.json"
PLAN_PATH = (
    ROOT / "docs/artifacts/humor-mechanics-curriculum-v1-batch2-evidence-plan-v1.json"
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_batch2_plan_is_exactly_bound_to_the_frozen_taxonomy() -> None:
    curriculum = _load(CURRICULUM_PATH)
    plan = _load(PLAN_PATH)
    expected = [item for item in curriculum["mechanisms"] if item["batch"] == 2]

    assert plan["curriculum_identity"] == curriculum["canonical_identity"]
    assert plan["mechanism_ordinals"] == list(range(11, 21))
    assert [item["mechanism_id"] for item in plan["mechanisms"]] == [
        item["id"] for item in expected
    ]
    assert [item["ordinal"] for item in plan["mechanisms"]] == list(range(11, 21))
    expected_by_id = {item["id"]: item for item in expected}
    for item in plan["mechanisms"]:
        assert item["positive_obligations"]
        assert item["negative_focus"]
        taxonomy_item = expected_by_id[item["mechanism_id"]]
        permitted_contrasts = set(taxonomy_item["distinguish_from"])
        if taxonomy_item["parent_id"] is not None:
            permitted_contrasts.add(taxonomy_item["parent_id"])
        assert set(item["contrast_with"]) <= permitted_contrasts

    claimed_identity = plan.pop("canonical_identity")
    canonical = json.dumps(
        plan,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == claimed_identity


def test_batch2_plan_grants_no_construction_or_execution_authority() -> None:
    authority = _load(PLAN_PATH)["authority"]

    assert authority
    assert all(value is False for value in authority.values())


def test_batch2_plan_requires_all_review_boundaries_before_owner_freeze() -> None:
    plan = _load(PLAN_PATH)

    assert len(plan["owner_review_gates"]) == 5
    assert plan["romanian_naturalness_review"]["review_required"] is True
    assert plan["contrastive_negative_contract"]["construction_status"] == (
        "NOT_AUTHORIZED_BY_THIS_PLAN"
    )
    assert plan["minimum_future_evidence_shape_per_mechanism"]["no_quota_fill"] is True
    assert plan["next_separate_decision"] == "AUTHORIZE_BOUNDED_SOURCE_DISCOVERY_ONLY"
