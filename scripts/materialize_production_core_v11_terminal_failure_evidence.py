"""Materialize V11 terminal disposition and stale-runner root-cause addendum."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / ".pastila-runtime/production-core-successor-execution-v11-attempt1"
RUNNER = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v3.py"
LAUNCHER = ROOT / "scripts/run_production_core_candidate_qualification_v11.sh"
AUTHORITY_PATH = ROOT / "docs/artifacts/production-core-candidate-execution-authority-v11.json"
GENERATION_PATH = ROOT / "docs/artifacts/production-core-successor-comparative-qualification-generation-v10.json"
ATTEMPT = "b1423e52b38f208b0bfcb0b8350e144ff7197af41e81451b61b99f199c334227"
AUTHORITY = "36e6ef21c93b597558714952974d32df9506fa0f64dc86c66da54f5f6a106118"
FAILURE = "f7116832890471cb7cf00e059be5e8a9023dcdbcf3e0da2db21e2a8568e26cbf"
GENERATION = "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
STALE_GENERATION = "b7af3517a14e987efa344e9cd9c7bcbbdd9ddb3656cc9060e72fdca71ca7c8d2"
HASHES = {
    "attempt": "8151479c6636c630880974703153732725c399b4db994b076b21360cbfccd45f",
    "terminal_failure": "95631554ec1a25afd00c54287fc96404c86a49e1694d065d4266e66ce7d3702e",
    "batch": "699be4dd51411664ede157f7fac6c6927b3c60ac511067d2a8a59eed1f2d28c3",
    "system_prompt": "70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36",
    "file_boundary": "d626a2ea8a1e7a05e0efdb116a1da5670cb9b2df512dac7f5f24402ff42fc0ca",
    "network_boundary": "abbd3cb07265e3479beab667bccc060088d55b016efd5262cafdf0ae52d34c4c",
    "runner_source": "ad29f2820159a7f47199a572db6c3f9a42b8664e0f2e3959d618a06513ad695f",
    "launcher_source": "ceddefe2fca34cf7edbda08518c15604172a25ad074029b8686fc5236f26bc7d",
    "execution_authority": "c8c40883b04b5b043345da1021142b9243e0a9458a756dcef36f267b5ae7e7ee",
    "qualification_generation": "2ca33d629ebdbc32e77f06d0365dc94e8aebc84b0848826244c39c2cfd396039",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def identity(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"evidence path rejected: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def constant(source: Path, name: str):
    tree = ast.parse(source.read_text("utf-8"))
    rows = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    if len(rows) != 1:
        raise ValueError(f"runner constant missing: {name}")
    return rows[0]


def build(execution=EXECUTION):
    paths = {
        "attempt": execution / "attempt.json",
        "terminal_failure": execution / "terminal-failure.json",
        "batch": execution / ".checkpoint-01.in-progress/batch.json",
        "system_prompt": execution / ".checkpoint-01.in-progress/system-prompt.txt",
        "file_boundary": execution / ".checkpoint-01.in-progress/results/file-boundary.json",
        "network_boundary": execution / ".checkpoint-01.in-progress/results/network-boundary.json",
        "runner_source": RUNNER,
        "launcher_source": LAUNCHER,
        "execution_authority": AUTHORITY_PATH,
        "qualification_generation": GENERATION_PATH,
    }
    observed = {name: sha(path) for name, path in paths.items()}
    if observed != HASHES:
        raise ValueError("V11 terminal evidence drift")
    attempt = json.loads(paths["attempt"].read_bytes())
    failure = json.loads(paths["terminal_failure"].read_bytes())
    authority = json.loads(AUTHORITY_PATH.read_bytes())
    generation = json.loads(GENERATION_PATH.read_bytes())
    if not (attempt["attempt_identity"] == ATTEMPT and attempt["attempt_ordinal"] == 1 and attempt["execution_authority_identity"] == AUTHORITY and attempt["qualification_generation_identity"] == GENERATION and attempt["status"] == "CONSUMED_BEFORE_EXECUTION"):
        raise ValueError("attempt binding mismatch")
    if not (failure["terminal_failure_identity"] == FAILURE and failure["attempt_identity"] == ATTEMPT and failure["failure_class"] == "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION" and failure["completed_rows"] == 0 and failure["partial_artifact_count"] == 5 and failure["partial_artifact_root"] == "a1f69cecc61e6b94d815e82536fd89c9ecf6a286f45d2f2f6a6b4920992f54a1"):
        raise ValueError("terminal failure binding mismatch")
    if authority["execution_authority_identity"] != AUTHORITY or authority["source_sha256"]["src/pastila_scout/production_core_candidate_qualification_runner_v3.py"] != HASHES["runner_source"] or generation["qualification_generation_identity"] != GENERATION:
        raise ValueError("published authority binding mismatch")
    if constant(RUNNER, "EXPECTED_GENERATION") != STALE_GENERATION:
        raise ValueError("stale runner generation witness mismatch")
    runner_adapters = constant(RUNNER, "EXPECTED_ADAPTERS")
    runner_prompts = constant(RUNNER, "EXPECTED_PROMPTS")
    observed_objects = attempt["preflight"]["observed_materializations"]["A"]["objects"]
    observed_adapters = {row["role"]: row["content_identity"] for row in observed_objects if row["role"].startswith("adapter_")}
    if set(runner_adapters.values()) & set(observed_adapters.values()):
        raise ValueError("latent adapter drift witness mismatch")
    if runner_prompts == attempt["preflight"]["system_prompt_sha256"] or set(runner_prompts.values()) & set(attempt["preflight"]["system_prompt_sha256"].values()):
        raise ValueError("latent prompt drift witness mismatch")
    runner_text = RUNNER.read_text("utf-8")
    if runner_text.index('os.environ["QUALIFICATION_GENERATION_IDENTITY"] != EXPECTED_GENERATION') > runner_text.index('_heartbeat("LOAD", 0, 0)'):
        raise ValueError("failure-order witness mismatch")
    if (execution / "completion.json").exists() or list(execution.rglob("*.receipt.json")):
        raise ValueError("unexpected completion or receipt evidence")
    disposition_core = {"schema":"pastila-production-core-v11-terminal-failure-disposition","schema_version":1,"status":"TERMINAL_FAILURE_ATTEMPT_CONSUMED","execution_authority_identity":AUTHORITY,"qualification_generation_identity":GENERATION,"attempt_ordinal":1,"attempt_identity":ATTEMPT,"attempt_consumed_permanently":True,"terminal_failure_identity":FAILURE,"failure_class":"UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION","completed_rows":0,"matrix_rows":2400,"published_checkpoints":0,"failed_batch":{"materialization":"A","repetition":1,"candidate_alias":"CANDIDATE-A"},"root_cause_recorded_separately":True,"retry_or_redraw":False,"candidate_execution_repeated":False,"adjudication_performed":False,"promotion_effect":False,"successor_requirement":"NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY","evidence_sha256":observed}
    disposition = {**disposition_core, "disposition_identity": identity(disposition_core)}
    addendum_core = {"schema":"pastila-production-core-v11-root-cause-addendum","schema_version":1,"terminal_disposition_identity":disposition["disposition_identity"],"terminal_disposition_reinterpreted":False,"attempt_ordinal":1,"attempt_identity":ATTEMPT,"terminal_failure_identity":FAILURE,"attempt_consumed_permanently":True,"attempt_relaunch_authorized":False,"execution_boundary_cause":"STALE_RUNNER_QUALIFICATION_GENERATION_BINDING","failure_stage":"RUNNER_AUTHORITY_VERIFICATION_BEFORE_FIRST_HEARTBEAT","authorized_generation_identity":GENERATION,"runner_expected_generation_identity":STALE_GENERATION,"inference_started":False,"latent_stale_runner_bindings":["ADAPTER_MANIFESTS","SYSTEM_PROMPTS"],"latent_bindings_reached":False,"demonstrated_observations":["AUTHORITY_BINDS_V3_RUNNER_SOURCE","EXECUTOR_TRANSMITS_V10_GENERATION_IDENTITY","RUNNER_EXPECTS_V3_GENERATION_IDENTITY","GENERATION_CHECK_PRECEDES_FIRST_HEARTBEAT","BOUNDARY_LOGS_PUBLISHED","HEARTBEAT_ABSENT","MODEL_LOAD_AND_INFERENCE_NOT_REACHED","CHECKPOINT_RECEIPT_ABSENT","TERMINAL_FAILURE_UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"],"evidence_sha256":observed,"retry_or_redraw":False,"adjudication_performed":False,"promotion_effect":False}
    addendum = {**addendum_core, "addendum_identity": identity(addendum_core)}
    return disposition, addendum


def put(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if path.exists() and (path.is_symlink() or path.read_bytes() != raw):
        raise ValueError(f"published artifact differs: {path}")
    if not path.exists():
        path.write_bytes(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disposition", type=Path, required=True)
    parser.add_argument("--addendum", type=Path, required=True)
    options = parser.parse_args()
    disposition, addendum = build()
    put(options.disposition, disposition)
    put(options.addendum, addendum)
    print(json.dumps({"disposition_identity": disposition["disposition_identity"], "addendum_identity": addendum["addendum_identity"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
