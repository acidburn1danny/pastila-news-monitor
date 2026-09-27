"""Materialize and finalize the minimal VNext SCOUT closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    temporary.replace(path)


def identify(value: dict, field: str) -> dict:
    value = {key: item for key, item in value.items() if key != field}
    return {**value, field: hashlib.sha256(canonical(value)).hexdigest()}


def materialize(repo: Path, product: Path) -> dict:
    if product != Path("/root/pastila-vnext/v1"):
        raise ValueError("unexpected persistent product root")
    runtime = product / "runtime/scout-v1"
    stage = product / "runtime/.scout-v1.stage"
    if runtime.exists() or stage.exists():
        raise ValueError("SCOUT runtime already materialized")
    stage.mkdir(parents=True)
    sources = {
        "scout.py": repo / "src/pastila_scout/vnext_scout_v1.py",
        "sources.json": repo / "docs/artifacts/editor-vnext-minimal-scout-sources-v1.json",
        "sourcepacket-contract.json": repo / "docs/artifacts/editor-vnext-minimal-scout-sourcepacket-contract-v1.json",
    }
    try:
        for name, source in sources.items():
            shutil.copyfile(source, stage / name)
        files = [{"path": name, "sha256": digest(stage / name), "size": (stage / name).stat().st_size} for name in sorted(sources)]
        contract = json.loads((stage / "sourcepacket-contract.json").read_text(encoding="utf-8"))
        source_config = json.loads((stage / "sources.json").read_text(encoding="utf-8"))
        lock = identify({
            "schema": "editor-vnext-minimal-scout-sourcepacket-dependency-lock", "schema_version": 1,
            "product_root": "/root/pastila-vnext/v1", "runtime_path": "runtime/scout-v1",
            "contract_identity": contract["contract_identity"], "sources_identity": source_config["sources_identity"],
            "python_dependency": "platform/python-ml-v1/bin/python", "python_scope": "STANDARD_LIBRARY_ONLY",
            "editor_runtime_path": "runtime/editor-v0-v1", "r2_component_path": "components/r2-reference-v1",
            "editor_runtime_lock_identity": "58b22d87a50f9eb28592043e1fdeb1ba6eb841b2e103b65f30ebd710785731ca",
            "r2_lock_identity": "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f",
            "database_path": "state/scout-v1/scout.db", "historical_database_required": False,
            "files": files, "legacy_dependency_count": 0,
        }, "lock_identity")
        atomic(stage / "dependency-lock.json", lock)
        stage.replace(runtime)
        (product / "state/scout-v1").mkdir(parents=True, exist_ok=True)
        return lock
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def update_product_lock(repo: Path, product: Path, scout_lock: dict, receipt: dict | None) -> dict:
    product_lock = json.loads((product / "product-lock.json").read_text(encoding="utf-8"))
    status = "PASS" if receipt and receipt.get("status") == "PASS_SCOUT_TO_EDITOR_E2E" and receipt.get("structural_valid") is True else "MATERIALIZED_PENDING_ACCEPTANCE"
    product_lock["components"]["SCOUT_SOURCEPACKET"] = {
        "lock_identity": scout_lock["lock_identity"], "status": status,
        "source_packet_contract_identity": scout_lock["contract_identity"],
        "acceptance_receipt_identity": receipt.get("receipt_identity") if receipt else None,
    }
    product_lock["layout"]["scout"] = "runtime/scout-v1"
    product_lock["layout"]["scout_state"] = "state/scout-v1"
    missing = [item for item in product_lock["missing_for_global_migration_pass"] if item not in {"SCOUT", "SOURCEPACKET_ORCHESTRATION"} or status != "PASS"]
    product_lock["missing_for_global_migration_pass"] = missing
    product_lock["global_vnext_migration_pass"] = False
    product_lock["legacy_dependency_count"] = 0
    product_lock = identify(product_lock, "product_lock_identity")
    atomic(product / "product-lock.json", product_lock)
    atomic(repo / "docs/artifacts/editor-vnext-product-lock-v1.json", product_lock)
    if receipt:
        closure = {
            "schema": "editor-vnext-minimal-scout-sourcepacket-closure", "schema_version": 1,
            "status": status, "product_root": "/root/pastila-vnext/v1",
            "scout_lock_identity": scout_lock["lock_identity"],
            "source_packet_contract_identity": scout_lock["contract_identity"],
            "sources_identity": scout_lock["sources_identity"],
            "source_packet_identity": receipt["packet_identity"],
            "acceptance_receipt_identity": receipt["receipt_identity"],
            "editor_receipt_identity": receipt["editor_receipt_identity"],
            "product_lock_identity": product_lock["product_lock_identity"],
            "acceptance": {
                "capture": "DETERMINISTIC_RSS_ATOM_FIXTURE_USING_PRODUCTION_PARSER",
                "network_reachability_tested": False, "grouping": True,
                "user_selection_equivalent": "EXPLICIT_EVENT_ID",
                "source_count": receipt["source_count"], "r2_inference": True,
                "structural_output_valid": receipt["structural_valid"],
                "factual_acceptance_authority": False,
            },
            "database": {"engine": "SQLITE", "fresh_schema": True, "historical_database_migrated": False},
            "shadow_verifier_authoritative": False, "optimizer_created": False,
            "training_performed": False, "legacy_dependency_count": 0,
        }
        closure = identify(closure, "closure_identity")
        atomic(repo / "docs/artifacts/editor-vnext-minimal-scout-sourcepacket-closure-v1.json", closure)
    return product_lock


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--product-root", type=Path, default=Path("/root/pastila-vnext/v1"))
    parser.add_argument("--finalize-receipt", type=Path)
    args = parser.parse_args()
    repo, product = args.repo.resolve(), args.product_root.resolve()
    runtime_lock_path = product / "runtime/scout-v1/dependency-lock.json"
    scout_lock = json.loads(runtime_lock_path.read_text(encoding="utf-8")) if runtime_lock_path.exists() else materialize(repo, product)
    receipt = json.loads(args.finalize_receipt.read_text(encoding="utf-8")) if args.finalize_receipt else None
    product_lock = update_product_lock(repo, product, scout_lock, receipt)
    print(json.dumps({"status": product_lock["components"]["SCOUT_SOURCEPACKET"]["status"], "scout_lock_identity": scout_lock["lock_identity"], "product_lock_identity": product_lock["product_lock_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
