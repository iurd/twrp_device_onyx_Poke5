#!/system/bin/sh

# Poke5's vendor init deliberately panics when its recovery shutdown sequence
# exceeds the timeout, which leaves the device in Qualcomm crashdump (0x900e).
# Unmount decrypted userdata before TWRP requests reboot,recovery so init takes
# its short path directly to the reboot syscall.
sync
umount /storage/emulated/0 2>/dev/null || true
umount /sdcard 2>/dev/null || true
umount /data 2>/dev/null || umount -l /data 2>/dev/null || true
sync
