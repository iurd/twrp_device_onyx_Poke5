#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
DEVICE_DIR="$ROOT_DIR/device/onyx/Poke5"

cd "$ROOT_DIR"
python3 "$DEVICE_DIR/patches/scripts/apply_poke5_drm_patch.py" "$ROOT_DIR"
python3 "$DEVICE_DIR/patches/scripts/apply_poke5_drm_v13_ebc_patch.py" "$ROOT_DIR"
