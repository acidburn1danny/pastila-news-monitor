"""Tokenizer-only EOS and ceiling audit for targeted R4."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts/audit_editor_core_v10_v12_targeted_token_lengths.py"
PREFIX = "editor-core-v10-v12-targeted-continuation-r4"


def module():
    spec = importlib.util.spec_from_file_location("targeted_token_base", BASE)
    value = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(value)
    value.PREFIX = PREFIX
    return value


def audit(model: Path, artifacts: Path) -> dict[str, object]:
    base = module(); result = base.audit(model, artifacts)
    result["schema"] = "pastila-editor-core-targeted-r4-token-audit"
    core = {key: value for key, value in result.items() if key != "audit_identity"}
    result["audit_identity"] = base.sha(base.canonical(core))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("model", type=Path); parser.add_argument("artifacts", type=Path)
    args = parser.parse_args(); print(json.dumps(audit(args.model, args.artifacts), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
