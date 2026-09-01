"""Static and negative-regression tests; no constructor is invoked."""

from pathlib import Path

import pytest

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_2 import (
    RealizationDraft,
    SurfaceNodeWitness,
    validate_realization_draft,
)

ROOT = Path(__file__).resolve().parents[1]


def plan():
    return (
        TypedPlanNode("L1", "FACT_REL", "RELATION_HEAD", "EXTEND", "FACT_OBJECT", (), ("INVENTED_1",), "P5", True),
        TypedPlanNode("L2", "INVENTED_1", "RELATION_HEAD", "PROPAGATE", "FACT_OBJECT", ("L1",), ("INVENTED_2",), "L1", True),
        TypedPlanNode("RESULT", "INVENTED_2", "RELATION_HEAD", "RESOLVE", "FACT_REL", ("L2",), (), "L2", True),
    )


def test_pilot09_meta_surface_fails_before_candidate_emission():
    surface = (ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-v1.txt").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="meta-language"):
        validate_realization_draft(plan(), RealizationDraft(surface, ()))


def test_claimed_nodes_without_explicit_witnesses_fail_closed():
    with pytest.raises(ValueError, match="missing plan or surface witnesses"):
        validate_realization_draft(plan(), RealizationDraft("O urmare imaginară este declarată.", ()))


def test_partial_node_manifest_fails_n_over_n_coverage():
    surface = "Relația produce urma unu."
    witness = SurfaceNodeWitness("L1", 0, len(surface), "FACT_REL", "Relația", "EXTEND", "produce", "FACT_OBJECT", "urma", (), (("INVENTED_1", "urma unu"),), False)
    with pytest.raises(ValueError, match="N/N"):
        validate_realization_draft(plan(), RealizationDraft(surface, (witness,)))


def test_terminal_result_witness_is_mandatory():
    parts = ("Relația produce urma unu.", "Urma unu produce urma doi.", "Urma doi închide relația.")
    surface = " ".join(parts)
    starts = (0, len(parts[0]) + 1, len(parts[0]) + len(parts[1]) + 2)
    witnesses = (
        SurfaceNodeWitness("L1", starts[0], starts[0] + len(parts[0]), "FACT_REL", "Relația", "EXTEND", "produce", "FACT_OBJECT", "urma", (), (("INVENTED_1", "urma unu"),), False),
        SurfaceNodeWitness("L2", starts[1], starts[1] + len(parts[1]), "INVENTED_1", "Urma unu", "PROPAGATE", "produce", "FACT_OBJECT", "urma", ("L1",), (("INVENTED_2", "urma doi"),), False),
        SurfaceNodeWitness("RESULT", starts[2], starts[2] + len(parts[2]), "INVENTED_2", "Urma doi", "RESOLVE", "închide", "FACT_REL", "relația", ("L2",), (), False),
    )
    with pytest.raises(ValueError, match="terminal result"):
        validate_realization_draft(plan(), RealizationDraft(surface, witnesses))
