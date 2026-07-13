#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
DEVICE_DIR="$ROOT_DIR/device/onyx/Poke5"
RECOVERY_DIR="$ROOT_DIR/bootable/recovery"
INTERFACES_DIR="$ROOT_DIR/hardware/interfaces"

apply_patch_dir() {
    local project_dir="$1"
    local patch_dir="$2"

    [[ -d "$patch_dir" ]] || return 0
    for patch in "$patch_dir"/*.patch; do
        [[ -e "$patch" ]] || continue
        if git -C "$project_dir" apply --recount --check "$patch" 2>/dev/null; then
            git -C "$project_dir" apply --recount "$patch"
            echo "Applied $(basename "$patch")"
        elif git -C "$project_dir" apply --recount --reverse --check "$patch" 2>/dev/null; then
            echo "Already applied $(basename "$patch")"
        else
            echo "Unable to apply $(basename "$patch") to $project_dir" >&2
            exit 1
        fi
    done
}

cd "$ROOT_DIR"

apply_patch_dir "$RECOVERY_DIR" "$DEVICE_DIR/patches"
apply_patch_dir "$INTERFACES_DIR" "$DEVICE_DIR/patches/hardware-interfaces"
