from __future__ import annotations
import argparse, json, tempfile
from pathlib import Path
from train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1 import fixture_run

class FixtureTokenizer:
    def __call__(self,text,**_): return {"input_ids":list(range(len(text))),"offset_mapping":[(i,i+1) for i in range(len(text))]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--fixture",type=Path,required=True); a=p.parse_args(); f=json.loads(a.fixture.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as d:
        out=Path(d); result=fixture_run(FixtureTokenizer(),f["assistant_content"],f["annotation"],out,"T1_CONTRACT_WEIGHTED_S1_HIGHER_PLASTICITY",314159)
        assert len(list(out.iterdir()))==5 and result["status"]=="PASS_FIXTURE_ONLY"
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
if __name__=="__main__": main()
