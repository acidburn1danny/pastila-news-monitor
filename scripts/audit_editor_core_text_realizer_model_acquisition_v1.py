"""Fixture/adversarial audit of the no-download acquisition boundary."""
import json
from pathlib import Path
from preflight_editor_core_text_realizer_model_acquisition_v1 import run

def main():
    result=run(Path(__file__).resolve().parents[1]); checks=[result["status"]=="PASS_NO_DOWNLOAD_PREFLIGHT",result["models"]==2,result["files"]==29,result["aggregate_bytes"]>29*2**30,not result["download_performed"],not result["model_loaded"],not result["quantization_performed"],not result["inference_performed"]]
    if not all(checks): raise ValueError("audit")
    print(json.dumps({"status":"PASS_ADVERSARIAL","checks":len(checks),"authority_identity":result["authority_identity"]},sort_keys=True))
if __name__ == "__main__": main()
