"""RFC-3161-bound, fail-closed deployment boundary for V2.3.12."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Mapping

from .semantic_authority_capture_orchestrator_v2_3_7 import canonical
from .semantic_authority_deployment_v2_3_9 import LINUX_LAUNCHER_SHA256, LinuxVerifier, REPOSITORY_ID, REPOSITORY_SLUG, RUNTIME_COMMIT, sha
from .semantic_authority_deployment_v2_3_10 import FrozenRun, run_once, verify_installed_dependency
from .semantic_authority_deployment_v2_3_11 import checkout_commit
from .semantic_authority_rfc3161_verifier_v2_3_13 import OPENSSL_EXECUTABLE_SHA256, verify_executable

SCHEMA = "PASTILA_CAPTURE_DEPLOYMENT_V2_3_12"
PAYLOAD_SCHEMA = "PASTILA_RFC3161_SCHEDULE_PRECOMMIT_V2_3_12"
RFC3161_QUALIFICATION_IDENTITY = "561bacaa18d5578539427c3b6c7abb235976046d6854e57315da21af5f37296c"
OPENSSL_SHA256 = OPENSSL_EXECUTABLE_SHA256
CA_BUNDLE_SHA256 = "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def schedule_payload(manifest: Mapping[str, object]) -> bytes:
    value = {
        "schema": PAYLOAD_SCHEMA,
        "repository_slug": manifest["repository_slug"],
        "repository_id": manifest["repository_id"],
        "core_runtime_commit": manifest["core_runtime_commit"],
        "deployment_runtime_commit": manifest["deployment_runtime_commit"],
        "workflow_commit": manifest["workflow_commit"],
        "scheduled_utc": manifest["scheduled_utc"],
        "schedule_cron": manifest["schedule_cron"],
        "schedule_precommit_verifier_sha256": manifest["schedule_precommit_verifier_sha256"],
        "schedule_precommit_tsa_root_sha256": manifest["schedule_precommit_tsa_root_sha256"],
        "rfc3161_qualification_identity": manifest["rfc3161_qualification_identity"],
    }
    return canonical(value) + b"\n"


def validate_manifest(value: Mapping[str, object]) -> None:
    required = {
        "schema", "repository_slug", "repository_id", "core_runtime_commit",
        "deployment_runtime_commit", "workflow_commit", "deployment_identity",
        "scheduled_utc", "schedule_cron", "ca_sha256", "cosign_sha256",
        "launcher_sha256", "trusted_root_sha256", "derivation_policy_identity",
        "seed_plan_identity", "schedule_precommit_payload_sha256",
        "schedule_precommit_receipt_sha256", "schedule_precommit_verifier_sha256",
        "schedule_precommit_tsa_root_sha256", "manifest_identity",
        "rfc3161_qualification_identity",
    }
    if set(value) != required or value["schema"] != SCHEMA or value["repository_slug"] != REPOSITORY_SLUG or value["repository_id"] != REPOSITORY_ID:
        raise ValueError("manifest schema/repository")
    if value["core_runtime_commit"] != RUNTIME_COMMIT or not HEX40.fullmatch(str(value["deployment_runtime_commit"])) or not HEX40.fullmatch(str(value["workflow_commit"])) or len({value["core_runtime_commit"], value["deployment_runtime_commit"], value["workflow_commit"]}) != 3:
        raise ValueError("runtime/workflow identity separation")
    if (value["rfc3161_qualification_identity"] != RFC3161_QUALIFICATION_IDENTITY
        or value["schedule_precommit_verifier_sha256"] != OPENSSL_SHA256
        or value["schedule_precommit_tsa_root_sha256"] != CA_BUNDLE_SHA256
        or value["ca_sha256"] != CA_BUNDLE_SHA256
        or value["launcher_sha256"] != LINUX_LAUNCHER_SHA256):
        raise ValueError("frozen verifier/CA trust")
    for key in required - {"schema", "repository_slug", "repository_id", "core_runtime_commit", "deployment_runtime_commit", "workflow_commit", "scheduled_utc", "schedule_cron"}:
        if key not in {"manifest_identity"} and not HEX64.fullmatch(str(value[key])):
            raise ValueError("manifest digest")
    if sha(schedule_payload(value)) != value["schedule_precommit_payload_sha256"]:
        raise ValueError("schedule payload binding")
    body = {k: v for k, v in value.items() if k not in {"deployment_identity", "manifest_identity"}}
    if value["deployment_identity"] != sha(canonical(body)):
        raise ValueError("deployment identity")
    complete = dict(value); identity = complete.pop("manifest_identity")
    if identity != sha(canonical(complete)):
        raise ValueError("manifest identity")
    scheduled = datetime.strptime(str(value["scheduled_utc"]), "%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
    if value["schedule_cron"] != f"{scheduled.minute} {scheduled.hour} {scheduled.day} {scheduled.month} *":
        raise ValueError("manifest schedule")


def _regular(path: Path, expected: str, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError(label)
    payload = path.read_bytes()
    if not payload or sha(payload) != expected:
        raise ValueError(label)
    return payload


def _contained(launcher: Path, launcher_sha256: str, verifier: Path, verifier_sha256: str, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["/usr/bin/bash", str(launcher), "--launcher-sha256", launcher_sha256,
         "--expected-sha256", verifier_sha256, str(verifier), *args],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30, env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"},
    )


def verify_schedule_precommit(manifest: Mapping[str, object], *, payload: Path, receipt: Path, verifier: Path, tsa_root: Path, launcher: Path) -> None:
    expected = schedule_payload(manifest)
    payload_bytes = _regular(payload, str(manifest["schedule_precommit_payload_sha256"]), "schedule payload")
    if payload_bytes != expected:
        raise ValueError("schedule payload canonical bytes")
    receipt_bytes = _regular(receipt, str(manifest["schedule_precommit_receipt_sha256"]), "schedule receipt")
    verify_executable(verifier)
    verify_installed_dependency(launcher, str(manifest["launcher_sha256"]))
    root_bytes = _regular(tsa_root, str(manifest["schedule_precommit_tsa_root_sha256"]), "TSA root")
    with tempfile.TemporaryDirectory() as folder:
        frozen = Path(folder)
        frozen_payload = frozen / "payload"; frozen_payload.write_bytes(payload_bytes)
        frozen_receipt = frozen / "receipt"; frozen_receipt.write_bytes(receipt_bytes)
        frozen_root = frozen / "tsa-root"; frozen_root.write_bytes(root_bytes)
        verified = _contained(launcher, str(manifest["launcher_sha256"]), verifier, str(manifest["schedule_precommit_verifier_sha256"]), ["ts", "-verify", "-data", str(frozen_payload), "-in", str(frozen_receipt), "-CAfile", str(frozen_root)])
        verification_channels = (verified.stdout.strip(), verified.stderr.strip())
        if verified.returncode != 0 or verification_channels not in ((b"Verification: OK", b""), (b"", b"Verification: OK")):
            raise ValueError("RFC3161 verification")
        inspected = _contained(launcher, str(manifest["launcher_sha256"]), verifier, str(manifest["schedule_precommit_verifier_sha256"]), ["ts", "-reply", "-in", str(frozen_receipt), "-text"])
    try:
        text = inspected.stdout.decode("utf-8", errors="strict")
        algorithm_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("Hash Algorithm:")]
        time_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("Time stamp:")]
        if algorithm_lines != ["Hash Algorithm: sha256"] or len(time_lines) != 1:
            raise ValueError("ambiguous RFC3161 fields")
        time_line = time_lines[0].split(":", 1)[1].strip()
        if not time_line.endswith(" GMT"):
            raise ValueError("noncanonical RFC3161 timezone")
        generated = parsedate_to_datetime(time_line).astimezone(timezone.utc)
        scheduled = datetime.strptime(str(manifest["scheduled_utc"]), "%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
    except (UnicodeDecodeError, ValueError, StopIteration) as exc:
        raise ValueError("RFC3161 verification time") from exc
    if inspected.returncode != 0 or inspected.stderr or generated >= scheduled:
        raise ValueError("RFC3161 precommit order")


def _load(path: Path) -> Mapping[str, object]:
    if not path.is_file() or path.is_symlink() or len(path.read_bytes()) > 1024 * 1024:
        raise ValueError("manifest file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest object")
    validate_manifest(value)
    return value


def execute(manifest: Mapping[str, object], *, checkout_sha: str, payload: Path, receipt: Path, rfc3161_verifier: Path, tsa_root: Path, bundle: Path, cosign: Path, launcher: Path, trusted_root: Path, ca: Path, output: Path, now: datetime) -> dict[str, object]:
    validate_manifest(manifest)
    if checkout_sha != manifest["deployment_runtime_commit"]:
        raise ValueError("deployment runtime checkout")
    verify_schedule_precommit(manifest, payload=payload, receipt=receipt, verifier=rfc3161_verifier, tsa_root=tsa_root, launcher=launcher)
    for path, key in ((cosign, "cosign_sha256"), (launcher, "launcher_sha256"), (trusted_root, "trusted_root_sha256"), (ca, "ca_sha256")):
        verify_installed_dependency(path, str(manifest[key]))
    run = {
        "deployment_identity": manifest["deployment_identity"], "repository_id": REPOSITORY_ID,
        "runtime_commit": manifest["core_runtime_commit"], "workflow_commit": manifest["workflow_commit"],
        "run_id": os.environ.get("GITHUB_RUN_ID", ""), "run_attempt": 1, "event_name": "schedule",
        "derivation_policy_identity": manifest["derivation_policy_identity"],
        "seed_plan_identity": manifest["seed_plan_identity"], "ca_sha256": manifest["ca_sha256"],
    }
    frozen = FrozenRun(str(manifest["scheduled_utc"]), str(manifest["schedule_cron"]), str(manifest["workflow_commit"]), str(manifest["deployment_identity"]), str(manifest["ca_sha256"]))
    runtime = LinuxVerifier(cosign, launcher, trusted_root, str(manifest["cosign_sha256"]), str(manifest["launcher_sha256"]), str(manifest["trusted_root_sha256"]))
    return run_once(config=frozen, environment=os.environ, now=now, run=run, bundle=bundle.read_bytes(), bundle_path=bundle, verifier=runtime, ca_file=ca, output=output)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    for name in ("manifest", "schedule-payload", "schedule-receipt", "rfc3161-verifier", "tsa-root", "bundle", "cosign", "launcher", "trusted-root", "ca", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args(argv)
    execute(_load(a.manifest), checkout_sha=checkout_commit(Path.cwd()), payload=a.schedule_payload, receipt=a.schedule_receipt, rfc3161_verifier=a.rfc3161_verifier, tsa_root=a.tsa_root, bundle=a.bundle, cosign=a.cosign, launcher=a.launcher, trusted_root=a.trusted_root, ca=a.ca, output=a.output, now=datetime.now(timezone.utc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
