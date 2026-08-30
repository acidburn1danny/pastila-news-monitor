"""Pre-attempt regression for Pilot 03 constructor source dispatch."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.humor_batch2_development_constructor_v1 import construct_development_candidate_v1

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def test_pilot03_source_uses_bound_natural_romanian_branch() -> None:
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot03-constructor-facing-assignment-g02b-v1.json").read_text(encoding="utf-8"))
    result = construct_development_candidate_v1(
        constructor_packet_bytes=json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    assert result.terminal_classification == "CANDIDATE_PRODUCED"
    assert result.failure_code is None
    surface = result.candidate_surface_utf8.decode("utf-8")
    assert surface.startswith("La momentul recepției nu este documentat conținutul exact al coletului.")
    assert "În povestea imaginară a coletului" in surface
    assert "pontaj" not in surface and "mobilier" not in surface
    assert "Ã" not in surface and "È" not in surface
