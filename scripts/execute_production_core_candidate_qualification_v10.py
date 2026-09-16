"""Execute V10 by applying an exact, audited authority projection to V3 mechanics."""
from __future__ import annotations
import hashlib
from pathlib import Path

_SOURCE=Path(__file__).with_name("execute_production_core_candidate_qualification_v3.py")
_EXPECTED_SOURCE_SHA256="9869bfcb65da5a189013f1b56ca3f914c86872bad59c2997d1d4c59ab97239f7"
raw=_SOURCE.read_bytes()
if hashlib.sha256(raw).hexdigest()!=_EXPECTED_SOURCE_SHA256:raise SystemExit("V3 executor source mismatch")
source=raw.decode("utf-8")
changes={
 'production_core_candidate_execution_authority_v3':'production_core_candidate_execution_authority_v10',
 'production-core-successor-comparative-qualification-generation-v9.json':'production-core-successor-comparative-qualification-generation-v10.json',
 'production-core-successor-candidate-object-manifest-v9.json':'production-core-successor-candidate-object-manifest-v10.json',
 'production-core-successor-candidate-generation-qualification-v9.json':'production-core-successor-candidate-generation-qualification-v10.json',
 'ROOT\n    / ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence"\n    / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt"':'ART / "pastila-editor-core-v1.1-json-successor-v10-system-prompt.txt"',
 'ROOT\n    / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence"\n    / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"':'ART / "pastila-editor-core-v1.2-json-successor-v10-system-prompt.txt"',
 '"9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc"':'"91c84e9ab10cbecdfdd7e255b133c56263feb546d55d7e1ea01362f9be5567bb"',
 '"111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"':'"70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36"',
}
for old,new in changes.items():
 if source.count(old)!=1:raise SystemExit(f"V10 executor projection witness mismatch: {old}")
 source=source.replace(old,new)
needle="    rows = validate_preflight(generation, requests, candidates, qualification)\n"
replacement=needle+'''    candidate_adapters = candidates["adapter_manifest_sha256"]
    if tuple(candidate_adapters) != ("pastila-editor-core-v1.1-json-successor-v10", "pastila-editor-core-v1.2-json-successor-v10"):
        raise SystemExit("V10 candidate manifest mapping mismatch")
    candidates = {**candidates, "adapter_manifest_sha256": {
        "pastila-editor-core-v1.1-json-successor-v2": candidate_adapters["pastila-editor-core-v1.1-json-successor-v10"],
        "pastila-editor-core-v1.2-json-successor": candidate_adapters["pastila-editor-core-v1.2-json-successor-v10"],
    }}
'''
if source.count(needle)!=1:raise SystemExit("V10 candidate compatibility insertion mismatch")
source=source.replace(needle,replacement)
exec(compile(source,str(_SOURCE),"exec"),globals(),globals())  # noqa: S102 - exact byte-pinned projection
