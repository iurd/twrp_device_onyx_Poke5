DEVICE_PATH := device/onyx/Poke5

PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_SHIPPING_API_LEVEL := 30
PRODUCT_TARGET_VNDK_VERSION := 30

AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += \
    abl \
    boot \
    dtbo \
    modem \
    product \
    recovery \
    system \
    system_ext \
    vbmeta \
    vbmeta_system \
    vendor \
    xbl

PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/recovery/root/init.recovery.qcom.rc:recovery/root/init.recovery.qcom.rc \
    $(DEVICE_PATH)/recovery/root/ueventd.rc:recovery/root/ueventd.rc \
    $(DEVICE_PATH)/recovery/root/system/bin/rebootrecovery.sh:recovery/root/system/bin/rebootrecovery.sh \
    $(DEVICE_PATH)/recovery.fstab:recovery/root/system/etc/twrp.fstab \
    $(DEVICE_PATH)/recovery/root/system/etc/fstab.poke5:recovery/root/system/etc/fstab.poke5 \
    $(DEVICE_PATH)/recovery/root/waveform/eink_waveform.wbf:recovery/root/waveform/eink_waveform.wbf

# Declare every theme resource as a recovery output so Make's stale
# installed-file cleanup keeps it. The Soong theme hook alone is not enough:
# losing ui.xml leaves TWRP unable to load any theme (black screen), and the
# stock fonts are not part of the custom theme directory.
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/theme/ui.xml:recovery/root/twres/ui.xml \
    $(DEVICE_PATH)/theme/portrait.xml:recovery/root/twres/portrait.xml \
    $(DEVICE_PATH)/theme/splash.xml:recovery/root/twres/splash.xml \
    $(DEVICE_PATH)/theme/fonts/RobotoCondensed-Regular.ttf:recovery/root/twres/fonts/RobotoCondensed-Regular.ttf \
    $(DEVICE_PATH)/theme/fonts/DroidSansMono.ttf:recovery/root/twres/fonts/DroidSansMono.ttf \
    $(call find-copy-subdir-files,*,$(DEVICE_PATH)/theme/images,recovery/root/twres/images)

PRODUCT_PROPERTY_OVERRIDES += \
    ro.twrp.device=Poke5 \
    ro.twrp.platform=bengal

PRODUCT_SYSTEM_DEFAULT_PROPERTIES += \
    ro.build.version.security_patch=2023-08-01 \
    ro.vendor.build.security_patch=2023-08-01 \
    ro.build.display.id=2024-06-05_12-04_3.5.1_19ed122a7

PRODUCT_DEFAULT_PROPERTY_OVERRIDES += \
    ro.build.version.security_patch=2023-08-01 \
    ro.vendor.build.security_patch=2023-08-01
