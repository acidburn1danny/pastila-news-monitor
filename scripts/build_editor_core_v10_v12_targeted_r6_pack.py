"""Construct the R6 development dataset; no model or optimizer is loaded."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r6"
PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
NEW_ROWS, REPLAY_ROWS, HOLDOUT_ROWS = 18, 18, 12


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def ordered(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


SOURCE = rows(ART / "editor-core-v10-v12-targeted-continuation-r2-training.jsonl")
SYSTEM = SOURCE[0]["messages"][0]["content"]
PROTOCOL = SOURCE[0]["messages"][1]["content"].split("\nINPUT=", 1)[0]


def make_case(number: int, holdout: bool) -> tuple[dict, dict]:
    if not 1 <= number <= 30 or holdout != (number > NEW_ROWS):
        raise ValueError("R6 case/split mismatch")
    group = "h" if holdout else "t"
    case = f"ec-v10-v12-r6-{group}-{number:02d}"
    span = f"ecv10r6:{group}:{number}:1"
    quantity = 71 + 17 * number
    pattern = ("PETITION_ATTRIBUTION", "DRAFT_REPORT_CONTEST", "WITNESS_ATTRIBUTION")[((number - 1) % 3)]
    subject = ("Arhiva Vela", "Fundația Orizont", "Serviciul Atlas", "Depozitul Mistral", "Centrul Cobalt")[(number - 1) % 5] + f"-{number:02d}"
    if pattern == "PETITION_ATTRIBUTION":
        if holdout:
            authority = (f"Asociația Delta a sesizat că {subject} ar fi omis {quantity} de dosare din registru. "
                         f"{subject} respinge sesizarea și indică un registru alternativ. Verificatorul nu a confirmat "
                         "omisiunea; analiza rămâne deschisă.")
            target_text = (f"Asociația Delta a susținut că {subject} ar fi omis {quantity} de dosare. "
                           f"{subject} a respins sesizarea. Verificatorul nu a confirmat omisiunea, iar analiza continuă.")
        else:
            authority = (f"În memoriul său, Liga Nord a afirmat că {subject} ar fi exclus {quantity} de înregistrări. "
                         f"{subject} contestă această acuzație. Direcția de control nu a stabilit faptele, iar "
                         "procedura este încă în curs.")
            target_text = (f"Liga Nord a afirmat că {subject} ar fi exclus {quantity} de înregistrări. "
                           f"{subject} a contestat acuzația. Direcția de control nu a stabilit faptele; procedura continuă.")
        request = "Separă afirmația petentului, răspunsul entității și stadiul verificării, în română corectă."
    elif pattern == "DRAFT_REPORT_CONTEST":
        if holdout:
            authority = (f"Un proiect de audit ridică ipoteza că {subject} ar fi clasificat greșit {quantity} de cereri. "
                         f"{subject} a depus observații contrare. Proiectul nu este aprobat, iar examinarea continuă.")
            target_text = (f"Proiectul de audit sugerează că {subject} ar fi clasificat greșit {quantity} de cereri. "
                           f"{subject} a contestat evaluarea. Documentul nu este aprobat, iar examinarea continuă.")
        else:
            authority = (f"Nota preliminară a auditorilor indică posibilitatea ca {subject} să fi etichetat eronat "
                         f"{quantity} de loturi. {subject} a transmis obiecții scrise. Comisia nu a adoptat "
                         "o concluzie finală și continuă verificarea.")
            target_text = (f"Nota preliminară indică posibilitatea ca {subject} să fi etichetat eronat {quantity} "
                           f"de loturi. {subject} a depus obiecții. Comisia continuă verificarea fără concluzie finală.")
        request = "Redă caracterul provizoriu, contestarea și lipsa unei concluzii finale fără a afirma vinovăția."
    else:
        if holdout:
            authority = (f"Un martor a relatat că {subject} ar fi întârziat procesarea a {quantity} de solicitări. "
                         f"{subject} neagă relatarea. Ancheta nu a verificat încă afirmația și nu există decizie finală.")
            target_text = (f"Martorul a relatat că {subject} ar fi întârziat {quantity} de solicitări. "
                           f"{subject} a negat relatarea. Ancheta nu a verificat afirmația și nu există decizie finală.")
        else:
            authority = (f"Potrivit declarației unui fost angajat, {subject} ar fi reținut {quantity} de notificări. "
                         f"{subject} respinge declarația. Inspectorii investighează, dar nu au confirmat "
                         "neregula și nu au închis cazul.")
            target_text = (f"Fostul angajat a declarat că {subject} ar fi reținut {quantity} de notificări. "
                           f"{subject} a respins declarația. Inspectorii nu au confirmat neregula, iar cazul rămâne deschis.")
        request = "Atribuie explicit relatarea martorului și păstrează negația și incertitudinea procedurală."

    core = {"case_id": case, "output_type": "FACTUAL", "required_factual_shape": "MATERIAL_PROPOSITIONS",
            "expected_material_proposition_count": 3, "required_commentary_components": [], "request": request,
            "authority_spans": [{"span_id": span, "text": authority}]}
    identity = "sha256:" + digest(canonical(core))
    request = {"case_id": case, "request_identity": identity, **{k: v for k, v in core.items() if k != "case_id"}}
    target = {"schema": "pastila-core-v2-structured-qualification-response", "schema_version": 2,
              "case_id": case, "request_identity": identity, "output_type": "FACTUAL", "outcome": "ANSWER",
              "text": target_text,
              "claim_bindings": [{"claim_index": i, "source_span_ids": [span]} for i in (1, 2, 3)],
              "abstention_code": None}
    record = {"example_id": case, "split": "INDEPENDENT_HOLDOUT" if holdout else "TARGETED_TRAIN",
              "failure_class": "ATTRIBUTION_GRAMMAR", "diagnostic_pattern": pattern,
              "design_role": "GRAMMATICAL_ATTRIBUTION_WITH_EPISTEMIC_GUARD",
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": PROTOCOL + "\nINPUT=" + ordered(request)}]}
    key = {"example_id": case, "request_identity": identity, "failure_class": "ATTRIBUTION_GRAMMAR",
           "diagnostic_pattern": pattern, "assistant_target": ordered(target)}
    return {**record, "messages": record["messages"] + [{"role": "assistant", "content": ordered(target)}]}, key


REPLAY_SOURCES = {
    "v10_v1_2": "pastila-editor-core-v1.2-json-successor-v10-train.jsonl",
    "targeted_r1": "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl",
    "targeted_r2": "editor-core-v10-v12-targeted-continuation-r2-training.jsonl",
}


def select_replay() -> list[dict]:
    used: set[str] = set()
    chosen: list[dict] = []
    for source in REPLAY_SOURCES.values():
        count = 0
        for row in sorted(rows(ART / source), key=lambda item: digest(canonical(item))):
            identity = digest(canonical(row))
            if identity in used:
                continue
            chosen.append(row)
            used.add(identity)
            count += 1
            if count == 6:
                break
        if count != 6:
            raise ValueError(f"insufficient independent replay rows: {source}")
    return chosen


def write_jsonl(label: str, values: list[dict]) -> dict:
    path = ART / f"{PREFIX}-{label}.jsonl"
    path.write_bytes(b"".join(ordered(value).encode() + b"\n" for value in values))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path.read_bytes()),
            "rows": len(values), "bytes": path.stat().st_size}


def main() -> None:
    new = [make_case(index, False)[0] for index in range(1, NEW_ROWS + 1)]
    replay = select_replay()
    pairs = [make_case(index, True) for index in range(NEW_ROWS + 1, NEW_ROWS + HOLDOUT_ROWS + 1)]
    holdout = [{**row, "messages": row["messages"][:2]} for row, _ in pairs]
    keys = [key for _, key in pairs]
    artifacts = {name: write_jsonl(name, values) for name, values in (
        ("new-train", new), ("replay-anchors", replay), ("training", new + replay),
        ("holdout-requests", holdout), ("holdout-answer-key", keys))}
    config_core = {"schema": "pastila-editor-core-targeted-continuation-training-config", "schema_version": 3,
                   "status": "PREPARED_TRAINING_NOT_AUTHORIZED", "candidate": "pastila-editor-core-v1.2-json-successor-targeted-r6",
                   "parent_adapter_content_identity": PARENT, "parent_checkpoint_identity": CHECKPOINT,
                   "training_corpus_sha256": artifacts["training"]["sha256"],
                   "new_training_rows": NEW_ROWS, "replay_rows": REPLAY_ROWS,
                   "independent_holdout_rows": HOLDOUT_ROWS, "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE",
                   "learning_rate": "0.0000005", "scheduler": "CONSTANT_WITHOUT_WARMUP",
                   "epochs": 1, "micro_batch_size": 1, "gradient_accumulation_steps": 6,
                   "expected_optimizer_steps": 6, "max_sequence_tokens": 3072,
                   "precision": "BF16", "packing": False, "shuffle": True, "seed": 314159,
                   "r2_r3_r4_r5_holdout_training_use": False,
                   "rejected_r3_r4_r5_adapter_training_use": False,
                   "training_authorized": False, "training_performed": False}
    config = {**config_core, "training_config_identity": digest(canonical(config_core))}
    config_path = ART / f"{PREFIX}-training-config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifacts["training-config"] = {"path": config_path.relative_to(ROOT).as_posix(),
                                    "sha256": digest(config_path.read_bytes())}
    manifest_core = {"schema": "pastila-editor-core-targeted-continuation-dataset-manifest", "schema_version": 3,
                     "status": "PREPARED_ZERO_TRAINING", "parent_adapter_content_identity": PARENT,
                     "parent_checkpoint_identity": CHECKPOINT, "failure_classes": ["ATTRIBUTION_GRAMMAR"],
                     "diagnostic_patterns": ["PETITION_ATTRIBUTION", "DRAFT_REPORT_CONTEST", "WITNESS_ATTRIBUTION"],
                     "source_diagnostic_case_ids": ["ec-v10-v12-r5-h-13", "ec-v10-v12-r5-h-15"],
                     "rows": {"new_train": NEW_ROWS, "replay": REPLAY_ROWS, "holdout": HOLDOUT_ROWS},
                     "artifacts": artifacts, "replay_sources": {name: 6 for name in REPLAY_SOURCES},
                     "frozen_holdout_used_as_diagnostic_only": True,
                     "frozen_holdout_target_training_use": False,
                     "holdout_answer_key_separate": True, "training_performed": False}
    manifest = {**manifest_core, "manifest_identity": digest(canonical(manifest_core))}
    (ART / f"{PREFIX}-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_identity": manifest["manifest_identity"],
                      "config_identity": config["training_config_identity"], "artifacts": artifacts}, sort_keys=True))


if __name__ == "__main__":
    main()
