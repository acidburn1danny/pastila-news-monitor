# Pilot 13 owner-controlled signing

This helper signs only the eight frozen Pilot 13 challenges and writes public response files outside the repository.

```powershell
$keyRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Secrets\Batch2-Custodians-v1'
$responseRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Handoff\Batch2-Development-Pilot13-v1'
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot13_signing_v1.py sign-all --key-dir $keyRoot --response-dir $responseRoot
```

The helper does not verify signatures, consume responses, ingest source bytes, write an archive, or advance the ledger.
