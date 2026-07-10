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
patches/scripts/apply_poke5_drm_v13_ebc_patch.py
```

It uses:

```c
#define ONYX_EBC_GET_BUFFER_INFO 0x7003
#define ONYX_EBC_SEND_UPDATE     0x700c
```

On Poke5, `/dev/ebc` reports an actual update buffer of `1448x1072` even though the DRM EPDC mode is `407x1083`. The TWRP surface is therefore overridden to `1448x1072` for EBC refresh.

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
