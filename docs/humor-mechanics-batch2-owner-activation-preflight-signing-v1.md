# Batch 2 owner activation-preflight signing V1

This procedure signs only content-free metadata challenges. It grants no
operational or content authority.

Inspect the frozen challenges:

~~~powershell
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_custodial_activation_preflight_v1.py inspect
~~~

Use the existing private-key directory and a new response directory, both
outside the repository:

~~~powershell
$keyRoot = Join-Path $env:USERPROFILE "Pastila-Owner-Secrets\Batch2-Custodians-v1"
$responseRoot = Join-Path $env:USERPROFILE "Pastila-Owner-Handoff\Batch2-Activation-Preflight-v1"
New-Item -ItemType Directory -Force -Path $responseRoot
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_custodial_activation_preflight_v1.py sign-all --key-dir $keyRoot --response-dir $responseRoot
git status --short
~~~

Return only the public preflight-response JSON files. Do not return private
keys. The helper refuses repository-local paths and output overwrites.
