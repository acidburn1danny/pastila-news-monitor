"""Build the fixture-only EDITOR Source-Bound Hybrid Feasibility Diagnostic v1."""
from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-source-bound-hybrid-feasibility-v1"
SEEDS = (161803, 271828, 314159)
SOURCE_CASES = "editor-core-r2-factorized-fact-plan-diagnostic-v1-cases.jsonl"
SOURCE_PLANS = "editor-core-r2-factorized-fact-plan-diagnostic-v1-oracle-plans.jsonl"

EPISTEMIC_MARKERS = (
    "afirmă", "afirmat", "susține", "susținut", "estimează", "estimat",
    "ar fi", "contestă", "contestat", "preliminar", "potrivit",
)
PROCEDURAL_MARKERS = (
    "propus", "propunere", "urmează", "vot", "aprobat", "decizie",
    "în curs", "nu a fost încă", "rămâne", "condiționat", "semnat",
)
FUNCTION_WORDS = (
    "a", "ai", "ale", "al", "au", "ca", "că", "care", "cu", "dar", "de",
    "din", "după", "este", "fi", "fost", "iar", "în", "însă", "la", "le",
    "mai", "nu", "o", "pe", "pentru", "prin", "sau", "se", "și", "un", "unei", "unui",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identified(value: dict, key: str) -> dict:
    result = dict(value)
    result[key] = sha(canonical(result))
    return result


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(name: str, value: object) -> None:
    (ART / name).write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def write_jsonl(name: str, values: list[dict]) -> None:
    (ART / name).write_bytes(b"".join(canonical(value) + b"\n" for value in values))


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+|\d+(?:[.,]\d+)?", text.casefold(), re.UNICODE)


def content_tokens(text: str) -> set[str]:
    return {token for token in tokens(text) if len(token) > 2 and token not in FUNCTION_WORDS}


def binding_tokens(text: str) -> set[str]:
    return {token for token in tokens(text) if token not in FUNCTION_WORDS}


def numbers(text: str) -> list[str]:
    return re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", text)


def markers(text: str, inventory: tuple[str, ...]) -> list[str]:
    low = text.casefold()
    return [marker for marker in inventory if marker in low]


def atom_type(text: str) -> str:
    if markers(text, EPISTEMIC_MARKERS):
        return "ATTRIBUTED_OR_QUALIFIED_CLAIM"
    if markers(text, PROCEDURAL_MARKERS):
        return "PROCEDURAL_STATUS"
    if numbers(text):
        return "NUMERIC_FACT"
    if re.search(r"\b(?:luni|marți|miercuri|joi|vineri|sâmbătă|duminică|astăzi|ieri|mâine)\b", text.casefold()):
        return "TEMPORAL_FACT"
    return "SOURCE_FACT"


def actor_terms(text: str) -> list[str]:
    candidates = re.findall(
        r"\b(?:[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț-]+(?:\s+[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț-]+){0,3})",
        text,
    )
    return list(dict.fromkeys(candidates))


def request_payload(case: dict) -> dict:
    return json.loads(case["messages"][1]["content"].split("\nINPUT=", 1)[1])


def support_for_requirement(requirement: str, spans: list[dict]) -> list[str]:
    req = binding_tokens(requirement)
    scored = []
    for span in spans:
        span_tokens = binding_tokens(span["text"])
        exact = len(req & span_tokens)
        fuzzy = sum(max((SequenceMatcher(None, token, candidate).ratio() for candidate in span_tokens), default=0.0) for token in req)
        score = exact * 2.0 + fuzzy
        scored.append((score, span["span_id"]))
    best = max(score for score, _ in scored)
    if best < 0.45:
        raise ValueError(f"unbound requirement: {requirement}")
    return [span_id for score, span_id in scored if abs(score - best) < 1e-9]


cases = read_jsonl(ART / SOURCE_CASES)
plans = {row["case_id"]: row for row in read_jsonl(ART / SOURCE_PLANS)}
if len(cases) != 48 or set(plans) != {case["case_id"] for case in cases}:
    raise ValueError("source inventory mismatch")

ledger_schema = identified({
    "schema": "editor-source-bound-factual-ledger-schema",
    "schema_version": 1,
    "authority_model": {
        "source_spans": "SOLE_FACTUAL_AUTHORITY",
        "ledger": "DERIVED_SOURCE_BOUND_AUTHORITY",
        "realizer": "NON_AUTHORITATIVE_ORDER_AND_CONNECTOR_PROPOSAL",
        "verifier": "ACCEPT_OR_REJECT_AGAINST_LEDGER",
        "fallback": "DETERMINISTIC_EXTRACTIVE_FROM_REQUIRED_ATOMS",
    },
    "atom_types": [
        "SOURCE_FACT", "NUMERIC_FACT", "TEMPORAL_FACT",
        "ATTRIBUTED_OR_QUALIFIED_CLAIM", "PROCEDURAL_STATUS",
    ],
    "selection_states": ["REQUIRED", "OPTIONAL", "EXCLUDED"],
    "relation_types": ["SUPPORTS_REQUIREMENT", "QUALIFIES", "UPDATES", "CONTESTS", "EXCLUDES"],
    "required_atom_fields": [
        "atom_id", "atom_type", "source_span_id", "source_sha256", "quote",
        "byte_start", "byte_end", "selection", "actors_entities", "numbers",
        "epistemic_markers", "procedural_markers",
    ],
    "invariants": [
        "QUOTE_BYTES_EQUAL_SOURCE_SLICE",
        "EVERY_ATOM_HAS_EXACTLY_ONE_SOURCE_SPAN",
        "REQUIRED_OBLIGATIONS_BIND_TO_ONE_OR_MORE_ATOMS",
        "EXCLUDED_ATOMS_CANNOT_ENTER_REALIZATION",
        "REALIZER_CANNOT_CREATE_FACTUAL_AUTHORITY",
        "ACCEPTED_TEXT_MUST_PASS_ALL_LEDGER_CHECKS",
        "FAILURE_USES_EXTRACTIVE_FALLBACK",
    ],
}, "ledger_schema_identity")

reconciliation_rules = identified({
    "schema": "editor-source-bound-ledger-reconciliation-rules",
    "schema_version": 1,
    "atomization": "ONE_ATOM_PER_AUTHORITY_SPAN_WITH_BYTE_EXACT_FULL_SPAN_QUOTE",
    "obligation_binding": {
        "tokens": "UNICODE_CASEFOLD_WORDS_AND_NUMBERS_EXCLUDING_FUNCTION_WORDS",
        "score": "2_TIMES_EXACT_TOKEN_OVERLAP_PLUS_SUM_OF_BEST_SEQUENCE_MATCH_RATIO_PER_REQUIREMENT_TOKEN",
        "minimum_score": 0.45,
        "tie": "KEEP_ALL_MAX_SCORE_SOURCE_SPANS",
        "failure": "FAIL_CLOSED_UNBOUND_REQUIREMENT",
    },
    "selection": {
        "REQUIRED": "SOURCE_SPAN_SUPPORTS_AT_LEAST_ONE_REQUIRED_OBLIGATION",
        "OPTIONAL": "NOT_REQUIRED_AND_AT_LEAST_THREE_CONTENT_TOKENS_OVERLAP_ORACLE_FIXTURE_TARGET",
        "EXCLUDED": "OTHERWISE",
    },
    "numeric_reconciliation": "PRESERVE_EXACT_SURFACE_VALUE_AND_SOURCE_ROLE; NO_ARITHMETIC_OR_UNIT_SUBSTITUTION",
    "actor_reconciliation": "ONLY_SOURCE_BOUND_ACTOR_OR_ENTITY_SURFACES_ARE_AUTHORIZED",
    "epistemic_reconciliation": "PRESERVE_EACH_SOURCE_MARKER; NEVER_PROMOTE_CLAIM_TO_ESTABLISHED_FACT",
    "procedural_reconciliation": "PRESERVE_CURRENT_STAGE_AND_CONDITIONS; NEVER_PROMOTE_PROPOSAL_OR_PENDING_STEP",
    "conflict_reconciliation": "KEEP_COMPETING_SOURCE_ATOMS_SEPARATE; REQUIRE_ATTRIBUTION; NEVER_AUTO_RESOLVE",
    "temporal_reconciliation": "KEEP_SOURCE_ORDER_AND_EXPLICIT_TEMPORAL_MARKERS; LATER_SOURCE_IS_NOT_AUTO_TRUTH",
    "fixture_limit": "ORACLE_TARGET_IS_USED_ONLY_TO LABEL REQUIRED_OPTIONAL_EXCLUDED FOR FEASIBILITY; A REAL ACQUISITION ROUTE MUST SUPPLY THIS CURATION_INDEPENDENTLY",
    "deterministic": True,
}, "reconciliation_identity")

ledgers: list[dict] = []
for case in cases:
    case_id = case["case_id"]
    plan = plans[case_id]
    payload = request_payload(case)
    spans = payload["authority_spans"]
    target_tokens = content_tokens(plan["oracle_setup_target"])
    requirement_support: dict[str, list[str]] = {}
    for fact in plan["selected_facts"]:
        requirement_support[fact["fact_id"]] = support_for_requirement(fact["surface_requirement"], spans)
    required_span_ids = {span_id for values in requirement_support.values() for span_id in values}
    atoms = []
    for index, span in enumerate(spans, 1):
        quote = span["text"]
        quote_bytes = quote.encode("utf-8")
        overlap = len(content_tokens(quote) & target_tokens)
        selection = "REQUIRED" if span["span_id"] in required_span_ids else ("OPTIONAL" if overlap >= 3 else "EXCLUDED")
        atoms.append({
            "atom_id": f"{case_id}:a{index}",
            "atom_type": atom_type(quote),
            "source_span_id": span["span_id"],
            "source_sha256": sha(quote_bytes),
            "quote": quote,
            "byte_start": 0,
            "byte_end": len(quote_bytes),
            "selection": selection,
            "actors_entities": actor_terms(quote),
            "numbers": numbers(quote),
            "epistemic_markers": markers(quote, EPISTEMIC_MARKERS),
            "procedural_markers": markers(quote, PROCEDURAL_MARKERS),
        })
    obligations = []
    for fact in plan["selected_facts"]:
        bound_atoms = [
            atom["atom_id"] for atom in atoms if atom["source_span_id"] in requirement_support[fact["fact_id"]]
        ]
        obligations.append({
            "obligation_id": f"{case_id}:o{len(obligations)+1}",
            "surface_requirement": fact["surface_requirement"],
            "support_atom_ids": bound_atoms,
            "coverage": "REQUIRED",
        })
    required_atoms = [atom for atom in atoms if atom["selection"] == "REQUIRED"]
    allowed_content = sorted({token for atom in required_atoms for token in content_tokens(atom["quote"])})
    allowed_numbers = sorted({number for atom in required_atoms for number in atom["numbers"]})
    required_epistemic = sorted({marker for atom in required_atoms for marker in atom["epistemic_markers"]})
    required_procedural = sorted({marker for atom in required_atoms for marker in atom["procedural_markers"]})
    ledger = {
        "schema": "editor-source-bound-factual-ledger",
        "schema_version": 1,
        "case_id": case_id,
        "partition": case["partition"],
        "failure_class": case["failure_class"],
        "request_identity": case["request_identity"],
        "request": payload["request"],
        "source_spans": [{
            "source_id": span["source_id"],
            "span_id": span["span_id"],
            "text": span["text"],
            "sha256": sha(span["text"].encode("utf-8")),
        } for span in spans],
        "atoms": atoms,
        "obligations": obligations,
        "relations": [{
            "relation": "SUPPORTS_REQUIREMENT",
            "obligation_id": obligation["obligation_id"],
            "atom_ids": obligation["support_atom_ids"],
        } for obligation in obligations],
        "realization_contract": {
            "minimum_sentences": 2,
            "maximum_sentences": 3,
            "allowed_atom_ids": [atom["atom_id"] for atom in atoms if atom["selection"] != "EXCLUDED"],
            "required_atom_ids": [atom["atom_id"] for atom in required_atoms],
            "excluded_atom_ids": [atom["atom_id"] for atom in atoms if atom["selection"] == "EXCLUDED"],
            "allowed_content_tokens": allowed_content,
            "allowed_numbers": allowed_numbers,
            "required_epistemic_markers": required_epistemic,
            "required_procedural_markers": required_procedural,
            "function_words": list(FUNCTION_WORDS),
        },
        "extractive_fallback": {
            "strategy": "ORDERED_REQUIRED_ATOM_QUOTES_MAX_THREE_SENTENCES",
            "atom_ids": [atom["atom_id"] for atom in required_atoms][:3],
            "overflow_behavior": "FAIL_CLOSED_INSUFFICIENT_FALLBACK",
        },
        "provenance": {
            "source_cases_file": SOURCE_CASES,
            "source_plans_file": SOURCE_PLANS,
            "historical_holdout": False,
            "oracle_used_for_fixture_selection_only": True,
        },
    }
    ledgers.append(identified(ledger, "ledger_identity"))

realization_schema = identified({
    "schema": "editor-ledger-bound-realization-proposal-schema",
    "schema_version": 1,
    "fields": {
        "case_id": "EXACT_LEDGER_CASE_ID",
        "sentences": "TWO_OR_THREE_SENTENCE_OBJECTS",
        "sentences[].text": "NON_AUTHORITATIVE_PROPOSED_TEXT",
        "sentences[].atom_ids": "NONEMPTY_SUBSET_OF_ALLOWED_ATOMS",
    },
    "verifier_checks": [
        "CASE_ID_MATCH", "TWO_TO_THREE_SENTENCES", "ALL_BINDINGS_ALLOWED",
        "ALL_REQUIRED_ATOMS_BOUND", "NO_EXCLUDED_ATOM_BOUND", "NO_UNAUTHORIZED_NUMBER",
        "NO_UNAUTHORIZED_CONTENT_TOKEN", "ALL_REQUIRED_EPISTEMIC_MARKERS",
        "ALL_REQUIRED_PROCEDURAL_MARKERS", "NO_REPETITIVE_CLAUSE",
    ],
    "accepted_output": "DETERMINISTIC_JOIN_OF_VERIFIED_SENTENCES",
    "rejected_output": "DISCARDED_NOT_EVIDENCE; RETURN_EXTRACTIVE_FALLBACK",
}, "realization_schema_identity")

comparison = identified({
    "schema": "editor-source-bound-hybrid-comparison",
    "schema_version": 1,
    "arms": [
        {"id": "B0_R2_ONE_PASS", "authority": "SOURCE_SPANS", "generation": "R2_STEP_9", "verification": "CONTRACT_ONLY"},
        {"id": "B1_EXTRACTIVE_BASELINE", "authority": "LEDGER_REQUIRED_ATOMS", "generation": "DETERMINISTIC_QUOTES", "verification": "LEDGER"},
        {"id": "B2_HYBRID", "authority": "LEDGER", "generation": "SEPARATE_TEXT_REALIZER", "verification": "LEDGER_AND_FALLBACK"},
    ],
    "matched": ["CASES", "PARTITIONS", "SEEDS", "LEDGER", "METRICS", "SENTENCE_BUDGET"],
    "seeds": list(SEEDS),
    "metrics": [
        "LEDGER_CONSTRUCTION_VALIDITY", "REQUIRED_ATOM_COVERAGE", "NOVEL_ACTOR",
        "NUMBER_ROLE_FIDELITY", "EPISTEMIC_MARKER_RETENTION", "PROCEDURAL_STATUS_RETENTION",
        "UNSUPPORTED_CONTENT_TOKEN", "SENTENCE_BUDGET", "REPETITION",
        "FALLBACK_RATE", "FALLBACK_SUFFICIENCY", "FUNCTIONAL_ROMANIAN_PROXY",
    ],
    "causal_questions": {
        "B1_VS_B0": "VALUE_OF_MOVING_FACT_AUTHORITY_TO_DETERMINISTIC_EXTRACTION",
        "B2_VS_B1": "VALUE_AND_RISK_OF_SEPARATE_TEXT_REALIZATION",
        "B2_VS_B0": "END_TO_END_HYBRID_VALUE",
    },
    "semantic_scoring_required_later": True,
    "real_execution_authority": False,
}, "comparison_identity")

decision = identified({
    "schema": "editor-source-bound-hybrid-terminal-rules",
    "schema_version": 1,
    "STOP": [
        "LEDGER_CANNOT_BIND_ALL_REQUIRED_FACTS_TO_SOURCE_BYTES",
        "ANY_ACCEPTED_NOVEL_ACTOR_OR_NUMBER",
        "ANY_ACCEPTED_EPISTEMIC_OR_PROCEDURAL_UPGRADE",
        "HYBRID_HAS_NO_SAFETY_OR_SUFFICIENCY_ADVANTAGE_OVER_R2",
        "FALLBACK_CANNOT_PRESERVE_REQUIRED_FACTS_WITHIN_THREE_SENTENCES",
    ],
    "REVISE": [
        "LEDGER_VALID_BUT_HYBRID_FALLBACK_RATE_EXCEEDS_25_PERCENT",
        "EXTRACTIVE_SAFE_BUT_FUNCTIONAL_ROMANIAN_FAILS",
        "HYBRID_SAFE_BUT_NO_REALIZATION_GAIN_OVER_EXTRACTIVE",
        "SEED_DIRECTION_NOT_REPLICATED_IN_TWO_OF_THREE",
    ],
    "CONTINUE": [
        "LEDGER_VALID_FOR_ALL_ADMITTED_CASES",
        "ZERO_ACCEPTED_FACTUAL_OR_EPISTEMIC_DRIFT",
        "HYBRID_BEATS_R2_ON_SUFFICIENCY_WITHOUT_REPLAY_REGRESSION",
        "HYBRID_BEATS_EXTRACTIVE_ON_FUNCTIONAL_ROMANIAN",
        "DIRECTION_REPLICATED_IN_AT_LEAST_TWO_OF_THREE_SEEDS",
        "TRAINABLE_RESIDUAL_ISOLATED_TO_REALIZATION_NOT_FACT_SELECTION",
    ],
    "precedence": "STOP_THEN_REVISE_THEN_CONTINUE",
    "parent_selection_authority": False,
}, "decision_identity")

protocol = identified({
    "schema": "editor-source-bound-hybrid-feasibility-protocol",
    "schema_version": 1,
    "status": "DESIGN_FIXTURE_ONLY_NO_REAL_EXECUTION_AUTHORITY",
    "objective": "MOVE_FACTUAL_AUTHORITY_FROM_PROBABILISTIC_BEHAVIOR_TO_SOURCE_BOUND_LEDGER",
    "parent": "R2_STEP_9",
    "parent_adapter_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
    "successor_training": "SUSPENDED",
    "closed_mechanisms": [
        "WEIGHTED_SFT_T1_S0_TESTED_FORMS", "CONTRASTIVE_TESTED_FORM", "R2_KL_TESTED_FORM",
        "FACTORIZED_FACT_PLAN_V1",
    ],
    "ledger_schema_identity": ledger_schema["ledger_schema_identity"],
    "reconciliation_identity": reconciliation_rules["reconciliation_identity"],
    "realization_schema_identity": realization_schema["realization_schema_identity"],
    "comparison_identity": comparison["comparison_identity"],
    "decision_identity": decision["decision_identity"],
    "cases": 48,
    "partitions": {"DEVELOPMENT": 24, "REPLAY_RETENTION": 24},
    "fixture_selection_uses_oracle": True,
    "autonomous_ledger_construction_claimed": False,
    "real_route_requires_independent_selection_curation": True,
    "historical_holdouts_allowed": False,
    "model_load_authorized": False,
    "inference_authorized": False,
    "optimizer_creation_authorized": False,
    "training_authorized": False,
    "successor_candidate_authorized": False,
    "parent_selection_authority": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "voice_or_chief_editor_objective": False,
}, "protocol_identity")

write_json(f"{PREFIX}-ledger-schema.json", ledger_schema)
write_json(f"{PREFIX}-reconciliation-rules.json", reconciliation_rules)
write_jsonl(f"{PREFIX}-ledgers.jsonl", ledgers)
write_json(f"{PREFIX}-realization-schema.json", realization_schema)
write_json(f"{PREFIX}-comparison.json", comparison)
write_json(f"{PREFIX}-terminal-rules.json", decision)
write_json(f"{PREFIX}-protocol.json", protocol)

files = [
    f"{PREFIX}-ledger-schema.json", f"{PREFIX}-ledgers.jsonl",
    f"{PREFIX}-reconciliation-rules.json",
    f"{PREFIX}-realization-schema.json", f"{PREFIX}-comparison.json",
    f"{PREFIX}-terminal-rules.json", f"{PREFIX}-protocol.json",
]
manifest = identified({
    "schema": "editor-source-bound-hybrid-feasibility-pack",
    "schema_version": 1,
    "files": {name: sha((ART / name).read_bytes()) for name in files},
    "source_files": {
        SOURCE_CASES: sha((ART / SOURCE_CASES).read_bytes()),
        SOURCE_PLANS: sha((ART / SOURCE_PLANS).read_bytes()),
    },
    "ledgers": 48,
    "development": 24,
    "replay_retention": 24,
    "atoms": sum(len(ledger["atoms"]) for ledger in ledgers),
    "obligations": sum(len(ledger["obligations"]) for ledger in ledgers),
    "protocol_identity": protocol["protocol_identity"],
    "historical_holdouts_read": False,
    "model_loaded": False,
    "inference_performed": False,
    "optimizer_created": False,
    "training_performed": False,
}, "pack_identity")
write_json(f"{PREFIX}-manifest.json", manifest)
print(json.dumps({
    "status": "PASS_BUILD",
    "pack_identity": manifest["pack_identity"],
    "protocol_identity": protocol["protocol_identity"],
    "ledgers": len(ledgers),
    "atoms": manifest["atoms"],
    "obligations": manifest["obligations"],
}, sort_keys=True))
