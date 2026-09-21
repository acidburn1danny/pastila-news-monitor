"""Build the deterministic R4 corrective pack without training."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r4"
PARENT_ADAPTER = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
PARENT_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
DIAGNOSTICS = [
    "ec-v10-v12-r3-holdout-epistemic-calibration-27",
    "ec-v10-v12-r3-holdout-epistemic-calibration-29",
    "ec-v10-v12-r3-holdout-epistemic-calibration-33",
]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def ordered(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


source = read_jsonl(ART / "editor-core-v10-v12-targeted-continuation-r2-training.jsonl")
system = source[0]["messages"][0]["content"]
protocol = source[0]["messages"][1]["content"].split("\nINPUT=", 1)[0]


def make_row(ordinal: int, holdout: bool) -> tuple[dict, dict]:
    split = "INDEPENDENT_HOLDOUT" if holdout else "TARGETED_TRAIN"
    kind = "holdout" if holdout else "train"
    case_id = f"ec-v10-v12-r4-{kind}-epistemic-calibration-{ordinal:02d}"
    number = 700 + ordinal * 13
    span_id = f"ecv10r4:{'h' if holdout else 't'}:epistemic:{ordinal}:1"
    actor = f"Compania Vela-{ordinal:02d}"
    location = f"depozitul Est-{ordinal:02d}"
    pattern = "ATTRIBUTION_DENIAL_FINALITY" if (holdout and ordinal % 2) or (not holdout and ordinal <= 8) else "PRELIMINARY_CONTEST_PENDING"
    if not holdout and pattern == "ATTRIBUTION_DENIAL_FINALITY":
        authority = f"Raportul grupului de control descrie numai bănuiala că {actor} ar fi omis {number} de unități la {location}. Compania respinge această bănuială. Examinarea nu s-a încheiat definitiv."
        request = "Redă bănuiala ca poziție atribuită, menține forma condițională și separă răspunsul companiei de stadiul nefinalizat."
        text = f"Grupul de control bănuiește că {actor} ar fi omis {number} de unități la {location}. Compania respinge bănuiala. Examinarea nu este încheiată definitiv."
    elif not holdout:
        authority = f"O fișă de lucru nefinalizată consemnează aprecierea provizorie că {actor} ar fi încadrat greșit {number} de operațiuni la {location}. Compania contestă evaluarea. Revizuirea continuă."
        request = "Rezumați caracterul provizoriu, obiecția companiei și continuarea revizuirii, fără o concluzie definitivă."
        text = f"Fișa de lucru formulează provizoriu aprecierea că {actor} ar fi încadrat greșit {number} de operațiuni la {location}. Compania a formulat obiecții. Revizuirea rămâne în curs."
    elif pattern == "ATTRIBUTION_DENIAL_FINALITY":
        authority = f"Minuta ședinței prezintă ca suspiciune posibilitatea ca {actor} să fi omis {number} de poziții la {location}. Compania neagă posibilitatea descrisă. Ancheta nu are o soluție finală."
        request = "Păstrați statutul de suspiciune, negarea separată și lipsa soluției finale."
        text = f"Minuta consemnează suspiciunea că {actor} ar fi omis {number} de poziții la {location}. Compania neagă suspiciunea. Ancheta nu are o soluție finală."
    else:
        authority = f"Concluzia intermediară a verificatorilor apreciază că {actor} ar fi etichetat eronat {number} de înregistrări la {location}. Compania a depus obiecții. Verificarea continuă fără concluzie finală."
        request = "Separați concluzia intermediară, obiecțiile și stadiul încă deschis."
        text = f"Verificatorii apreciază intermediar că {actor} ar fi etichetat eronat {number} de înregistrări la {location}. Compania a depus obiecții. Verificarea rămâne deschisă."
    core = {
        "case_id": case_id, "output_type": "FACTUAL", "required_factual_shape": "MATERIAL_PROPOSITIONS",
        "expected_material_proposition_count": 3, "required_commentary_components": [], "request": request,
        "authority_spans": [{"span_id": span_id, "text": authority}],
    }
    identity = "sha256:" + sha(canonical(core))
    inp = {"case_id": case_id, "request_identity": identity, **{k: v for k, v in core.items() if k != "case_id"}}
    target = {
        "schema": "pastila-core-v2-structured-qualification-response", "schema_version": 2,
        "case_id": case_id, "request_identity": identity, "output_type": "FACTUAL", "outcome": "ANSWER",
        "text": text, "claim_bindings": [{"claim_index": i, "source_span_ids": [span_id]} for i in (1, 2, 3)],
        "abstention_code": None,
    }
    base = {
        "example_id": case_id, "split": split, "failure_class": "EPISTEMIC_CALIBRATION",
        "diagnostic_pattern": pattern, "length_bucket": ("SHORT", "MEDIUM", "LONG")[(ordinal - 1) % 3],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": protocol + "\nINPUT=" + ordered(inp)}],
    }
    train = {**base, "messages": base["messages"] + [{"role": "assistant", "content": ordered(target)}]}
    key = {"example_id": case_id, "request_identity": identity, "failure_class": "EPISTEMIC_CALIBRATION", "diagnostic_pattern": pattern, "assistant_target": ordered(target)}
    return train, key


new_rows = [make_row(n, False)[0] for n in range(1, 13)]
holdout_pairs = [make_row(n, True) for n in range(13, 25)]
holdout_rows = [{**row, "messages": row["messages"][:2]} for row, _ in holdout_pairs]
key_rows = [key for _, key in holdout_pairs]


def take_unique(rows: list[dict], count: int, used: set[str]) -> list[dict]:
    result = []
    for row in sorted(rows, key=lambda item: sha(canonical(item))):
        identity = sha(canonical(row))
        if identity not in used:
            used.add(identity); result.append(row)
            if len(result) == count:
                return result
    raise ValueError("insufficient unique replay rows")


used: set[str] = set()
replay = []
for name in ("pastila-editor-core-v1.2-json-successor-v10-train.jsonl", "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl", "editor-core-v10-v12-targeted-continuation-r2-training.jsonl"):
    replay += take_unique(read_jsonl(ART / name), 12, used)
training = new_rows + replay


def write_jsonl(name: str, values: list[dict]) -> dict:
    path = ART / f"{PREFIX}-{name}.jsonl"
    path.write_bytes(b"".join(ordered(value).encode() + b"\n" for value in values))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path.read_bytes()), "rows": len(values), "bytes": path.stat().st_size}


artifacts = {
    "new-train": write_jsonl("new-train", new_rows), "replay-anchors": write_jsonl("replay-anchors", replay),
    "training": write_jsonl("training", training), "holdout-requests": write_jsonl("holdout-requests", holdout_rows),
    "holdout-answer-key": write_jsonl("holdout-answer-key", key_rows),
}
config_core = {
    "schema": "pastila-editor-core-targeted-continuation-training-config", "schema_version": 3,
    "status": "PREPARED_TRAINING_NOT_AUTHORIZED", "candidate": "pastila-editor-core-v1.2-json-successor-targeted-r4",
    "parent_adapter_content_identity": PARENT_ADAPTER, "parent_checkpoint_identity": PARENT_CHECKPOINT,
    "training_corpus_sha256": artifacts["training"]["sha256"], "new_training_rows": 12, "replay_rows": 36,
    "independent_holdout_rows": 12, "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE", "learning_rate": "0.000001",
    "scheduler": "CONSTANT_WITHOUT_WARMUP", "epochs": 1, "micro_batch_size": 1,
    "gradient_accumulation_steps": 8, "expected_optimizer_steps": 6, "max_sequence_tokens": 3072,
    "precision": "BF16", "packing": False, "shuffle": True, "seed": 314159,
    "r2_holdout_training_use": False, "r3_holdout_training_use": False, "r4_evidence_used": False,
    "rejected_r3_adapter_training_use": False, "training_authorized": False, "training_performed": False,
}
config = {**config_core, "training_config_identity": sha(canonical(config_core))}
config_path = ART / f"{PREFIX}-training-config.json"
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
artifacts["training-config"] = {"path": config_path.relative_to(ROOT).as_posix(), "sha256": sha(config_path.read_bytes())}
manifest_core = {
    "schema": "pastila-editor-core-targeted-continuation-dataset-manifest", "schema_version": 3,
    "status": "PREPARED_ZERO_TRAINING", "parent_adapter_content_identity": PARENT_ADAPTER,
    "parent_checkpoint_identity": PARENT_CHECKPOINT, "failure_classes": ["EPISTEMIC_CALIBRATION"],
    "diagnostic_patterns": ["ATTRIBUTION_DENIAL_FINALITY", "PRELIMINARY_CONTEST_PENDING"],
    "source_diagnostic_case_ids": DIAGNOSTICS, "rows": {"new_train": 12, "replay": 36, "holdout": 12},
    "artifacts": artifacts,
    "replay_sources": {"v10_v1_2": 12, "targeted_r1": 12, "targeted_r2": 12},
    "r3_holdout_used_as_diagnostic_only": True, "r3_holdout_training_use": False,
    "rejected_r3_adapter_training_use": False, "holdout_answer_key_separate": True,
    "r4_evidence_used": False, "training_performed": False,
}
manifest = {**manifest_core, "manifest_identity": sha(canonical(manifest_core))}
(ART / f"{PREFIX}-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"manifest_identity": manifest["manifest_identity"], "training_config_identity": config["training_config_identity"], "artifacts": artifacts}, sort_keys=True))
