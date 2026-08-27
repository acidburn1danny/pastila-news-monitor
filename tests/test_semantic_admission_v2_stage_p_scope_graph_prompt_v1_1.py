from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_prompt_v1_1 import (
    PROMPT_RELATIVE,
    StagePScopeGraphPromptContractV1_1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_prompt_v1_1.py"


def test_prompt_bytes_identity_and_unpadded_render_are_exact():
    data = (ROOT / PROMPT_RELATIVE).read_bytes()
    contract = StagePScopeGraphPromptContractV1_1(ROOT)
    assert data.endswith(b"\n") and not data.endswith(b"\n\n")
    assert contract.prompt_identity == "sha256:" + hashlib.sha256(data[:-1]).hexdigest()
    rendered = contract.render(factual_summary="Autoritate exactă.", candidate="Comentariu exact.")
    assert rendered == rendered.strip() and not rendered.endswith("\n")
    assert rendered.count("Autoritate exactă.") == rendered.count("Comentariu exact.") == 1


def test_prompt_requires_candidate_origin_and_creative_host_first_reasoning():
    text = StagePScopeGraphPromptContractV1_1(ROOT).template
    required = ("candidate commentary is the sole inventory object", "never supply, complete, or substitute",
                "First identify the smallest integrated creative hosts", "before assigning any real-world return",
                "Contextual or narrative dependence", "is not factual return",
                "neutralize the creative vehicle", "candidate communicative force still carries")
    assert all(fragment in text for fragment in required)


def test_prompt_requires_governed_support_without_banning_partial_support():
    text = StagePScopeGraphPromptContractV1_1(ROOT).template
    assert "GOVERNED_EVENT always requires non-null exact authority_support" in text
    assert "Unsupported factual return remains a REAL_WORLD_COMMITMENT with NEW_UNSUPPORTED_EVENT" in text
    assert "no requirement that every candidate contain a creative host" in text


def test_prompt_preserves_hidden_outcomes_abstention_and_multiple_segmentations():
    text = StagePScopeGraphPromptContractV1_1(ROOT).template
    assert "Expected case labels, outcomes, and owner annotations are unavailable" in text
    assert "Multiple segmentations are valid" in text
    assert "emit UNRESOLVED_SCOPE and remain INDETERMINATE" in text
    assert "FSEM_" not in text


@pytest.mark.parametrize("summary,candidate", [("", "x"), ("x", ""), (None, "x"),
                                                  ("x", None), ("{factual_summary}", "x"),
                                                  ("x", "{candidate}")])
def test_invalid_sources_fail_closed(summary, candidate):
    with pytest.raises(ValueError, match="source text|reserved placeholder"):
        StagePScopeGraphPromptContractV1_1(ROOT).render(factual_summary=summary, candidate=candidate)


def test_prompt_contract_has_no_execution_edge():
    tree = ast.parse(SOURCE.read_text("utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names}
    assert not any(any(term in name.lower() for term in ("subprocess", "transformers", "torch", "runner", "provider"))
                   for name in imported)
