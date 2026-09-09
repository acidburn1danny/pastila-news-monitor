import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
ARTIFACT = (
    ROOT
    / "docs/artifacts/production-core-non-promotional-diagnostic-adjudicator-registry-v2.json"
)
V1 = (
    ROOT
    / "docs/artifacts/production-core-non-promotional-diagnostic-adjudicator-registry-v1.json"
)


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def test_b03_registry_identity_and_supersession_are_closed():
    value = json.loads(ARTIFACT.read_bytes())
    identity = value.pop("registry_identity")
    assert identity == hashlib.sha256(canonical(value)).hexdigest()
    assert (
        identity == "87104f9ef345177ca9b310e9d726a6430a034b9bfb5b187a5e7ec54c1cca3e51"
    )
    assert (
        value["supersedes_registry_identity"]
        == "40b813e9f99123bd11f3c2db34d1526614a063aa07dd269e9646822200e2035b"
    )
    assert (
        value["supersedes_registry_artifact_sha256"]
        == hashlib.sha256(V1.read_bytes()).hexdigest()
    )
    assert value["historical_evidence_mutated"] is False
    assert value["hard_gate_compensation_permitted"] is False
    assert value["candidate_qualification_effect"] is False
    assert value["candidate_promotion_effect"] is False
    assert value["retry_or_redraw_permitted"] is False
    assert value["new_run_authorized"] is False


def test_b03_exact_key_and_proof_of_possession_verify(tmp_path):
    openssl = shutil.which("openssl")
    assert openssl is not None
    value = json.loads(ARTIFACT.read_bytes())
    record = value["roles"]["ADJUDICATOR_B"]
    proof = record["proof_of_possession"]
    public_key = base64.b64decode(record["public_key_pem_base64"], validate=True)
    challenge = proof["challenge_text"].encode("ascii")
    signature = base64.b64decode(proof["signature_base64"], validate=True)
    assert record["adjudicator_id"] == "EVALUATOR-B-03"
    assert hashlib.sha256(public_key).hexdigest() == record["public_key_sha256"]
    assert hashlib.sha256(challenge).hexdigest() == proof["challenge_sha256"]
    assert hashlib.sha256(signature).hexdigest() == proof["signature_sha256"]
    assert len(signature) == 64
    key, message, sig = tmp_path / "key.pem", tmp_path / "challenge", tmp_path / "sig"
    key.write_bytes(public_key)
    message.write_bytes(challenge)
    sig.write_bytes(signature)
    run = subprocess.run(
        [
            openssl,
            "pkeyutl",
            "-verify",
            "-pubin",
            "-inkey",
            key,
            "-rawin",
            "-in",
            message,
            "-sigfile",
            sig,
        ],
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0
