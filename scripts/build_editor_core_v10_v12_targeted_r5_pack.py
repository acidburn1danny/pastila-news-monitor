"""Build the R5 development pack. This never loads or trains a model."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r5"
PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()

def ordered(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]

source = rows(ART / "editor-core-v10-v12-targeted-continuation-r2-training.jsonl")
SYSTEM = source[0]["messages"][0]["content"]
PROTOCOL = source[0]["messages"][1]["content"].split("\nINPUT=", 1)[0]

def make_case(n, holdout):
    split = "INDEPENDENT_HOLDOUT" if holdout else "TARGETED_TRAIN"
    group = "h" if holdout else "t"
    pattern = "ATTRIBUTION_DENIAL_FINALITY" if n % 2 else "PRELIMINARY_CONTEST_PENDING"
    case = f"ec-v10-v12-r5-{group}-{n:02d}"
    span = f"ecv10r5:{group}:{n}:1"
    actor = f"Atelierul Meridian-{n:02d}"
    amount = 130 + 19 * n
    if pattern == "ATTRIBUTION_DENIAL_FINALITY":
        authority = (f"Într-o notă de inspecție, o asociație formulează suspiciunea că {actor} ar fi declarat "
                     f"incorect {amount} de piese. {actor} contestă acuzația și prezintă o evidență alternativă. "
                     "Autoritatea nu a stabilit încă faptele și nu există o hotărâre definitivă.")
        request = "Relatează pozițiile separate și stadiul incert, fără a transforma suspiciunea în fapt stabilit."
        answer = (f"Asociația suspectează că {actor} ar fi declarat incorect {amount} de piese. "
                  f"{actor} contestă acuzația. Faptele rămân neverificate și nu există hotărâre definitivă.")
    else:
        authority = (f"Un raport intermediar sugerează că {actor} ar fi încadrat greșit {amount} de loturi. "
                     f"{actor} a formulat obiecții documentate. Comisia continuă examinarea și nu a adoptat "
                     "o concluzie finală.")
        request = "Păstrează caracterul provizoriu, obiecția și examinarea deschisă în trei propoziții."
        answer = (f"Raportul intermediar apreciază că {actor} ar fi încadrat greșit {amount} de loturi. "
                  f"{actor} a depus obiecții. Examinarea continuă fără concluzie finală.")
    if holdout and pattern == "ATTRIBUTION_DENIAL_FINALITY":
        actor = f"Clinica Polaris-{n:02d}"
        authority = (f"Petiția unei organizații afirmă că există indicii potrivit cărora {actor} ar fi raportat "
                     f"eronat {amount} de consultații. Clinica respinge afirmația și solicită verificarea registrelor. "
                     "Inspectoratul nu a confirmat abaterea și procedura este încă deschisă.")
        request = "Distinge acuzația petentului de poziția clinicii și de constatarea încă neîncheiată a inspectoratului."
        answer = (f"Organizația suspectează că {actor} ar fi raportat eronat {amount} de consultații. "
                  "Clinica respinge acuzația. Inspectoratul nu a confirmat abaterea, iar procedura continuă.")
    elif holdout:
        actor = f"Cooperativa Solis-{n:02d}"
        authority = (f"Un proiect de constatare al auditorilor avansează posibilitatea ca {actor} să fi înregistrat "
                     f"necorespunzător {amount} de livrări. Cooperativa a transmis un răspuns de contestare. "
                     "Documentul este preliminar; analiza probelor nu s-a încheiat.")
        request = "Redă evaluarea ca provizorie, menționează contestarea și evită un verdict de vinovăție."
        answer = (f"Proiectul auditorilor sugerează posibilitatea unei înregistrări greșite a {amount} de livrări "
                  f"de către {actor}. Cooperativa contestă evaluarea. Analiza rămâne preliminară și neîncheiată.")
    core = {"case_id": case, "output_type": "FACTUAL", "required_factual_shape": "MATERIAL_PROPOSITIONS",
            "expected_material_proposition_count": 3, "required_commentary_components": [], "request": request,
            "authority_spans": [{"span_id": span, "text": authority}]}
    identity = "sha256:" + digest(canonical(core))
    inp = {"case_id": case, "request_identity": identity, **{k: v for k, v in core.items() if k != "case_id"}}
    target = {"schema": "pastila-core-v2-structured-qualification-response", "schema_version": 2,
              "case_id": case, "request_identity": identity, "output_type": "FACTUAL", "outcome": "ANSWER",
              "text": answer, "claim_bindings": [{"claim_index": i, "source_span_ids": [span]} for i in (1, 2, 3)],
              "abstention_code": None}
    base = {"example_id": case, "split": split, "failure_class": "EPISTEMIC_CALIBRATION",
            "diagnostic_pattern": pattern, "design_role": "ATTRIBUTION_REPAIR" if n % 2 else "GAIN_GUARD",
            "length_bucket": ("SHORT", "MEDIUM", "LONG")[(n - 1) % 3],
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": PROTOCOL + "\nINPUT=" + ordered(inp)}]}
    training = {**base, "messages": base["messages"] + [{"role": "assistant", "content": ordered(target)}]}
    key = {"example_id": case, "request_identity": identity, "failure_class": "EPISTEMIC_CALIBRATION",
           "diagnostic_pattern": pattern, "assistant_target": ordered(target)}
    return training, key

def select_replay():
    used = set()
    sources = ["pastila-editor-core-v1.2-json-successor-v10-train.jsonl",
               "editor-core-v10-v12-targeted-continuation-v1-new-train.jsonl",
               "editor-core-v10-v12-targeted-continuation-r2-training.jsonl"]
    result = []
    for source_name in sources:
        chosen = []
        for row in sorted(rows(ART / source_name), key=lambda x: digest(canonical(x))):
            identity = digest(canonical(row))
            if identity not in used:
                used.add(identity)
                chosen.append(row)
                if len(chosen) == 8:
                    break
        if len(chosen) != 8:
            raise ValueError("insufficient distinct replay anchors: " + source_name)
        result.extend(chosen)
    return result

def write_jsonl(label, values):
    path = ART / f"{PREFIX}-{label}.jsonl"
    path.write_bytes(b"".join(ordered(v).encode() + b"\n" for v in values))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path.read_bytes()),
            "rows": len(values), "bytes": path.stat().st_size}

def main():
    new = [make_case(n, False)[0] for n in range(1, 13)]
    replay = select_replay()
    holdout_pairs = [make_case(n, True) for n in range(13, 25)]
    holdout = [{**row, "messages": row["messages"][:2]} for row, _ in holdout_pairs]
    key = [k for _, k in holdout_pairs]
    artifacts = {"new-train": write_jsonl("new-train", new),
                 "replay-anchors": write_jsonl("replay-anchors", replay),
                 "training": write_jsonl("training", new + replay),
                 "holdout-requests": write_jsonl("holdout-requests", holdout),
                 "holdout-answer-key": write_jsonl("holdout-answer-key", key)}
    config_core = {"schema": "pastila-editor-core-targeted-continuation-training-config", "schema_version": 3,
                   "status": "PREPARED_TRAINING_NOT_AUTHORIZED", "candidate": "pastila-editor-core-v1.2-json-successor-targeted-r5",
                   "parent_adapter_content_identity": PARENT, "parent_checkpoint_identity": CHECKPOINT,
                   "training_corpus_sha256": artifacts["training"]["sha256"],
                   "new_training_rows": 12, "replay_rows": 24, "independent_holdout_rows": 12,
                   "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE", "learning_rate": "0.0000005",
                   "scheduler": "CONSTANT_WITHOUT_WARMUP", "epochs": 1, "micro_batch_size": 1,
                   "gradient_accumulation_steps": 6, "expected_optimizer_steps": 6,
                   "max_sequence_tokens": 3072, "precision": "BF16", "packing": False, "shuffle": True,
                   "seed": 314159, "r2_holdout_training_use": False, "r3_holdout_training_use": False,
                   "r4_holdout_training_use": False, "rejected_r3_r4_adapter_training_use": False,
                   "training_authorized": False, "training_performed": False}
    config = {**config_core, "training_config_identity": digest(canonical(config_core))}
    config_path = ART / f"{PREFIX}-training-config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifacts["training-config"] = {"path": config_path.relative_to(ROOT).as_posix(), "sha256": digest(config_path.read_bytes())}
    manifest_core = {"schema": "pastila-editor-core-targeted-continuation-dataset-manifest", "schema_version": 3,
                     "status": "PREPARED_ZERO_TRAINING", "parent_adapter_content_identity": PARENT,
                     "parent_checkpoint_identity": CHECKPOINT, "failure_classes": ["EPISTEMIC_CALIBRATION"],
                     "diagnostic_patterns": ["ATTRIBUTION_DENIAL_FINALITY", "PRELIMINARY_CONTEST_PENDING"],
                     "source_diagnostic_case_ids": ["ec-v10-v12-r4-holdout-epistemic-calibration-15",
                                                    "ec-v10-v12-r4-holdout-epistemic-calibration-17",
                                                    "ec-v10-v12-r4-holdout-epistemic-calibration-19"],
                     "gain_guard_case_ids": ["ec-v10-v12-r4-holdout-epistemic-calibration-21",
                                             "ec-v10-v12-r4-holdout-epistemic-calibration-23"],
                     "rows": {"new_train": 12, "replay": 24, "holdout": 12},
                     "artifacts": artifacts, "replay_sources": {"v10_v1_2": 8, "targeted_r1": 8, "targeted_r2": 8},
                     "frozen_holdout_used_as_diagnostic_only": True, "frozen_holdout_target_training_use": False,
                     "holdout_answer_key_separate": True, "training_performed": False}
    manifest = {**manifest_core, "manifest_identity": digest(canonical(manifest_core))}
    (ART / f"{PREFIX}-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_identity": manifest["manifest_identity"], "config_identity": config["training_config_identity"], "artifacts": artifacts}, sort_keys=True))

if __name__ == "__main__":
    main()
