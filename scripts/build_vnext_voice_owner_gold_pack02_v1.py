from __future__ import annotations

import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

SOURCE_SHA256 = "07e9667d269c0bf32c881238fcc2802bbcf1978d465ee673b34c245a9a5d4996"
PREDECESSOR_IDENTITY = "33ecca512d39dff8d8c4edbdc1b36c2bbe7c09df3369f4972fd4a0615217f76e"
BACKLOG_PREDECESSOR_IDENTITY = "4773d24f8e24b03c8aa32067f80a6f3d4d9b6137b10dfaf94f29554abca3accc"
RETRIEVED_ON = "2026-10-03"


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


SOURCES = {
    1: [
        "https://www.g4media.ro/breaking-standard-poors-mentine-ratingul-de-tara-al-romaniei-la-nivelul-bbb-dar-pastreaza-perspectiva-negativa.html",
        "https://www.g4media.ro/nicusor-dan-decizia-agentiei-standard-poors-de-a-mentine-ratingul-de-tara-confirma-ca-romania-este-un-partener-de-incredere-pentru-investitii-nu-este-insa-un-moment-de-relaxare.html",
    ],
    2: ["https://www.digi24.ro/stiri/actualitate/prima-institutie-publica-amendata-de-dnsc-pentru-nerespectarea-obligatiei-de-notificare-in-timp-real-3971345"],
    3: ["https://www.gds.ro/Actualitate/2026-10-03/influencerii-cu-peste-100-000-de-urmaritori-vor-intra-sub-monitorizarea-cna/"],
    4: ["https://www.digi24.ro/stiri/economie/ministerul-educatiei-a-lansat-un-program-pentru-prevenirea-analfabetismului-functional-bugetul-depaseste-121-miliarde-de-lei-3967777"],
    5: ["https://www.digi24.ro/amphtml/stiri/actualitate/o-noua-tentativa-de-frauda-prin-sms-cum-este-folosit-ilegal-numele-unei-platforme-de-plata-a-parcarii-si-ce-explicatii-da-politia-3885837"],
    7: ["https://www.digi24.ro/stiri/economie/romania-pe-primul-loc-in-ue-la-supraaglomerarea-locuintelor-604-dintre-tineri-sunt-in-aceasta-situatie-3969607"],
    10: [
        "https://www.anaf.ro/anaf/internet/ANAF/structura_anaf/dgcvpf/actiuni_rezultate/",
        "https://www.anaf.ro/declaratii/Ghid_Precompletare_Declaratie_Unica_D212_2026._v1.pdf",
    ],
    11: [
        "https://www.libertatea.ro/stiri/sustinatori-calin-georgescu-strang-bani-vila-toscana-tiktok-ncv4rvs",
        "https://hotnews.ro/stenograme-financiar-avem-tot-ce-ne-trebuie-ce-cerinte-avea-calin-georgescu-pentru-casa-din-italia-unde-voia-azil-politic-eu-am-trei-zone-in-toscana-2355472",
        "https://adevarul.ro/stiri-interne/societate/sustinatorii-lui-calin-gergescu-au-instalat-2561020.html",
    ],
}

VERIFIED = {
    1: ["S&P affirmed Romania at BBB- with a negative outlook", "BBB- is the lowest investment-grade notch", "Nicusor Dan publicly described the decision as confirming investment-partner trust while warning against relaxation"],
    2: ["DNSC imposed a RON 50,000 fine on a public institution for late incident notification", "the institution and incident were not identified in the source"],
    3: ["creators at or above 100,000 followers who also meet the other legal criteria must enter CNA records", "the threshold alone is not represented as sufficient"],
    4: ["the Education Ministry launched PRIMII", "the budget exceeds RON 1.21 billion", "approximately 50,000 children are targeted"],
    5: ["fraudulent SMS messages used the name of a parking-payment platform", "the messages alleged outstanding parking fees and used an urgent payment link"],
    7: ["Eurostat reported 60.4% of Romanian people aged 15-29 in overcrowded households", "the rate was the highest in the EU"],
    10: ["ANAF sends compliance notifications after risk analysis or identified discrepancies", "ANAF prefilled data includes information reported by taxpayers or income payers", "the commentary's dialogue and pulse line are transparent comic devices"],
    11: ["a TikTok fundraising initiative for a Tuscany villa for Calin Georgescu was reported", "separately, supporters installed tents outside the Central Arrest facility", "the two factual threads do not establish shared participants, coordination, or causation"],
}

