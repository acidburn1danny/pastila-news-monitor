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
 c=tmp_path/"current";s=tmp_path/"staged";c.mkdir();s.mkdir();(c/"product-lock.json").write_text("old");(s/"product-lock.json").write_text("new");return c,s
def test_full_root_fault_windows_restore_names_and_bytes(tmp_path):
 for point in ("BEFORE_BACKUP","AFTER_BACKUP","AFTER_ACTIVATE"):
  base=tmp_path/point;base.mkdir();c,s=roots(base);result=simulate(c,s,point)
  assert result["status"].startswith("PASS")
  assert c.is_dir() and s.is_dir() and (c/"product-lock.json").read_text()=="old" and (s/"product-lock.json").read_text()=="new"
  assert not (base/"current.activation-backup").exists()
def test_builder_declares_separate_runtime_and_assembly_lineage():
 text=(ROOT/"scripts/build_vnext_active_integration_product_lock_boundary_v1.py").read_text()
 assert '"runtime_source_commit":RUNTIME_SOURCE' in text
 assert '"assembly_boundary_commit":assembly_commit' in text
 assert 'target/"product-lock.json"' in text
