import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/artifacts/production-core-candidate-tokenizer-materialization-v1.json"
PROBE = ROOT / "src/pastila_scout/production_core_tokenizer_materialization_probe_v1.py"
LAUNCHER = ROOT / "scripts/qualify_production_core_tokenizer_materialization_v1.sh"


def _value() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidates_bind_the_same_content_addressed_tokenizer_only_object() -> None:
    value = _value()
    identities = set(value["candidate_mapping"].values())
    assert identities == {
        "sha256:2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
    }
    obj = value["tokenizer_object"]
    assert obj["logical_name"] == f"sha256/{obj['sha256']}.tar"
    assert obj["model_weights_included"] is False
    assert obj["adapter_bytes_included"] is False
    assert obj["candidate_results_included_or_inspected"] is False
    assert tuple(obj["ordered_files"]) == (
        "chat_template.jinja",
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json",
    )


def test_two_materializations_reproduce_object_and_observation() -> None:
    value = _value()
    materializations = value["materializations"]
    assert [item["logical_id"] for item in materializations] == ["A", "B"]
    assert len({item["reconstructed_object_sha256"] for item in materializations}) == 1
    assert len({item["frozen_default_observation_sha256"] for item in materializations}) == 1
    assert len({item["fixed_observation_sha256"] for item in materializations}) == 1
    observation = value["observation"]
    assert observation["model_loaded"] is False
    assert observation["inference_executed"] is False
    assert observation["candidate_result_inspected"] is False


def test_probe_and_launcher_are_exactly_bound_and_network_denied() -> None:
    value = _value()
    runtime = value["runtime"]
    assert runtime["probe_sha256"] == hashlib.sha256(PROBE.read_bytes()).hexdigest()
    assert runtime["launcher_sha256"] == hashlib.sha256(LAUNCHER.read_bytes()).hexdigest()
    assert runtime["network"] == "DENY_ALL_NEW_NAMESPACE"
    assert runtime["rootfs_and_tokenizer_mounts"] == "READ_ONLY"
    probe = PROBE.read_text(encoding="utf-8")
    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert "AutoModel" not in probe
    assert "PeftModel" not in probe
    assert "unshare --net --mount --fork" in launcher
    assert "network namespace contains a non-loopback interface" in launcher
    assert 'snapshot="$(tar --sort=name' in launcher
    assert "tokenizer snapshot identity mismatch" in launcher
    assert 'mount -o remount,bind,ro "$1/tmp/tokenizer"' in launcher
    assert "/mnt/c/pf9" not in launcher
    assert "/home/pastila" not in launcher
    assert "AUTHORITY_ROOT=" not in launcher
    assert 'REPO_ROOT="$(realpath -e -- "$SCRIPT_DIR/..")"' in launcher
    assert 'OBJECT_STORE_ROOT="$(realpath -e -- "$STORE_INPUT")"' in launcher
    assert '"$OBJECT_STORE_ROOT" != "$STORE_INPUT"' in launcher
    assert 'case "$TOKENIZER" in "$OBJECT_STORE_ROOT"/*)' in launcher
    assert "content-addressed tokenizer object mismatch" in launcher
    assert '"${10}" = fixed' in launcher
    assert "qualification tokenizer emitted stderr" in launcher
    assert '"$MODE" = frozen-default' in launcher
    assert '"$4" != comparison-only' in launcher
    assert "comparison-only tokenizer stderr identity mismatch" in launcher
    assert "4425935b0a695ecb79d5d3b975e8b3fbd73594c24ae6deb1bb235491faae873d" in launcher
    assert "EXPECTED_FILE_SHA256" in probe
    assert "tokenizer file identity mismatch" in probe


def test_derivation_remains_fail_closed_pending_explicit_authority() -> None:
    value = _value()
    assert {item["code"] for item in value["remaining_blockers"]} == {
        "COMPLETE_TOKEN_UPPER_BOUND_PROOF_NOT_YET_IMPLEMENTED",
    }
    semantics = value["qualification_execution_profile_v1_tokenizer_semantics"]
    assert semantics["load_argument"] == "fix_mistral_regex=True"
    assert semantics["missing_or_false_argument"] == "FAIL_CLOSED"
    assert semantics["incorrect_regex_warning_or_any_stderr"] == "FAIL_CLOSED"
    assert semantics["profile_specific_only"] is True
    assert semantics["defines_global_core_v2_tokenizer_policy"] is False
    assert semantics["promotes_candidate"] is False
    assert semantics["claims_universal_equivalence_with_frozen_default"] is False
    runtime = value["runtime"]
    assert runtime["object_store_resolution"] == "EXPLICIT_CALLER_SUPPLIED_CANONICAL_ROOT"
    assert runtime["embedded_absolute_host_path"] is False
    assert runtime["symlink_or_containment_escape"] == "FAIL_CLOSED"
    assert runtime["content_addressed_tokenizer_object_required"] is True
    assert value["technical_byte_ceiling_emitted"] is False
    assert value["technical_token_ceiling_emitted"] is False
    assert value["candidate_evaluation_or_promotion_effect"] is False
    assert value["network_activity"] is False
