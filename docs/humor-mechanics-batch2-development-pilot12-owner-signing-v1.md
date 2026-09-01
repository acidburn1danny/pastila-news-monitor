# Pilot 12 owner-operated custodial signing

This procedure signs only the eight challenges frozen in the Pilot 12 unsigned
packet. Private keys remain in the owner-controlled secret directory; only
public response JSON files are written to the external handoff directory.

```powershell
$keyRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Secrets\Batch2-Custodians-v1'
$responseRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Handoff\Batch2-Development-Pilot12-v1'
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot12_signing_v1.py inspect
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot12_signing_v1.py sign-all --key-dir $keyRoot --response-dir $responseRoot
```

The helper refuses repository-local key or response paths and refuses to
overwrite an existing response. It does not independently verify signatures,
consume responses, ingest artifacts, or advance the ledger.
