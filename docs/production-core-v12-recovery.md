# Production Core V12 recovery

The V12 source checkpoint is commit `2c64de10398fe39cbd42d7f2d46d544e5ac0fe3f` on
`successor/core-v2-v12-runner-binding-remediation`. The recovery metadata added after that
checkpoint does not authorize or perform candidate execution.

## Before reinstall

Keep `E:\backup\pastila-recovery-v12\objects` outside the WSL VHDX. Verify it with:

```powershell
python -c "import json,pathlib; from pastila_scout.production_core_recovery_v12 import verify_external_objects; m=json.loads(pathlib.Path('docs/artifacts/production-core-v12-clean-recovery.json').read_bytes()); verify_external_objects(m,pathlib.Path(r'E:\backup\pastila-recovery-v12\objects'))"
```

The private Ed25519 signing key is deliberately excluded from Git and from the unencrypted
recovery set. Back it up separately in an encrypted secret store, or explicitly rotate it after
reinstall. Rotation must never rewrite historical authority or signature records.

## Clean bootstrap

1. Install Git, Python 3.14, WSL2 `Ubuntu-24.04`, and a compatible NVIDIA WSL driver.
2. Clone `https://github.com/acidburn1danny/pastila-news-monitor.git` into a new directory.
3. Check out `successor/core-v2-v12-runner-binding-remediation` and verify that the published
   branch contains source checkpoint `2c64de10398fe39cbd42d7f2d46d544e5ac0fe3f`.
4. Create a fresh virtual environment and install the project from `pyproject.toml`.
5. Run `pytest tests/test_production_core_recovery_v12.py tests/test_production_core_candidate_qualification_runner_v12.py`.
6. Verify the external object set with the command above, then restore the content-addressed
   objects into newly created WSL runtime directories. Never trust paths without rechecking hashes.
7. Re-run the V12 runner materializer and require identity
   `b7073a3b75036e5be26aa4b1d9546aa9f012370168a74df552b648708e399e29`.

The next project action is exactly: build and audit the successor execution authority binding the
canonical V12 recovery commit and runner V12 identity, with candidate execution and attempt
consumption still zero. Do not infer candidate-execution authorization from this recovery document.
