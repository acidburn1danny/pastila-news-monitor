import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SCRIPT=ROOT/"scripts/materialize_production_core_v10_corpora_and_configs.py"; ART=ROOT/"docs/artifacts"

def module():
 spec=importlib.util.spec_from_file_location("v10_corpora",SCRIPT); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

def test_materialization_reproduces_and_is_isolated(tmp_path):
 m=module(); old=m.main
 import sys
 prior=sys.argv; sys.argv=[str(SCRIPT),"--output-dir",str(tmp_path)]
 try: old()
 finally: sys.argv=prior
 published=json.loads((ART/"production-core-v10-corpus-and-training-config-manifest.json").read_bytes()); reproduced=json.loads((tmp_path/"production-core-v10-corpus-and-training-config-manifest.json").read_bytes()); assert published==reproduced
 assert published["qualification_content_used"]==0 and published["consumed_attempt_outputs_used"]==0
 assert published["training_authorized"] is False and published["training_performed"] is False
 assert published["qualification_attempt_consumed"] is False and published["promotion_effect"] is False

def test_all_targets_and_phase_projections_are_canonical():
 for path in ART.glob("pastila-editor-core-v1.*-json-successor-v10-*.jsonl"):
  rows=[json.loads(line) for line in path.read_text("utf-8").splitlines()]; assert len(rows) in {240,480}
  assert {r["length_bucket"] for r in rows}=={"SHORT","MEDIUM","LONG","ADVERSARIAL","BOUNDARY"}
  for row in rows:
   target=row["messages"][2]["content"]; assert target.startswith("{") and target.endswith("}") and "```" not in target
   assert json.dumps(json.loads(target),ensure_ascii=False,separators=(",",":"))==target
   if row["length_bucket"]=="ADVERSARIAL": assert "```json" in row["messages"][1]["content"]

def test_configs_cannot_authorize_training():
 for path in ART.glob("pastila-editor-core-v1.*-json-successor-v10-training-config-v10.json"):
  value=json.loads(path.read_bytes()); assert value["status"]=="FROZEN_PRETRAINING_ZERO_EXECUTION"
  assert value["optimizer"]=="PAGED_ADAMW_8BIT" and value["training_authorized"] is False
  assert value["max_sequence_tokens"]==3072
  assert value["post_training_gate"]["production_renderer_required"] is True

def test_manifest_and_all_artifact_identities_are_closed():
 import hashlib
 manifest=json.loads((ART/"production-core-v10-corpus-and-training-config-manifest.json").read_bytes()); core=dict(manifest); claimed=core.pop("manifest_identity")
 assert hashlib.sha256(json.dumps(core,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()==claimed
 for name,row in manifest["artifacts"].items(): assert hashlib.sha256((ART/name).read_bytes()).hexdigest()==row["sha256"]
 for path in ART.glob("pastila-editor-core-v1.*-json-successor-v10-training-config-v10.json"):
  value=json.loads(path.read_bytes()); core=dict(value); claimed=core.pop("training_config_identity"); assert hashlib.sha256(json.dumps(core,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()==claimed
