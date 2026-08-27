from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_prompt_v1 import (
    PROMPT_RELATIVE,
    StagePScopeGraphPromptContractV1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_prompt_v1.py"


def test_prompt_bytes_are_canonical_and_identity_excludes_one_storage_newline():
    data = (ROOT / PROMPT_RELATIVE).read_bytes()
    contract = StagePScopeGraphPromptContractV1(ROOT)
    assert data.endswith(b"\n") and not data.endswith(b"\n\n")
    assert contract.prompt_identity == "sha256:" + hashlib.sha256(data[:-1]).hexdigest()
    assert contract.template == data[:-1].decode("utf-8") == contract.template.strip()


def test_render_is_exact_unpadded_and_source_bound():
    contract = StagePScopeGraphPromptContractV1(ROOT)
    rendered = contract.render(factual_summary="Autoritate exactă.", candidate="Comentariu exact.")
    assert rendered.startswith("SEMANTIC ADMISSION V2") and rendered.endswith("nothing else.")
    assert not rendered.endswith("\n")
    assert rendered.count("Autoritate exactă.") == rendered.count("Comentariu exact.") == 1
    assert "{factual_summary}" not in rendered and "{candidate}" not in rendered


def test_prompt_encodes_factual_return_and_no_shield_boundary():
    text = StagePScopeGraphPromptContractV1(ROOT).template
    required = ("creative semantic head never shields", "asserts, presupposes, entails, or necessarily implies",
                "truth-evaluable real-world proposition", "Unsupported factual return remains a real-world commitment",
                "Select the basis from communicative force, not surface grammar")
    assert all(fragment in text for fragment in required)


def test_prompt_encodes_graph_and_complete_coverage_invariants():
    text = StagePScopeGraphPromptContractV1(ROOT).template
    for term in ("FACTUAL_RETURN_WITHIN_CREATIVE_HOST", "creative_host_entry_id", "factual_return_basis",
                 "overlapping_spans_reconciled", "integrated_creative_hosts_checked",
                 "factual_return_tests_completed", "not self-referential", "Maximum eight entries"):
        assert term in text


def test_prompt_preserves_multiple_segmentations_and_fail_closed_abstention():
    text = StagePScopeGraphPromptContractV1(ROOT).template
    assert "There is no single mandatory segmentation" in text
    assert "Multiple segmentations are valid" in text
    assert "emit UNRESOLVED_SCOPE and remain INDETERMINATE" in text
    assert "Expected case labels, outcomes, and owner annotations are unavailable" in text
    assert "FSEM_" not in text


@pytest.mark.parametrize("summary,candidate", [("", "x"), ("x", ""), (None, "x"), ("x", None),
                                                  ("{factual_summary}", "x"), ("x", "{candidate}")])
def test_invalid_or_reserved_sources_fail_closed(summary, candidate):
    with pytest.raises(ValueError, match="source text|reserved placeholder"):
        StagePScopeGraphPromptContractV1(ROOT).render(factual_summary=summary, candidate=candidate)


def test_contract_has_no_execution_or_provider_edge():
    tree = ast.parse(SOURCE.read_text("utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names}
    forbidden = ("subprocess", "transformers", "torch", "provider", "runner", "ollama")
    assert not any(any(token in name.lower() for token in forbidden) for name in imported)
