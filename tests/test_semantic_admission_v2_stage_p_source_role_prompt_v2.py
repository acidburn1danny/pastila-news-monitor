import hashlib
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_source_role_prompt_v2 import PROMPT_RELATIVE,StagePSourceRolePromptContractV2


ROOT=Path(__file__).resolve().parents[1]


def test_prompt_bytes_are_canonical_and_identity_excludes_one_storage_newline() -> None:
    data=(ROOT/PROMPT_RELATIVE).read_bytes();contract=StagePSourceRolePromptContractV2(ROOT)
    assert data.endswith(b"\n") and not data.endswith(b"\n\n")
    assert contract.prompt_identity=="sha256:"+hashlib.sha256(data[:-1]).hexdigest()
    assert contract.template==data[:-1].decode("utf-8") and contract.template==contract.template.strip()


def test_prompt_makes_candidate_sole_inventory_and_summary_support_only() -> None:
    prompt=StagePSourceRolePromptContractV2(ROOT).render(factual_summary="Autoritate exactă.",candidate="Comentariu exact.")
    assert "candidate commentary is the sole object" in prompt
    assert "factual summary is read-only support authority" in prompt
    assert "Never inventory the factual summary itself" in prompt
    assert "every candidate_span is a non-empty exact substring" in prompt
    assert "Autoritate exactă." in prompt and "Comentariu exact." in prompt
    assert "{factual_summary}" not in prompt and "{candidate}" not in prompt


def test_prompt_preserves_inventory_scope_and_indeterminate_boundary() -> None:
    text=StagePSourceRolePromptContractV2(ROOT).template
    for term in ("assertion, presupposition, entailment, or necessary implication","creative surface cannot hide",
                 "Maximum eight entries","INDETERMINATE","No surrounding bytes"):
        assert term in text
    assert "FSEM_" not in text

