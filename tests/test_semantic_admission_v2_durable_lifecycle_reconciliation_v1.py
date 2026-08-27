import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.durable_lifecycle_reconciliation_v1 import reconcile_durable_lifecycle_v1


ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"tests/fixtures/semantic_admission_v2/durable_lifecycle_reconciliation_v1.json"


def _fixture():
    return json.loads(FIXTURE.read_text("utf-8"))


def _deps():
    return _fixture()["dependency_identities"]


def _synthetic_root(tmp_path):
    for event in _fixture()["events"]:
        name=f'{event["actor"]}-{event["sequence"]:05d}-{event["event"].lower().replace("_", "-")}.json'
        (tmp_path/name).write_text(json.dumps(event,sort_keys=True,separators=(",",":")),"utf-8")
    return tmp_path


def test_synthetic_lifecycle_reconciles_authoritative_phases(tmp_path) -> None:
    result=reconcile_durable_lifecycle_v1(root=_synthetic_root(tmp_path),relative_path="synthetic/durable-lifecycle",
        expected_runner_sha256=_fixture()["runner_sha256"],expected_dependency_identities=_deps())
    assert result.reconciliation_status=="VALID" and result.file_count==8
    assert result.model_load==result.generation==result.terminal_eos==result.response_persisted=="OBSERVED"
    assert result.host_timeout=="NOT_OBSERVED_BEFORE_TERMINAL_EVENT"
    assert len(result.tree_identity)==64


def test_identity_drift_makes_derived_phases_unavailable(tmp_path) -> None:
    result=reconcile_durable_lifecycle_v1(root=_synthetic_root(tmp_path),relative_path="x",expected_runner_sha256="0"*64,
        expected_dependency_identities=_deps())
    assert result.reconciliation_status=="INVALID_OR_UNAVAILABLE"
    assert result.model_load==result.generation=="LIFECYCLE_UNAVAILABLE"


def test_duplicate_sequence_and_actor_drift_fail_closed(tmp_path) -> None:
    source=_synthetic_root(tmp_path)
    item=next(path for path in source.iterdir() if path.name.startswith("host-00002"))
    value=json.loads(item.read_text("utf-8"));value["sequence"]=1
    item.write_text(json.dumps(value),"utf-8")
    result=reconcile_durable_lifecycle_v1(root=tmp_path,relative_path="x",expected_runner_sha256=_fixture()["runner_sha256"],
        expected_dependency_identities=_deps())
    assert result.reconciliation_status=="INVALID_OR_UNAVAILABLE"
