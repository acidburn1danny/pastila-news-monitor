from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path
from verify_editor_core_source_bound_hybrid_authority_v1 import ARMS, AUTH, SEEDS, verify

RUNTIME_SHA256 = "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f"

def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)

def verify_model_materialization(model: Path, artifacts: Path) -> None:
    manifest_path = artifacts / "semantic-admission-v2-stage-p-construction-obligation-v2-model-adapter-immutable-manifest-v1.json"
    authority = json.loads(AUTH.read_text())
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != authority["base_model_manifest_artifact_sha256"]:
        raise ValueError("base model manifest artifact")
    manifest = json.loads(manifest_path.read_text())["base_snapshot"]
    files = manifest["files"]
    if len(files) != authority["base_model_file_count"] or sum(x["size"] for x in files) != authority["base_model_total_file_bytes"]:
        raise ValueError("base model inventory")
    for item in files:
        path = model / item["path"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["size"]:
            raise ValueError("base model file inventory")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""): digest.update(block)
        if digest.hexdigest() != item["sha256"]: raise ValueError("base model file identity")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--execute-authorized", action="store_true")
    parser.add_argument("--runtime-python", type=Path)
    parser.add_argument("--model", type=Path); parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--parent", type=Path); parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--preflight", type=Path); parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    authority = verify()  # Authority and all bound hashes are verified before any root is created.
    planned = [f"{arm.lower()}__seed_{seed}" for arm in ARMS for seed in SEEDS]
    if args.fixture_only:
        print(json.dumps({"status": "PASS_FIXTURE_9", "authority_identity": authority["authority_identity"],
                          "slots": 9, "distinct_outputs": len(set(planned)), "model_loaded": False,
                          "inference_performed": False, "optimizer_created": False, "training_performed": False}, sort_keys=True))
        return
    if args.output_root.exists() and (args.output_root.is_symlink() or any(args.output_root.iterdir())):
        raise ValueError("program output root must be new or empty")
    if not args.execute_authorized or os.environ.get("SOURCE_BOUND_HYBRID_PROGRAM_AUTHORIZED") != "1":
        raise SystemExit("separate owner authorization required")
    authority_doc = json.loads(AUTH.read_text())
    actual_paths = {"model": str(args.model), "tokenizer": str(args.tokenizer), "parent": str(args.parent),
                    "artifacts": str(args.artifacts), "preflight": str(args.preflight), "worker": str(args.worker)}
    if actual_paths != authority_doc["bound_paths"]: raise SystemExit("bound path identity")
    if not args.runtime_python or str(args.runtime_python) != authority_doc["runtime_python"] or hashlib.sha256(args.runtime_python.read_bytes()).hexdigest() != RUNTIME_SHA256:
        raise SystemExit("runtime python identity")
    if not all((args.model, args.tokenizer, args.parent, args.artifacts, args.preflight, args.worker)):
        raise SystemExit("missing bound input")
    if hashlib.sha256(args.preflight.read_bytes()).hexdigest() != authority_doc["preflight_sha256"]: raise SystemExit("preflight identity")
    if hashlib.sha256(args.worker.read_bytes()).hexdigest() != authority_doc["worker_sha256"]: raise SystemExit("worker identity")
    verify_model_materialization(args.model, args.artifacts)
    args.output_root.mkdir(parents=True, exist_ok=False)
    work = args.output_root / ".inflight"
    work.mkdir()
    completed = []
    for arm in ARMS:
        for seed in SEEDS:
            slot_id = f"{arm}__seed_{seed}"; verify(arm, seed)
            final = args.output_root / f"{arm.lower()}__seed_{seed}"
            staging = work / f"slot-{arm.lower()}__seed_{seed}"
            zero = work / f"zero-step-{arm.lower()}__seed_{seed}"
            phase = "ZERO_STEP"
            try:
                subprocess.run([str(args.runtime_python), "-B", str(args.preflight), "--artifact-root", str(args.artifacts),
                                "--tokenizer-dir", str(args.tokenizer), "--parent-adapter", str(args.parent),
                                "--output", str(zero)], check=True)
                receipt = json.loads((zero / "zero-step.json").read_text())
                if receipt["status"] != "PASS_9_ZERO_STEP" or receipt["model_loaded"]: raise ValueError("zero-step receipt")
                phase = "SLOT_EXECUTION"
                environment = {**os.environ, "SOURCE_BOUND_HYBRID_SLOT_AUTHORIZED": "1"}
                subprocess.run([str(args.runtime_python), "-B", str(args.worker), "--arm", arm, "--seed", str(seed),
                                "--output", str(staging), "--model", str(args.model), "--tokenizer", str(args.tokenizer),
                                "--parent", str(args.parent), "--artifacts", str(args.artifacts), "--execute-authorized"],
                               check=True, env=environment)
                terminal = json.loads((staging / "terminal.json").read_text())
                if terminal["status"] != "PASS_TERMINAL" or terminal["slot_id"] != slot_id: raise ValueError("terminal receipt")
                completed.append(slot_id)
            except Exception as error:
                if work.exists(): shutil.rmtree(work)
                atomic_json(args.output_root / "failure.json", {"status": "TERMINAL_FAILURE", "slot_id": slot_id,
                                                                "phase": phase, "error_type": type(error).__name__,
                                                                "partial_eligible_evidence": False})
                raise
    for arm in ARMS:
        for seed in SEEDS:
            (work / f"slot-{arm.lower()}__seed_{seed}").replace(args.output_root / f"{arm.lower()}__seed_{seed}")
    shutil.rmtree(work)
    atomic_json(args.output_root / "terminal.json", {"status": "PASS_TERMINAL_9", "slots": completed,
                                                     "authority_identity": authority["authority_identity"]})

if __name__ == "__main__": main()
