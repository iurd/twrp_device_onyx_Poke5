# TWRP device tree for ONYX BOOX Poke5

Unofficial TWRP 11 device tree for the ONYX BOOX Poke5.

## Device

- Model: ONYX BOOX Poke5
- Platform: Qualcomm Bengal / QCS2290 family
- Android: 11
- Kernel: 4.19.157
- Storage: eMMC, dedicated `recovery_a` / `recovery_b` partitions
- Tested firmware: `2024-06-05_12-04_3.5.1_19ed122a7`

## Current display status

The current display path follows the working BOOX Leaf3/Page approach:

1. Select the real EPDC DRM connector (`DSI-2`, connector 46) and CRTC 112.
2. Initialize `/dev/ebc` with ONYX private ioctls.
3. Map the EBC framebuffer.
4. Render TWRP into the EBC buffer.
5. Refresh the e-ink panel with `ONYX_EBC_SEND_UPDATE`.

The key patch is:

```text
patches/0001-minuitwrp-poke5-ebc-display.patch
```

It uses:

```c
#define ONYX_EBC_GET_BUFFER_INFO 0x7003
#define ONYX_EBC_SEND_UPDATE     0x700c
```

On Poke5, `/dev/ebc` reports a physical update buffer of `1448x1072` and a logical/touch size of `1072x1448` even though the DRM EPDC mode is `407x1083`. The TWRP surface is therefore overridden to portrait `1072x1448`; when refreshing, pixels are rotated into the physical `1448x1072` EBC buffer and the update ioctl uses the physical rect.

## E-ink theme

This tree includes a monochrome Kindle e-ink TWRP theme under `theme/`, derived from `MollySophia/twrp_device_amazon_kindle`. `TW_CUSTOM_THEME` points to that directory. The theme keeps its original `1080x1920` design resolution so TWRP's built-in theme scaler can map it onto the Poke5 logical portrait framebuffer (`1072x1448`).

The build patch `patches/0002-gui-support-custom-theme-directory.patch` extends the TWRP Soong theme copy hook so the complete device theme is copied after the default resources instead of being overwritten by them.

## Data decryption

The production patch series automatically mounts metadata-encrypted `/data`,
loads the user 0 DE/default CE keys, and exposes plaintext internal storage.
Only qseecomd and the Qualcomm Keymaster service are started from the
device-owned recovery rc. Metadata/FBE state and TWRP storage refresh remain in
`partitionmanager.cpp`, where they can update the live recovery process.

Diagnostic `poke5md` and `poke5fbe` commands are archived under
`patches/debug-disabled/` and are not applied to production builds.

## Stock-derived blobs

This tree currently includes stock-derived files needed for this build:

```text
prebuilt/Image
prebuilt/dtb
prebuilt/recovery_dtbo
recovery/root/waveform/eink_waveform.wbf
```

The waveform file is required for the kernel EPDC waveform loader:

```text
/waveform/eink_waveform.wbf
```

## Build

Clone into a synced TWRP 11 tree at:

```text
device/onyx/Poke5
```

Apply patches:

```sh
device/onyx/Poke5/apply-patches.sh
```

Build:

```sh
source build/envsetup.sh
export ALLOW_MISSING_DEPENDENCIES=true
lunch omni_Poke5-eng
mka recoveryimage
```

`TW_INCLUDE_CRYPTO_FBE` is enabled so TWRP's make-side relinker packages the
FBE and Keymaster support libraries into a clean recovery ramdisk. If an old
incremental output directory has a stale `relink_libraries-timestamp` after
files were manually removed, run `m installclean` once before rebuilding.

Output:

```text
out/target/product/Poke5/recovery.img
```

## Flashing notes

Poke5 has real recovery partitions. Do not flash this image to `boot_a` or `boot_b`.

Example from rooted Android:

```sh
adb push recovery.img /data/local/tmp/poke5_twrp.img
adb shell '/product/bin/su -c "dd if=/data/local/tmp/poke5_twrp.img of=/dev/block/by-name/recovery_a bs=4096 conv=fsync; sync"'
adb reboot recovery
```

Keep stock recovery backups before testing.

## References

This display implementation was informed by:

- `LGiki/twrp_device_onyx_leaf3`, especially its ONYX EBC refresh path.
- Stock Poke5 recovery `librecovery_ui.so` / minui reverse engineering.
