import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
from preflight_vnext_active_integration_candidate_v1 import identity
from simulate_vnext_atomic_product_root_swap_v1 import simulate
def load(n):return json.loads((ROOT/"docs/artifacts"/n).read_text())
def test_successor_graph_is_content_addressed_and_uses_real_unique_paths():
 g=load("vnext-active-product-dependency-graph-v2.json");claimed=g.pop("authority_identity");assert identity(g)==claimed
 paths=[x["target_path"] for x in g["nodes"]];assert len(paths)==len(set(paths))
 assert "app/cli/product.py" in paths
 assert "app/acceptance/structural.py" not in paths and "app/state/migrations" not in paths
def test_platform_semantics_separates_frozen_and_stable_identity():
 p=load("vnext-active-integration-platform-lock-semantics-v2.json");claimed=p.pop("authority_identity");assert identity(p)==claimed
 assert p["frozen_platform_authority_identity"]=="ef5318bfa36af16350ec96d16ef84eb8b55c527894c3c5045f08d4b9ba1bc498"
 assert p["stable_content_identity_algorithm"].endswith("_V1")
 assert p["host_dependencies"]["python"]=={"path":"/usr/bin/python3","version":"3.12.3"}
def roots(tmp_path):
 c=tmp_path/"current";s=tmp_path/"staged";c.mkdir();s.mkdir();(c/"product-lock.json").write_text("old");(s/"product-lock.json").write_text("new");(c/"nested").mkdir();(c/"nested/current.bin").write_bytes(b"current");(c/"empty").mkdir();(s/"nested").mkdir();(s/"nested/staged.bin").write_bytes(b"staged");return c,s
def test_full_root_fault_windows_restore_names_and_bytes(tmp_path):
 for point in ("BEFORE_BACKUP","AFTER_BACKUP","AFTER_ACTIVATE"):
  base=tmp_path/point;base.mkdir();c,s=roots(base);result=simulate(c,s,point)
  assert result["status"].startswith("PASS")
  assert c.is_dir() and s.is_dir() and (c/"product-lock.json").read_text()=="old" and (s/"product-lock.json").read_text()=="new"
  assert result["full_root_tree_verified"] is True and result["rollback_byte_exact"] is True
  assert (c/"nested/current.bin").read_bytes()==b"current" and (s/"nested/staged.bin").read_bytes()==b"staged" and (c/"empty").is_dir()
  assert not (base/"current.activation-backup").exists()
def test_builder_declares_separate_runtime_and_assembly_lineage():
 text=(ROOT/"scripts/build_vnext_active_integration_product_lock_boundary_v1.py").read_text()
 assert '"runtime_source_commit":RUNTIME_SOURCE' in text
 assert '"assembly_boundary_commit":assembly_commit' in text
 assert 'target/"product-lock.json"' in text

def test_canonical_runtime_writer_is_shared():
 for name in ("build_vnext_active_integration_product_lock_boundary_v1.py","accept_vnext_active_integration_candidate_v1.py","product_cli_vnext_v1.py"):
  assert 'writer_identity="vnext-product-runtime-v1"' in (ROOT/"scripts"/name).read_text()

def test_mutable_state_is_separate_from_immutable_inventory():
 builder=(ROOT/"scripts/build_vnext_active_integration_product_lock_boundary_v1.py").read_text()
 preflight=(ROOT/"scripts/preflight_vnext_active_integration_candidate_v1.py").read_text()
 assert '"mutable_state"' in builder and '"state"' not in builder.split('for base in (',1)[1].split('):',1)[0]
 assert 'require_pristine_state' in preflight and 'PRAGMA integrity_check' in preflight


def test_candidate_v2_lock_and_terminal_result_identities():
 lock=load("vnext-active-integration-product-lock-candidate-v2.json")
 claimed=lock.pop("product_lock_identity")
 assert identity(lock)==claimed=="28e930dc7725f71fc9ae8b8256cbec860ef409ec7034cf35c19da60a9055f9ca"
 assert lock["runtime_source_commit"]=="c211a07551284627a8e23c6e84d7dbf7e1125681"
 assert lock["assembly_boundary_commit"]=="f84a9c6b493e7f54de3ea47f7fd97441af3d3db2"
 result=load("vnext-active-integration-candidate-closure-atomic-semantics-repair-v1.json")
 result_claimed=result.pop("result_identity")
 assert identity(result)==result_claimed=="f56dd9edd429ed265b97f89b4508a1efe7c951b546ed55c1c57893a403a3bee1"
 assert result["status"]=="PASS" and result["blockers"]==0
 assert result["active_product_root_mutated"] is False and result["product_lock_replaced"] is False
 assert result["legacy_dependency_count"]==0

def test_candidate_v2_has_one_root_lock_and_exhaustive_inventory_semantics():
 lock=load("vnext-active-integration-product-lock-candidate-v2.json")
 assert lock["product_root"]=="/root/pastila-vnext/v1"
 assert lock["activation"]["full_root_atomic_swap_required"] is True
 assert lock["mutable_state"]["database"]=="state/product.sqlite3"
 assert lock["active_integration_state"]=="CANDIDATE_NOT_ACTIVATED"
 preflight=(ROOT/"scripts/preflight_vnext_active_integration_candidate_v1.py").read_text()
 assert "managed inventory mismatch" in preflight
 assert 'root/"product-lock.json"' in preflight
