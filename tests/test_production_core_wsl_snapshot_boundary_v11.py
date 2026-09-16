import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"scripts/run_production_core_candidate_qualification_v11.sh"
MATERIALIZER=ROOT/"scripts/materialize_production_core_wsl_snapshot_runner_v11.py"
SMOKE=ROOT/"scripts/smoke_production_core_wsl_snapshot_boundary_v11.sh"
CAPACITY=ROOT/"scripts/preflight_production_core_wsl_host_capacity_v11.py"

def source():return RUNNER.read_text("utf-8")
def materializer():
 spec=importlib.util.spec_from_file_location("v11_materializer",MATERIALIZER);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value

def test_v11_snapshot_is_private_read_only_bind_without_physical_copy():
 value=source()
 assert 'cp -a --reflink=auto -- "$MODEL" "$MODEL_SNAPSHOT"' not in value
 assert 'cp -a --reflink=auto -- "$ADAPTER" "$ADAPTER_SNAPSHOT"' not in value
 assert 'mount --bind "$source" "$target"' in value
 assert 'mount -o remount,bind,ro "$target"' in value
 assert 'mounted+=("$target")' in value
 assert RUNNER.read_bytes()==materializer().build()

def test_v11_rejects_writable_or_symlinked_authority_inputs_before_mount():
 value=source()
 symlink=value.index('find "$MODEL" "$ADAPTER" -type l')
 writable=value.index('find "$MODEL" "$ADAPTER" \\( -type f -o -type d \\) -perm /222')
 snapshot=value.index('MODEL_SNAPSHOT="$WORK/model-snapshot"')
 assert symlink < writable < snapshot
 assert 'writable authority input rejected' in value

def test_v11_keeps_private_namespace_and_final_read_only_probes():
 value=source()
 assert 'unshare --mount --net --pid --ipc --uts --fork' in value
 assert 'model_opts="$(findmnt -no OPTIONS --target "$ROOTFS/tmp/input/model")"' in value
 assert 'adapter_opts="$(findmnt -no OPTIONS --target "$ROOTFS/tmp/input/adapter")"' in value
 assert 'candidate_private_snapshots":true' in value

def test_v11_smoke_is_zero_qualification_and_checks_inode_bound_read_only_mounts():
 value=SMOKE.read_text("utf-8")
 assert 'unshare --mount --pid --fork' in value
 assert value.count('stat -Lc \'%d:%i\'')>=4
 assert 'mount -o remount,bind,ro "$target"' in value
 assert 'touch "$target/.v11-write-probe"' in value
 assert '"qualification_rows":0,"candidate_execution":0,"attempt_consumption":0' in value

def test_v11_host_capacity_preflight_is_fixed_fail_closed_and_zero_attempt():
 value=CAPACITY.read_text("utf-8")
 assert 'VHD=Path(r"E:\\WSL\\Ubuntu-24.04\\ext4.vhdx")' in value
 assert "MINIMUM_FREE_BYTES=68_719_476_736" in value
 assert "usage.free<MINIMUM_FREE_BYTES" in value
 assert "FILE_ATTRIBUTE_REPARSE_POINT" in value
 assert '"qualification_rows":0' in value
 assert '"candidate_execution":0' in value
 assert '"attempt_consumption":0' in value
