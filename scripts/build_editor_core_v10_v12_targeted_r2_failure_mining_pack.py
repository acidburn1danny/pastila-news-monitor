"""Build the deterministic R2 failure-mining pack without training or inference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r2"
PARENT_ADAPTER = "50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4"
PARENT_CHECKPOINT = "00ee968941f8cba8ea47534d441c272c7a3120f9076953aa552f67e302a0ceef"
CLASSES = ("UNSUPPORTED_MATERIAL_CLAIMS", "EPISTEMIC_CALIBRATION", "TRANSITION_NO_NEW_FACTS")
NAMES = ("Arin", "Brumăr", "Cerna", "Dorna", "Ezer", "Făget", "Gorun", "Hârtop", "Iaz", "Jder", "Luncavăț", "Mesteacăn", "Nucet", "Oituz", "Paltin", "Runc", "Siret", "Tisa")
CITIES = ("Alba Iulia", "Bacău", "Călărași", "Deva", "Făgăraș", "Giurgiu", "Huși", "Iași", "Lugoj", "Mediaș", "Năsăud", "Oradea", "Pitești", "Roman", "Sebeș", "Tulcea", "Urziceni", "Zalău")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def ordered(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


source = read_jsonl(ART / "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl")
system = source[0]["messages"][0]["content"]
protocol = source[0]["messages"][1]["content"].split("\nINPUT=", 1)[0]


def make_input(family: str, ordinal: int, split: str) -> tuple[dict, dict]:
    case_id = f"ec-v10-v12-r2-{'train' if split == 'TARGETED_TRAIN' else 'holdout'}-{family.lower().replace('_', '-')}-{ordinal:02d}"
    name, city, number = NAMES[ordinal - 1], CITIES[ordinal - 1], 211 + ordinal * 17
    span_id = f"ecv10r2:{'t' if split == 'TARGETED_TRAIN' else 'h'}:{family.lower()}:{ordinal}:1"
    holdout = split == "INDEPENDENT_HOLDOUT"
    if family == "UNSUPPORTED_MATERIAL_CLAIMS":
        if holdout:
            authority = f"Fișa de monitorizare {name} înregistrează {number} de sesizări în {city}. Raportul nu oferă o explicație pentru evoluția față de perioada precedentă."
            request = "Rezumați datele disponibile fără a atribui un motiv schimbării observate."
            text = f"Fișa de monitorizare {name} înregistrează {number} de sesizări în {city}. Raportul nu explică evoluția față de perioada precedentă."
        else:
            authority = f"Registrul unității {name} consemnează {number} de solicitări la punctul din {city}; documentul nu precizează cauza diferenței față de trimestrul anterior."
            request = "Redactează numai constatările documentate și păstrează explicit necunoscută explicația variației."
            text = f"Unitatea {name} a consemnat {number} de solicitări la punctul din {city}. Documentul nu precizează cauza diferenței față de trimestrul anterior."
        output_type, shape, count = "FACTUAL", "MATERIAL_PROPOSITIONS", 2
        bindings = [{"claim_index": i, "source_span_ids": [span_id]} for i in (1, 2)]
    elif family == "EPISTEMIC_CALIBRATION":
        if holdout:
            authority = f"Potrivit sesizării controlorilor, societatea {name} este suspectată că a înscris incorect {number} de poziții la {city}. Societatea respinge susținerea, iar dosarul nu are o soluție definitivă."
            request = "Relatați prudent pozițiile consemnate și stadiul încă nesoluționat al dosarului."
            text = f"Controlorii suspectează că societatea {name} a înscris incorect {number} de poziții la {city}. Societatea respinge susținerea, iar dosarul nu are o soluție definitivă."
        else:
            authority = f"Inspectorii afirmă că operatorul {name} ar fi declarat eronat {number} de unități în {city}; constatarea este contestată și nu există o hotărâre definitivă."
            request = "Păstrează distinct afirmația inspectorilor, contestarea și lipsa unei hotărâri definitive."
            text = f"Inspectorii afirmă că operatorul {name} ar fi declarat eronat {number} de unități în {city}. Constatarea este contestată și nu există o hotărâre definitivă."
        output_type, shape, count = "FACTUAL", "MATERIAL_PROPOSITIONS", 2
        bindings = [{"claim_index": i, "source_span_ids": [span_id]} for i in (1, 2)]
    else:
        if holdout:
            authority = f"Textul încheiat anterior a descris procesul-verbal asociat centrului {name}."
            request = "Formulați o trecere scurtă spre tema următoare, fără informații sau conexiuni suplimentare."
            text = ("Schimbăm tema și mergem mai departe." if ordinal % 2 else "Trecem acum la o secțiune diferită.")
        else:
            authority = f"Secțiunea anterioară s-a încheiat cu prezentarea notei tehnice a unității {name}."
            request = "Scrie o tranziție neutră și autonomă către următorul subiect, fără a introduce fapte, cauze, actori sau legături noi."
            text = ("Continuăm cu un subiect distinct, prezentat separat." if ordinal % 2 else "Urmează o temă diferită, tratată separat.")
        output_type, shape, count = "COMMENTARY", "QUALIFICATION_SENTENCE_UNITS", 0
        bindings = []
    core = {
        "case_id": case_id,
        "output_type": output_type,
        "required_factual_shape": shape,
        "expected_material_proposition_count": count,
        "required_commentary_components": [],
        "request": request,
        "authority_spans": [{"span_id": span_id, "text": authority}],
    }
    identity = "sha256:" + sha(canonical(core))
    inp = {"case_id": case_id, "request_identity": identity, **{k: v for k, v in core.items() if k != "case_id"}}
    target = {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 2,
        "case_id": case_id,
        "request_identity": identity,
        "output_type": output_type,
        "outcome": "ANSWER",
        "text": text,
        "claim_bindings": bindings,
        "abstention_code": None,
    }
    return inp, target


def make_row(family: str, ordinal: int, split: str) -> tuple[dict, dict]:
    inp, target = make_input(family, ordinal, split)
    base = {
        "example_id": inp["case_id"],
        "split": split,
        "failure_class": family,
        "length_bucket": ("SHORT", "MEDIUM", "LONG")[(ordinal - 1) % 3],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": protocol + "\nINPUT=" + ordered(inp)}],
    }
    train = {**base, "messages": base["messages"] + [{"role": "assistant", "content": ordered(target)}]}
    key = {"example_id": inp["case_id"], "request_identity": inp["request_identity"], "failure_class": family, "assistant_target": ordered(target)}
    return train, key


new_rows, holdout_rows, key_rows = [], [], []
for family in CLASSES:
    for ordinal in range(1, 13):
        row, _ = make_row(family, ordinal, "TARGETED_TRAIN")
        new_rows.append(row)
    for ordinal in range(13, 19):
        row, key = make_row(family, ordinal, "INDEPENDENT_HOLDOUT")
        holdout_rows.append({**row, "messages": row["messages"][:2]})
        key_rows.append(key)

v10 = read_jsonl(ART / "pastila-editor-core-v1.2-json-successor-v10-train.jsonl")
r1 = source
v10_replay = sorted(v10, key=lambda row: sha(canonical(row)))[:18]
r1_replay = sorted(r1, key=lambda row: sha(canonical(row)))[:18]
replay = v10_replay + r1_replay
training = new_rows + replay


def write_jsonl(name: str, values: list[dict]) -> dict:
    path = ART / f"{PREFIX}-{name}.jsonl"
    path.write_bytes(b"".join(ordered(value).encode() + b"\n" for value in values))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path.read_bytes()), "rows": len(values), "bytes": path.stat().st_size}


artifacts = {
    "new-train": write_jsonl("new-train", new_rows),
    "replay-anchors": write_jsonl("replay-anchors", replay),
    "training": write_jsonl("training", training),
    "holdout-requests": write_jsonl("holdout-requests", holdout_rows),
    "holdout-answer-key": write_jsonl("holdout-answer-key", key_rows),
}
config_core = {
    "schema": "pastila-editor-core-targeted-continuation-training-config",
    "schema_version": 2,
    "status": "PREPARED_TRAINING_NOT_AUTHORIZED",
    "candidate": "pastila-editor-core-v1.2-json-successor-targeted-r2",
    "parent_adapter_content_identity": PARENT_ADAPTER,
    "parent_checkpoint_identity": PARENT_CHECKPOINT,
    "training_corpus_sha256": artifacts["training"]["sha256"],
    "new_training_rows": 36,
    "replay_rows": 36,
    "independent_holdout_rows": 18,
    "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE",
    "learning_rate": "0.000003",
    "scheduler": "CONSTANT_WITHOUT_WARMUP",
    "epochs": 1,
    "micro_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "expected_optimizer_steps": 9,
    "max_sequence_tokens": 3072,
    "precision": "BF16",
    "packing": False,
    "shuffle": True,
    "seed": 271828,
    "holdout_training_use": False,
    "r4_training_use": False,
    "training_authorized": False,
    "training_performed": False,
}
config = {**config_core, "training_config_identity": sha(canonical(config_core))}
config_path = ART / f"{PREFIX}-training-config.json"
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
artifacts["training-config"] = {"path": config_path.relative_to(ROOT).as_posix(), "sha256": sha(config_path.read_bytes())}
manifest_core = {
    "schema": "pastila-editor-core-targeted-continuation-dataset-manifest",
    "schema_version": 2,
    "status": "PREPARED_ZERO_TRAINING",
    "parent_adapter_content_identity": PARENT_ADAPTER,
    "parent_checkpoint_identity": PARENT_CHECKPOINT,
    "failure_classes": list(CLASSES),
    "rows_per_failure_class": {"new_train": 12, "holdout": 6},
    "artifacts": artifacts,
    "replay_sources": {
        "v10_v1_2": {"rows": 18, "source": "docs/artifacts/pastila-editor-core-v1.2-json-successor-v10-train.jsonl"},
        "targeted_r1": {"rows": 18, "source": "docs/artifacts/editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl"},
    },
    "holdout_answer_key_separate": True,
    "prior_holdout_targets_reused": False,
    "r4_evidence_used": False,
    "training_performed": False,
}
manifest = {**manifest_core, "manifest_identity": sha(canonical(manifest_core))}
(ART / f"{PREFIX}-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"manifest_identity": manifest["manifest_identity"], "training_config_identity": config["training_config_identity"], "artifacts": artifacts}, sort_keys=True))
