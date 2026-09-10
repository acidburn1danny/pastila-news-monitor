#!/usr/bin/env bash
set -euo pipefail
readonly PARENT_SHA="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
readonly PACKAGES=(gcc gcc-13 gcc-13-x86-64-linux-gnu cpp cpp-13 cpp-13-x86-64-linux-gnu binutils binutils-x86-64-linux-gnu libc6-dev linux-libc-dev libgcc-13-dev python3.12-dev libpython3.12-dev)
if [[ $# -ne 2 ]]; then echo "usage: builder PARENT_ROOTFS_TAR EMPTY_OUTPUT_DIR" >&2; exit 2; fi
PARENT="$(realpath -e -- "$1")"; OUTPUT="$(realpath -m -- "$2")"
[[ "$(id -u)" == 0 && -f "$PARENT" && "$(sha256sum "$PARENT" | cut -d' ' -f1)" == "$PARENT_SHA" ]] || exit 3
mkdir -p "$OUTPUT"; [[ -z "$(find "$OUTPUT" -mindepth 1 -print -quit)" ]] || exit 3
WORK="$(mktemp -d /tmp/pcs-rootfs.XXXXXXXX)"; ROOT="$WORK/root"; mkdir "$ROOT"
cleanup() { rm -rf -- "$WORK"; }; trap cleanup EXIT INT TERM
tar -xf "$PARENT" -C "$ROOT"
[[ ! -e "$ROOT/lib" && ! -L "$ROOT/lib" ]] || exit 4
ln -s usr/lib "$ROOT/lib"
VERSIONS="$WORK/package-versions.tsv"; : > "$VERSIONS"
PATHS="$WORK/package-paths.txt"; : > "$PATHS"
for package in "${PACKAGES[@]}"; do
  dpkg-query -W -f='${binary:Package}\t${Version}\n' "$package" >> "$VERSIONS"
  dpkg-query -L "$package" >> "$PATHS"
done
LC_ALL=C sort -u -o "$PATHS" "$PATHS"; LC_ALL=C sort -o "$VERSIONS" "$VERSIONS"
while IFS= read -r path; do
  [[ "$path" == /* ]] || exit 4
  if [[ -f "$path" || -L "$path" ]]; then cp -a --parents -- "$path" "$ROOT"; fi
done < "$PATHS"
printf '#include <cuda.h>\n#include <Python.h>\nint main(void){return 0;}\n' > "$ROOT/tmp/toolchain-probe.c"
/usr/sbin/chroot "$ROOT" /usr/bin/gcc /tmp/toolchain-probe.c -O3 -shared -fPIC -o /tmp/toolchain-probe.so -l:libcuda.so.1 -L/usr/lib/wsl/lib -I/usr/include/python3.12 -I/opt/production-core-runtime/lib/python3.12/site-packages/triton/backends/nvidia/include
rm -f -- "$ROOT/tmp/toolchain-probe.c"
rm -f -- "$ROOT/tmp/toolchain-probe.so"
INVENTORY="$WORK/toolchain-inventory.tsv"; : > "$INVENTORY"
while IFS= read -r path; do
  target="$ROOT$path"
  if [[ -f "$target" && ! -L "$target" ]]; then printf '%s\t%s\n' "$path" "$(sha256sum "$target" | cut -d' ' -f1)" >> "$INVENTORY"; fi
done < "$PATHS"
LC_ALL=C sort -u -o "$INVENTORY" "$INVENTORY"
tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner --format=posix --pax-option=delete=atime,delete=ctime -cf "$OUTPUT/rootfs.tar" -C "$ROOT" .
ROOTFS_SHA="$(sha256sum "$OUTPUT/rootfs.tar" | cut -d' ' -f1)"
cp "$VERSIONS" "$OUTPUT/package-versions.tsv"; cp "$INVENTORY" "$OUTPUT/toolchain-inventory.tsv"
printf '{"schema":"pastila-production-core-offline-training-rootfs","schema_version":1,"parent_rootfs_sha256":"%s","training_rootfs_sha256":"%s","package_versions_sha256":"%s","toolchain_inventory_sha256":"%s","network_activity":false,"qualification_attempt_consumed":false,"promotion_effect":false}\n' "$PARENT_SHA" "$ROOTFS_SHA" "$(sha256sum "$VERSIONS" | cut -d' ' -f1)" "$(sha256sum "$INVENTORY" | cut -d' ' -f1)" > "$OUTPUT/rootfs-manifest.json"
printf '%s\n' "$ROOTFS_SHA"
