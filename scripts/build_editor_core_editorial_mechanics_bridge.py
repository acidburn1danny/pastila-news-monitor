"""Build a source-bound, Voice-free R2 editorial-mechanics research pack.

This constructs data only. It does not load a model, train, or select a parent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-editorial-mechanics-bridge-v1"
PARENT_ADAPTER = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
PARENT_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
OPERATORS = (
    "FACT_SELECTION", "QUALIFIED_COMPRESSION", "CHRONOLOGICAL_ORDER",
    "PRECISE_ATTRIBUTION", "SUPPORTED_CONTRAST", "FACTUAL_TRANSITION",
    "NATURAL_ROMANIAN", "EPISTEMIC_GUARD",
)
SCENES = (
    ("Arhiva Lunca", "Valea Pinului", 31), ("Centrul Argint", "Dealul Verde", 42),
    ("Biroul Salcie", "Portul Mic", 53), ("Atelierul Borna", "Piața Veche", 64),
    ("Serviciul Nufăr", "Satul Nou", 75), ("Registrul Stejar", "Colina Albă", 86),
    ("Oficiul Meridian", "Râul Lin", 97), ("Centrul Corabia", "Câmpul Rece", 108),
    ("Biroul Sânziana", "Podul Nou", 119), ("Arhiva Fag", "Lacul Mic", 130),
    ("Serviciul Coral", "Drumul Lung", 141), ("Oficiul Mălin", "Pădurea Sud", 152),
)
SPLIT = ("TRAIN",) * 6 + ("DEVELOPMENT",) * 3 + ("INDEPENDENT_HOLDOUT",) * 3
KEY_ORDER = ("schema", "schema_version", "case_id", "request_identity", "output_type", "outcome", "text", "claim_bindings", "abstention_code")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_contract() -> tuple[str, str, str]:
    source = ART / "editor-core-v10-v12-targeted-continuation-r2-training.jsonl"
    first = json.loads(source.read_bytes().splitlines()[0])
    return first["messages"][0]["content"], first["messages"][1]["content"].split("\nINPUT=", 1)[0], sha(source.read_bytes())


def realization(op: str, scene: tuple[str, str, int], split: str) -> tuple[list[str], tuple[int, int], str, str, str]:
    agent, place, number = scene
    # Each split uses a different source register. Scene families are disjoint.
    lead = {"TRAIN": "În nota din", "DEVELOPMENT": "Conform fișei pentru", "INDEPENDENT_HOLDOUT": "Dosarul privind"}[split]
    if op == "FACT_SELECTION":
        spans = [f"{lead} {place}, {agent} a înregistrat {number} de cereri privind iluminatul.",
                 f"Aceeași notă menționează cumpărarea a două scaune pentru birou.",
                 f"Comisia locală a confirmat primirea cererilor, dar nu a stabilit un termen de soluționare."]
        return spans, (0, 2), f"La {place}, {agent} a înregistrat {number} de cereri privind iluminatul. Comisia a confirmat primirea lor; termenul de soluționare nu este stabilit.", "Selectează cererile și stadiul lor. Exclude achiziția fără legătură și reformulează concis.", "UNRELATED_FACT_INCLUSION"
    if op == "QUALIFIED_COMPRESSION":
        spans = [f"{lead} {place}, petenții susțin că {agent} ar fi omis {number} de înregistrări din evidență.",
                 "Verificarea omisiunii nu este încheiată și nu există o concluzie confirmată."]
        return spans, (0, 1), f"La {place}, petenții afirmă că {agent} ar fi omis {number} de înregistrări. Verificarea continuă fără concluzie confirmată.", "Comprimă relatarea fără să transformi acuzația în fapt sau verificarea în verdict.", "QUALIFIER_DROPPED"
    if op == "CHRONOLOGICAL_ORDER":
        spans = [f"Pe 18 ale lunii, {agent} a publicat un răspuns pentru cele {number} de solicitări din {place}.",
                 "Pe 12 ale aceleiași luni, locuitorii depuseseră solicitările la registratură."]
        return spans, (1, 0), f"Pe 12 ale lunii, locuitorii din {place} au depus {number} de solicitări. {agent} a publicat răspunsul pe 18.", "Redă cronologic cele două acțiuni, fără a adăuga motivul intervalului dintre ele.", "UNSUPPORTED_CAUSE"
    if op == "PRECISE_ATTRIBUTION":
        spans = [f"{lead} {place}, un fost angajat afirmă că {agent} ar fi întârziat {number} de dosare.",
                 f"{agent} respinge afirmația; inspectorii nu au încheiat verificarea."]
        return spans, (0, 1), f"Un fost angajat susține că {agent} ar fi întârziat {number} de dosare la {place}. Instituția neagă afirmația, iar verificarea rămâne deschisă.", "Atribuie afirmația, separă negația și păstrează statutul verificării.", "ALLEGATION_TO_FACT"
    if op == "SUPPORTED_CONTRAST":
        spans = [f"{agent} a comunicat că toate cele {number} de cereri din {place} au primit răspuns.",
                 f"Registrul public arată răspunsuri pentru {number - 2} cereri și două cereri încă deschise."]
        return spans, (0, 1), f"{agent} afirmă că toate cele {number} de cereri din {place} au primit răspuns. Registrul public indică însă {number - 2} răspunsuri și două cereri deschise.", "Arată contrastul dintre comunicat și registru fără a deduce intenții sau vinovăție.", "UNSUPPORTED_INTENT"
    if op == "FACTUAL_TRANSITION":
        spans = [f"La începutul lunii, {agent} a primit {number} de sesizări din {place}.",
                 "Săptămâna următoare, comisia a început examinarea sesizărilor."]
        return spans, (0, 1), f"După primirea celor {number} de sesizări din {place} de către {agent}, comisia a început examinarea lor în săptămâna următoare.", "Scrie o tranziție scurtă între faptele susținute, fără cauzalitate inventată.", "INVENTED_CAUSAL_LINK"
    if op == "NATURAL_ROMANIAN":
        spans = [f"Se aduce la cunoștință faptul că {agent} a primit {number} de cereri din {place}.",
                 "Se consemnează faptul că serviciul de evidență a confirmat primirea lor."]
        return spans, (0, 1), f"{agent} a primit {number} de cereri din {place}. Serviciul de evidență a confirmat primirea lor.", "Redă aceleași fapte în română naturală, fără formulări birocratice sau informații noi.", "BUREAUCRATIC_COPY"
    if op == "EPISTEMIC_GUARD":
        spans = [f"Un raport preliminar sugerează că {agent} ar fi clasificat greșit {number} de fișe din {place}.",
                 f"{agent} contestă observația; raportul nu este aprobat și analiza continuă."]
        return spans, (0, 1), f"Raportul preliminar indică posibilitatea ca {agent} să fi clasificat greșit {number} de fișe din {place}. Instituția contestă observația; analiza continuă fără raport aprobat.", "Păstrează caracterul preliminar, contestarea și lipsa unei concluzii finale.", "PRELIMINARY_TO_FINAL"
    raise ValueError(op)


def response(case_id: str, request_identity: str, text: str, span_ids: list[str]) -> dict:
    result = {"schema": "pastila-core-v2-structured-qualification-response", "schema_version": 2,
              "case_id": case_id, "request_identity": request_identity, "output_type": "FACTUAL",
              "outcome": "ANSWER", "text": text,
              "claim_bindings": [{"claim_index": i, "source_span_ids": [sid]} for i, sid in enumerate(span_ids, 1)],
              "abstention_code": None}
    assert tuple(result) == KEY_ORDER
    return result


def case(op: str, ordinal: int, system: str, protocol: str) -> tuple[dict, dict, dict, dict]:
    split = SPLIT[ordinal]
    op_index = OPERATORS.index(op)
    suffix = ("Nord", "Est", "Sud", "Vest", "Central", "Nou", "Mic", "Mare")[op_index]
    base_agent, base_place, base_number = SCENES[ordinal]
    scene = (f"{base_agent} {suffix}", f"{base_place} {suffix}", base_number + 100 * op_index)
    spans, selection, edited, request, negative_code = realization(op, scene, split)
    case_id = f"ec-bridge-v1-{op.lower().replace('_', '-')}-{ordinal + 1:02d}"
    span_ids = [f"ebv1:{op.lower()}:{ordinal + 1}:{i + 1}" for i in range(len(spans))]
    authority = [{"span_id": sid, "text": text} for sid, text in zip(span_ids, spans)]
    core = {"case_id": case_id, "output_type": "FACTUAL", "required_factual_shape": "MATERIAL_PROPOSITIONS",
            "expected_material_proposition_count": 2, "required_commentary_components": [], "request": request,
            "authority_spans": authority}
    request_identity = "sha256:" + sha(canonical(core))
    payload = {"case_id": case_id, "request_identity": request_identity, **{k: v for k, v in core.items() if k != "case_id"}}
    user = protocol + "\nINPUT=" + compact(payload)
    base = {"example_id": case_id, "split": split, "operator": op, "source_family": f"bridge-scene-{op_index + 1:02d}-{ordinal + 1:02d}",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    selected_ids = [span_ids[i] for i in selection]
    literal = " ".join(spans[i] for i in selection)
    # Naturalization requires a minimal grammatical control, not an invalid
    # bureaucratic copy. Both target modes preserve the same source claims.
    if op == "NATURAL_ROMANIAN":
        literal = f"{scene[0]} a primit {scene[2]} de cereri din {scene[1]}. Serviciul de evidență le-a confirmat primirea."
    if op == "FACTUAL_TRANSITION":
        literal = spans[0] + " Apoi, " + spans[1][0].lower() + spans[1][1:]
    edited_target = response(case_id, request_identity, edited, selected_ids)
    control_target = response(case_id, request_identity, literal, selected_ids)
    mechanics = {**base, "messages": base["messages"] + [{"role": "assistant", "content": compact(edited_target)}]}
    control = {**base, "messages": base["messages"] + [{"role": "assistant", "content": compact(control_target)}]}
    key = {"example_id": case_id, "request_identity": request_identity, "operator": op,
           "assistant_target": compact(edited_target), "control_target": compact(control_target),
           "must_preserve": ["SOURCE_FACTS", "ATTRIBUTION", "MODALITY", "CAUSALITY", "PROCEDURAL_STATUS"],
           "rewrite_required": True, "exact_string_match_is_semantic_verdict": False}
    agent, place, number = scene
    negative_text = {
        "FACT_SELECTION": literal + " Au fost cumpărate și două scaune pentru birou.",
        "QUALIFIED_COMPRESSION": f"La {place}, {agent} a omis {number} de înregistrări; verificarea a confirmat omisiunea.",
        "CHRONOLOGICAL_ORDER": f"Pe 18 ale lunii, {agent} a răspuns celor {number} de solicitări deoarece locuitorii le depuseseră pe 12.",
        "PRECISE_ATTRIBUTION": f"{agent} a întârziat {number} de dosare la {place}, iar inspectorii au demonstrat neregula.",
        "SUPPORTED_CONTRAST": f"{agent} a ascuns intenționat două cereri din {place}, după ce a pretins că toate au primit răspuns.",
        "FACTUAL_TRANSITION": f"Din cauza celor {number} de sesizări primite de {agent}, comisia a fost obligată să înceapă examinarea.",
        "NATURAL_ROMANIAN": " ".join(spans),
        "EPISTEMIC_GUARD": f"Raportul final a stabilit că {agent} a clasificat greșit {number} de fișe din {place}.",
    }[op]
    negative = {"example_id": case_id, "operator": op, "reason_code": negative_code,
                "negative_text": negative_text, "source_request_identity": request_identity,
                "status": "CONTRASTIVE_EVALUATION_ONLY", "source_copy_status":
                "INSUFFICIENT_FOR_REQUEST" if op in ("FACT_SELECTION", "NATURAL_ROMANIAN", "FACTUAL_TRANSITION") else "MAY_BE_SAFE_BUT_NOT_EDITORIAL_OPTIMAL"}
    return mechanics, control, base, {**key, "negative_design": negative}


def jsonl(values: list[dict]) -> bytes:
    return b"".join(compact(v).encode("utf-8") + b"\n" for v in values)


REPLAY_SOURCES = (
    "pastila-editor-core-v1.2-json-successor-v10-train.jsonl",
    "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl",
    "editor-core-v10-v12-targeted-continuation-r2-training.jsonl",
)


def replay(protective: bool) -> list[dict]:
    selected: list[dict] = []
    used: set[str] = set()
    safety = {"UNSUPPORTED_MATERIAL_CLAIMS", "EPISTEMIC_CALIBRATION", "TRANSITION_NO_NEW_FACTS",
              "INSUFFICIENT_AUTHORITY_ABSTENTION", "ENTITY_NUMBER_ROLE_FIDELITY"}
    for source in REPLAY_SOURCES:
        candidates = [json.loads(raw) for raw in (ART / source).read_bytes().splitlines()]
        candidates.sort(key=lambda row: (0 if protective and row.get("failure_class") in safety else 1,
                                         sha(canonical(row))))
        count = 0
        for row in candidates:
            identity = sha(canonical(row))
            if identity in used:
                continue
            used.add(identity)
            selected.append(row)
            count += 1
            if count == 16:
                break
        if count != 16:
            raise ValueError(f"insufficient replay: {source}")
    return selected


def generic_instruction_variant(row: dict) -> dict:
    """Hold source facts and target text fixed; remove operator-specific instruction."""
    clone = json.loads(json.dumps(row, ensure_ascii=False))
    original_id = clone["example_id"]
    clone["example_id"] = original_id + "-generic"
    user = clone["messages"][1]["content"]
    protocol, raw = user.split("\nINPUT=", 1)
    payload = json.loads(raw)
    payload["case_id"] = clone["example_id"]
    payload["request"] = "Redactează o relatare factuală, fidelă surselor, în română naturală."
    core = {k: v for k, v in payload.items() if k != "request_identity"}
    payload["request_identity"] = "sha256:" + sha(canonical(core))
    clone["messages"][1]["content"] = protocol + "\nINPUT=" + compact(payload)
    target = json.loads(clone["messages"][2]["content"])
    target["case_id"] = clone["example_id"]
    target["request_identity"] = payload["request_identity"]
    clone["messages"][2]["content"] = compact(target)
    clone["instruction_mode"] = "GENERIC_FACTUAL_REWRITE"
    return clone


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    system, protocol, source_hash = source_contract()
    grouped = {split: [] for split in ("TRAIN", "DEVELOPMENT", "INDEPENDENT_HOLDOUT")}
    for op in OPERATORS:
        for ordinal in range(len(SCENES)):
            grouped[SPLIT[ordinal]].append(case(op, ordinal, system, protocol))
    files: dict[str, dict] = {}

    def emit(label: str, values: list[dict]) -> None:
        raw = jsonl(values)
        path = output / f"{PREFIX}-{label}.jsonl"
        path.write_bytes(raw)
        files[label] = {"sha256": sha(raw), "bytes": len(raw), "rows": len(values)}

    mechanics_train = [item[0] for item in grouped["TRAIN"]]
    control_train = [item[1] for item in grouped["TRAIN"]]
    emit("train-mechanics", mechanics_train)
    emit("train-control", control_train)
    emit("train-mechanics-generic", [generic_instruction_variant(row) for row in mechanics_train])
    emit("train-control-generic", [generic_instruction_variant(row) for row in control_train])
    emit("replay-baseline", replay(False))
    emit("replay-protective", replay(True))
    for split, label in (("DEVELOPMENT", "development"), ("INDEPENDENT_HOLDOUT", "holdout")):
        emit(f"{label}-requests", [item[2] for item in grouped[split]])
        emit(f"{label}-answer-key", [item[3] for item in grouped[split]])
    emit("counterexamples", [item[3]["negative_design"] for split in grouped for item in grouped[split]])
    plan = {
        "schema": "pastila-editor-core-editorial-mechanics-bridge-plan", "schema_version": 1,
        "parent_adapter_identity": PARENT_ADAPTER, "parent_checkpoint_identity": PARENT_CHECKPOINT,
        "source_r2_corpus_sha256": source_hash, "training_authorized": False, "training_performed": False,
        "voice_or_comedy_training": False, "frozen_holdout_target_training_use": False,
        "operators": list(OPERATORS), "case_counts": {"train": 48, "development": 24, "holdout": 24},
        "split_by": "SYNTHETIC_EVENT_FAMILY; six train, three development, three holdout families shared across operators but disjoint across splits",
        "factorial": {
            "target_design": ["LITERAL_SAFE_CONTROL", "NEUTRAL_EDITORIAL_MECHANICS"],
            "instruction_signal": ["OPERATOR_SPECIFIC", "GENERIC_FACTUAL_REWRITE"],
            "recipe_strength": ["R2_LIKE", "STRONGER_PREDECLARED"],
            "replay_strategy": ["FIXED_BASELINE", "PROTECTIVE_SELECTION"],
            "one_factor_at_a_time": True,
            "arms": [
                {"id": "A0", "mode": "UNTRAINED_R2_PARENT"},
                {"id": "A1", "target": "LITERAL_SAFE_CONTROL", "instruction": "OPERATOR_SPECIFIC", "recipe": "R2_LIKE", "replay": "FIXED_BASELINE"},
                {"id": "A2", "target": "NEUTRAL_EDITORIAL_MECHANICS", "instruction": "OPERATOR_SPECIFIC", "recipe": "R2_LIKE", "replay": "FIXED_BASELINE"},
                {"id": "A3", "target": "LITERAL_SAFE_CONTROL", "instruction": "OPERATOR_SPECIFIC", "recipe": "STRONGER_PREDECLARED", "replay": "FIXED_BASELINE"},
                {"id": "A4", "target": "NEUTRAL_EDITORIAL_MECHANICS", "instruction": "OPERATOR_SPECIFIC", "recipe": "STRONGER_PREDECLARED", "replay": "FIXED_BASELINE"},
                {"id": "A5", "target": "NEUTRAL_EDITORIAL_MECHANICS", "instruction": "OPERATOR_SPECIFIC", "recipe": "R2_LIKE", "replay": "PROTECTIVE_SELECTION"},
                {"id": "A6", "target": "LITERAL_SAFE_CONTROL", "instruction": "GENERIC_FACTUAL_REWRITE", "recipe": "R2_LIKE", "replay": "FIXED_BASELINE"},
                {"id": "A7", "target": "NEUTRAL_EDITORIAL_MECHANICS", "instruction": "GENERIC_FACTUAL_REWRITE", "recipe": "R2_LIKE", "replay": "FIXED_BASELINE"},
            ],
            "fixed_training_rows_per_arm": 96,
            "replay_sources": list(REPLAY_SOURCES),
            "replay_selection": "48 deterministic rows, 16 per accepted V10/R1/R2 source; protective arm prioritizes labeled factual/epistemic/transition classes within each source",
            "recipe_values": {
                "R2_LIKE": {"learning_rate": "0.000003", "epochs": 1, "micro_batch_size": 1, "gradient_accumulation_steps": 8, "expected_steps": 12},
                "STRONGER_PREDECLARED": {"learning_rate": "0.000003", "epochs": 2, "micro_batch_size": 1, "gradient_accumulation_steps": 8, "expected_steps": 24},
            },
            "recipe_interpretation": "strength varies exposure/steps only; same LR, rows, order seed, parent and runtime; training-token budget must pass before authorization",
            "common_runtime": {"optimizer": "PAGED_ADAMW_8BIT_NEW_STATE", "scheduler": "CONSTANT_WITHOUT_WARMUP",
                               "precision": "BF16", "packing": False, "max_sequence_tokens": 3072,
                               "base_model_and_runtime": "BIND_TO_PUBLISHED_R2_COMPATIBLE_RUNTIME_BEFORE_EXECUTION"},
            "replicate_seeds": [271828, 314159, 161803],
            "research_runs": 21,
            "arm_a0": "ONE_FROZEN_R2_BASELINE_EVALUATION; NO_TRAINING",
        },
        "evaluation": {
            "gates": ["FACTUAL_EPISTEMIC_SAFETY", "EDITORIAL_REWRITE_QUALITY", "ROMANIAN_NATURALNESS", "REGRESSION_PROTECTION"],
            "safety_priority": "ANY_MATERIAL_FACTUAL_OR_EPISTEMIC_REGRESSION_BLOCKS_PARENT_SELECTION",
            "source_copy": "SAFE_COPY_CAN_PASS_FACTUALITY_BUT_FAIL_EXPLICIT_REWRITE_QUALITY",
            "exact_target_string": "DIAGNOSTIC_ONLY_NOT_SEMANTIC_VERDICT",
            "development_set": "TUNING_AND_FAILURE_MINING_ONLY",
            "holdout_set": "UNTOUCHED_UNTIL_ARM_SELECTION_RULES_FROZEN; NOT_USED_FOR_TUNING",
            "human_review": "BLINDED_CASE_BY_CASE_ON_SOURCE_BOUND_FACTUALITY_AND_EDITORIAL_QUALITY",
        },
    }
    plan_core = dict(plan)
    plan["plan_identity"] = sha(canonical(plan_core))
    plan_raw = json.dumps(plan, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    (output / f"{PREFIX}-plan.json").write_bytes(plan_raw)
    files["plan"] = {"sha256": sha(plan_raw), "bytes": len(plan_raw)}
    manifest_core = {"schema": "pastila-editor-core-editorial-mechanics-bridge-manifest", "schema_version": 1,
                     "status": "DESIGN_AND_DATA_ONLY", "parent_adapter_identity": PARENT_ADAPTER,
                     "parent_checkpoint_identity": PARENT_CHECKPOINT, "source_r2_corpus_sha256": source_hash,
                     "files": files, "training_performed": False, "adjudication_performed": False,
                     "development_parent_changed": False, "voice_or_comedy_material_imported": False}
    manifest = {**manifest_core, "manifest_identity": sha(canonical(manifest_core))}
    (output / f"{PREFIX}-manifest.json").write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    return {"manifest_identity": manifest["manifest_identity"], "plan_identity": plan["plan_identity"], "files": files}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), sort_keys=True))
