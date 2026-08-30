"""Freeze the already completed blind G03 open-recovery pass."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-g03-pass-a-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit("Pass A already frozen")
    result = {
        "primary_mechanism": "PERSONIFICATION",
        "primary_role": "DOMINANT",
        "supporting_mechanisms": ["ABSURDITY", "EXTENDED_METAPHOR"],
        "confidence": "HIGH",
        "defining_surface_operation": "O regulă abstractă este tratată ca un angajat: «intră în tură», iar verificarea de la 17:00 îi «închide pontajul».",
        "structural_dependency": "Efectul depinde de atribuirea coerentă a unui scenariu administrativ și ocupațional unor entități neînsuflețite sau abstracte; fără această transferare de agențialitate, rămâne doar o descriere neutră a două verificări.",
        "shortcut_dependence": {
            "lexical": "MATERIAL", "punctuation": "NON_MATERIAL", "formatting": "NON_MATERIAL",
            "template": "NON_MATERIAL",
            "explanation": "Lexicul ocupațional-birocratic aplicat regulii și verificării realizează personificarea; punctuația, formatarea și un șablon fix nu sunt necesare mecanismului.",
        },
        "strongest_alternative": "EXTENDED_METAPHOR",
        "alternative_comparison": "Metafora ocupațional-birocratică susține întregul pasaj, dar operația comică centrală este personificarea explicită a regulii și verificării ca participanți la muncă și pontaj.",
    }
    core = {
        "schema_name": "batch2-development-pilot01-g03-open-recovery-pass-a-v1",
        "schema_version": "1.0.0",
        "candidate_identity": "f96e626487812b4a9ad32ef548d4ac715fae4ea9bb24590a73f942b0783f080f",
        "candidate_raw_sha256": "2f848e2bc9d87b113df95996a4d49d48fbe4334d6c204ef707664158e23caf9d",
        "g02_identity": "bc6e7ce8975f94ad43de4cbc99b209099f6c330d8d53e85882fb356348d0d210",
        "pass": "A_OPEN_RECOVERY",
        "evaluator_view": "IMMUTABLE_CANDIDATE_SURFACE_ONLY",
        "choice_set_exposed": False,
        "sealed_mapping_exposed": False,
        "other_pass_exposed": False,
        "repository_access": False,
        "result": result,
    }
    receipt = {**core, "pass_a_identity": seal("B2_DEVELOPMENT_PILOT01_G03_PASS_A_V1", core)}
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(receipt["pass_a_identity"])


if __name__ == "__main__":
    main()
