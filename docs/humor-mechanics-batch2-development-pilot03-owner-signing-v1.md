# DEVELOPMENT Pilot 03 custodial signing

This procedure signs only the frozen prospective Pilot 03 metadata packet. It does not ingest, archive, append a ledger event, perform G01 admission, or grant operational authority.

Inspect the eight unsigned requests:

```powershell
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot03_signing_v1.py inspect
```

Confirm the reported packet identity, prior ledger head, every role, purpose, nonce, object identity, and challenge identity.

Then, as the owner, sign with the six registered role-separated keys retained outside the repository:

```powershell
$keyRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Secrets\Batch2-Custodians-v1'
$responseRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Handoff\Batch2-Development-Pilot03-v1'
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot03_signing_v1.py sign-all --key-dir $keyRoot --response-dir $responseRoot
```

The helper refuses repository-local key and response paths, never prints private material, and never overwrites a response. Return the eight public response JSON files for a separately authorized verification decision. Do not stage the owner source, declaration, private keys, or response directory.