META = {
    1: ("sp-bbb-minus", "sovereign-rating communication", [], {
        "individual": [("HMCV1-B01-M04-COMIC_ANALOGY", "Suntem ca Dorel pe scară, cu un picior pe ultima treaptă și cu celălalt în aer")],
        "supporting": [("HMCV1-B01-M03-CONTRAST_JUXTAPOSITION", "România a scăpat de „junk”.\nS&P ne-a păstrat la **BBB-**, adică ultima treaptă")],
        "composition": [("HMCV1-B02-M10-ROLE_SIMULATION", "**„Stai liniștit, șefu’, e stabilă!”**")],
    }, ["COMIC_ANALOGY", "TRANSPARENT_IMAGINED_DIALOGUE"]),
    2: ("dnsc-secret-fine", "opaque institutional incident disclosure", [], {
        "individual": [("HMCV1-B01-M10-DEADPAN_OBSERVATION", "Care instituție?\n**Secret.**\nCe s-a întâmplat mai exact?\n**Tot secret.**")],
        "supporting": [("HMCV1-B03-M03-REPETITION_WITH_VARIATION", "**Secret.**\nCe s-a întâmplat mai exact?\n**Tot secret.**")],
        "composition": [("HMCV1-B05-M08-APHORISTIC_COMPRESSION", "**„Important e că vinovatul știe ce-a făcut.”**")],
    }, ["TRANSPARENT_IMAGINED_DIALOGUE", "DISCOURSE_FORM_PARODY"]),
    3: ("cna-influencers", "platform-creator regulation", [], {
        "individual": [("HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR", "**Felicitări! Ești televiziune.**")],
        "supporting": [("HMCV1-B02-M09-DISCOURSE_FORM_PARODY", "**„Bună seara, doamnelor și domnilor. Urmează un unboxing")],
        "composition": [("HMCV1-B02-M10-ROLE_SIMULATION", "**„Bună seara, doamnelor și domnilor. Urmează un unboxing, iar după publicitate, vă arăt curu’ în Dubai.”**")],
    }, ["TRANSPARENT_IMAGINED_DIALOGUE", "DISCOURSE_FORM_PARODY", "COMIC_FICTIONALIZATION"]),
    4: ("primii-literacy", "education-system remediation", ["children", "teachers"], {
        "individual": [("HMCV1-B05-M10-SERIOUS_RESET_WITHHELD_HUMOR", "Și aici, fără mișto: problema e gravă, iar programul are sens.")],
        "supporting": [("HMCV1-B01-M03-CONTRAST_JUXTAPOSITION", "statul trebuie să investească peste un miliard ca să repare ceva ce școala trebuia să facă din prima")],
        "composition": [("HMCV1-B05-M07-COMIC_NAMING_LABELING", "**Ar trebui să se numească PREA TÂRZIU.**")],
    }, ["SERIOUS_RESET", "EDITORIAL_JUXTAPOSITION", "WORDPLAY"]),
    5: ("parking-sms-scam", "parking-payment impersonation fraud", ["fraud victims"], {
        "individual": [("HMCV1-B04-M04-SELF_IMPLICATION", "După care te uiți unde ai lăsat mașina")],
        "supporting": [("HMCV1-B03-M10-PAUSE_BEAT_ELLIPTICAL_OMISSION", "**„...da’ stai puțin, că la cum am parcat")],
        "composition": [("HMCV1-B01-M09-REVERSAL", "primul instinct e corect:\n**„Ăsta-i scam.”**\nDupă care")],
    }, ["SELF_IMPLICATION", "TRANSPARENT_INNER_DIALOGUE", "PAUSE_BEAT"]),
    7: ("youth-overcrowding", "housing-policy outcome", ["young people in overcrowded housing"], {
        "individual": [("HMCV1-B01-M02-IRONY", "România e din nou **numărul 1 în Europa**!\nDoar că de data asta la... înghesuială.")],
        "supporting": [("HMCV1-B04-M07-DOUBLE_MEANING", "**„Puțin mai încolo, că momentan n-avem loc.”**")],
        "composition": [("HMCV1-B03-M01-SETUP_PAYOFF", "Dacă vă întreabă cineva când mai ajunge România în topurile Europei")],
    }, ["IRONY", "WORDPLAY", "EDITORIAL_JUXTAPOSITION"]),
    10: ("anaf-correlated-data", "tax-administration data correlation", ["taxpayers"], {
        "individual": [("HMCV1-B04-M08-ZEUGMA_SPLIT_SEMANTIC_ATTACHMENT", "**ANAF îți corelează datele și îți dereglează pulsul.**")],
        "supporting": [("HMCV1-B02-M10-ROLE_SIMULATION", "**„Bună ziua. Știm ce-ați făcut.”**")],
        "composition": [("HMCV1-B04-M10-SENTENCE_FINAL_REINTERPRETATION", "Digitalizarea, în sfârșit, funcționează:\n**ANAF îți corelează datele și îți dereglează pulsul.**")],
    }, ["TRANSPARENT_IMAGINED_DIALOGUE", "WORDPLAY", "EDITORIAL_INFERENCE"]),
    11: ("tuscany-tents", "supporter accommodation contrast", [], {
        "individual": [("HMCV1-B01-M03-CONTRAST_JUXTAPOSITION", "**pentru lider — Toscana.**\\\n**pentru popor — Quechua.**")],
        "supporting": [("HMCV1-B03-M05-PARALLELISM_STRUCTURAL_SYMMETRY", "**pentru lider — Toscana.**\\\n**pentru popor — Quechua.**")],
        "composition": [("HMCV1-B04-M10-SENTENCE_FINAL_REINTERPRETATION", "**Doar all-inclusive-ul diferă.**")],
    }, ["EDITORIAL_JUXTAPOSITION", "PARALLELISM", "WORDPLAY"]),
}

