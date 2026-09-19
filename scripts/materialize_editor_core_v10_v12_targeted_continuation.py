"""Materialize the zero-training Editor Core V10 V1.2 continuation dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from pastila_scout.production_core_execution_contract_v10 import (
    EDITORIAL_PROMPT_SHA256,
    OUTPUT_PROTOCOL,
    canonical,
    contract_identity,
    render_training_messages,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-v1"
PARENT_ADAPTER = "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f"
PARENT_CHECKPOINT = "6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1"
BASE_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
SOURCE_TRAIN = ART / "pastila-editor-core-v1.2-json-successor-v10-train.jsonl"
REQUEST_MANIFEST = ART / "production-core-candidate-request-manifest-v2.json"

FAMILIES = (
    "UNSUPPORTED_MATERIAL_CLAIMS",
    "CROSS_EVENT_SOURCE_SEPARATION",
    "EPISTEMIC_CALIBRATION",
    "ENTITY_NUMBER_ROLE_FIDELITY",
    "INSUFFICIENT_AUTHORITY_ABSTENTION",
    "TRANSITION_NO_NEW_FACTS",
    "ROMANIAN_CONCISE_COMPLETION",
    "JSON_EOS_SCHEMA_CLOSURE",
)

NAMES = ("Arin", "Bistra", "Cerna", "Dorna", "Elan", "Făget", "Gura", "Halta", "Iaz", "Jiu", "Lunca", "Mureș")
PLACES = ("Alba", "Brașov", "Cluj", "Deva", "Focșani", "Galați", "Iași", "Lugoj", "Mediaș", "Oradea", "Sibiu", "Tulcea")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def seal(core: dict, field: str) -> dict:
    return {**core, field: sha(canonical(core))}


def protocol() -> str:
    manifest = json.loads(REQUEST_MANIFEST.read_bytes())
    prefixes = {r["candidate_visible_request"].split("\nINPUT=", 1)[0] for r in manifest["requests"]}
    if len(prefixes) != 1:
        raise ValueError("request protocol divergence")
    return next(iter(prefixes))


def authoritative_editorial(source_rows: list[dict]) -> bytes:
    combined = source_rows[0]["messages"][0]["content"]
    suffix = "\n\n" + OUTPUT_PROTOCOL
    if not combined.endswith(suffix):
        raise ValueError("V10 source system projection mismatch")
    raw = combined[:-len(suffix)].encode("utf-8")
    expected = EDITORIAL_PROMPT_SHA256["pastila-editor-core-v1.2-json-successor"]
    if sha(raw) != expected:
        raise ValueError("V10 editorial authority mismatch")
    return raw


def answer(case_id: str, request_id: str, output_type: str, text: str | None,
           bindings: list[list[str]], abstention: str | None = None) -> dict:
    return {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 2,
        "case_id": case_id,
        "request_identity": request_id,
        "output_type": output_type,
        "outcome": "ABSTAIN" if abstention else "ANSWER",
        "text": text,
        "claim_bindings": [
            {"claim_index": i, "source_span_ids": ids} for i, ids in enumerate(bindings, 1)
        ],
        "abstention_code": abstention,
    }


def scenario(family: str, ordinal: int, *, holdout: bool) -> tuple[dict, dict]:
    offset = 8 if holdout else 0
    k = ordinal + offset
    name = NAMES[k % len(NAMES)]
    place = PLACES[(k * 3 + 1) % len(PLACES)]
    value = 137 + 17 * k
    sid1 = f"ecv10r1:{'h' if holdout else 't'}:{family.lower()}:{ordinal}:1"
    sid2 = f"ecv10r1:{'h' if holdout else 't'}:{family.lower()}:{ordinal}:2"
    spans: list[dict[str, str]]
    output_type = "FACTUAL"
    shape = "MATERIAL_PROPOSITIONS"
    components: list[str] = []
    if family == "UNSUPPORTED_MATERIAL_CLAIMS":
        if holdout:
            spans = [{"span_id": sid1, "text": f"Fișa observatorului {name} numără {value} de înregistrări la punctul din {place}; documentul nu explică diferența față de luna trecută."}]
            request = "Compune nota numai din datele documentului și marchează limita explicației disponibile."
            target = answer("", "", output_type, f"Observatorul {name} a numărat {value} de înregistrări la punctul din {place}. Documentul nu explică diferența față de luna trecută.", [[sid1], [sid1]])
        else:
            spans = [{"span_id": sid1, "text": f"Buletinul Centrului {name} consemnează {value} de cereri în {place}, fără a indica motivul variației."}]
            request = "Redactează strict informația confirmată; nu completa cauza sau efectul din cunoștințe generale."
            target = answer("", "", output_type, f"Centrul {name} a consemnat {value} de cereri în {place}; buletinul nu indică motivul variației.", [[sid1], [sid1]])
    elif family == "CROSS_EVENT_SOURCE_SEPARATION":
        if holdout:
            spans = [
                {"span_id": sid1, "text": f"Muzeul {name} din {place} a amânat vernisajul până în ziua {12 + ordinal}."},
                {"span_id": sid2, "text": f"Separat, un muzeu din alt oraș a cumpărat {value} de obiecte pentru colecția sa."},
            ]
            request = f"Scrie doar despre programarea vernisajului de la Muzeul {name}; nu combina achiziția celeilalte instituții."
            target = answer("", "", output_type, f"Muzeul {name} din {place} a amânat vernisajul până în ziua {12 + ordinal}.", [[sid1]])
        else:
            spans = [
                {"span_id": sid1, "text": f"În {place}, operatorul {name} a suspendat linia {k + 2} timp de {k + 3} minute."},
                {"span_id": sid2, "text": f"Într-un eveniment separat din alt județ, compania Runc a anunțat un buget de {value} de mii de lei."},
            ]
            request = f"Rezuma exclusiv incidentul operatorului {name}; evenimentul separat nu îi aparține."
            target = answer("", "", output_type, f"În {place}, operatorul {name} a suspendat linia {k + 2} timp de {k + 3} minute.", [[sid1]])
    elif family == "EPISTEMIC_CALIBRATION":
        if holdout:
            spans = [{"span_id": sid1, "text": f"Inspectorii bănuiesc că asociația {name} ar fi omis {value} de poziții, iar verificarea administrativă este încă deschisă."}]
            request = "Relatează fără a transforma suspiciunea inspectorilor într-o constatare finală."
            target = answer("", "", output_type, f"Inspectorii bănuiesc că asociația {name} ar fi omis {value} de poziții. Verificarea administrativă este încă deschisă.", [[sid1], [sid1]])
        else:
            spans = [{"span_id": sid1, "text": f"Procurorii susțin că firma {name} ar fi raportat eronat {value} de unități; acuzația nu a fost judecată definitiv."}]
            request = "Păstrează explicit statutul de acuzație și lipsa unei hotărâri definitive."
            target = answer("", "", output_type, f"Procurorii susțin că firma {name} ar fi raportat eronat {value} de unități. Acuzația nu a fost judecată definitiv.", [[sid1], [sid1]])
    elif family == "ENTITY_NUMBER_ROLE_FIDELITY":
        if holdout:
            spans = [
                {"span_id": sid1, "text": f"Arhitectul-șef Luca {name} a inventariat precis {value} de planșe."},
                {"span_id": sid2, "text": f"Predarea va avea loc în {place}, la ora {9 + ordinal}:30, pe {18 + ordinal} ale lunii."},
            ]
            request = "Păstrează fără aproximare funcția, numele, cantitatea, ora, data și localitatea."
            target = answer("", "", output_type, f"Arhitectul-șef Luca {name} a inventariat precis {value} de planșe. Predarea va avea loc în {place}, la ora {9 + ordinal}:30, pe {18 + ordinal} ale lunii.", [[sid1], [sid2]])
        else:
            spans = [
                {"span_id": sid1, "text": f"Coordonatoarea Mara {name} a transmis că lotul are exact {value} de dosare."},
                {"span_id": sid2, "text": f"Verificarea este programată la {place} în ziua {10 + k} a lunii."},
            ]
            request = "Redă exact persoana, rolul, numărul, locul și data, fără substituții."
            target = answer("", "", output_type, f"Coordonatoarea Mara {name} a transmis că lotul are exact {value} de dosare. Verificarea este programată la {place} în ziua {10 + k} a lunii.", [[sid1], [sid2]])
    elif family == "INSUFFICIENT_AUTHORITY_ABSTENTION":
        if holdout:
            spans = [{"span_id": sid1, "text": f"Anunțul atelierului {name} confirmă anularea întâlnirii din {place}, fără să menționeze cine a cerut anularea."}]
            request = "Identifică persoana care a cerut anularea."
        else:
            spans = [{"span_id": sid1, "text": f"Nota instituției {name} confirmă deschiderea unei verificări în {place}, dar nu precizează autorul sesizării."}]
            request = "Numește autorul sesizării."
        target = answer("", "", output_type, None, [], "INSUFFICIENT_AUTHORITY")
    elif family == "TRANSITION_NO_NEW_FACTS":
        if holdout:
            spans = [{"span_id": sid1, "text": f"Secvența încheiată a prezentat calendarul cultural al organizației {name}."}]
            request = "Închide secvența și schimbă tema printr-o formulare neutră, fără informații despre tema următoare."
        else:
            spans = [{"span_id": sid1, "text": f"Materialul precedent privește raportul tehnic al centrului {name}."}]
            request = "Scrie o tranziție neutră către următorul subiect, fără fapte, actori sau relații noi."
        output_type = "COMMENTARY"
        shape = "QUALIFICATION_SENTENCE_UNITS"
        components = []
        target = answer("", "", output_type, "Schimbăm acum registrul discuției." if holdout else "Urmează un alt subiect, prezentat separat.", [])
    elif family == "ROMANIAN_CONCISE_COMPLETION":
        if holdout:
            spans = [{"span_id": sid1, "text": f"Grădina {name} din {place} primește vizitatori duminică, de la {7 + ordinal}:30 până la {15 + ordinal}:00."}]
            request = "Redă programul clar, într-un singur enunț românesc, apoi oprește răspunsul."
            target = answer("", "", output_type, f"Grădina {name} din {place} primește vizitatori duminică, de la {7 + ordinal}:30 până la {15 + ordinal}:00.", [[sid1]])
        else:
            spans = [{"span_id": sid1, "text": f"Biblioteca {name} din {place} va fi deschisă sâmbătă între orele {8 + k % 3}:00 și {14 + k % 4}:00."}]
            request = "Formulează o singură propoziție firească în română și încheie imediat."
            target = answer("", "", output_type, f"Biblioteca {name} din {place} va fi deschisă sâmbătă între orele {8 + k % 3}:00 și {14 + k % 4}:00.", [[sid1]])
    elif family == "JSON_EOS_SCHEMA_CLOSURE":
        if holdout:
            spans = [{"span_id": sid1, "text": f"Catalogul {name} certifică {value} de fișe procesate în punctul {place}."}]
            request = "Emite exclusiv obiectul JSON cerut și termină fluxul după acolada finală."
            target = answer("", "", output_type, f"Catalogul {name} certifică {value} de fișe procesate în punctul {place}.", [[sid1]])
        else:
            spans = [{"span_id": sid1, "text": f"Registrul {name} indică {value} de poziții validate la {place}."}]
            request = "Returnează răspunsul canonic o singură dată, fără Markdown, explicații sau continuare după obiect."
            target = answer("", "", output_type, f"Registrul {name} indică {value} de poziții validate la {place}.", [[sid1]])
    else:
        raise ValueError(family)
    input_value = {
        "case_id": "",
        "request_identity": "",
        "output_type": output_type,
        "required_factual_shape": shape,
        "expected_material_proposition_count": len(target["claim_bindings"]),
        "required_commentary_components": components,
        "request": request,
        "authority_spans": spans,
    }
    return input_value, target


def make_case(family: str, ordinal: int, *, holdout: bool, request_protocol: str,
              editorial: bytes) -> tuple[dict, dict]:
    split = "INDEPENDENT_HOLDOUT" if holdout else "TARGETED_TRAIN"
    case_id = f"ec-v10-v12-r1-{'holdout' if holdout else 'train'}-{FAMILIES.index(family)+1:02d}-{ordinal:02d}"
    request_id = "sha256:" + sha((case_id + ":independent-v1").encode())
    inp, target = scenario(family, ordinal, holdout=holdout)
    inp["case_id"] = case_id
    inp["request_identity"] = request_id
    target["case_id"] = case_id
    target["request_identity"] = request_id
    user = request_protocol + "\nINPUT=" + canonical(inp).decode()
    messages = list(render_training_messages(
        candidate="pastila-editor-core-v1.2-json-successor",
        editorial_prompt=editorial,
        user_prompt=user,
    ))
    meta = {
        "example_id": case_id,
        "split": split,
        "failure_class": family,
        "length_bucket": ("SHORT", "MEDIUM", "LONG", "ADVERSARIAL", "BOUNDARY")[(ordinal - 1) % 5],
    }
    request_row = {**meta, "messages": messages}
    answer_row = {
        "example_id": case_id,
        "request_identity": request_id,
        "failure_class": family,
        "assistant_target": canonical(target).decode(),
    }
    if not holdout:
        request_row["messages"] = messages + [{"role": "assistant", "content": answer_row["assistant_target"]}]
    return request_row, answer_row


def select_replay(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["length_bucket"]].append(row)
    quotas = {"SHORT": 13, "MEDIUM": 13, "LONG": 13, "ADVERSARIAL": 13, "BOUNDARY": 12}
    selected = []
    for bucket, quota in quotas.items():
        ranked = sorted(grouped[bucket], key=lambda r: sha(r["example_id"].encode()))
        selected.extend(ranked[:quota])
    return sorted(selected, key=lambda r: r["example_id"])


def write_jsonl(path: Path, rows: list[dict]) -> dict:
    raw = b"".join(canonical(row) + b"\n" for row in rows)
    path.write_bytes(raw)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(raw), "rows": len(rows), "bytes": len(raw)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ART)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    request_protocol = protocol()
    source_rows = [json.loads(line) for line in SOURCE_TRAIN.read_bytes().splitlines()]
    source_canonical_raw = b"".join(canonical(row) + b"\n" for row in source_rows)
    editorial = authoritative_editorial(source_rows)
    new_rows, holdout_rows, key_rows = [], [], []
    for family in FAMILIES:
        for ordinal in range(1, 9):
            row, _ = make_case(family, ordinal, holdout=False, request_protocol=request_protocol, editorial=editorial)
            new_rows.append(row)
        for ordinal in range(1, 5):
            row, key = make_case(family, ordinal, holdout=True, request_protocol=request_protocol, editorial=editorial)
            holdout_rows.append(row)
            key_rows.append(key)
    replay = select_replay(source_rows)
    combined = new_rows + replay
    artifacts = {}
    for suffix, rows in (
        ("new-train", new_rows),
        ("replay-anchors", replay),
        ("training", combined),
        ("holdout-requests", holdout_rows),
        ("holdout-answer-key", key_rows),
    ):
        name = f"{PREFIX}-{suffix}.jsonl"
        artifacts[suffix] = write_jsonl(args.output_dir / name, rows)
    config_core = {
        "schema": "pastila-editor-core-targeted-continuation-training-config",
        "schema_version": 1,
        "status": "PREPARED_TRAINING_NOT_AUTHORIZED",
        "candidate": "pastila-editor-core-v1.2-json-successor-targeted-r1",
        "parent_candidate": "pastila-editor-core-v1.2-json-successor-v10",
        "parent_adapter_content_identity": PARENT_ADAPTER,
        "parent_checkpoint_identity": PARENT_CHECKPOINT,
        "base_model_manifest_sha256": BASE_MODEL,
        "execution_contract_identity": contract_identity(),
        "training_corpus_sha256": artifacts["training"]["sha256"],
        "new_training_rows": 64,
        "replay_rows": 64,
        "independent_holdout_rows": 32,
        "objective": "ASSISTANT_ONLY_NEXT_TOKEN_CROSS_ENTROPY_EXPLICIT_EOS",
        "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE",
        "learning_rate": "0.000005",
        "scheduler": "CONSTANT_WITHOUT_WARMUP",
        "epochs": 1,
        "micro_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "max_sequence_tokens": 3072,
        "precision": "BF16",
        "weight_decay": "0.0",
        "seed": 314159,
        "packing": False,
        "shuffle": True,
        "checkpoint_policy": "SAVE_FINAL_AND_EVERY_8_OPTIMIZER_STEPS",
        "expected_optimizer_steps": 16,
        "network_activity": False,
        "training_authorized": False,
        "training_performed": False,
        "holdout_training_use": False,
        "r4_training_use": False,
        "human_receipt_training_use": False,
    }
    config = seal(config_core, "training_config_identity")
    config_path = args.output_dir / f"{PREFIX}-training-config.json"
    config_raw = json.dumps(config, ensure_ascii=False, indent=2).encode() + b"\n"
    config_path.write_bytes(config_raw)
    artifacts["training-config"] = {"path": config_path.relative_to(ROOT).as_posix(), "sha256": sha(config_raw)}
    manifest_core = {
        "schema": "pastila-editor-core-targeted-continuation-dataset-manifest",
        "schema_version": 1,
        "status": "PREPARED_ZERO_TRAINING",
        "parent_adapter_content_identity": PARENT_ADAPTER,
        "parent_checkpoint_identity": PARENT_CHECKPOINT,
        "base_model_manifest_sha256": BASE_MODEL,
        "failure_classes": list(FAMILIES),
        "rows_per_failure_class": {"new_train": 8, "holdout": 4},
        "artifacts": artifacts,
        "replay_source": {
            "path": SOURCE_TRAIN.relative_to(ROOT).as_posix(),
            "canonical_sha256": sha(source_canonical_raw),
            "worktree_physical_sha256": sha(SOURCE_TRAIN.read_bytes()),
            "eol_policy": "CANONICAL_JSON_LINES_LF",
            "selection": "SHA256_RANK_PER_LENGTH_BUCKET",
            "bucket_counts": {"SHORT": 13, "MEDIUM": 13, "LONG": 13, "ADVERSARIAL": 13, "BOUNDARY": 12},
        },
        "holdout_answer_key_separate": True,
        "training_performed": False,
        "candidate_execution_performed": False,
        "adjudication_performed": False,
    }
    manifest = seal(manifest_core, "manifest_identity")
    manifest_path = args.output_dir / f"{PREFIX}-manifest.json"
    manifest_path.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n")
    print(manifest["manifest_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
