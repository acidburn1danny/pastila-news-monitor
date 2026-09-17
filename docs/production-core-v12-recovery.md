# Production Core V12 recovery

The V12 source checkpoint is commit `2c64de10398fe39cbd42d7f2d46d544e5ac0fe3f` on
`successor/core-v2-v12-runner-binding-remediation`. The recovery metadata added after that
checkpoint does not authorize or perform candidate execution.

## Before reinstall

Keep `D:\backup\pastila-recovery-v12\objects` outside the WSL VHDX. Verify it with:

```powershell
python -c "import json,pathlib; from pastila_scout.production_core_recovery_v12 import verify_external_objects; m=json.loads(pathlib.Path('docs/artifacts/production-core-v12-clean-recovery.json').read_bytes()); verify_external_objects(m,pathlib.Path(r'D:\backup\pastila-recovery-v12\objects'))"
```

The private Ed25519 signing key is deliberately excluded from Git and from the unencrypted
recovery set. Its verified byte-exact backup is stored on the owner-held BitLocker To Go volume
labelled `SCOUT_BACKUP`, under `pastila-v12-secret-recovery/private.pem`. BitLocker protection was
verified on with 100% used-space encryption and automatic unlock disabled. The owner must retain
the password or numerical recovery password separately. Never disclose the private-key hash.

## Clean bootstrap

1. Install Git, Python 3.14, WSL2 `Ubuntu-24.04`, and a compatible NVIDIA WSL driver.
2. Clone `https://github.com/acidburn1danny/pastila-news-monitor.git` into a new directory.
3. Check out `successor/core-v2-v12-runner-binding-remediation` and verify that the published
   branch contains source checkpoint `2c64de10398fe39cbd42d7f2d46d544e5ac0fe3f`.
4. Create a fresh virtual environment and install the project from `pyproject.toml`.
5. Run `pytest tests/test_production_core_recovery_v12.py tests/test_production_core_candidate_qualification_runner_v12.py`.
6. Verify the external object set with the command above, then restore the content-addressed
   objects into newly created WSL runtime directories. Never trust paths without rechecking hashes.
   A recovery smoke may point the V12 test at the sealed recovery resolution JSON through
   `PASTILA_V12_OBJECT_RESOLUTION`. The default is
   `.pastila-runtime/production-core-v12-recovery/v12-recovery-runtime-resolution.json`.
   Set `PASTILA_V12_RECOVERY_ROOT` to use another recovery directory. The corresponding
   `v12-executor-resolution.json` is the schema-v2 projection for the executor boundary.
   If the restored adapters live on a Windows volume, set `PASTILA_V12_ADAPTER_HOST_ROOT` to
   their parent directory; this avoids treating a drvfs path as an inaccessible WSL UNC path.
7. Re-run the V12 runner materializer and require identity
   `b7073a3b75036e5be26aa4b1d9546aa9f012370168a74df552b648708e399e29`.

The subsequent project phase is to build and audit successor execution authority binding the
canonical V12 recovery commit and runner V12 identity, with candidate execution and attempt
consumption still zero. This recovery document does not authorize that phase or candidate execution.

## Recovery gate status

The isolated Windows replay at `C:\pf9-v12-recovery-replay` has a sealed resolution identity
`89e328339d6627f3f3cc5231b816353a4b580da391431feab4174029eb34779a`.
The read-only audit checks that seal, source claims, both model and adapter materializations,
tokenizers, rootfs, and exact projection paths. The Linux symlink negative test passes under
Ubuntu 24.04. Windows drive directories in that replay appear writable (`777`) inside WSL,
so it cannot pass the runtime permission gate. A new replay must use native WSL ext4 paths;
the materializer accepts Linux paths and closes directory permissions after writing both
artifacts. These checks do not consume a candidate attempt.

The clean ext4 replay is at `/root/pf9-v12-recovery-replay-20260917` in
`Ubuntu-24.04`. Its sealed resolution identity is
`7623e67ceeeb42fc42f18a329d825311ddc723046595201060b6d0f638f81e77`.
The final audit verified every referenced content identity, the exact A/B projection,
Linux-visible permissions on objects and their ancestors, distinct physical model and
adapter materializations, and the executor's actual object-authority helper. The V11
executor's `object_authority` function accepted the recovered V12 adapter without
running the executor. The recovery root contains only the expected four object groups
and two resolution artifacts. The Linux negative suite passed all eight focused tests,
including symlink substitution.

`POST_REINSTALL_V12_RECOVERY_READY = PASS` with `0 BLOCKERS` for the recovery contract.
Candidate execution, successor attempt consumption, adjudication, and promotion remain
zero or false. No execution-authority artifact has been emitted, signed, published, or frozen.
