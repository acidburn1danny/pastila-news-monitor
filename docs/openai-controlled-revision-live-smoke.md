# OpenAI Controlled Revision live smoke test

The standalone smoke-test harness validates one provider-backed Controlled Revision
through the production OpenAI composition, canonical provider runtime, interpreter,
and gateway boundary. It is not collected by pytest and skips paid execution unless
explicitly enabled.

Requirements:

- `config/config.yaml` must contain the approved OpenAI model.
- `OPENAI_API_KEY` must be available through the environment or the repository's
  local `.env` fallback.
- The account must have access to the configured model.

Safe dry run, which performs no provider request:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_openai_controlled_revision.py
```

One-request live run:

```powershell
$env:SCOUT_RUN_LIVE_OPENAI_TESTS='1'
.\.venv\Scripts\python.exe scripts\smoke_test_openai_controlled_revision.py
Remove-Item Env:SCOUT_RUN_LIVE_OPENAI_TESTS
```

The execution-local policy permits one attempt, disables SDK retries, uses a
30-second timeout, and never falls back to another provider or model. The fixture is
short, synthetic Romanian text. Output is limited to content-free operational
status, counters, token usage, and availability flags; neither credential, prompt,
source draft, revised draft, nor raw provider response is printed.

External failures can include missing credentials, authentication or authorization,
model access, billing, rate limiting, timeout, transport, or provider availability.
Do not repeat a failed live execution without first identifying an allowed external
configuration correction and observing the milestone's two-request absolute limit.
