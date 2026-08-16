from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(value: str) -> list[str]:
    text = unicodedata.normalize("NFC", value).casefold()
    return sorted(
        {token.strip(".,:;!?()[]{}") for token in text.split() if len(token) > 2}
    )


def _expression(record: dict[str, Any], owner_class: str) -> dict[str, Any]:
    raw = owner_class in {"KEEP_DEFAULT_RAW", "SPECIAL_RAW"}
    return {
        "expression_id": record["expression_id"],
        "text": record["authentic_text"],
        "owner_class": owner_class,
        "semantic_gloss": record.get("semantic_meaning") or record["authentic_text"],
        "semantic_families": record.get("themes", []),
        "keywords": _tokens(
            " ".join([record["authentic_text"], record.get("semantic_meaning", "")])
        ),
        "risk_tags": record.get("risk_flags", []),
        "regionalism": False,
        "regions": [],
        "raw": raw,
        "meme": False,
        "max_per_episode": record.get("usage_budget", {}).get("max_per_episode", 1),
        "cooldown_episodes": record.get("usage_budget", {}).get("cooldown_episodes", 0),
        "enabled": True,
    }


def compile_catalog(*, diagnostics: Path, output: Path) -> dict[str, Any]:
    calibration = (
        diagnostics
        / "romanian-expression-corpus-v1-batch2-raw-human-decisions-20260815-001"
    )
    promotion = (
        diagnostics / "expression-corpus-v1-production-promotion-retry-20260816-001"
    )
    defaults = _load(calibration / "cumulative-human-reviewed-default-family-v1.json")[
        "records"
    ]
    specials = _load(calibration / "cumulative-human-reviewed-special-family-v1.json")[
        "records"
    ]
    promoted = _load(promotion / "canonical-expression-promotion-v2.json")["promotions"]
    preliminary = _load(
        diagnostics
        / "romanian-expression-corpus-v1-modern-street-broader-triage-20260816-001"
        / "modern371-preliminary-owner-decisions.json"
    )["records"]
    preliminary_by_id = {record["candidate_id"]: record for record in preliminary}
    expressions = [_expression(record, "KEEP_DEFAULT") for record in defaults]
    expressions.extend(_expression(record, "SPECIAL_USE") for record in specials)
    for item in promoted:
        source = preliminary_by_id[item["source_record_ids"][0]]
        expressions.append(
            {
                "expression_id": item["canonical_expression_id"],
                "text": item["canonical_text"],
                "owner_class": item["owner_class"],
                "semantic_gloss": source["meaning_ro"],
                "semantic_families": source.get("semantic_families", []),
                "keywords": _tokens(
                    source["meaning_ro"] + " " + item["canonical_text"]
                ),
                "risk_tags": [],
                "regionalism": bool(item.get("regional_metadata")),
                "regions": (item.get("regional_metadata") or {}).get(
                    "region_association", []
                ),
                "raw": item["owner_class"] in {"KEEP_DEFAULT_RAW", "SPECIAL_RAW"},
                "meme": item["owner_class"] == "SPECIAL_MEME",
                "max_per_episode": 1,
                "cooldown_episodes": 1,
                "enabled": True,
            }
        )
    decisions = _load(promotion / "candidate-promotion-decisions-v2.json")["records"]
    source_authority_ids = sorted(
        {
            item["source_record_id"]
            for item in decisions
            if item.get("source_record_id")
            and item["production_status"].startswith("PROMOTE_")
        }
    )
    surface_source = {
        6: "modern-street-v1:dca54ce2f135e3f9e6d5",
        39: "modern-street-v1:60035501feffe814952a",
        59: "modern-street-v1:4b249d64d0f826695cb2",
        62: "modern-street-v1:b3bbddd0865e2b16da83",
    }
    promoted_surfaces = _load(promotion / "preferred-surface-promotion-v2.json")[
        "promotions"
    ]
    preferred_surfaces = []
    for index, item in enumerate(promoted_surfaces, 1):
        row_text = " ".join(item.get("source_record_ids", []))
        row = next(
            (number for number in surface_source if str(number) in row_text), None
        )
        source_id = surface_source.get(row)
        if source_id is None:
            source_id = next(
                (
                    expression["expression_id"]
                    for expression in expressions
                    if item["preferred_surface"].casefold()
                    == expression["text"].casefold()
                ),
                None,
            )
        if source_id is None:
            source_id = item.get("source_record_ids", [])[0]
        if not source_id:
            source_id = f"promotion-v2:surface-source:{index:02d}"
        source_authority_ids.append(source_id)
        preferred_surfaces.append(
            {
                "surface_id": f"surface-v1:{index:02d}",
                "source_expression_id": source_id,
                "surface": item["preferred_surface"],
                "relation_type": item["relation_type"],
            }
        )
    families = _load(promotion / "productive-family-promotion-v2.json")["promotions"]
    productive_families = [
        {"family_id": item["authority_id"], "members": item["members"]}
        for item in families
    ]
    terms = _load(promotion / "controlled-term-promotion-v2.json")["promotions"]
    controlled_terms = [
        {
            "term_id": item["authority_id"],
            "term": item["preferred_surface"],
            "domains": item["semantic_families"],
            "triggers": item["context_constraints"]["triggers"],
            "factual_constraints": item["context_constraints"]["factual_constraints"],
            "risk_tags": item["risk_tags"],
            "temporal_sensitivity": item["temporal_metadata"]["sensitivity"],
            "max_per_episode": item["max_per_episode"],
            "cooldown_episodes": item["cooldown"],
            "enabled": True,
        }
        for item in terms
    ]
    device_items = _load(promotion / "comedy-device-promotion-v2.json")["promotions"]
    affordances = {
        "absolute-cinema": ["entertainment", "meme"],
        "stinge-lumina": ["bureaucracy", "absurdity", "improvisation"],
        "legenda-spune": ["unfinished_project", "bureaucracy"],
        "ne-ai-facut-o": ["entertainment", "reaction"],
        "jos-palaria": ["politics", "contradiction", "arrogance"],
        "poveste-fara-sfarsit": ["unfinished_project", "bureaucracy"],
        "s-a-terminat": ["entertainment", "closing"],
        "rupe-fasul": ["absurdity", "escalation"],
        "toti-banii": ["detail", "closing"],
        "dus-rece": ["international", "failed_project", "contrast"],
        "ai-n-ai": ["bureaucracy", "improvisation"],
        "sa-fie-bine": ["bureaucracy", "absurdity"],
        "hagism-compound": ["bureaucracy", "improvisation"],
        "mare-clasic": ["signature_context"],
    }
    comedy_devices = []
    for item in device_items:
        suffix = item["authority_id"].split(":")[-1]
        source = item.get("source_record", {})
        comedy_devices.append(
            {
                "device_id": item["authority_id"],
                "device_type": source.get("type", "cultural_device"),
                "family": "hagism"
                if suffix
                in {"ai-n-ai", "sa-fie-bine", "hagism-compound", "mare-clasic"}
                else suffix,
                "structure": item["preferred_surface"],
                "semantic_affordances": affordances[suffix],
                "best_for": affordances[suffix],
                "bad_for": ["victim_sensitive", "tragedy_sensitive"],
                "replaceable_slots": source.get("replaceable_slots", []),
                "forbidden_transforms": source.get("forbidden_transformations", []),
                "source_expression_ids": source.get("source_expression_ids", []),
                "callback_capable": bool(source.get("callback_capable", False)),
                "signature_capable": suffix == "mare-clasic",
                "compound_capable": suffix == "hagism-compound",
                "max_per_episode": 1,
                "recurrence_mode": "signature"
                if suffix == "mare-clasic"
                else "ordinary",
                "risk_tags": ["roast", "victim_targeting"]
                if suffix in {"ne-ai-facut-o", "rupe-fasul"}
                else [],
            }
        )
    signature_devices = [
        {
            "signature_id": "signature-v1:mare-clasic",
            "device_id": "promotion-v2:device:mare-clasic",
            "family": "hagism",
            "recurrence_mode": "signature",
            "max_per_episode": 1,
            "hard_cooldown": 0,
            "preferred_spacing_episodes": 2,
            "canonical_signature": True,
        },
        {
            "signature_id": "signature-v1:legenda-spune",
            "device_id": "promotion-v2:device:legenda-spune",
            "family": "legend_callback",
            "recurrence_mode": "candidate",
            "max_per_episode": 1,
            "hard_cooldown": 0,
            "preferred_spacing_episodes": 0,
            "canonical_signature": False,
        },
        {
            "signature_id": "signature-v1:hagism-compound",
            "device_id": "promotion-v2:device:hagism-compound",
            "family": "hagism",
            "recurrence_mode": "compound",
            "max_per_episode": 1,
            "hard_cooldown": 0,
            "preferred_spacing_episodes": 0,
            "canonical_signature": False,
        },
    ]
    catalog = {
        "corpus_schema_version": 1,
        "editorial_calibration_version": 1,
        "device_catalog_version": 1,
        "bundle_version": 1,
        "generated_from_manifest_sha256": "7f8afc480a99ac43de80cdda6cd779d10b7b6cef9acbd7d8e77db30ce44a3dfe",
        "source_authority_ids": sorted(set(source_authority_ids)),
        "expressions": expressions,
        "preferred_surfaces": preferred_surfaces,
        "productive_families": productive_families,
        "controlled_terms": controlled_terms,
        "comedy_devices": comedy_devices,
        "signature_devices": signature_devices,
        "counts": {
            "expressions": len(expressions),
            "preferred_surfaces": len(preferred_surfaces),
            "productive_families": len(productive_families),
            "controlled_terms": len(controlled_terms),
            "comedy_devices": len(comedy_devices),
            "signature_devices": len(signature_devices),
        },
        "excluded_counts": {"deferred": 3, "rejected": 30},
    }
    canonical = json.dumps(
        catalog, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    catalog["bundle_content_sha256"] = hashlib.sha256(canonical).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--diagnostics", type=Path, default=Path(r"C:\PastilaScout-Diagnostics")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "src/pastila_scout/resources/expression_retrieval_v1/catalog.json"
        ),
    )
    args = parser.parse_args()
    compile_catalog(diagnostics=args.diagnostics, output=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
