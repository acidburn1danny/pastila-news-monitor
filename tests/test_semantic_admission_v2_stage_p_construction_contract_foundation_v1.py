from __future__ import annotations

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2.stage_p_construction_role_contract_v1 import (
    ConstructionRecordV1,
    ConstructionResolution,
    ConstructionRole,
    ConstructionRoleLedgerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_creative_target_contract_v1 import (
    CreativeTargetAuditV1,
    CreativeTargetClass,
    CreativeTargetLedgerV1,
    CreativeTargetResolution,
    CreativeTargetSurvivalBasis,
)


def test_contract_schemas_are_closed_and_deterministic() -> None:
    for model in (CreativeTargetLedgerV1, ConstructionRoleLedgerV1):
        first = model.model_json_schema()
        assert first == model.model_json_schema()
        assert first["additionalProperties"] is False


def test_nonfactual_creative_target_tuple_is_coherent() -> None:
    audit = CreativeTargetAuditV1(
        audit_id="T1",
        creative_host_entry_id="P1",
        vehicle_span="metaforă",
        semantic_target="descriere editorială",
        target_class=CreativeTargetClass.NONFACTUAL_EDITORIAL_OR_CREATIVE,
        survival_basis=CreativeTargetSurvivalBasis.DOES_NOT_SURVIVE_AS_FACT,
        proposition_entry_id=None,
        resolution=CreativeTargetResolution.RETAINED_NONFACTUAL,
    )
    assert audit.proposition_entry_id is None


def test_creative_target_rejects_incoherent_resolution() -> None:
    with pytest.raises(ValidationError, match="NONFACTUAL_TARGET_INCOHERENT"):
        CreativeTargetAuditV1(
            audit_id="T1",
            creative_host_entry_id="P1",
            vehicle_span="metaforă",
            semantic_target="descriere editorială",
            target_class=CreativeTargetClass.NONFACTUAL_EDITORIAL_OR_CREATIVE,
            survival_basis=CreativeTargetSurvivalBasis.DOES_NOT_SURVIVE_AS_FACT,
            proposition_entry_id=None,
            resolution=CreativeTargetResolution.FAIL_CLOSED_UNRESOLVED,
        )


def test_literal_construction_record_is_coherent() -> None:
    record = ConstructionRecordV1(
        construction_id="C1",
        candidate_span="declarație",
        construction_role=ConstructionRole.LITERAL_ONLY,
        role_basis="Literal real-world statement",
        creative_host_entry_id=None,
        literal_or_return_entry_ids=("P1",),
        resolution=ConstructionResolution.LITERAL_PATH_RETAINED,
    )
    assert record.construction_role is ConstructionRole.LITERAL_ONLY


def test_material_construction_requires_creative_host() -> None:
    with pytest.raises(ValidationError, match="CONSTRUCTION_HOST_PRESENCE_MISMATCH"):
        ConstructionRecordV1(
            construction_id="C1",
            candidate_span="metaforă",
            construction_role=ConstructionRole.MATERIAL_CREATIVE_OR_EDITORIAL,
            role_basis="Material creative construction",
            creative_host_entry_id=None,
            literal_or_return_entry_ids=(),
            resolution=ConstructionResolution.CREATIVE_HOST_REQUIRED,
        )
