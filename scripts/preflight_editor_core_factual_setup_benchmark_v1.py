"""Read-only physical preflight for the R1/R2 EDITOR benchmark comparison."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


EXPECTED = {
    "rootfs": "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
    "model": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
    "r1": "50b292f9cfdfb2f44dcc8bb9ef811ea367c78db505e4adc2c62e851e6060d3a4",
    "r2": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
    "requests": "436adcaf59392c852965501a1b1ed8068c991619e8f3de9e2cd92047f80ae51f",
    "worker": "77d562f0c3b688b9b6697b11426f7d12f9af9ffe446829c162d235af7b8c2be3",
    "constraint": "5c98158062dcf19d484a641b456b509bdcca1e5d21eba14754977bbd6a36ba6c",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def flat(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(root.iterdir(), key=lambda item: item.name.encode())
    if not paths or any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError("flat manifest closure")
    for path in paths:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(sha(path)))
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 8:
        raise SystemExit("usage: preflight ROOTFS MODEL R1 R2 REQUESTS WORKER CONSTRAINT")
    rootfs, model, r1, r2, requests, worker, constraint = map(Path, argv[1:])
    observed = {"rootfs": sha(rootfs), "model": flat(model), "r1": flat(r1), "r2": flat(r2),
                "requests": sha(requests), "worker": sha(worker), "constraint": sha(constraint)}
    if observed != EXPECTED:
        raise ValueError({key: [EXPECTED[key], observed[key]] for key in EXPECTED if EXPECTED[key] != observed[key]})
    print(json.dumps({"status": "PASS", "identities": observed, "model_loaded": False,
                      "inference": False, "training": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
