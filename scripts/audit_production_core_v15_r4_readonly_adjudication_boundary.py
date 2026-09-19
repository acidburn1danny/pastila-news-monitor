"""Fresh adversarial audit for the R4 read-only adjudication boundary."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import materialize_production_core_successor_execution_authority_v12 as signing
import materialize_production_core_v15_r4_readonly_adjudication_boundary as issuer


def audit() -> dict[str, object]:
    root = issuer.OUTPUT
    if root.is_symlink() or {p.name for p in root.iterdir()} != set(issuer.ARTIFACTS):
        raise ValueError("signed adjudication artifact set mismatch")
    paths = {name: root / name for name in issuer.ARTIFACTS}
    if any(p.is_symlink() or not p.is_file() for p in paths.values()):
        raise ValueError("signed adjudication artifact substitution")
    raw, binding, signature = paths["boundary.json"].read_bytes(), paths["binding.json"].read_bytes(), paths["binding.sig"].read_bytes()
    boundary = json.loads(raw); core = dict(boundary); claimed = core.pop("boundary_identity", None)
    if (claimed != issuer.digest(issuer.canonical(core)) or boundary != issuer.build()
            or raw != json.dumps(boundary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            or binding != issuer.canonical(issuer.binding_for(boundary, raw))
            or paths["builder-source.py"].read_bytes() != (issuer.ROOT / "scripts/materialize_production_core_v15_r4_readonly_adjudication_boundary.py").read_bytes()
            or boundary["adjudication_performed"] is not False or boundary["adjudication_verdict"] is not None
            or boundary["promotion"] is not False or boundary["r4_evidence"]["row_count"] != 2400):
        raise ValueError("adjudication boundary reproduction mismatch")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY), "-rawin", "-in", str(paths["binding.json"]), "-sigfile", str(paths["binding.sig"])], check=True, capture_output=True)
    signed_ids = (str(claimed), issuer.digest(binding), issuer.digest(signature))
    if any(any(value.encode() in (issuer.ROOT / name).read_bytes() for value in signed_ids) for name in issuer.SOURCES):
        raise ValueError("signed dependency cycle")
    return {
        "verdict": "PASS + 0 BLOCKERS",
        "boundary_identity": claimed,
        "binding_identity": issuer.digest(binding),
        "signature_identity": issuer.digest(signature),
        "ed25519": "PASS", "source_closure": "PASS", "r4_evidence_closure": "PASS",
        "adjudication_state": "READY_FOR_TWO_INDEPENDENT_HUMAN_RECEIPTS_NO_VERDICT",
        "promotion": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
