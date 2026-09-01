from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_v4_constructor_and_denyset_are_sealed_static_and_non_authorizing():
    implementation = json.loads((ART / "humor-mechanics-batch2-development-constructor-implementation-v4.json").read_text(encoding="utf-8"))
    denyset = json.loads((ART / "humor-mechanics-batch2-nonblind-development-fragment-denyset-v4.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-constructor-v4-static-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(implementation); identity = core.pop("constructor_implementation_identity")
    assert identity == seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V4", core)
    core = dict(denyset); identity = core.pop("fragment_denyset_identity")
    assert identity == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V4", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_CONSTRUCTOR_V4_STATIC_AUDIT_V1", core)
    module = (ROOT / implementation["module_path"]).read_bytes()
    ast.parse(module.decode("utf-8"))
    assert hashlib.sha256(module).hexdigest() == implementation["module_sha256"]
    assert implementation["invocations"] == 0 and implementation["candidate_surface"] is None
    assert implementation["release_authority"] is False
    assert denyset["blind_reserve_accessed"] is False
    assert denyset["complete_surface_text_included"] is False
    assert len(denyset["candidate_sources"]) == 7
    assert audit["constructor_invocations"] == audit["candidate_surfaces_created"] == 0
    assert audit["g02b_release"] == "NOT_PERFORMED"
    assert audit["downstream_authority"] is False
