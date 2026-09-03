"""Offline proof consumer executed only in the pinned OCI image with --network none."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pastila_scout.milestone9_release_pipeline import (  # noqa: E402
    OPENSSL_EXECUTABLE_SHA256,
    load_canonical,
    validate_proof,
)


def run(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["/usr/bin/openssl", *args], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "SSL_CERT_FILE": "/dev/null"},
        timeout=30, check=False,
    )


def main() -> int:
    objects = ROOT / "deployment" / "milestone-9"
    executable = Path("/usr/bin/openssl").read_bytes()
    if hashlib.sha256(executable).hexdigest() != OPENSSL_EXECUTABLE_SHA256:
        raise ValueError("OpenSSL executable identity")
    release = load_canonical(objects / "release.json")
    validation = load_canonical(objects / "request-validation.json")
    proof = load_canonical(objects / "proof.json")
    query = (objects / "request.tsq").read_bytes()
    receipt = (objects / "receipt.tsr").read_bytes()
    validate_proof(release, validation, query, receipt, proof)
    parsed = run("ts", "-query", "-in", str(objects / "request.tsq"), "-text")
    if parsed.returncode or b"Hash Algorithm: sha256" not in parsed.stdout or b"Certificate required: yes" not in parsed.stdout:
        raise ValueError("query semantics")
    verified = run(
        "ts", "-verify", "-queryfile", str(objects / "request.tsq"),
        "-in", str(objects / "receipt.tsr"),
        "-CAfile", str(ROOT / "deployment/objects/rfc3161-root.pem"),
        "-untrusted", str(ROOT / "deployment/objects/rfc3161-intermediate.pem"),
    )
    if verified.returncode or verified.stdout.strip() != b"Verification: OK":
        raise ValueError("receipt verification")
    print(proof["proof_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
