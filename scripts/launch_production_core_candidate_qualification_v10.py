"""Detached-signed V10 entry projected from the byte-pinned V9 launcher."""
from __future__ import annotations
import hashlib
from pathlib import Path
_SOURCE=Path(__file__).with_name("launch_production_core_candidate_qualification_v9.py");_SHA="3f061226e7f0108226bcdcb676bc6d74b6c58d39a2ca2532ce315ce298ccbe59";raw=_SOURCE.read_bytes()
if hashlib.sha256(raw).hexdigest()!=_SHA:raise SystemExit("V9 launcher source mismatch")
source=raw.decode()
changes={
 'execute_production_core_candidate_qualification_v3.py':'execute_production_core_candidate_qualification_v10.py',
 'production_core_candidate_execution_authority_v3.py':'production_core_candidate_execution_authority_v10.py',
 'production-core-candidate-execution-authority-v9.binding.json':'production-core-candidate-execution-authority-v10.binding.json',
 'production-core-candidate-execution-authority-v9.binding.sig':'production-core-candidate-execution-authority-v10.binding.sig',
 'production-core-candidate-execution-authority-v9.json':'production-core-candidate-execution-authority-v10.json',
 'production-core-successor-comparative-qualification-generation-v9.json':'production-core-successor-comparative-qualification-generation-v10.json',
 'production-core-successor-candidate-object-manifest-v9.json':'production-core-successor-candidate-object-manifest-v10.json',
 'production-core-successor-candidate-generation-qualification-v9.json':'production-core-successor-candidate-generation-qualification-v10.json',
 'e7ff0930b99a4145c4b77b4a3ba0a163edf7f757943a85b93780cdfbef6a0a97':'2ca33d629ebdbc32e77f06d0365dc94e8aebc84b0848826244c39c2cfd396039',
 'f3505bdf6cecf94b9081028c6ac4af1ee35012daf7fd3b97451b94c85b1ad0ab':'a39e10122536e67beae30f87229a69f9f57d71de18f970856ae52dc14b90dbb2',
 '924383035ef35df80cbaa98d9cdf187ecb639e580030746392d5361fcac52c90':'bd726fc667e619705c5616d2f408c7f0cc499d3a56e76a932c650580aaaa7406',
 '9869bfcb65da5a189013f1b56ca3f914c86872bad59c2997d1d4c59ab97239f7':'1e0a2ad61fdfeb48dff87a2e4d04a57051b98f0d083196018f8bd3931ceeaaee',
 '5616841ee9dfc3c174d100aed07c79419df8850c0f63fbd7add9b1fd527ef33b':'f0701d611170906a6b8b17cad2565d32cd471cb3e582bde41a293c46d450ebd1',
 'pastila-production-core-v9-detached-authority-binding':'pastila-production-core-v10-detached-authority-binding',
 'FROZEN_SUCCESSOR_V9_DUAL_STRUCTURAL_REMEDIATION_ZERO_ATTEMPTS':'FROZEN_SUCCESSOR_V10_UNIFIED_EXECUTION_CONTRACT_ZERO_ATTEMPTS',
 'b1915eed044bb05a00e977188dae9a6d7227169e3f1b12731075e1cc691e59f3':'50eb1fb7b425fdee07b7fbd672c405c0dc2cd5b34e0df6270bb0468c3ea846d8',
 'scripts/launch_production_core_candidate_qualification_v9.py':'scripts/launch_production_core_candidate_qualification_v10.py',
 '"schema_version") != 10':'"schema_version") != 11',
}
for old,new in changes.items():
 if old not in source:raise SystemExit(f"V10 launcher projection witness absent: {old}")
 source=source.replace(old,new)
source=source.replace('"candidate_audit_receipt_identity": "50eb1fb7b425fdee07b7fbd672c405c0dc2cd5b34e0df6270bb0468c3ea846d8",','"candidate_audit_receipt_identity": "50eb1fb7b425fdee07b7fbd672c405c0dc2cd5b34e0df6270bb0468c3ea846d8",\n        "execution_contract_sha256": "eb2ab0914175f0f9ae50882c4c96fbc792cfee1fe40fa39740b9ef8f58a1825d",')
source=source.replace('"predecessor_terminal_failure_identity",\n            "predecessor_root_cause_addendum_identity",','"predecessor_terminal_disposition_identity",')
source=source.replace('or mechanism.get("predecessor_terminal_failure_identity")\n        != "077fc4b81f0e5768c7fd3b49394358a1f56a3ef217c9c527ede70bf9b870e9bb"\n        or mechanism.get("predecessor_root_cause_addendum_identity") is not None','or mechanism.get("predecessor_terminal_disposition_identity")\n        != "7855e21d82402416dcee091baa7a6bcc5cb4c63783aafa33c65bd355c7d83587"')
exec(compile(source,str(_SOURCE),"exec"),globals(),globals())  # noqa: S102
