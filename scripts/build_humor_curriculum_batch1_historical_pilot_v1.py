"""Build the read-only Batch 1 historical curriculum evidence pilot.

The builder consumes only the existing owner-final Voice-ready ledger and its
byte-exact local corpus files. It does not generate, rewrite, repair, enrich, or
promote commentary and it grants no training or runtime authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LEDGER = (
    ROOT
    / ".pastilaacida-voice-lora-v1-commentary-adjudication-v1-evidence"
    / "voice-ready-ledger.json"
)
CURRICULUM_MANIFEST = (
    ROOT / "docs" / "artifacts" / "humor-mechanics-curriculum-v1.manifest.json"
)
OUTPUT = (
    ROOT
    / ".humor-mechanics-curriculum-v1-batch1-historical-pilot-v1-evidence"
)

MECHANISMS = {
    "sarcasm": "HMCV1-B01-M01-SARCASM",
    "irony": "HMCV1-B01-M02-IRONY",
    "contrast": "HMCV1-B01-M03-CONTRAST_JUXTAPOSITION",
    "analogy": "HMCV1-B01-M04-COMIC_ANALOGY",
    "frame": "HMCV1-B01-M05-FRAME_TRANSFER",
    "hyperbole": "HMCV1-B01-M06-HYPERBOLE",
    "understatement": "HMCV1-B01-M07-UNDERSTATEMENT",
    "escalation": "HMCV1-B01-M08-ESCALATION",
    "reversal": "HMCV1-B01-M09-REVERSAL",
    "deadpan": "HMCV1-B01-M10-DEADPAN_OBSERVATION",
}

OWNER_ADJUDICATION = {
    "status": "OWNER_APPROVED_AND_FROZEN",
    "decision_date": "2026-08-25",
    "scope": "HISTORICAL_CURRICULUM_EVIDENCE_ONLY",
    "decisions": {
        "HMCV1-B1-PILOT-ORQ-001": {
            "decision": "APPROVED_AS_RECOMMENDED",
            "resolution": "story-v1:29:06 is DOMINANT Sarcasm with ALLEGATION_TO_FACT and NOT_ADJUDICATED warnings; story-v1:30:02 is SUPPORTING Sarcasm with Irony dominant.",
        },
        "HMCV1-B1-PILOT-ORQ-002": {
            "decision": "APPROVED_AS_RECOMMENDED",
            "resolution": "All three Understatement annotations remain SUPPORTING; no dominant historical Understatement example was found.",
        },
        "HMCV1-B1-PILOT-ORQ-003": {
            "decision": "APPROVED_AS_RECOMMENDED",
            "resolution": "The three Deadpan annotations remain DELIVERY; no clean dominant historical Deadpan example was found.",
        },
        "HMCV1-B1-PILOT-ORQ-004": {
            "decision": "APPROVED_AS_RECOMMENDED",
            "resolution": "story-v1:32:01 is DOMINANT Frame Transfer; story-v1:32:06 is SUPPORTING Frame Transfer with Escalation dominant; story-v1:33:05 is DOMINANT Contrast and not independent Frame Transfer evidence.",
        },
        "HMCV1-B1-PILOT-ORQ-005": {
            "decision": "APPROVED_AS_RECOMMENDED",
            "resolution": "story-v1:29:06, story-v1:31:04, and story-v1:31:06 remain byte-exact historical mechanism evidence with all warnings preserved; narrower-span recovery is not authorized.",
        },
        "HMCV1-B1-PILOT-ORQ-006": {
            "decision": "APPROVED_AS_RECOMMENDED",
            "resolution": "The 13-record annotation baseline is frozen as historical curriculum evidence only with genuine gaps, roles, provenance, spans, and warnings preserved.",
        },
    },
    "current_authority_eligible": False,
    "training_eligible": False,
    "runtime_eligible": False,
    "further_recovery_authorized": False,
    "synthetic_enrichment_authorized": False,
    "integration_authorized": False,
}


SELECTIONS = {
    "candidate-story-v2:25:05": {
        "domains": ["CONSUMER_PRODUCT_SERVICE", "PUBLIC_AUTHORITY"],
        "annotations": [
            ("hyperbole", "DOMINANT", "The quantity is amplified through apocalypse supplies and resale fantasy."),
            ("escalation", "COMPOSITION", "Question, scale, apocalypse, and invented resale scene increase pressure."),
        ],
        "compatibility": "INCOMPATIBLE_FACTUAL_RECAP",
        "negative": ["FACTUAL_PARAPHRASE_OR_RECAP", "INVENTED_QUOTATION_OR_ROLE_KNOWLEDGE"],
        "review": "Hyperbole is clear, but the full historical span repeats the quantity and invents dialogue; retain as historical evidence only.",
    },
    "story-v1:29:05": {
        "domains": ["TECHNOLOGY", "CONSUMER_PRODUCT_SERVICE"],
        "annotations": [
            ("analogy", "DOMINANT", "Billing instability is mapped to quantum physics and server burnout."),
            ("irony", "SUPPORTING", "The explanation is reframed as evidence of the system contradiction."),
            ("deadpan", "DELIVERY", "The final burnout line lands with compressed dry delivery."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": [],
        "review": "Same-event factual authority is not frozen in the source ledger; annotate mechanism only, not current training compatibility.",
    },
    "story-v1:29:06": {
        "domains": ["PUBLIC_AUTHORITY", "PUBLIC_COMMUNICATION"],
        "annotations": [
            ("sarcasm", "DOMINANT", "Salary is treated as a mere recommendation to criticize alleged corruption."),
            ("irony", "SUPPORTING", "The law-enforcement role is placed against alleged conduct."),
            ("escalation", "COMPOSITION", "The passage develops from pay to institutional legitimacy and public cynicism."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": ["ALLEGATION_TO_FACT"],
        "review": "Owner review must decide whether this is acceptable mechanism evidence despite categorical phrasing around allegation-sensitive conduct.",
    },
    "story-v1:30:02": {
        "domains": ["EDUCATION", "PUBLIC_AUTHORITY"],
        "annotations": [
            ("irony", "DOMINANT", "A discussion about phones in education is contrasted with the official's phone attention."),
            ("sarcasm", "SUPPORTING", "The narrator charitably imagines important phone activity."),
            ("understatement", "SUPPORTING", "The faux-charitable possibilities minimize the visible contradiction."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": [],
        "review": "Mechanism evidence is strong; current factual compatibility remains unadjudicated because the reusable authority binding is absent.",
    },
    "story-v1:30:07": {
        "domains": ["PUBLIC_AUTHORITY", "EDUCATION"],
        "annotations": [
            ("hyperbole", "DOMINANT", "Bank financing and authenticity certificates magnify the price absurdity."),
            ("contrast", "SUPPORTING", "The amount is placed against the ordinary object and educational purpose."),
            ("analogy", "SUPPORTING", "The object is reframed through banking and luxury authenticity."),
            ("escalation", "COMPOSITION", "Repetition of the amount develops into increasingly elevated comparisons."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": ["FACTUAL_PARAPHRASE_OR_RECAP"],
        "review": "The historical surface prominently repeats a factual amount and is not eligible for current commentary training without separate adjudication.",
    },
    "story-v1:30:09": {
        "domains": ["SCIENCE_HEALTH_COMMUNICATION"],
        "annotations": [
            ("irony", "DOMINANT", "Long familiarity with nicotine is contrasted with incomplete scientific understanding."),
            ("escalation", "COMPOSITION", "Generational and historical scale develops before the cautionary landing."),
        ],
        "compatibility": "INCOMPATIBLE_FACTUAL_RECAP",
        "negative": ["FACTUAL_PARAPHRASE_OR_RECAP", "INVENTED_QUOTATION_OR_ROLE_KNOWLEDGE"],
        "review": "Retain as historical irony evidence; the span repeats scientific claims and invents a researcher quotation.",
    },
    "story-v1:31:04": {
        "domains": ["PUBLIC_AUTHORITY", "SCIENCE_HEALTH_COMMUNICATION"],
        "annotations": [
            ("reversal", "DOMINANT", "The closing proposes reversing enforcement and diagnosis order."),
            ("irony", "SUPPORTING", "The expected helping role is contrasted with the described intervention."),
            ("understatement", "SUPPORTING", "Diagnosis is called the boring part after the forceful response."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": ["FACTUAL_PARAPHRASE_OR_RECAP", "PROTECTED_SUBJECT_OR_WRONG_TARGET"],
        "review": "Owner review must confirm target discipline and whether the medical subject supports this historical mechanism evidence.",
    },
    "story-v1:31:05": {
        "domains": ["CONSUMER_PRODUCT_SERVICE"],
        "annotations": [
            ("analogy", "DOMINANT", "Delays and promises are mapped to a VIP all-inclusive service package."),
            ("contrast", "SUPPORTING", "The package abundance is placed against the missing car."),
            ("understatement", "SUPPORTING", "The missing central deliverable is introduced as the one excluded item."),
            ("deadpan", "DELIVERY", "The final short sentence supplies a dry landing."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": [],
        "review": "Strong multi-mechanism historical evidence; current authority compatibility remains unadjudicated.",
    },
    "story-v1:31:06": {
        "domains": ["PUBLIC_COMMUNICATION", "PUBLIC_AUTHORITY"],
        "annotations": [
            ("irony", "DOMINANT", "An official explanation is presented as increasing rather than resolving uncertainty."),
            ("contrast", "SUPPORTING", "Simple official wording is placed against growing public suspicion."),
        ],
        "compatibility": "INCOMPATIBLE_UNSUPPORTED_CAUSALITY_INTENT_OR_STATUS",
        "negative": ["UNSUPPORTED_CAUSALITY_OR_INTENT", "FACTUAL_PARAPHRASE_OR_RECAP"],
        "review": "The historical line about secrecy and hiding risks turning uncertainty into insinuation; keep only as review evidence.",
    },
    "story-v1:32:01": {
        "domains": ["PUBLIC_AUTHORITY", "ORDINARY_HARMLESS_FRUSTRATION"],
        "annotations": [
            ("frame", "DOMINANT", "The event is recast as a fictional pawn-shop dialogue."),
            ("escalation", "COMPOSITION", "Successive questions reveal the institutional ownership at the end."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": ["INVENTED_QUOTATION_OR_ROLE_KNOWLEDGE", "FICTION_THAT_SOUNDS_FACTUAL"],
        "review": "Owner review must confirm that explicit fiction marking is sufficient and that the reenactment is not mistaken for real dialogue.",
    },
    "story-v1:32:06": {
        "domains": ["PUBLIC_AUTHORITY", "CONSUMER_PRODUCT_SERVICE"],
        "annotations": [
            ("escalation", "DOMINANT", "Souvenir examples accumulate into a licensing and personality-cult conclusion."),
            ("frame", "SUPPORTING", "The public institution is recast through a souvenir-store and licensing frame."),
            ("analogy", "SUPPORTING", "Political personalization is mapped to commercial brand licensing."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": ["INVENTED_QUOTATION_OR_ROLE_KNOWLEDGE", "FACTUAL_PARAPHRASE_OR_RECAP"],
        "review": "The span mixes satire, invented dialogue, and factual claims; retain for mechanism audit, not current training.",
    },
    "story-v1:33:05": {
        "domains": ["TECHNOLOGY", "PUBLIC_AUTHORITY"],
        "annotations": [
            ("contrast", "DOMINANT", "Large-scale cyber capability is juxtaposed with a mundane water-pressure failure."),
            ("hyperbole", "SUPPORTING", "National technical power is compressed into an exaggerated domestic scene."),
            ("escalation", "COMPOSITION", "The passage moves from capability inventory to domestic dialogue and a final language joke."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": ["INVENTED_QUOTATION_OR_ROLE_KNOWLEDGE"],
        "review": "Strong contrast evidence, but the invented dialogue and absent authority binding block current compatibility.",
    },
    "story-v1:33:06": {
        "domains": ["MEDIA_INFORMATION", "SCIENCE_HEALTH_COMMUNICATION"],
        "annotations": [
            ("contrast", "DOMINANT", "Opposed internet labels are contrasted with the overlooked nutritional label."),
            ("irony", "SUPPORTING", "The truth is said to be in the middle and then located literally on the label."),
            ("deadpan", "DELIVERY", "The label landing is followed by a dry question about whether anyone reads it."),
        ],
        "compatibility": "NOT_ADJUDICATED",
        "negative": [],
        "review": "Mechanism evidence is defensible; current same-event authority is not frozen in the source ledger.",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def syntactic_metadata(text: str) -> dict[str, object]:
    stripped = text.strip()
    sentence_count = len(re.findall(r"[.!?]+(?:\s|$)", stripped))
    if "—" in text or "\n—" in text or "\r\n—" in text:
        surface = "DIALOGUE"
    elif text.count("?") >= 2:
        surface = "QUESTION"
    elif len([line for line in text.splitlines() if line.strip()]) >= 6:
        surface = "PROSE"
    else:
        surface = "PROSE"
    if text.count("?") >= 2:
        shape = "INTERROGATIVE"
    elif len(text.splitlines()) >= 8:
        shape = "MIXED"
    else:
        shape = "COMPOUND"
    if re.search(r"\b(eu|îmi|mi-|mine)\b", text.lower()):
        person = "FIRST_SINGULAR"
    elif re.search(r"\b(vă|voi|știți|credeți)\b", text.lower()):
        person = "SECOND"
    else:
        person = "THIRD"
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    return {
        "sentence_shape": shape,
        "person": person,
        "cadence": "MIXED" if len(text.splitlines()) >= 6 else "LONG_TO_SHORT",
        "turn_position": "DISTRIBUTED" if len(text.splitlines()) >= 6 else "SENTENCE_FINAL",
        "surface_form": surface,
        "word_count": len(words),
        "sentence_count": max(sentence_count, 1),
        "romanian_naturalness": "NOT_ADJUDICATED",
    }


def attractors(record_id: str, text: str) -> list[dict[str, object]]:
    lowered = text.lower()
    rules = [
        ("LEXICAL_ATTRACTOR", "BAI_OPENING", r"^băi"),
        ("LEXICAL_ATTRACTOR", "PRACTIC_MARKER", r"\bpractic\b"),
        ("SYNTACTIC_ATTRACTOR", "RHETORICAL_QUESTION_CHAIN", r"\?[^?]{0,180}\?"),
        ("FRAME_ATTRACTOR", "FICTIONAL_DIALOGUE", r"—|a zis|au zis"),
        ("FRAME_ATTRACTOR", "SERVICE_PACKAGE", r"vip|all inclusive|pachet"),
        ("CADENCE_ATTRACTOR", "FRAGMENT_LIST", r"(?:\r?\n){2}[^\r\n]{1,24}(?:\r?\n){2}"),
    ]
    found = []
    for category, signature, pattern in rules:
        if re.search(pattern, lowered, flags=re.MULTILINE | re.DOTALL):
            found.append(
                {
                    "category": category,
                    "signature": signature,
                    "scope": "PILOT_RECORD",
                    "severity": "REVIEW",
                    "matched_evidence_ids": [f"HMCV1-B1-HIST-{record_id}"],
                }
            )
    return found


def build() -> None:
    curriculum = json.loads(CURRICULUM_MANIFEST.read_text(encoding="utf-8"))
    if curriculum["canonical_identity"] != (
        "39fd9ef64470464ba0a9245b82d3e3c4924506fc2338c69bb7cb47b9ed77f9dc"
    ):
        raise RuntimeError("unexpected frozen curriculum manifest identity")
    rows = json.loads(SOURCE_LEDGER.read_text(encoding="utf-8"))
    by_id = {row["record_id"]: row for row in rows}
    if len(by_id) != 19:
        raise RuntimeError("Voice-ready source universe is not the frozen 19-record ledger")

    source_inventory = []
    evidence_records = []
    all_attractors = []
    for record_id, row in sorted(by_id.items()):
        parent = Path(row["parent_file"])
        parent_bytes = parent.read_bytes()
        if sha256(parent_bytes) != row["parent_file_sha256"]:
            raise RuntimeError(f"parent hash mismatch: {record_id}")
        start_byte, end_byte = row["parent_utf8_byte_range"]
        exact_bytes = parent_bytes[start_byte:end_byte]
        if sha256(exact_bytes) != row["commentary_raw_sha256"]:
            raise RuntimeError(f"byte-range hash mismatch: {record_id}")
        exact_text = exact_bytes.decode("utf-8")
        if exact_text != row["commentary_text"]:
            raise RuntimeError(f"byte-range text mismatch: {record_id}")
        parent_text = parent_bytes.decode("utf-8")
        start_char, end_char = row["parent_char_range"]
        if parent_text[start_char:end_char] != exact_text:
            raise RuntimeError(f"character-range mismatch: {record_id}")

        selected = record_id in SELECTIONS
        source_inventory.append(
            {
                "record_id": record_id,
                "episode": row["episode"],
                "source_disposition": row["disposition"],
                "pilot_disposition": (
                    "INCLUDED_BATCH1_MECHANISM_EVIDENCE"
                    if selected
                    else "NOT_SELECTED_NO_DEFENSIBLE_ADDITIONAL_BATCH1_EVIDENCE"
                ),
                "style_signals": row["style_signals"],
                "parent_file": str(parent),
                "parent_file_sha256": row["parent_file_sha256"],
                "byte_range_verified": True,
                "character_range_verified": True,
            }
        )
        if not selected:
            continue

        decision = SELECTIONS[record_id]
        evidence_id = f"HMCV1-B1-HIST-{record_id}"
        annotations = []
        for key, role, rationale in decision["annotations"]:
            annotations.append(
                {
                    "mechanism_id": MECHANISMS[key],
                    "mechanism_version": "1.0.0",
                    "role": role,
                    "confidence": "OWNER_APPROVED_HISTORICAL",
                    "evidence_span": [0, len(exact_text)],
                    "rationale": rationale,
                }
            )
        record_attractors = attractors(record_id, exact_text)
        all_attractors.extend(record_attractors)
        authority = row.get("authority_binding") or {}
        evidence_records.append(
            {
                "evidence_id": evidence_id,
                "evidence_version": "1.0.0",
                "provenance_class": "OWNER_FINAL_HISTORICAL",
                "source": {
                    "record_id": record_id,
                    "episode_id": str(row["episode"]),
                    "source_artifact": str(parent),
                    "source_artifact_identity": row["parent_file_sha256"],
                    "source_char_range": row["parent_char_range"],
                    "source_utf8_byte_range": row["parent_utf8_byte_range"],
                    "source_sha256": row["commentary_raw_sha256"],
                    "commentary_exact": True,
                    "byte_range_verified": True,
                    "character_range_verified": True,
                },
                "factual_context": {
                    "authority_identity": authority.get("authority_identity"),
                    "summary_identity": authority.get("accepted_factual_summary_sha256"),
                    "accepted_factual_input": authority.get("accepted_factual_input"),
                    "accepted_factual_input_sha256": authority.get("accepted_factual_input_sha256"),
                    "summary_byte_immutable": True,
                    "current_authority_compatibility": decision["compatibility"],
                },
                "surface": {
                    "language": "ro",
                    "text": exact_text,
                    "text_sha256": sha256(exact_text.encode("utf-8")),
                },
                "mechanism_annotations": annotations,
                "semantic_domains": decision["domains"],
                "syntactic_metadata": syntactic_metadata(exact_text),
                "attractor_annotations": record_attractors,
                "negative_annotations": [
                    {
                        "class": item,
                        "status": "PRESERVED_OWNER_APPROVED_WARNING",
                    }
                    for item in decision["negative"]
                ],
                "owner_review": {
                    "status": "CLOSED_OWNER_APPROVED",
                    "question": decision["review"],
                },
                "owner_adjudication": "APPROVED_HISTORICAL_EVIDENCE_ONLY",
                "training_eligibility": "NOT_ELIGIBLE",
                "runtime_eligibility": "NOT_ELIGIBLE",
                "current_authority_eligibility": "NOT_ELIGIBLE",
            }
        )

    coverage = []
    for mechanism in curriculum["mechanisms"][:10]:
        matching = []
        roles = set()
        for record in evidence_records:
            for annotation in record["mechanism_annotations"]:
                if annotation["mechanism_id"] == mechanism["id"]:
                    matching.append(record["evidence_id"])
                    roles.add(annotation["role"])
        if "DOMINANT" in roles:
            status = "HISTORICAL_DOMINANT_CANDIDATE_FOUND"
        elif matching:
            status = "HISTORICAL_SUPPORTING_OR_DELIVERY_ONLY"
        else:
            status = "GENUINE_COVERAGE_GAP"
        coverage.append(
            {
                "mechanism_id": mechanism["id"],
                "mechanism_name": mechanism["name"],
                "coverage_status": status,
                "roles_found": sorted(roles),
                "evidence_ids": sorted(set(matching)),
            }
        )

    signature_map: dict[tuple[str, str], set[str]] = {}
    for item in all_attractors:
        key = (item["category"], item["signature"])
        signature_map.setdefault(key, set()).update(item["matched_evidence_ids"])
    aggregate_attractors = [
        {
            "category": category,
            "signature": signature,
            "scope": "BATCH1_HISTORICAL_PILOT",
            "severity": "REVIEW",
            "matched_evidence_ids": sorted(ids),
            "count": len(ids),
        }
        for (category, signature), ids in sorted(signature_map.items())
    ]

    owner_queue = [
        {
            "queue_id": "HMCV1-B1-PILOT-ORQ-001",
            "subject": "SARCASTIC_DOMINANT_AND_CURRENT_AUTHORITY",
            "evidence_ids": ["HMCV1-B1-HIST-story-v1:29:06", "HMCV1-B1-HIST-story-v1:30:02"],
            "question": "Which, if either, is accepted as dominant historical Sarcasm evidence, and neither may be promoted to current training compatibility without separate factual adjudication?",
            "controls": ["ACCEPT_MECHANISM_ANNOTATION", "RECLASSIFY_SUPPORTING_ONLY", "REJECT_MECHANISM_ANNOTATION"],
        },
        {
            "queue_id": "HMCV1-B1-PILOT-ORQ-002",
            "subject": "UNDERSTATEMENT_DOMINANT_GAP",
            "evidence_ids": ["HMCV1-B1-HIST-story-v1:30:02", "HMCV1-B1-HIST-story-v1:31:04", "HMCV1-B1-HIST-story-v1:31:05"],
            "question": "Confirm that these remain supporting Understatement evidence and that no clean dominant Understatement example was found in the 19-record source universe.",
            "controls": ["CONFIRM_GAP", "PROMOTE_EXISTING_WITH_RATIONALE", "REJECT_SUPPORTING_ANNOTATION"],
        },
        {
            "queue_id": "HMCV1-B1-PILOT-ORQ-003",
            "subject": "DEADPAN_IS_DELIVERY_ONLY",
            "evidence_ids": ["HMCV1-B1-HIST-story-v1:29:05", "HMCV1-B1-HIST-story-v1:31:05", "HMCV1-B1-HIST-story-v1:33:06"],
            "question": "Confirm Deadpan as a delivery annotation rather than forcing a dominant semantic label.",
            "controls": ["CONFIRM_DELIVERY_ROLE", "PROMOTE_WITH_RATIONALE", "REJECT_ANNOTATION"],
        },
        {
            "queue_id": "HMCV1-B1-PILOT-ORQ-004",
            "subject": "FICTIONAL_FRAME_REAL_DIALOGUE_RISK",
            "evidence_ids": ["HMCV1-B1-HIST-story-v1:32:01", "HMCV1-B1-HIST-story-v1:32:06", "HMCV1-B1-HIST-story-v1:33:05"],
            "question": "Accept these as historical Frame/Contrast evidence while retaining their invented-dialogue current-authority warnings?",
            "controls": ["ACCEPT_HISTORICAL_ONLY", "REJECT", "REQUEST_NARROWER_BYTE_EXACT_SPAN_LATER"],
        },
        {
            "queue_id": "HMCV1-B1-PILOT-ORQ-005",
            "subject": "SERIOUS_AND_ALLEGATION_SENSITIVE_HISTORICAL_SURFACES",
            "evidence_ids": ["HMCV1-B1-HIST-story-v1:29:06", "HMCV1-B1-HIST-story-v1:31:04", "HMCV1-B1-HIST-story-v1:31:06"],
            "question": "Accept only their mechanism annotations, reject them, or request later narrower byte-exact spans; no current training eligibility is implied.",
            "controls": ["ACCEPT_MECHANISM_EVIDENCE_ONLY", "REJECT", "REQUEST_NARROWER_SPAN_LATER"],
        },
        {
            "queue_id": "HMCV1-B1-PILOT-ORQ-006",
            "subject": "PILOT_ANNOTATION_SET",
            "evidence_ids": [record["evidence_id"] for record in evidence_records],
            "question": "Approve the 13-record pilot annotation set as the Batch 1 historical coverage baseline, without changing any training or runtime eligibility?",
            "controls": ["APPROVE_PILOT_BASELINE", "REVISE_ANNOTATIONS", "REJECT_PILOT_BASELINE"],
        },
    ]
    for item in owner_queue:
        item["status"] = "CLOSED_OWNER_APPROVED"
        item["decision"] = OWNER_ADJUDICATION["decisions"][item["queue_id"]]

    coverage_report = {
        "schema_name": "pastila-humor-mechanics-batch1-historical-coverage-report",
        "schema_version": "1.0.0",
        "curriculum_identity": curriculum["canonical_identity"],
        "source_universe_count": len(rows),
        "included_evidence_count": len(evidence_records),
        "excluded_from_pilot_count": len(rows) - len(evidence_records),
        "mechanism_coverage": coverage,
        "genuine_gaps": [
            "No owner-confirmed dominant Understatement example in the 19-record Voice-ready historical universe.",
            "Deadpan appears as a delivery role rather than a clean dominant semantic mechanism.",
            "Sarcasm candidates are allegation-sensitive or lack reusable current factual authority.",
            "Most included historical spans are not yet compatible with the current commentary-only authority.",
            "The source universe is concentrated in public authority, public communication, technology, and consumer-service domains.",
        ],
        "no_quota_fill": True,
        "generation_calls": 0,
        "synthetic_examples_created": 0,
    }

    manifest = {
        "schema_name": "pastila-humor-mechanics-batch1-historical-evidence-pilot",
        "schema_version": "1.0.0",
        "pilot_id": "HMCV1_BATCH1_HISTORICAL_EVIDENCE_PILOT_V1",
        "lifecycle": "OWNER_APPROVED_AND_FROZEN",
        "curriculum_identity": curriculum["canonical_identity"],
        "curriculum_batch": 1,
        "source_ledger": str(SOURCE_LEDGER.relative_to(ROOT)),
        "source_ledger_sha256": sha256(SOURCE_LEDGER.read_bytes()),
        "builder_script": str(Path(__file__).resolve().relative_to(ROOT)),
        "builder_script_sha256": sha256(Path(__file__).read_bytes()),
        "source_universe_count": len(rows),
        "included_evidence_count": len(evidence_records),
        "owner_review_queue_count": len(owner_queue),
        "owner_adjudication": OWNER_ADJUDICATION,
        "generation_calls": 0,
        "synthetic_examples_created": 0,
        "runtime_actions": 0,
        "training_authorized": False,
        "integration_authorized": False,
        "canonical_identity": None,
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT / "source-inventory.json", source_inventory)
    write_json(OUTPUT / "evidence-records.json", evidence_records)
    write_json(OUTPUT / "coverage-report.json", coverage_report)
    write_json(OUTPUT / "attractor-report.json", aggregate_attractors)
    write_json(OUTPUT / "owner-review-queue.json", owner_queue)

    lines = [
        "# Batch 1 Historical Evidence Pilot V1",
        "",
        "Status: `OWNER_APPROVED_AND_FROZEN`",
        "",
        f"- Frozen curriculum identity: `{curriculum['canonical_identity']}`",
        f"- Source universe: {len(rows)} byte-verified Voice-ready owner-final spans",
        f"- Included Batch 1 evidence records: {len(evidence_records)}",
        f"- Not selected: {len(rows) - len(evidence_records)}",
        "- Generation calls: 0",
        "- Synthetic examples: 0",
        "- Runtime, prompt, model, integration, and training actions: 0",
        "",
        "## Coverage",
        "",
        "| Mechanism | Status | Roles | Records |",
        "|---|---|---|---:|",
    ]
    for item in coverage:
        lines.append(
            f"| {item['mechanism_name']} | {item['coverage_status']} | "
            f"{', '.join(item['roles_found']) or 'none'} | {len(item['evidence_ids'])} |"
        )
    lines.extend(
        [
            "",
            "## Genuine gaps",
            "",
            *[f"- {gap}" for gap in coverage_report["genuine_gaps"]],
            "",
            "## Owner adjudication",
            "",
            "All six bounded decisions are owner-approved and closed. The 13-record baseline",
            "is frozen as historical curriculum evidence only. No record has current-authority,",
            "training, or runtime eligibility, and no further recovery or enrichment is authorized.",
            "",
        ]
    )
    (OUTPUT / "pilot-report.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )

    queue_lines = [
        "# Batch 1 Historical Evidence Pilot — Owner Review Queue",
        "",
        "Status: `OWNER_APPROVED_AND_FROZEN`",
        "",
        "All decisions are closed and owner-approved. They affect historical curriculum",
        "evidence annotations only and grant no current-authority, runtime, integration,",
        "or training eligibility.",
        "",
    ]
    for item in owner_queue:
        queue_lines.extend(
            [
                f"## {item['queue_id']} — {item['subject']}",
                "",
                item["question"],
                "",
                f"Decision: `{item['decision']['decision']}`",
                "",
                item["decision"]["resolution"],
                "",
                "Evidence:",
                "",
                *[f"- `{evidence_id}`" for evidence_id in item["evidence_ids"]],
                "",
                "Allowed decisions:",
                "",
                *[f"- `{control}`" for control in item["controls"]],
                "",
            ]
        )
    (OUTPUT / "owner-review-queue.md").write_text(
        "\n".join(queue_lines), encoding="utf-8", newline="\n"
    )

    artifact_hashes = {}
    for name in (
        "source-inventory.json",
        "evidence-records.json",
        "coverage-report.json",
        "attractor-report.json",
        "owner-review-queue.json",
        "owner-review-queue.md",
        "pilot-report.md",
    ):
        artifact_hashes[name] = sha256((OUTPUT / name).read_bytes())
    manifest["artifacts"] = artifact_hashes
    manifest["canonical_identity"] = sha256(
        canonical_bytes({k: v for k, v in manifest.items() if k != "canonical_identity"})
    )
    write_json(OUTPUT / "manifest.json", manifest)


if __name__ == "__main__":
    build()
