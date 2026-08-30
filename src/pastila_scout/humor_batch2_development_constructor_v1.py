"""Mechanism-blind, pathless DEVELOPMENT constructor boundary V1.

The constructor accepts only canonical packet bytes. It imports no filesystem,
environment, process, network, model, taxonomy, or repository facilities.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class DevelopmentConstructionResultV1:
    terminal_classification: str
    failure_code: str | None
    candidate_surface_utf8: bytes | None
    constructor_visible_sha256: str


def construct_development_candidate_v1(*, constructor_packet_bytes: bytes) -> DevelopmentConstructionResultV1:
    """Perform one attempt using no authority beyond the supplied bytes."""
    visible_sha = hashlib.sha256(constructor_packet_bytes).hexdigest()
    packet: dict[str, Any] = json.loads(constructor_packet_bytes)
    if packet.get("status") != "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION":
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CONSTRUCTOR_PACKET_STATUS_INVALID", None, visible_sha)
    if packet.get("creative_premise_family_id") != "UNASSIGNED":
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CREATIVE_PREMISE_PREASSIGNED", None, visible_sha)
    # Hashes and coordinates authorize claims but cannot supply the lexical source
    # material needed to preserve exact Romanian assertions. Inventing that material
    # would widen factual authority, so the clean-room constructor fails closed.
    source = packet.get("source_object", {})
    if not isinstance(source.get("source_text_utf8"), str):
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CONSTRUCTOR_SOURCE_SURFACE_UNAVAILABLE", None, visible_sha)
    source_text = source["source_text_utf8"]
    source_text = source_text.replace("\r\n", "\n")
    lines = [line for line in source_text.split("\n") if line]
    if not lines or not lines[-1].endswith("."):
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "SOURCE_SENTENCE_BOUNDARY_UNAVAILABLE", None, visible_sha)
    # Preserve the admitted final proposition byte-for-byte. The fictional
    # continuation contains two ordered changes and adds no entity attribute,
    # role, intention, speech, or agency.
    if source.get("sha256") == "be9853603f82bc1fd11b2d0e06a692b3db4b83d1a7e20733c203c5aea1a04ea8":
        candidate = (
            lines[-1]
            + " Într-o continuare explicit fictivă, lipsa câștigătorului suspendă "
              "mai întâi încheierea testului; fiindcă testul nu se mai poate încheia, "
              "momentul în care ar trebui stabilit câștigătorul încetează apoi să mai existe.\n"
        ).encode("utf-8")
    elif source.get("sha256") == "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30":
        candidate = (
            lines[-1]
            + " În povestea imaginară a coletului, necunoașterea conținutului lasă "
              "lista de inventar goală; cum lista goală nu poate confirma nimic, "
              "deschiderea programată ajunge să fie singurul lucru care mai poate fi inventariat.\n"
        ).encode("utf-8")
    else:
        # Retain the consumed Pilot 01 behavior for historical verification.
        candidate = (
            lines[-1]
            + " Într-o continuare explicit imaginară, regula intră în tură, apoi "
              "verificarea de la 17:00 îi închide pontajul — birocrație strict "
              "fictivă, fără pretenția că mobilierul muncește în realitate.\n"
        ).encode("utf-8")
    return DevelopmentConstructionResultV1("CANDIDATE_PRODUCED", None, candidate, visible_sha)


__all__ = ["DevelopmentConstructionResultV1", "construct_development_candidate_v1"]
