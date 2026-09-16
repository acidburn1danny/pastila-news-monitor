"""Zero-attempt host-capacity preflight for the V11 WSL execution boundary."""
from __future__ import annotations
import json,os,shutil
from pathlib import Path

VHD=Path(r"E:\WSL\Ubuntu-24.04\ext4.vhdx")
HOST_VOLUME=Path("E:/")
MINIMUM_FREE_BYTES=68_719_476_736
FILE_ATTRIBUTE_REPARSE_POINT=0x400

def build()->dict[str,object]:
 if not VHD.is_file() or VHD.is_symlink():raise RuntimeError("V11 WSL VHDX absent or symlinked")
 stat=VHD.stat();attributes=getattr(stat,"st_file_attributes",0)
 if attributes&FILE_ATTRIBUTE_REPARSE_POINT:raise RuntimeError("V11 WSL VHDX reparse point rejected")
 usage=shutil.disk_usage(HOST_VOLUME)
 if usage.free<MINIMUM_FREE_BYTES:raise RuntimeError("V11 host capacity gate failed")
 return {"schema":"pastila-production-core-v11-wsl-host-capacity-preflight","schema_version":1,"result":"PASS","vhd_path":str(VHD),"vhd_length":stat.st_size,"host_volume":"E:\\","observed_free_bytes":usage.free,"minimum_free_bytes":MINIMUM_FREE_BYTES,"qualification_rows":0,"candidate_execution":0,"attempt_consumption":0}
def main()->int:
 print(json.dumps(build(),separators=(",",":")));return 0
if __name__=="__main__":raise SystemExit(main())
