import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "src/pastila_scout/production_core_inference_resource_calibration_v1.py"
LAUNCHER = ROOT / "scripts/calibrate_production_core_inference_resources_v1.sh"


def test_probe_is_non_semantic_and_candidate_neutral() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "output_decoded_or_inspected\": False" in text
    assert "semantic_candidate_evaluation\": False" in text
    assert "token_hasher" in text
    assert "TOTAL_CONTEXT_TOKENS = 8192" in text
    assert "GENERATION_PROMPT_TOKENS = 1924" in text
    assert "TECHNICAL_TOKEN_CEILING = 6268" in text
    assert "GENERATION_PROMPT_TOKENS + TECHNICAL_TOKEN_CEILING != TOTAL_CONTEXT_TOKENS" in text
    assert 'deregister_op_overrides(disable_op_symbols="bmm")' in text
    assert "tokenizer.decode(" not in text
    assert "batch_decode(" not in text
    assert text.count("pastila-editor-core-v1.") == 4
    assert "ADAPTER_MANIFESTS[candidate]" in text


def test_launcher_closes_runtime_and_network_boundary() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "unshare --mount --net --fork" in text
    assert '[[ "$(id -u)" == 0 ]]' in text
    assert "/usr/sbin/chroot \"$ROOTFS\" /opt/production-core-runtime/bin/python -I" in text
    assert "mount -o remount,bind,ro" in text
    assert "env -i" in text
    assert "TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib" in text
    assert "TRITON_CACHE_DIR=/tmp/triton-cache" in text
    assert "REQUIRED_ANCESTOR=\"ca9e7027ad4472412d77291c3446dc1c3b1de026\"" in text
    assert 'git --git-dir="$GIT_DIR" show "$HEAD_COMMIT:src/' in text
    assert 'git --git-dir="$GIT_DIR" show "$HEAD_COMMIT:scripts/' in text
    assert "candidate object identity mismatch" in PROBE.read_text(encoding="utf-8")
    assert "RECEIPT_TMP" in text and "receipt identity mismatch" in text


def test_probe_rejects_invalid_authority_before_runtime_import() -> None:
    result = subprocess.run([sys.executable, str(PROBE), "missing", "missing", "invalid"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "invalid calibration authority" in result.stderr


def test_launcher_rejects_incomplete_invocation() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "[[ $# -ne 5 ]]" in text
    assert "! -e \"$RECEIPT\"" in text
    assert "mktemp -p" in text
    assert "mv -Tn" in text
    assert 'sync -f "$RECEIPT"' in text
    assert 'sync -f "$RECEIPT_PARENT"' in text
    assert "published receipt byte mismatch" in text


def test_probe_snapshot_and_consumed_objects_are_verified_after_use() -> None:
    text = PROBE.read_text(encoding="utf-8")
    assert "calibration probe snapshot mismatch" in text
    assert "calibration probe mutated during execution" in text
    assert "calibration object mutated during execution" in text
    assert text.count("_file_manifest(base)") >= 2
    assert text.count("_file_manifest(adapter)") >= 2
