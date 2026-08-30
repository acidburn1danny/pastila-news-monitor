# Development Pilot 01 owner custodial signing

This procedure signs only the frozen pre-ingestion metadata packet. It does not
ingest or archive the source and grants no operational content authority.

From `C:\Projects\pastila-news-monitor`, first inspect the eight exact requests:

```powershell
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot01_signing_v1.py inspect
```

Confirm packet identity `5e02059125ffe6a8553eb2cbc7ffc1cca7b98201ba905cfe59dad50aa1e6ac75`,
the current ledger head, each role, purpose, nonce, and challenge identity. Then,
as the owner, sign with the six previously registered role-separated keys:

```powershell
$keyRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Secrets\Batch2-Custodians-v1'
$responseRoot = Join-Path $env:USERPROFILE 'Pastila-Owner-Handoff\Batch2-Development-Pilot01-v1'
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_development_pilot01_signing_v1.py sign-all --key-dir $keyRoot --response-dir $responseRoot
```

The helper refuses repository-local key and response directories, never prints
private-key material, never overwrites a response, and writes only public
signature responses. Keep the private PEM files outside Git. Return the eight
JSON responses from the handoff directory for a separately authorized
verification/ingestion decision. Do not stage the owner source, declaration,
private keys, or response directory.
