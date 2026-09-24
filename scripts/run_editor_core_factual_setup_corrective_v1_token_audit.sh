#!/usr/bin/env bash
set -euo pipefail
[[ $# == 3 && $(id -u) == 0 ]] || exit 2
ROOTFS_TAR=$(realpath -e -- "$1"); MODEL=$(realpath -e -- "$2"); REPO=$(realpath -e -- "$3")
WORK=$(mktemp -d /tmp/editor-fsc-token.XXXXXXXX); ROOT="$WORK/rootfs"; mkdir "$ROOT"
cleanup(){ umount -R "$ROOT/dev" 2>/dev/null || true; umount "$ROOT/tmp/input/repo" 2>/dev/null || true; umount "$ROOT/tmp/input/model" 2>/dev/null || true; rm -rf -- "$WORK"; }; trap cleanup EXIT
tar -xf "$ROOTFS_TAR" -C "$ROOT"; mkdir -p "$ROOT/tmp/input/model" "$ROOT/tmp/input/repo" "$ROOT/dev"
mount --rbind /dev "$ROOT/dev"; mount --make-rslave "$ROOT/dev"
mount --bind "$MODEL" "$ROOT/tmp/input/model"; mount -o remount,bind,ro "$ROOT/tmp/input/model"
mount --bind "$REPO" "$ROOT/tmp/input/repo"; mount -o remount,bind,ro "$ROOT/tmp/input/repo"
env -i PATH=/usr/bin:/bin HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 /usr/sbin/chroot "$ROOT" /opt/production-core-runtime/bin/python -I -B /tmp/input/repo/scripts/audit_editor_core_factual_setup_corrective_v1_tokens.py /tmp/input/model /tmp/input/repo/docs/artifacts
