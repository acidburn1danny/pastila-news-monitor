# Pilot 10 owner-controlled custodial signing

This helper signs only the eight challenges in the frozen Pilot 10 unsigned packet. It reads owner-controlled private keys outside the repository and emits public response JSON files outside the repository. It does not verify or consume responses and does not perform ingestion.

```powershell
$keyRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Secrets\Batch2-Custodians-v1'
$responseRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Handoff\Batch2-Development-Pilot10-v1'
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot10_signing_v1.py sign-all --key-dir $keyRoot --response-dir $responseRoot
```

The helper refuses repository-local secret or response paths and refuses to overwrite any existing public response.
