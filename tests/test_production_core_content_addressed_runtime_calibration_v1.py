import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/artifacts/production-core-content-addressed-runtime-calibration-v1.json"


def _value() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_runtime_is_content_addressed_and_reproduced_twice() -> None:
    value = _value()
    identity = value["runtime_object"]["sha256"]
    assert value["runtime_object"]["logical_object_name"] == f"sha256/{identity}.tar"
    assert value["runtime_object"]["candidate_bytes_included"] is False
    assert len(value["clean_materializations"]) == 2
    for item in value["clean_materializations"]:
        assert item["rootfs_sha256_before_execution"] == identity
        assert item["rootfs_sha256_after_execution"] == identity
        receipt = {key: content for key, content in item.items() if key != "receipt_sha256"}
        receipt_bytes = (
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode()
        assert item["receipt_sha256"] == hashlib.sha256(receipt_bytes).hexdigest()
        assert item["runtime_probe"]["packages"] == value["runtime_packages"]


def test_launchers_and_frozen_authority_are_exactly_bound() -> None:
    value = _value()
    components = value["components"]
    assert value["frozen_authority"]["commit"] == "d5885027194ade26a8dec3ac13ccecd3ae6f6b9d"
    assert value["frozen_authority"]["tree"] == "f8d14d3d99570a24b379d01e8789158bde786a6d"
    assert value["frozen_authority"]["current_head_required_to_equal_freeze"] is False
    for field, path in (
        ("materializer_sha256", ROOT / "scripts/materialize_production_core_runtime_v1.sh"),
        ("offline_launcher_sha256", ROOT / "scripts/run_production_core_offline_calibration_v1.sh"),
        ("runtime_probe_sha256", ROOT / "src/pastila_scout/production_core_runtime_probe_v1.py"),
        ("calibration_harness_sha256", ROOT / "src/pastila_scout/production_core_synthetic_calibration_v1.py"),
    ):
        assert components[field] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_execution_is_network_denied_read_only_and_environment_closed() -> None:
    value = _value()
    boundary = value["execution_boundary"]
    assert boundary["network"] == "NEW_CHILD_NAMESPACE_WITH_NO_EXTERNAL_INTERFACE"
    assert boundary["parent_network_namespace"] not in boundary["observed_child_network_namespaces"]
    assert boundary["rootfs"] == "READ_ONLY_BIND_REMOUNT"
    assert boundary["host_environment_inherited"] is False
    assert list(boundary["allowed_manifest_bound_environment"]) == [
        "CUBLAS_WORKSPACE_CONFIG",
        "CUDA_VISIBLE_DEVICES",
        "PYTHONHASHSEED",
        "TOKENIZERS_PARALLELISM",
    ]
    accelerator = value["accelerator_probe"]
    assert accelerator["nvidia_smi_compute_capability"] == "12.0"
    assert accelerator["nvidia_smi_memory_total_mib"] == 16303
    assert accelerator["torch_compute_capability"] == [12, 0]
    assert accelerator["torch_bf16_supported"] is True
    assert accelerator["torch_deterministic_algorithms_enabled"] is True
    assert accelerator["cuda_device_count"] == 1


def test_candidate_free_limits_do_not_overstate_inference_authority() -> None:
    value = _value()
    limits = value["candidate_free_limit_proposals"]
    assert limits["authority_status"] == "PENDING_OWNER_APPROVAL"
    assert limits["scope"] == "SUPERVISOR_AND_STRUCTURAL_RUNTIME_OVERHEAD_ONLY_NOT_MODEL_INFERENCE"
    assert limits["technical_output_bytes"] is None
    assert limits["technical_output_tokens"] is None
    assert {item["code"] for item in value["unresolved_limits"]} == {
        "INFERENCE_RESOURCE_CEILINGS_REQUIRE_NON_SEMANTIC_CANDIDATE_EXECUTION",
        "TECHNICAL_OUTPUT_ENVELOPE_REQUIRES_FROZEN_TOKENIZER_AND_BOUNDED_IDENTIFIERS",
    }
    assert value["network_activity"] is False
    assert value["candidate_evaluation_started"] is False
    assert value["candidate_promotion_effect"] is False
    provenance = value["provenance_scope"]
    assert provenance["bootstrap_source_is_future_resolution_authority"] is False
    assert provenance["future_materialization_source"] == (
        "VERIFIED_ROOTFS_OBJECT_DESCRIPTOR_ONLY"
    )
    assert provenance["upstream_package_origin_claimed"] is False


def test_materializer_and_launcher_fail_closed_on_substitution() -> None:
    materializer = (ROOT / "scripts/materialize_production_core_runtime_v1.sh").read_text()
    launcher = (ROOT / "scripts/run_production_core_offline_calibration_v1.sh").read_text()
    assert 'exec 3<"$ROOTFS_OBJECT"' in materializer
    assert "sha256sum /proc/self/fd/3" in materializer
    assert 'readonly STAGING="$AUTHORITY_ROOT/.materializing-' in materializer
    assert 'trap cleanup EXIT INT TERM' in materializer
    assert 'trap - EXIT INT TERM' in materializer
    assert 'mv -T -- "$STAGING" "$TARGET"' in materializer
    for script in (materializer, launcher):
        assert '$(dirname -- "$' in script
        assert '$(basename -- "$' in script
        assert '=~ ^materialized-[a-z0-9-]+$' in script
        assert '!= "$AUTHORITY_ROOT"' in script
    assert '"$(realpath -e -- "$ROOTFS")" != "$ROOTFS"' in launcher
    assert 'mount -o remount,bind,ro "$1"' in launcher
    assert 'if [ "$before" != "$5" ]' in launcher
    assert 'if [ "$after" != "$5" ]' in launcher
    assert "! -name lo" in launcher
