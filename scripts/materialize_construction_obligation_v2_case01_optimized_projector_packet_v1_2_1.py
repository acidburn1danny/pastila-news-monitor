"""Materialize only the deterministic zero-execution optimized-projector packet."""
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import (
    PACKET_RELATIVE, materialize_case01_issuance_packet_v1_2_1)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    packet = root / PACKET_RELATIVE
    if packet.exists() or packet.is_symlink():
        raise FileExistsError("OPTIMIZED_PROJECTOR_PACKET_ALREADY_EXISTS")
    files = materialize_case01_issuance_packet_v1_2_1(project_root=root)
    packet.mkdir(parents=False)
    for name, raw in files.items():
        target = packet / name
        if target.exists() or target.is_symlink():
            raise FileExistsError("OPTIMIZED_PROJECTOR_PACKET_FILE_ALREADY_EXISTS")
        target.write_bytes(raw)


if __name__ == "__main__":
    main()
