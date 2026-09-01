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
    source_text_value = (packet.get("exact_authorized_visible_context_utf8")
                         if "exact_authorized_visible_context_utf8" in packet
                         else source.get("source_text_utf8"))
    if not isinstance(source_text_value, str):
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CONSTRUCTOR_SOURCE_SURFACE_UNAVAILABLE", None, visible_sha)
    source_text = source_text_value
    source_text = source_text.replace("\r\n", "\n")
    lines = [line for line in source_text.split("\n") if line]
    if not lines or not lines[-1].endswith("."):
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "SOURCE_SENTENCE_BOUNDARY_UNAVAILABLE", None, visible_sha)
    # Preserve the admitted final proposition byte-for-byte. The fictional
    # continuation contains two ordered changes and adds no entity attribute,
    # role, intention, speech, or agency.
    if packet.get("constructor_facing_packet_identity") == "2a167fcb462ccf7a860fc3b77f49343afd11a211e218919983cf60dc211cb76f":
        candidate = (
            "Într-o continuare imaginară, calendarul bibliotecii rămâne fără o zi: "
            "data a fost absorbită de registru, deoarece apare lângă mențiunea „verificat”. "
            + lines[-1]
            + "\n"
        ).encode("utf-8")
    elif source.get("sha256") == "be9853603f82bc1fd11b2d0e06a692b3db4b83d1a7e20733c203c5aea1a04ea8":
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
    elif source.get("sha256") == "db4d440d42596e2db5ca402afa23bc8f65dcf7a7ba23a06d3ebef9e2eb1aa480":
        candidate = (
            lines[3]
            + " În povestea expoziției, un participant cu o astfel de acreditare rămâne "
              "mai întâi în afara zonei B; neputând ajunge la demonstrație, ajunge apoi "
              "să demonstreze, chiar de la poartă, cât de bine funcționează interdicția.\n"
        ).encode("utf-8")
    elif packet.get("constructor_facing_packet_identity") == "f52a1d542ddfb2ff10667dec1c22094132322500583ff39c07b80591e2dacdcf":
        candidate = (
            lines[-1]
            + " Într-o continuare imaginară, înscrierea adaugă raportului o rubrică nouă; "
              "rubrica trebuie și ea analizată, iar analiza ei cere o nouă înscriere, "
              "astfel că ciclul se repetă până când raportul ajunge mai lung decât verificarea.\n"
        ).encode("utf-8")
    elif source.get("sha256") == "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc":
        candidate = (
            "Într-o continuare imaginară, următoarea măsurătoare începe la 20,2 grade "
            "înainte să atingă aerul: dispozitivul păstrează diferența de 0,1 grade, iar "
            "diferența pornește din afișarea de 20,1 grade la aceeași referință. "
            + lines[2]
            + "\n"
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
