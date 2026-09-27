import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_build_preflight_and_audit_without_download():
    subprocess.run([sys.executable,"-B","scripts/build_editor_core_text_realizer_model_acquisition_v1.py"],cwd=ROOT,check=True)
    pre=subprocess.run([sys.executable,"-B","scripts/preflight_editor_core_text_realizer_model_acquisition_v1.py"],cwd=ROOT,check=True,capture_output=True,text=True)
    audit=subprocess.run([sys.executable,"-B","scripts/audit_editor_core_text_realizer_model_acquisition_v1.py"],cwd=ROOT,check=True,capture_output=True,text=True)
    assert json.loads(pre.stdout)["download_performed"] is False
    assert json.loads(audit.stdout)["checks"]==8

def test_downloader_is_separately_authorized_and_atomic():
    text=(ROOT/"scripts/acquire_editor_core_text_realizer_models_v1.py").read_text(encoding="utf-8")
    assert "EDITOR_MODEL_ACQUISITION_AUTHORIZED" in text
    assert "staging.rename(final)" in text
    assert "no overwrite" in text
