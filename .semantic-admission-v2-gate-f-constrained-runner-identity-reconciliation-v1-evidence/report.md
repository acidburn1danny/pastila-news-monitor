# Gate F constrained-runner identity reconciliation V1

The historical constrained-runner manifest remains unchanged with identity `56954793dafaec12845efa57b8432eede593f8dc3bef9e09e46a5d9e34bdb5ac`. It expects host-executor SHA-256 `c27ec5bd143783e84a39ac93ed6352c0b4b67425f63308bc1c9f0a270ac03b4c` and focused-test SHA-256 `1dc52df165fa8ca55450b08aeeee3fce2f6b5724c85012c523a15871f5d2c951`.

Neither expected byte sequence exists in any reachable Git version of its path or in current repository content. They were not reconstructed or fabricated. The other six historical artifacts match their recorded SHA-256 values.

The current host executor and focused test originate at commit `14bf5fa3084b4a5907c7ffe549f6cf7a219b6dcb`. Their respective Git blobs are `03a8cf71297f1e6d326c19e865feede4b0a58c98` and `92ef1e56ac3a8c565e7f8d4ed5c2b4aebb5a8d5e`; their SHA-256 values are bound by the reconciliation receipt.

No byte-equivalence or semantic-equivalence claim is made. This receipt grants no WSL execution, runner execution, provider, model, probe, inference, runtime, or production authority.
