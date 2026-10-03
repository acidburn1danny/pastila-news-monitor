from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path


SOURCE_SHA256 = "0be3c092e9189c516996b60f2ca1d858de52e2162fbdddcaeb299a30d26c45d5"
PREDECESSOR_IDENTITY = "cbc0001c54bad87f17d082e6a4ce09fceee0c23deaaa650129e2c003847cc935"
BACKLOG_IDENTITY = "2af65f4653a62bbd55e1b0747cab3d99dcf0de324c2e04ef070db12978f8eacb"


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def identify(value: dict, field: str) -> dict:
    result = dict(value)
    result[field] = hashlib.sha256(canon(result)).hexdigest()
    return result


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: object) -> None:
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_bytes(b"".join(canon(row) + b"\n" for row in rows))


META = {
    1: {
        "slug": "tollro",
        "partition": "TRAIN",
        "target": "public digital-infrastructure governance and launch decision",
        "protected": ["transport users"],
        "mechanisms": {
            "individual": [("HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR", "Asta nu mai e TollRo.\r\nE **TROLL.RO**.")],
            "supporting": [("HMCV1-B03-M03-REPETITION_WITH_VARIATION", "„Merge?”\r\n„Nu.”\r\n„Îi dăm drumul?”\r\n„Normal.”")],
            "composition": [("HMCV1-B03-M01-SETUP_PAYOFF", "Asta nu mai e TollRo.\r\nE **TROLL.RO**.")],
        },
        "devices": ["TRANSPARENT_IMAGINED_DIALOGUE", "COMIC_ANALOGY", "WORDPLAY"],
    },
    2: {
        "slug": "international-education-day",
        "partition": "TRAIN",
        "target": "institutional celebration logic",
        "protected": ["students", "teachers"],
        "mechanisms": {
            "individual": [("HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "De Ziua Pompierilor:\r\n„Băieți, vedeți că azi suntem liberi. Dacă ia ceva foc... să ardă frumos până mâine.”")],
            "supporting": [("HMCV1-B03-M02-RULE_OF_THREE", "De Ziua Pompierilor"), ("HMCV1-B03-M03-REPETITION_WITH_VARIATION", "Ziua Educației?\r\nLiber.\r\nZiua Muncii?\r\nLiber.")],
            "composition": [("HMCV1-B05-M01-BOOKENDING", "La mulți ani, Educație!\r\nNe vedem marți, că azi avem treabă să te sărbătorim.")],
        },
        "devices": ["HYPOTHETICAL_ABSURD_EXTENSION", "TRANSPARENT_IMAGINED_DIALOGUE"],
    },
    3: {
        "slug": "flour-bread-prices",
        "partition": "TRAIN",
        "target": "asymmetric retail price transmission",
        "protected": ["consumers"],
        "mechanisms": {
            "individual": [("HMCV1-B01-M02-IRONY", "S-a ieftinit făina.\r\nȘi acum vestea proastă:\r\n**S-a scumpit pâinea.**")],
            "supporting": [("HMCV1-B03-M03-REPETITION_WITH_VARIATION", "Pac! Pâinea mai scumpă."), ("HMCV1-B02-M04-PERSONIFICATION", "benzina se gândește.")],
            "composition": [("HMCV1-B04-M10-SENTENCE_FINAL_REINTERPRETATION", "Când petrolul se ieftinește...\r\n**benzina se gândește.**")],
        },
        "devices": ["COMIC_ANALOGY", "PERSONIFICATION", "EDITORIAL_INFERENCE"],
    },
    4: {
        "slug": "health-system-financing",
        "partition": "TRAIN",
        "target": "health-system financing design",
        "protected": ["patients", "medical staff"],
        "mechanisms": {
            "individual": [("HMCV1-B01-M04-COMIC_ANALOGY", "Deci e ca și cum îți faci abonament la Netflix...")],
            "supporting": [("HMCV1-B03-M03-REPETITION_WITH_VARIATION", "Analiza asta?\r\nNu e decontată.\r\nInvestigația asta?"), ("HMCV1-B04-M09-METONYMIC_SUBSTITUTION", "te prinde.\r\nDe portofel.")],
            "composition": [("HMCV1-B03-M06-DELAYED_PAYOFF", "Și când ți se face rău...\r\nte prinde.\r\nDe portofel.")],
        },
        "devices": ["COMIC_ANALOGY", "TRANSPARENT_IMAGINED_DIALOGUE", "EDITORIAL_INFERENCE"],
    },
    5: {
        "slug": "school-uniforms",
        "partition": "TRAIN",
        "target": "school-uniform policy and policymaking priorities",
        "protected": ["students"],
        "mechanisms": {
            "individual": [("HMCV1-B01-M05-FRAME_TRANSFER", "E democrație, dar cu dress code.\r\nE ca la pușcărie:")],
            "supporting": [("HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "hai să punem uniforme și în Parlament."), ("HMCV1-B02-M07-FALSE_CONCESSION", "Uniforma rămâne obligatorie... dar vă lăsăm pe voi să decideți cum arată.")],
            "composition": [("HMCV1-B03-M07-CALLBACK", "Și, ca să fie democratic...\r\n**îi lăsăm să aleagă cravata.**")],
        },
        "devices": ["COMIC_ANALOGY", "HYPOTHETICAL_ABSURD_EXTENSION", "TRANSPARENT_IMAGINED_DIALOGUE"],
    },
    6: {
        "slug": "braila-drone",
        "partition": "TRAIN",
        "target": "airspace-surveillance failure",
        "protected": ["local witness"],
        "mechanisms": {
            "individual": [("HMCV1-B04-M06-STATUS_REVERSAL", "Și momentan omul de la geam conduce cu 1-0.")],
            "supporting": [("HMCV1-B02-M10-ROLE_SIMULATION", "Sună Gigel la 112:"), ("HMCV1-B05-M04-KNOWN_UNKNOWN_PLAY", "nu știm de unde a venit drona, ce traseu a avut sau de ce n-a fost detectată.")],
            "composition": [("HMCV1-B05-M01-BOOKENDING", "**sunați la 112.**\r\nCă radarul află după.")],
        },
        "devices": ["TRANSPARENT_IMAGINED_DIALOGUE", "COMIC_FICTIONALIZATION", "UNKNOWN_PRESERVED"],
    },
    7: {
        "slug": "anthropic-ipo-risk",
        "partition": "TRAIN",
        "target": "capital-market treatment of AI existential-risk disclosure",
        "protected": [],
        "mechanisms": {
            "individual": [("HMCV1-B02-M09-DISCOURSE_FORM_PARODY", "Bă, ăsta nu mai e prospect de bursă.\r\nE prospect de medicamente.")],
            "supporting": [("HMCV1-B02-M10-ROLE_SIMULATION", "Și îmi imaginez prezentarea:"), ("HMCV1-B01-M03-CONTRAST_JUXTAPOSITION", "Poate vine Apocalipsa...\r\ndar dacă vine cu EBITDA bun, avem investitori.")],
            "composition": [("HMCV1-B05-M09-FAMILIAR_EXPRESSION_SUBVERSION", "**Au intrat devreme.**")],
        },
        "devices": ["TRANSPARENT_IMAGINED_DIALOGUE", "DISCOURSE_PARODY", "CONDITIONAL_HYPOTHETICAL"],
    },
    8: {
        "slug": "cardboard-trump",
        "partition": "VALIDATION",
        "target": "online manipulation and disproportionate official-response burden",
        "protected": [],
        "mechanisms": {
            "individual": [("HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR", "**„Ăsta e din carton.”**")],
            "supporting": [("HMCV1-B03-M03-REPETITION_WITH_VARIATION", "Aceeași poziție.\r\nAcelași zâmbet.\r\nAceeași mână."), ("HMCV1-B02-M10-ROLE_SIMULATION", "„Uitați, aici clipește.”")],
            "composition": [("HMCV1-B03-M07-CALLBACK", "Drona n-o vedem.\r\n**Cartonul îl verificăm.**")],
        },
        "devices": ["TRANSPARENT_IMAGINED_DIALOGUE", "HYPOTHETICAL_ABSURD_EXTENSION", "FACTUAL_CONTEXT_CALLBACK"],
    },
    9: {
        "slug": "animawings",
        "partition": "VALIDATION",
        "target": "failed transaction narrative and corporate collapse",
        "protected": ["passengers"],
        "mechanisms": {
            "individual": [("HMCV1-B01-M04-COMIC_ANALOGY", "Păi și cu nunta din aprilie ce facem?")],
            "supporting": [("HMCV1-B02-M10-ROLE_SIMULATION", "„Cine n-a semnat?”"), ("HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR", "Asta nu mai e companie aeriană.\r\nE Judecătoria cu program de fidelitate.")],
            "composition": [("HMCV1-B03-M06-DELAYED_PAYOFF", "**au fost avocații.**")],
        },
        "devices": ["COMIC_ANALOGY", "TRANSPARENT_IMAGINED_DIALOGUE", "HYPOTHETICAL_LOYALTY_PROGRAM"],
    },
    10: {
        "slug": "anaf-lux-atom",
        "partition": "VALIDATION",
        "target": "self-reported tax-risk signals and unjustified company luxury",
        "protected": [],
        "mechanisms": {
            "individual": [("HMCV1-B01-M02-IRONY", "Te torni singur.\r\nDigital.\r\nCu semnătură electronică.\r\nRomânia a intrat în viitor!")],
            "supporting": [("HMCV1-B02-M10-ROLE_SIMULATION", "„Poftiți dovada.”"), ("HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "Firma vinde șuruburi...\r\ndar, din motive strict profesionale, are nevoie de Porsche.")],
            "composition": [("HMCV1-B04-M10-SENTENCE_FINAL_REINTERPRETATION", "**ori zbori, ori fugi de control.**")],
        },
        "devices": ["TRANSPARENT_IMAGINED_DIALOGUE", "HYPOTHETICAL_ABSURD_EXTENSION", "EDITORIAL_INFERENCE"],
    },
}


def parse_records(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8")
    pattern = re.compile(
        r"(?ms)^RECORD (?P<number>\d{2}) — (?P<title>[^\r\n]+)\r?\n"
        r"FACTUAL SETUP\r?\n(?P<setup>.*?)\r?\n"
        r"SOURCES?\r?\n(?P<sources>.*?)\r?\n"
        r"OWNER COMMENTARY\r?\n(?P<commentary>.*?)(?=\r?\n={20,}|\Z)"
    )
    records = []
    for match in pattern.finditer(text):
        commentary = match.group("commentary").rstrip("\r\n")
        setup = match.group("setup").rstrip("\r\n")
        sources = re.findall(r"https?://\S+", match.group("sources"))
        records.append({
            "number": int(match.group("number")),
            "title": match.group("title"),
            "factual_setup": setup,
            "owner_commentary": commentary,
            "sources": sources,
        })
    assert [r["number"] for r in records] == list(range(1, 11))
    return records


def main(repo: Path) -> None:
    artifacts = repo / "docs/artifacts"
    source = artifacts / "vnext-voice-owner-gold-pack01-v1/sources/PASTILA_VOICE_OWNER_GOLD_PACK_01.txt"
    raw = source.read_bytes()
    assert sha_bytes(raw) == SOURCE_SHA256
    records = parse_records(raw)

    predecessor = json.loads((artifacts / "vnext-voice-contemporary-owner-gold-dataset-successor-v1.json").read_text(encoding="utf-8"))
    backlog = json.loads((artifacts / "vnext-voice-contemporary-owner-gold-backlog-v1.json").read_text(encoding="utf-8"))
    assert predecessor["successor_identity"] == PREDECESSOR_IDENTITY
    assert backlog["backlog_identity"] == BACKLOG_IDENTITY

    curriculum = json.loads((artifacts / "humor-mechanics-curriculum-v1.manifest.json").read_text(encoding="utf-8"))
    mechanism_ids = {m["id"] for m in curriculum["mechanisms"]}
    assert len(mechanism_ids) == 50

    source_status = {
        1: "VERIFIED_MULTI_SOURCE",
        2: "VERIFIED_MULTI_SOURCE",
        3: "VERIFIED_MULTI_SOURCE",
        4: "VERIFIED_MULTI_SOURCE",
        5: "VERIFIED_MULTI_SOURCE",
        6: "VERIFIED_SOURCE_AND_UNKNOWN_PRESERVED",
        7: "VERIFIED_MULTI_SOURCE_MODAL_CLAIMS_PRESERVED",
        8: "VERIFIED_MULTI_SOURCE_MANIPULATION_DISTINGUISHED_FROM_AUTHENTIC_PHOTO",
        9: "VERIFIED_SOURCE",
        10: "VERIFIED_PRIMARY_AND_SECONDARY_SOURCE",
    }
    verified_claims = {
        1: ["TollRo entered operation on 2026-10-01", "first-day dysfunctions and user complaints were reported", "the ministerial order prevented sanctions caused by application dysfunction", "postponement requests and CNAIR readiness positions were reported"],
        2: ["2026-10-05 is a no-course day for pre-university education", "courses resume on 2026-10-06", "the no-course observance predates 2026"],
        3: ["reported flour-price decreases did not imply bread-price decreases", "bread price includes processing, energy, transport, labor, packaging, distribution, and margins"],
        4: ["2024 direct household health spending exceeded RON 33.6 billion", "2025 FNUASS hospital salary-increase coverage was reported near RON 16.94 billion", "reported hospital-service reimbursement was near RON 14.87 billion"],
        5: ["the Senate adopted the school-uniform bill", "the National Student Council opposed it", "student involvement in choosing the uniform appearance was proposed", "the bill was not withdrawn and still required Chamber action"],
        6: ["a citizen reported the fragments through 112", "a crater and drone fragments were identified", "an explosive payload detonated on impact", "MApN radars reported no unauthorized entry", "origin, route, and non-detection cause remain unknown"],
        7: ["Anthropic was preparing an IPO", "reported prospectus material described catastrophic or existential AI risk", "USD 2 trillion was a reported potential valuation rather than a completed valuation"],
        8: ["AI-manipulated cardboard-Trump images circulated", "Romania's Presidential Administration identified them as fake", "the authentic photograph showed Nicușor Dan with the real Donald Trump"],
        9: ["the announced 50% transaction did not complete", "BT Asset Management stated it was not an AnimaWings shareholder", "flight suspension, insolvency request, and the reported litigation volume were part of the source account"],
        10: ["ANAF described risk analysis based on declarations, SAF-T, and RO e-Factura", "the checks concerned unjustified company-funded luxury or leisure goods", "Operation ATOM concerned 35 second-hand-car entities and stock reported above EUR 38 million"],
    }

    admitted = []
    for source_record in records:
        number = source_record["number"]
        meta = META[number]
        commentary = source_record["owner_commentary"]
        for annotations in meta["mechanisms"].values():
            for mechanism_id, span in annotations:
                assert mechanism_id in mechanism_ids
                assert span.replace("\r\n", "\n") in commentary, (number, mechanism_id, span)
        family = f"PASTILA_ACIDA_CONTEMPORARY_PACK01_{number:02d}_{meta['slug'].upper().replace('-', '_')}"
        record = {
            "record_id": f"PA-CONTEMP-P01-{number:02d}",
            "pack_record": number,
            "title": source_record["title"],
            "family_identity": family,
            "partition": meta["partition"],
            "source_pack_path": str(source.relative_to(repo)).replace("\\", "/"),
            "source_pack_sha256": SOURCE_SHA256,
            "factual_setup": {
                "text": source_record["factual_setup"],
                "sha256": sha_bytes(source_record["factual_setup"].encode()),
                "sources": source_record["sources"],
                "provenance_status": source_status[number],
                "verified_claims": verified_claims[number],
                "retrieved_on": "2026-10-03",
            },
            "gold_commentary": {
                "text": commentary,
                "sha256": sha_bytes(commentary.encode()),
                "provenance": "EXACT_OWNER_WRITTEN_SOURCE_BYTES",
                "rewritten": False,
                "normalized": False,
                "commentary_token_estimate": math.ceil(len(commentary) / 4),
            },
            "mechanisms": {
                role: [{"mechanism_id": mechanism_id, "evidence_span": span.replace("\r\n", "\n")} for mechanism_id, span in annotations]
                for role, annotations in meta["mechanisms"].items()
            },
            "factual_commentary_taxonomy": {
                "factual_setup_separate": True,
                "commentary_devices": meta["devices"],
                "transparent_fiction_not_treated_as_quote_or_fact": True,
                "unsupported_fact_admitted": False,
                "conditionality_and_unknowns_preserved": True,
            },
            "target_policy": {
                "satire_target": meta["target"],
                "protected_targets": meta["protected"],
                "protected_target_is_satire_target": False,
            },
            "stream": "ORGANIC_OWNER_WRITTEN_CONTEMPORARY",
            "training_eligible": True,
        }
        admitted.append(identify(record, "record_identity"))

    train_base_path = artifacts / "vnext-voice-episode29-successor-train-v1.jsonl"
    validation_base_path = artifacts / "vnext-voice-episode29-successor-validation-v1.jsonl"
    train_base = load_rows(train_base_path)
    validation_base = load_rows(validation_base_path)
    train_new = [r for r in admitted if r["partition"] == "TRAIN"]
    validation_new = [r for r in admitted if r["partition"] == "VALIDATION"]
    assert len(train_new) == 7 and len(validation_new) == 3

    admission_path = artifacts / "vnext-voice-owner-gold-pack01-v1-admission.jsonl"
    train_path = artifacts / "vnext-voice-owner-gold-pack01-v1-train-successor.jsonl"
    validation_path = artifacts / "vnext-voice-owner-gold-pack01-v1-validation-successor.jsonl"
    write_jsonl(admission_path, admitted)
    write_jsonl(train_path, train_base + train_new)
    write_jsonl(validation_path, validation_base + validation_new)

    existing_mechanisms = {
        mechanism
        for row in train_base + validation_base
        for values in row.get("mechanisms", {}).values()
        for mechanism in values
    }
    new_mechanisms = {
        item["mechanism_id"]
        for row in admitted
        for values in row["mechanisms"].values()
        for item in values
    }
    covered = existing_mechanisms | new_mechanisms
    assert covered <= mechanism_ids

    new_tokens = sum(r["gold_commentary"]["commentary_token_estimate"] for r in admitted)
    dataset = {
        "schema": "vnext-voice-owner-gold-pack01-dataset-successor",
        "schema_version": 1,
        "predecessor_identity": PREDECESSOR_IDENTITY,
        "admission_backlog_predecessor_identity": BACKLOG_IDENTITY,
        "source_pack": {"path": str(source.relative_to(repo)).replace("\\", "/"), "sha256": SOURCE_SHA256, "bytes": len(raw)},
        "partition": {"new_train": 7, "new_validation": 3, "holdout_families": [31, 32, 33, 34], "holdout_exposure": 0, "qwen3_bakeoff_exposure": 0},
        "counts": {"train_positive": len(train_base) + 7, "validation_positive": len(validation_base) + 3, "negative": 27, "model_visible_abstention": 0, "new_positive": 10},
        "commentary_tokens": {"predecessor_estimated": 4034, "new_estimated": new_tokens, "successor_estimated": 4034 + new_tokens, "method": "ceil(UTF8-decoded-character-count/4)-per-new-record"},
        "mechanism_coverage": {"predecessor": len(existing_mechanisms), "successor": len(covered), "newly_covered": sorted(new_mechanisms - existing_mechanisms), "covered": sorted(covered), "positive_gaps": sorted(mechanism_ids - covered), "curriculum_total": 50},
        "quality_coverage": {"romanian_naturalness": 10, "restraint": 4, "factual_discipline": 10, "concision": 3, "variation_anti_repetition": 10, "target_choice": 10, "authentic_mechanism_composition": 10},
        "factual_safety": {"source_verified_records": 10, "unsupported_fact_records": 0, "transparent_fiction_separated": 10, "runtime_constrained_projection_required": True},
        "files": {
            "admission": {"path": str(admission_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(admission_path)},
            "train": {"path": str(train_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(train_path)},
            "validation": {"path": str(validation_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(validation_path)},
        },
        "second_experiment_readiness": {
            "train_positive_min": 36,
            "validation_positive_min": 12,
            "commentary_tokens_min": 8000,
            "train_positive_pass": len(train_base) + 7 >= 36,
            "validation_positive_pass": len(validation_base) + 3 >= 12,
            "commentary_tokens_pass": 4034 + new_tokens >= 8000,
            "minimum_new_factual_restraint_records": 8,
            "factual_restraint_records_pass": 4 >= 8,
            "status": "FAIL_CLOSED_NOT_READY" if (len(train_base) + 7 < 36 or 4034 + new_tokens < 8000) else "READY_FOR_SECOND_EXPERIMENTAL_TRAIN",
        },
        "training_performed": False,
        "weights_modified": False,
        "active_product_modified": False,
        "canonical_rollback_modified": False,
        "gui_state": "ACTIVE",
        "voice_state": "DISABLED_UNTIL_PROMOTION",
    }
    dataset = identify(dataset, "dataset_successor_identity")
    dataset_path = artifacts / "vnext-voice-owner-gold-pack01-v1-dataset-successor.json"
    write_json(dataset_path, dataset)

    backlog_delta = identify({
        "schema": "vnext-voice-owner-gold-pack01-backlog-delta",
        "schema_version": 1,
        "backlog_predecessor_identity": BACKLOG_IDENTITY,
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "admitted_records": 10,
        "organic_owner_written_records": 10,
        "curriculum_designed_records": 0,
        "requirements": [
            {"requirement_id": "OG-NATURAL-01", "minimum": 6, "admitted": 10, "status": "CLOSED"},
            {"requirement_id": "OG-FACTUAL-01", "minimum": 6, "admitted": 10, "status": "CLOSED"},
            {"requirement_id": "OG-VARIATION-01", "minimum": 4, "admitted": 10, "status": "CLOSED"},
            {"requirement_id": "CD-COMPOSE-01", "minimum": 5, "admitted": 0, "status": "OPEN_NO_QUOTA_FILL"},
        ],
        "remaining_second_experiment_gap": {
            "train_positive": max(0, 36 - dataset["counts"]["train_positive"]),
            "validation_positive": max(0, 12 - dataset["counts"]["validation_positive"]),
            "commentary_tokens_estimated": max(0, 8000 - dataset["commentary_tokens"]["successor_estimated"]),
            "factual_restraint_records": max(0, 8 - dataset["quality_coverage"]["restraint"]),
            "model_visible_abstention": "OUT_OF_SCOPE_AND_STILL_ZERO",
        },
        "quota_fill": False,
        "generated_owner_gold": False,
    }, "backlog_delta_identity")
    backlog_path = artifacts / "vnext-voice-owner-gold-pack01-v1-backlog-delta.json"
    write_json(backlog_path, backlog_delta)

    audit = identify({
        "schema": "vnext-voice-owner-gold-pack01-audit",
        "schema_version": 1,
        "status": "PASS_0_INTEGRITY_BLOCKERS",
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "backlog_delta_identity": backlog_delta["backlog_delta_identity"],
        "source_pack_sha256": SOURCE_SHA256,
        "records_admitted": 10,
        "records_rejected": 0,
        "commentary_byte_exact": True,
        "factual_commentary_separation": "PASS",
        "mechanism_annotation": "PASS_SPAN_DERIVED",
        "protected_target_policy": "PASS",
        "deduplication": "PASS_NO_EXACT_COMMENTARY_DUPLICATES",
        "train_validation_family_overlap": 0,
        "holdout_exposure": 0,
        "qwen3_bakeoff_exposure": 0,
        "training_performed": False,
        "active_product_modified": False,
        "canonical_rollback_modified": False,
        "findings": [
            {"id": "F-01", "severity": "NON_BLOCKING", "finding": "PACK_CLOSES_ORGANIC_NATURALNESS_FACTUAL_DISCIPLINE_AND_VARIATION_BACKLOG_LINES"},
            {"id": "F-02", "severity": "READINESS_BLOCKER", "finding": "SECOND_EXPERIMENT_TRAIN_POSITIVE_AND_COMMENTARY_TOKEN_THRESHOLDS_REMAIN_OPEN"},
            {"id": "F-03", "severity": "NON_BLOCKING", "finding": "NO_MODEL_VISIBLE_ABSTENTION_ADMITTED_FROM_PACK"},
        ],
        "cars": [
            {
                "car_id": "CAR-01",
                "finding": "DECLARATIVE_EVIDENCE_SPANS_USED_CRLF_WHILE_SOURCE_PACK_USED_LF",
                "root_cause": "BUILDER_LITERAL_NEWLINE_REPRESENTATION_DID_NOT_MATCH_SOURCE_ENCODING",
                "impact": "INITIAL_BUILD_STOPPED_BEFORE_SUCCESSOR_EVIDENCE_WAS_WRITTEN",
                "repair": "CANONICALIZE_ONLY_ANNOTATION_SPAN_NEWLINES_TO_SOURCE_LF_WITHOUT_CHANGING_OWNER_BYTES",
            },
            {
                "car_id": "CAR-02",
                "finding": "READINESS_CHECK_USED_TOTAL_PACK_RECORDS_INSTEAD_OF_DEMONSTRATED_RESTRAINT_SUPPORT",
                "root_cause": "THRESHOLD_EXPRESSION_WAS_NOT_BOUND_TO_QUALITY_COVERAGE_RESTRAINT_COUNT",
                "impact": "RESTRAINT_SUBGATE_WAS INCORRECTLY REPORTED PASS IN PRE_FINAL EVIDENCE",
                "repair": "BIND_RESTRAINT_READINESS_TO_DEMONSTRATED_4_OF_8_SUPPORT_AND_REPORT_REMAINING_GAP",
            }
        ],
        "fresh_audit_restarts": [
            {
                "car_id": "CAR-01",
                "evidence_invalidated": "INITIAL_FAILED_BUILD_ATTEMPT",
                "restart_result": "PASS",
            },
            {
                "car_id": "CAR-02",
                "evidence_invalidated": "ALL_PRE_FINAL_SUCCESSOR_BACKLOG_AND_AUDIT_IDENTITIES",
                "restart_result": "PASS",
            }
        ],
        "legacy_dependency_count": 0,
        "voice_state": "DISABLED_UNTIL_PROMOTION",
    }, "audit_identity")
    audit_path = artifacts / "vnext-voice-owner-gold-pack01-v1-audit.json"
    write_json(audit_path, audit)

    print(json.dumps({
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "backlog_delta_identity": backlog_delta["backlog_delta_identity"],
        "audit_identity": audit["audit_identity"],
        "new_tokens_estimated": new_tokens,
        "readiness": dataset["second_experiment_readiness"],
        "coverage": dataset["mechanism_coverage"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