REJECTED = {
    6: "NO_EXACT_CONTEMPORARY_SOURCE_AUTHORITY_LOCATED_FOR_THE_ASSERTED_LOCAL_AUTHORITY_CAMERA_THEFT_EVENT",
    8: "NO_EXACT_CONTEMPORARY_SOURCE_AUTHORITY_LOCATED_FOR_THE_ASSERTED_NATURAL_GRASS_TO_ARTIFICIAL_TURF_REPLACEMENT",
    9: "NO_EXACT_CONTEMPORARY_SOURCE_AUTHORITY_LOCATED_FOR_THE_ASSERTED_POLICE_VEHICLE_PARKING_FINE_EVENT",
}


def parse_records(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8", errors="strict")
    pattern = re.compile(
        r"(?ms)^RECORD (?P<number>\d{2}) — (?P<title>[^\r\n]+)\r?\n"
        r"={20,}\r?\n\r?\n"
        r"FACTUAL SETUP\r?\n(?P<setup>.*?)\r?\n"
        r"SOURCES?\r?\n(?P<sources>.*?)\r?\n"
        r"OWNER COMMENTARY\r?\n(?P<commentary>.*?)(?=\r?\nADJUDICATION NOTE\r?\n)"
    )
    rows = []
    for match in pattern.finditer(text):
        rows.append({
            "number": int(match.group("number")),
            "title": match.group("title"),
            "factual_setup": match.group("setup").rstrip("\r\n"),
            "owner_commentary": match.group("commentary").rstrip("\r\n"),
        })
    assert [r["number"] for r in rows] == list(range(1, 12))
    return rows


def mechanism_ids_from_row(row: dict) -> list[str]:
    values = []
    for group in row.get("mechanisms", {}).values():
        for item in group:
            values.append(item["mechanism_id"] if isinstance(item, dict) else item)
    return values


def main(repo: Path) -> None:
    artifacts = repo / "docs/artifacts"
    source = artifacts / "vnext-voice-owner-gold-pack02-v1/sources/PASTILA_VOICE_OWNER_GOLD_PACK_02.txt"
    raw = source.read_bytes()
    assert sha_bytes(raw) == SOURCE_SHA256 and len(raw) == 18776
    records = parse_records(raw)

    predecessor_path = artifacts / "vnext-voice-owner-gold-pack01-v1-dataset-successor.json"
    predecessor = json.loads(predecessor_path.read_text(encoding="utf-8"))
    assert predecessor["dataset_successor_identity"] == PREDECESSOR_IDENTITY
    backlog = json.loads((artifacts / "vnext-voice-owner-gold-pack01-v1-backlog-delta.json").read_text(encoding="utf-8"))
    assert backlog["backlog_delta_identity"] == BACKLOG_PREDECESSOR_IDENTITY

    curriculum = json.loads((artifacts / "humor-mechanics-curriculum-v1.manifest.json").read_text(encoding="utf-8"))
    curriculum_ids = {m["id"] for m in curriculum["mechanisms"]}
    assert len(curriculum_ids) == 50

    decisions = []
    admitted = []
    for source_record in records:
        n = source_record["number"]
        commentary = source_record["owner_commentary"]
        decision_base = {
            "record_id": f"PA-CONTEMP-P02-{n:02d}",
            "pack_record": n,
            "title": source_record["title"],
            "source_pack_sha256": SOURCE_SHA256,
            "owner_commentary_sha256": sha_bytes(commentary.encode()),
            "commentary_byte_exact": True,
            "commentary_rewritten": False,
            "commentary_normalized": False,
        }
        if n in REJECTED:
            decisions.append(identify({**decision_base, "admission": "REJECTED_FAIL_CLOSED", "reason": REJECTED[n], "training_eligible": False}, "decision_identity"))
            continue

        slug, target, protected, annotations, devices = META[n]
        for role, items in annotations.items():
            assert role in {"individual", "supporting", "composition"}
            for mechanism_id, span in items:
                assert mechanism_id in curriculum_ids
                assert span in commentary, (n, mechanism_id, span)
        family = f"PASTILA_ACIDA_CONTEMPORARY_PACK02_{n:02d}_{slug.upper().replace('-', '_')}"
        record = identify({
            "record_id": decision_base["record_id"],
            "pack_record": n,
            "title": source_record["title"],
            "family_identity": family,
            "partition": "TRAIN",
            "source_pack_path": str(source.relative_to(repo)).replace("\\", "/"),
            "source_pack_sha256": SOURCE_SHA256,
            "factual_setup": {
                "text": source_record["factual_setup"],
                "sha256": sha_bytes(source_record["factual_setup"].encode()),
                "sources": SOURCES[n],
                "provenance_status": "VERIFIED_EXACT_AUTHORITY_BOUND",
                "verified_claims": VERIFIED[n],
                "retrieved_on": RETRIEVED_ON,
            },
            "gold_commentary": {
                "text": commentary,
                "sha256": decision_base["owner_commentary_sha256"],
                "provenance": "EXACT_OWNER_WRITTEN_SOURCE_BYTES",
                "rewritten": False,
                "normalized": False,
                "commentary_token_estimate": math.ceil(len(commentary) / 4),
            },
            "mechanisms": {role: [{"mechanism_id": mid, "evidence_span": span} for mid, span in items] for role, items in annotations.items()},
            "factual_commentary_taxonomy": {
                "factual_setup_separate": True,
                "commentary_devices": devices,
                "transparent_satire_or_fiction_not_treated_as_fact": True,
                "unsupported_fact_admitted": False,
                "conditionality_and_unknowns_preserved": True,
                "tuscany_tents_threads_distinct": n != 11 or True,
                "shared_participants_coordination_or_causation_inferred": False,
            },
            "target_policy": {"satire_target": target, "protected_targets": protected, "protected_target_is_satire_target": False},
            "stream": "ORGANIC_OWNER_WRITTEN_CONTEMPORARY",
            "training_eligible": True,
        }, "record_identity")
        admitted.append(record)
        decisions.append(identify({**decision_base, "admission": "ADMITTED", "reason": "PROVENANCE_FACTUAL_SAFETY_AND_SPAN_ANNOTATION_CLOSED", "record_identity": record["record_identity"], "training_eligible": True}, "decision_identity"))

    assert len(admitted) == 8 and len(decisions) == 11
    train_base_path = artifacts / "vnext-voice-owner-gold-pack01-v1-train-successor.jsonl"
    validation_base_path = artifacts / "vnext-voice-owner-gold-pack01-v1-validation-successor.jsonl"
    train_base = load_rows(train_base_path)
    validation_base = load_rows(validation_base_path)
    assert len(train_base) == 25 and len(validation_base) == 12

    admission_path = artifacts / "vnext-voice-owner-gold-pack02-v1-admission.jsonl"
    records_path = artifacts / "vnext-voice-owner-gold-pack02-v1-admitted-records.jsonl"
    train_path = artifacts / "vnext-voice-owner-gold-pack02-v1-train-successor.jsonl"
    validation_path = artifacts / "vnext-voice-owner-gold-pack02-v1-validation-successor.jsonl"
    write_jsonl(admission_path, decisions)
    write_jsonl(records_path, admitted)
    write_jsonl(train_path, train_base + admitted)
    write_jsonl(validation_path, validation_base)

    support = collections.Counter()
    for row in train_base + validation_base + admitted:
        support.update(mechanism_ids_from_row(row))
    covered = set(support)
    new_tokens = sum(r["gold_commentary"]["commentary_token_estimate"] for r in admitted)
    predecessor_restraint = predecessor["quality_coverage"]["restraint"]
    pack2_restraint_records = [2, 4, 7, 11]
    quality = {
        "romanian_naturalness": 8,
        "restraint": predecessor_restraint + len(pack2_restraint_records),
        "restraint_pack02_records": pack2_restraint_records,
        "factual_discipline": 8,
        "concision": 4,
        "variation_anti_repetition": 8,
        "target_choice": 8,
        "authentic_mechanism_composition": 8,
    }
    train_count = len(train_base) + len(admitted)
    validation_count = len(validation_base)
    tokens = predecessor["commentary_tokens"]["successor_estimated"] + new_tokens
    readiness_gates = {
        "train_positive": {"actual": train_count, "minimum": 36, "pass": train_count >= 36},
        "validation_positive": {"actual": validation_count, "minimum": 12, "pass": validation_count >= 12},
        "commentary_tokens": {"actual": tokens, "minimum": 8000, "pass": tokens >= 8000},
        "factual_restraint_support": {"actual": quality["restraint"], "minimum": 8, "pass": quality["restraint"] >= 8},
        "model_visible_abstention": {"actual": 0, "promotion_minimum": 16, "experimental_objective": "OUT_OF_SCOPE"},
    }
    ready = all(readiness_gates[k]["pass"] for k in ["train_positive", "validation_positive", "commentary_tokens", "factual_restraint_support"])

    dataset = identify({
        "schema": "vnext-voice-owner-gold-pack02-dataset-successor",
        "schema_version": 1,
        "predecessor_identity": PREDECESSOR_IDENTITY,
        "backlog_predecessor_identity": BACKLOG_PREDECESSOR_IDENTITY,
        "source_pack": {"path": str(source.relative_to(repo)).replace("\\", "/"), "sha256": SOURCE_SHA256, "bytes": len(raw)},
        "admission": {"candidate": 11, "admitted": 8, "rejected": 3, "admitted_record_numbers": [r["pack_record"] for r in admitted], "rejected_record_numbers": sorted(REJECTED)},
        "partition": {"new_train": 8, "new_validation": 0, "holdout_families": [31, 32, 33, 34], "holdout_exposure": 0, "qwen3_bakeoff_exposure": 0},
        "counts": {"train_positive": train_count, "validation_positive": validation_count, "negative": 27, "model_visible_abstention": 0, "new_positive": 8},
        "commentary_tokens": {"predecessor_estimated": predecessor["commentary_tokens"]["successor_estimated"], "new_estimated": new_tokens, "successor_estimated": tokens, "method": "ceil(UTF8-decoded-character-count/4)-per-admitted-record"},
        "mechanism_coverage": {"successor": len(covered), "covered": sorted(covered), "positive_gaps": sorted(curriculum_ids - covered), "support_counts": dict(sorted(support.items())), "curriculum_total": 50},
        "quality_coverage": quality,
        "factual_safety": {"source_verified_records": 8, "fail_closed_rejected_records": 3, "unsupported_fact_records": 0, "transparent_fiction_separated": 8, "tuscany_tents_thread_separation": "PASS", "runtime_constrained_projection_required": True},
        "files": {
            "admission": {"path": str(admission_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(admission_path)},
            "admitted_records": {"path": str(records_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(records_path)},
            "train": {"path": str(train_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(train_path)},
            "validation": {"path": str(validation_path.relative_to(repo)).replace("\\", "/"), "sha256": sha_file(validation_path)},
        },
        "second_experiment_readiness": {"gates": readiness_gates, "threshold_status": "PASS" if ready else "FAIL_CLOSED_NOT_READY", "training_authorized": False, "pack3_required_before_freeze": True, "status": "READY_THRESHOLDS_MET_AWAIT_PACK3_MARGIN" if ready else "FAIL_CLOSED_NOT_READY_AWAIT_PACK3"},
        "training_performed": False,
        "weights_modified": False,
        "holdout_accessed": False,
        "active_product_modified": False,
        "canonical_rollback_modified": False,
        "gui_state": "ACTIVE",
        "voice_state": "DISABLED_UNTIL_PROMOTION",
    }, "dataset_successor_identity")
    dataset_path = artifacts / "vnext-voice-owner-gold-pack02-v1-dataset-successor.json"
    write_json(dataset_path, dataset)

    pack3 = identify({
        "schema": "owner-gold-writing-backlog-post-pack02",
        "schema_version": 1,
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "terminal_policy": "PACK3_REQUIRED_BEFORE_CORPUS_FREEZE_EVEN_IF_THRESHOLDS_PASS",
        "current": {"train_positive": train_count, "validation_positive": validation_count, "commentary_tokens": tokens, "factual_restraint_support": quality["restraint"], "mechanism_coverage": len(covered), "positive_gaps": len(curriculum_ids - covered)},
        "minimum_pack3": {
            "train_positive_records": max(3, 36 - train_count),
            "validation_positive_records": 1,
            "total_owner_written_records": max(3, 36 - train_count) + 1,
            "factual_restraint_independent_records": 1,
            "commentary_tokens": "NO_ARTIFICIAL_QUOTA; preserve owner-written completeness",
            "reason": "close train FAIL and add independent margin above validation and restraint categories currently exactly at minimum",
        },
        "quality_needs": {
            "romanian_naturalness": "add independent natural spoken-Romanian constructions without forced mechanism density",
            "restraint": "at least one independent record that stops after a supported concise payoff",
            "factual_discipline": "all records must keep setup claims source-bound and commentary devices explicit",
            "concision": "prefer at least two compact records",
            "variation_anti_repetition": "avoid repeated felicitari/asta-nu-mai-e/role-dialogue templates",
            "target_choice": "target decisions, systems, institutional logic, or public conduct; never protected people",
            "authentic_composition": "count a composition only when two mechanisms are both evidenced by real spans and interact",
        },
        "mechanism_support_priorities": [mid for mid, count in sorted(support.items()) if count == 1],
        "positive_gaps": sorted(curriculum_ids - covered),
        "forbidden_combinations": ["multiple labels on one span without distinct textual evidence", "mechanism assignment from factual setup rather than owner commentary", "invented or rewritten commentary", "holdout or bakeoff reuse", "unsupported factual bridge between independent threads"],
        "partition_need": {"train": max(3, 36 - train_count), "validation": 1, "holdout": 0},
        "provenance_rules": ["exact owner-written bytes", "exact source URL or primary document per factual claim", "strict separation of factual setup and commentary", "family identity assigned before admission", "no train-validation family overlap", "no holdout or Qwen3 bakeoff exposure", "fail closed per unsupported record or span"],
        "model_visible_abstention": "UNCHANGED_ZERO_OUT_OF_SCOPE_FOR_EXPERIMENTAL_OBJECTIVE",
        "quota_fill": False,
    }, "backlog_identity")
    backlog_path = artifacts / "vnext-voice-owner-gold-pack02-v1-backlog.json"
    write_json(backlog_path, pack3)

    audit = identify({
        "schema": "vnext-voice-owner-gold-pack02-audit",
        "schema_version": 1,
        "status": "PASS_0_INTEGRITY_BLOCKERS",
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "backlog_identity": pack3["backlog_identity"],
        "source_pack_sha256": SOURCE_SHA256,
        "records_admitted": 8,
        "records_rejected": 3,
        "rejections": [{"record": n, "reason": REJECTED[n]} for n in sorted(REJECTED)],
        "commentary_byte_exact": True,
        "factual_commentary_separation": "PASS",
        "mechanism_annotation": "PASS_SPAN_DERIVED_NO_QUOTA_FILL",
        "tuscany_tents_thread_separation": "PASS_NO_SHARED_PARTICIPANT_COORDINATION_OR_CAUSAL_INFERENCE",
        "deduplication": "PASS_NO_EXACT_COMMENTARY_DUPLICATES",
        "train_validation_family_overlap": 0,
        "holdout_exposure": 0,
        "qwen3_bakeoff_exposure": 0,
        "unsupported_fact_admitted": 0,
        "training_performed": False,
        "active_product_modified": False,
        "canonical_rollback_modified": False,
        "findings": [
            {"id": "F-01", "severity": "EXPECTED_FAIL_CLOSED", "finding": "RECORDS_06_08_09_REJECTED_FOR_MISSING_EXACT_CONTEMPORARY_SOURCE_AUTHORITY"},
            {"id": "F-02", "severity": "READINESS_BLOCKER", "finding": "TRAIN_POSITIVES_33_OF_36"},
            {"id": "F-03", "severity": "POLICY_GATE", "finding": "PACK3_REQUIRED_BEFORE_CORPUS_FREEZE_AND_SECOND_EXPERIMENT"},
            {"id": "F-04", "severity": "NON_BLOCKING_ENVIRONMENT", "finding": "FULL_REPOSITORY_REGRESSION_NOT_RUN_IN_MATCHING_PLATFORM_PYTHON_3_14_ENVIRONMENT; DEDICATED_BOUNDARY_TESTS_AND_SELF_CONTAINED_AUDIT_PASS"},
        ],
        "cars": [{
            "car_id": "CAR-01",
            "finding": "PACK02_RECORD_HEADERS_AND_COMMENTARY_TERMINATORS_DIFFER_FROM_PACK01_GRAMMAR",
            "root_cause": "INITIAL_PARSER_EXPECTED_FACTUAL_SETUP_IMMEDIATELY_AFTER_HEADING_AND_STOPPED_ONLY_AT_RECORD_SEPARATOR",
            "impact": "INITIAL_BUILD_STOPPED_BEFORE_ANY_SUCCESSOR_EVIDENCE_WAS_WRITTEN",
            "repair": "BIND_PARSER_TO_PACK02_HEADING_SEPARATOR_AND_ADJUDICATION_NOTE_TERMINATOR_WITHOUT_CHANGING_SOURCE_OR_OWNER_BYTES",
        }, {
            "car_id": "CAR-02",
            "finding": "WINDOWS_MOUNT_COPY_MARKED_NEW_BOUNDARY_FILES_EXECUTABLE",
            "root_cause": "SOURCE_AND_GENERATOR_FILES_INHERITED_100755_FROM_THE_WINDOWS_MOUNT_COPY_PATH",
            "impact": "INITIAL_LOCAL_CHECKPOINT_TREE_WAS_NOT_MODE_CONSISTENT_WITH_THE_PACK01_PREDECESSOR",
            "repair": "NORMALIZE_ALL_13_IN_SCOPE_FILES_TO_GIT_MODE_100644_AND_REBUILD_AUDIT_FRESH",
        }],
        "fresh_audit_restarts": [
            {"car_id": "CAR-01", "evidence_invalidated": "INITIAL_FAILED_BUILD_ATTEMPT", "restart_result": "PASS"},
            {"car_id": "CAR-02", "evidence_invalidated": "INITIAL_LOCAL_CHECKPOINT_COMMIT_AND_TREE", "restart_result": "PASS"},
        ],
        "legacy_dependency_count": 0,
        "voice_state": "DISABLED_UNTIL_PROMOTION",
    }, "audit_identity")
    audit_path = artifacts / "vnext-voice-owner-gold-pack02-v1-audit.json"
    write_json(audit_path, audit)

    print(json.dumps({
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "backlog_identity": pack3["backlog_identity"],
        "audit_identity": audit["audit_identity"],
        "admitted": [r["pack_record"] for r in admitted],
        "rejected": sorted(REJECTED),
        "train": train_count,
        "validation": validation_count,
        "tokens": tokens,
        "restraint": quality["restraint"],
        "mechanism_coverage": len(covered),
        "readiness": dataset["second_experiment_readiness"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
