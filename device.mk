DEVICE_PATH := device/onyx/Poke5

PRODUCT_SHIPPING_API_LEVEL := 30
PRODUCT_TARGET_VNDK_VERSION := 30

PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/recovery/root/init.recovery.qcom.rc:recovery/root/init.recovery.qcom.rc \
    $(DEVICE_PATH)/recovery/root/ueventd.rc:recovery/root/ueventd.rc \
    $(DEVICE_PATH)/recovery/root/waveform/eink_waveform.wbf:recovery/root/waveform/eink_waveform.wbf

PRODUCT_PROPERTY_OVERRIDES += \
    ro.twrp.device=Poke5 \
    ro.twrp.platform=bengal
