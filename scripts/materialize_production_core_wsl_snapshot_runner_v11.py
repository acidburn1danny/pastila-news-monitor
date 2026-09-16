"""Materialize the V11 no-copy WSL snapshot runner from byte-pinned V3."""
from __future__ import annotations
import argparse,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scripts/run_production_core_candidate_qualification_v3.sh"
SOURCE_SHA256="74d57b5c89c32792fee22eb2ac5b3206008577a2becccaa318d0f0fc90878e43"
OLD='''[[ -z "$(find "$MODEL" "$ADAPTER" -type l -print -quit)" ]] || exit 4
MODEL_SNAPSHOT="$WORK/model-snapshot"; ADAPTER_SNAPSHOT="$WORK/adapter-snapshot"
cp -a --reflink=auto -- "$MODEL" "$MODEL_SNAPSHOT"
cp -a --reflink=auto -- "$ADAPTER" "$ADAPTER_SNAPSHOT"
'''
NEW='''[[ -z "$(find "$MODEL" "$ADAPTER" -type l -print -quit)" ]] || exit 4
[[ -z "$(find "$MODEL" "$ADAPTER" \\( -type f -o -type d \\) -perm /222 -print -quit)" ]] || { echo "writable authority input rejected" >&2; exit 5; }
MODEL_SNAPSHOT="$WORK/model-snapshot"; ADAPTER_SNAPSHOT="$WORK/adapter-snapshot"
mkdir "$MODEL_SNAPSHOT" "$ADAPTER_SNAPSHOT"
for source_target in "$MODEL|$MODEL_SNAPSHOT" "$ADAPTER|$ADAPTER_SNAPSHOT"; do source="${source_target%%|*}"; target="${source_target#*|}"; mount --bind "$source" "$target"; mounted+=("$target"); mount -o remount,bind,ro "$target"; done
'''
def build():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError("V3 runner source drift")
 text=raw.decode("utf-8")
 if text.count(OLD)!=1:raise ValueError("V11 projection witness mismatch")
 return text.replace(OLD,NEW).encode()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);o=p.parse_args();raw=build()
 if o.output.exists() and (o.output.is_symlink() or o.output.read_bytes()!=raw):raise SystemExit("published V11 runner differs")
 if not o.output.exists():o.output.write_bytes(raw)
 print(hashlib.sha256(raw).hexdigest());return 0
if __name__=="__main__":raise SystemExit(main())
