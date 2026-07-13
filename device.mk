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
    $(DEVICE_PATH)/recovery.fstab:recovery/root/system/etc/twrp.fstab \
    $(DEVICE_PATH)/recovery/root/system/etc/fstab.poke5:recovery/root/system/etc/fstab.poke5 \
    $(DEVICE_PATH)/recovery/root/waveform/eink_waveform.wbf:recovery/root/waveform/eink_waveform.wbf

# Declare all non-ui.xml theme resources as recovery outputs so Make's stale
# installed-file cleanup keeps them. Patch 0002 then makes the Soong theme hook
# copy the complete directory after its default resources, preserving content.
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/theme/portrait.xml:recovery/root/twres/portrait.xml \
    $(DEVICE_PATH)/theme/splash.xml:recovery/root/twres/splash.xml \
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
