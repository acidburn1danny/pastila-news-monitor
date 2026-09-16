"""Materialize V10 terminal disposition and forensic SIGBUS addendum."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXECUTION=ROOT/".pastila-runtime/production-core-successor-execution-v10-attempt1"
STDERR=ROOT/".pastila-runtime/v10-qualification-attempt1-final.stderr.log"
ATTEMPT="7a31793e27306f76523c20a69eb06cced7aa67258af7726d40f3def36b57f517"
AUTHORITY="7eee3b6aa16704d754ab38327a4d98f7147697d0d4a3e7e8684e3e982a87a94d"
FAILURE="20bd5a4390566e5d78fd1bac251d13234323d82301bc735bd71575e4f3ccf74e"
GENERATION="a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
HASHES={"attempt":"166b117bd4662c3d6b4fa49843a6a7ad409c16d4fced0daa3b51f5ff78d99be9","terminal_failure":"63d5fa33081134a74458c77488c1848c0c55221ad0a592b313f03c3fd81b59f7","batch":"699be4dd51411664ede157f7fac6c6927b3c60ac511067d2a8a59eed1f2d28c3","system_prompt":"70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36","stderr":"ad1ffa8d6f0ba0100db40d4b6e562913fd6037a4acc68583092d0551a2436b06"}

def canonical(v):return json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(",",":"),sort_keys=True).encode()
def identity(v):return hashlib.sha256(canonical(v)).hexdigest()
def load(path):
 raw=path.read_bytes(); value=json.loads(raw)
 if path.is_symlink() or not path.is_file() or not isinstance(value,dict):raise ValueError(f"evidence path rejected: {path}")
 return value,raw
def sha(raw):return hashlib.sha256(raw).hexdigest()

def build(execution=EXECUTION,stderr_path=STDERR):
 attempt,attempt_raw=load(execution/"attempt.json"); failure,failure_raw=load(execution/"terminal-failure.json")
 batch_raw=(execution/".checkpoint-01.in-progress/batch.json").read_bytes(); prompt_raw=(execution/".checkpoint-01.in-progress/system-prompt.txt").read_bytes(); stderr_raw=stderr_path.read_bytes(); text=stderr_raw.decode("utf-8")
 observed={"attempt":sha(attempt_raw),"terminal_failure":sha(failure_raw),"batch":sha(batch_raw),"system_prompt":sha(prompt_raw),"stderr":sha(stderr_raw)}
 if observed!=HASHES:raise ValueError("V10 terminal evidence drift")
 if not (attempt.get("attempt_identity")==ATTEMPT and attempt.get("attempt_ordinal")==1 and attempt.get("execution_authority_identity")==AUTHORITY and attempt.get("qualification_generation_identity")==GENERATION):raise ValueError("attempt binding mismatch")
 if not (failure.get("terminal_failure_identity")==FAILURE and failure.get("attempt_identity")==ATTEMPT and failure.get("failure_class")=="UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION" and failure.get("completed_rows")==0 and failure.get("failed_batch")=={"materialization":"A","repetition":1,"candidate_alias":"CANDIDATE-A"} and failure.get("partial_artifact_count")==3 and failure.get("partial_artifact_root")=="b9af81cf47b997f9015927380ead8f6a03a1eec08f8cda1829f123d7a1267005" and failure.get("retry_or_redraw_authorized") is False and failure.get("promotion_effect") is False):raise ValueError("terminal failure binding mismatch")
 if (execution/"completion.json").exists() or list(execution.rglob("*.receipt.json")):raise ValueError("unexpected completion or receipt evidence")
 cp_pattern=r'bash: line 24:\s+\d+ Bus error\s+\(core dumped\) cp -a --reflink=auto -- "\$MODEL" "\$MODEL_SNAPSHOT"'
 unshare_pattern=r'bash: line 117:\s+\d+ Bus error\s+\(core dumped\) unshare --mount --net --pid --ipc --uts --fork bash -s'
 if len(re.findall(cp_pattern,text))!=1 or len(re.findall(unshare_pattern,text))!=1:raise ValueError("SIGBUS evidence mismatch")
 disposition_core={"schema":"pastila-production-core-v10-terminal-failure-disposition","schema_version":1,"status":"TERMINAL_FAILURE_ATTEMPT_CONSUMED","execution_authority_identity":AUTHORITY,"qualification_generation_identity":GENERATION,"attempt_ordinal":1,"attempt_identity":ATTEMPT,"attempt_consumed_permanently":True,"terminal_failure_identity":FAILURE,"failure_class":"UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION","completed_rows":0,"matrix_rows":2400,"published_checkpoints":0,"failed_batch":{"materialization":"A","repetition":1,"candidate_alias":"CANDIDATE-A"},"root_cause_determined":False,"retry_or_redraw":False,"candidate_execution_repeated":False,"adjudication_performed":False,"promotion_effect":False,"successor_requirement":"NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY","evidence_sha256":observed}
 disposition={**disposition_core,"disposition_identity":identity(disposition_core)}
 addendum_core={"schema":"pastila-production-core-v10-root-cause-addendum","schema_version":1,"terminal_disposition_identity":disposition["disposition_identity"],"terminal_disposition_reinterpreted":False,"attempt_ordinal":1,"attempt_identity":ATTEMPT,"terminal_failure_identity":FAILURE,"attempt_consumed_permanently":True,"attempt_relaunch_authorized":False,"execution_boundary_cause":"WSL_EXECUTION_BOUNDARY_SIGBUS_DURING_MODEL_SNAPSHOT","internal_sigbus_cause":"UNDETERMINED","failure_stage":"MODEL_SNAPSHOT_BEFORE_RUNNER_START","demonstrated_observations":["CP_MODEL_SNAPSHOT_TERMINATED_BY_SIGBUS","UNSHARE_EXECUTION_BOUNDARY_TERMINATED_BY_SIGBUS","RUNNER_OUTPUT_ABSENT","CHECKPOINT_RECEIPT_ABSENT","TERMINAL_FAILURE_UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"],"evidence_sha256":observed,"retry_or_redraw":False,"adjudication_performed":False,"promotion_effect":False}
 addendum={**addendum_core,"addendum_identity":identity(addendum_core)}
 return disposition,addendum

def put(path,value):
 raw=json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n"
 if path.exists() and (path.is_symlink() or path.read_bytes()!=raw):raise ValueError(f"published artifact differs: {path}")
 if not path.exists():path.write_bytes(raw)
def main():
 p=argparse.ArgumentParser();p.add_argument("--disposition",type=Path,required=True);p.add_argument("--addendum",type=Path,required=True);o=p.parse_args();d,a=build();put(o.disposition,d);put(o.addendum,a);print(json.dumps({"disposition_identity":d["disposition_identity"],"addendum_identity":a["addendum_identity"]}));return 0
if __name__=="__main__":raise SystemExit(main())
