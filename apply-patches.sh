#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
DEVICE_DIR="$ROOT_DIR/device/onyx/Poke5"
RECOVERY_DIR="$ROOT_DIR/bootable/recovery"

cd "$ROOT_DIR"

for patch in "$DEVICE_DIR"/patches/*.patch; do
    if git -C "$RECOVERY_DIR" apply --check "$patch" 2>/dev/null; then
        git -C "$RECOVERY_DIR" apply "$patch"
        echo "Applied $(basename "$patch")"
    elif git -C "$RECOVERY_DIR" apply --reverse --check "$patch" 2>/dev/null; then
        echo "Already applied $(basename "$patch")"
    else
        echo "Unable to apply $(basename "$patch")" >&2
        exit 1
    fi
done
