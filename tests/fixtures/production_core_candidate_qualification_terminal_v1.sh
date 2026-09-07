#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d)"; trap 'rm -rf -- "$work"' EXIT
PYTHONPATH=/mnt/c/pf9/src python3 - "$work" <<'PY' &
import hashlib, importlib.util, pathlib, sys, time
root = pathlib.Path('/mnt/c/pf9')
spec = importlib.util.spec_from_file_location('pcq_exec', root/'scripts/execute_production_core_candidate_qualification_v1.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
output = pathlib.Path(sys.argv[1]); core = {'schema':'attempt','schema_version':1}
attempt = {**core, 'attempt_identity': hashlib.sha256(module.canonical_json_bytes(core)).hexdigest()}
module._install_terminal_signal_handlers(output, 'a'*64, attempt)
(output/'ready').write_text('1'); time.sleep(30)
PY
child=$!
for _ in $(seq 1 100); do [[ -f "$work/ready" ]] && break; sleep 0.02; done
[[ -f "$work/ready" ]]; kill -TERM "$child"; set +e; wait "$child"; status=$?; set -e
[[ "$status" -ne 0 && -f "$work/terminal-failure.json" ]]
grep -q 'SIGNAL_15_AFTER_ATTEMPT_CONSUMPTION' "$work/terminal-failure.json"
