# TWRP 11 Device Tree for ONYX BOOX Poke5

> Unofficial TWRP 11 device tree for the ONYX BOOX Poke5, maintained in the
> [`iurd` fork](https://github.com/iurd/twrp_device_onyx_Poke5).

本仓库是 ONYX BOOX Poke5 的 TWRP 3.7.0（Android 11）设备树。相比原始设备树，
本 fork 修复了 **Recovery 黑屏问题（主题资源漏打包）**，并增加了 **GitHub Actions
自动构建与 Release 发布**流程。所有构建、提交和发布都只在 `iurd` 仓库进行。

## 设备信息

| 项目 | 值 |
| --- | --- |
| 型号 | ONYX BOOX Poke5 |
| 平台 | Qualcomm Scuba / QCM2290（Bengal 家族，`qcs2290`） |
| 系统 | Android 11（SDK 30） |
| 内核 | 4.19.157-perf #9（Onyx 原厂内核，2025-02-25） |
| 存储 | eMMC，A/B 分区，独立 `recovery_a` / `recovery_b` |
| 屏幕 | 6 英寸电子纸，逻辑 1072×1448，物理更新缓冲 1448×1072 |
| 测试固件 | `2025-04-02_15-00_v4.0-rel_77d3ae190` |
| TWRP | `3.7.0_11-Poke5-4.0-2025-04-02` |

## 重要修复：Recovery 黑屏

原镜像的 recovery ramdisk 里有 `twres/portrait.xml`、`twres/splash.xml` 和图片，
但缺少：

```text
twres/ui.xml
twres/fonts/RobotoCondensed-Regular.ttf
twres/fonts/DroidSansMono.ttf
```

TWRP 的主界面入口固定是 `/twres/ui.xml`，字体从 `/twres/fonts/` 读取。
缺少这些文件时 TWRP 无法加载主题，启动后停留在黑屏；前置光也没有走到 GUI
阶段的亮度初始化。

本设备树在 `device.mk` 中用 `PRODUCT_COPY_FILES` 显式声明主题入口和字体，
避免 Make 的 stale installed-file cleanup 把它们删除：

```make
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/theme/ui.xml:recovery/root/twres/ui.xml \
    $(DEVICE_PATH)/theme/portrait.xml:recovery/root/twres/portrait.xml \
    $(DEVICE_PATH)/theme/splash.xml:recovery/root/twres/splash.xml \
    $(DEVICE_PATH)/theme/fonts/RobotoCondensed-Regular.ttf:recovery/root/twres/fonts/RobotoCondensed-Regular.ttf \
    $(DEVICE_PATH)/theme/fonts/DroidSansMono.ttf:recovery/root/twres/fonts/DroidSansMono.ttf \
    $(call find-copy-subdir-files,*,$(DEVICE_PATH)/theme/images,recovery/root/twres/images)
```

主题版本为 5，与 TWRP 3.7.0 匹配。CI 会验证 `twres/ui.xml` 和字体确实在最终
ramdisk 中，避免再次发布黑屏镜像。

## 显示：ONYX EBC

Poke5 使用 ONYX 私有 EBC 接口刷新电子纸，而不是传统的 DRM page-flip：

1. 选择真实的 EPDC DRM connector（`DSI-2`，connector 46）和 CRTC 112。
2. 用 ONYX 私有 ioctl 初始化 `/dev/ebc`。
3. 映射 EBC framebuffer。
4. 将 TWRP 画面写入 EBC 缓冲。
5. 通过 `ONYX_EBC_SEND_UPDATE` 触发电子纸刷新。

关键补丁：

```text
patches/0001-minuitwrp-poke5-ebc-display.patch
```

使用的 ioctl：

```c
#define ONYX_EBC_GET_BUFFER_INFO 0x7003
#define ONYX_EBC_SEND_UPDATE     0x700c
```

Poke5 的 `/dev/ebc` 报告物理更新缓冲 `1448×1072`、逻辑/触摸尺寸 `1072×1448`，
而 DRM EPDC 模式是 `407×1083`。因此 TWRP 表面改为纵向 `1072×1448`，刷新时
旋转写入物理 `1448×1072` 缓冲，并按物理矩形发送更新。

## Data 解密

本设备树支持 metadata 加密 + FBE（wrapped key）：

- `recovery.fstab` / `fstab.poke5` 使用标准 Android fstab 语法，供 init、BCB 和
  `libfs_mgr` 解析。
- `twrp.fstab` 使用 TWRP 分区语法。
- 恢复流程启动 `qseecomd` 和 Qualcomm Keymaster HAL，通过 Keymaster 解开
  metadata 密钥；随后加载 user 0 的 DE/default CE 密钥并挂载 plaintext `/data`。
- `patches/0003`、`0004`、`0007`、`0009` 分别处理 crypto HAL 启动、Poke5 fstab、
  checkpoint 和 per-boot key。
- 诊断命令 `poke5md` / `poke5fbe` 位于 `patches/debug-disabled/`，不参与生产构建。

Data 解密依赖原厂 vendor 分区和测试固件 `4.0`，其他固件需要重新确认 fstab
和 Keymaster 行为。

## 仓库结构

```text
BoardConfig.mk                  # 分区、内核、TWRP 配置
device.mk                       # recovery root、主题、字体、属性
twrp_Poke5.mk                   # lunch product
prebuilt/Image.gz               # Onyx 原厂 4.19 内核（gzip，#9 2025-02-25）
prebuilt/dtb                    # 追加 DTB
prebuilt/recovery_dtbo          # Qualcomm QCDT
recovery/root/                  # init.recovery.qcom.rc、fstab、waveform
patches/                        # minuitwrp、GUI、fscrypt、Keymaster 补丁
theme/                          # 单色电子纸 TWRP 主题（ui.xml、字体、图片）
.github/workflows/release.yml   # 构建 + 校验 + Release
```

预编译文件来自 Poke5 原厂固件（v4.0，2025-04-02）：

```text
prebuilt/Image.gz
prebuilt/dtb
prebuilt/recovery_dtbo
recovery/root/waveform/eink_waveform.wbf
```

`eink_waveform.wbf` 是内核 EPDC waveform loader 所需文件，不能删除。

## 本地构建

### 环境

- Linux x86_64（Ubuntu 22.04 / 24.04 / 26.04 均可）
- OpenJDK 11
- Python 3、`repo`、`git`
- 建议 **10 GB 内存 + 8 GB swap**（`soong_build` 在 8 GB 环境下可能 OOM）
- 约 60 GB 可用磁盘
- 常用 AOSP 依赖：`bc bison build-essential ccache cpio curl flex g++-multilib
  gcc-multilib gperf imagemagick lib32ncurses5-dev lib32readline-dev lib32z1-dev
  libelf-dev liblz4-tool libncurses5 libssl-dev libxml2-utils lzop rsync
  schedtool squashfs-tools unzip xz-utils xsltproc zip zlib1g-dev`

WSL2 示例（`C:\Users\<you>\.wslconfig`）：

```ini
[wsl2]
memory=10GB
swap=8GB
```

修改后执行 `wsl --shutdown` 再重新进入。

### 初始化源码

```sh
mkdir -p ~/twrp11 && cd ~/twrp11
repo init --depth=1 \
  -u https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp.git \
  -b twrp-11
repo sync -c --no-clone-bundle --no-tags --fail-fast -j4
```

国内网络可把 AOSP remote 换成 TUNA（GitHub Actions 不需要）：

```sh
sed -i 's#fetch="https://android.googlesource.com"#fetch="https://mirrors.tuna.tsinghua.edu.cn/git/AOSP"#' \
  .repo/manifests/default.xml
```

TeamWin 仓库如果遇到 GitHub TLS 中断，可使用 ghproxy：

```sh
git config --global url."https://ghproxy.net/https://github.com/TeamWin/".insteadOf \
  "https://github.com/TeamWin/"
```

### 放入设备树并编译

```sh
git clone https://github.com/iurd/twrp_device_onyx_Poke5.git device/onyx/Poke5
bash device/onyx/Poke5/apply-patches.sh

source build/envsetup.sh
export ALLOW_MISSING_DEPENDENCIES=true
lunch twrp_Poke5-eng
mka -j4 recoveryimage
```

输出：

```text
out/target/product/Poke5/recovery.img
```

首次全量编译约 30–60 分钟（8 核）。当前源码构建产物约 **34.5 MB**，小于
100 MB 的 recovery 分区上限。

> 如果增量构建出现 `relink_libraries-timestamp` 相关的旧产物问题，执行一次
> `m installclean` 再编译。

## GitHub Actions 发布

工作流：`.github/workflows/release.yml`

功能：

1. 同步 TWRP 11 minimal manifest 源码。
2. 应用本设备树的全部补丁。
3. `lunch twrp_Poke5-eng` + `mka recoveryimage`。
4. 校验镜像：
   - 内核、QCDT、DTB 的 SHA-256 与 `prebuilt/` 一致
   - ramdisk 中存在 `init.recovery.qcom.rc`、`twres/ui.xml`、
     `twres/portrait.xml`、`twres/splash.xml`、两个主题字体、
     `waveform/eink_waveform.wbf`、`system/bin/recovery`、
     `system/lib64/libminuitwrp.so`
5. 上传 artifact。
6. 创建 GitHub Release，附带：
   - `twrp-Poke5-<version>.img`
   - `twrp-Poke5-<version>.img.sha256`

发布策略：

- 仅保留 `workflow_dispatch` 手动触发，并限制为仓库所有者 `iurd` 运行。
- 已关闭 tag 自动触发；
  后续只通过 **Actions → Build and Release Poke5 TWRP → Run workflow** 发布。
- 手动运行时填写 `tag`（默认 `v3.7.0-poke5`）和是否预发布。
- Release 由 `GITHUB_TOKEN` 创建，仓库需在
  **Settings → Actions → General → Workflow permissions** 中选择
  **Read and write permissions**。

Actions 页面：

```text
https://github.com/iurd/twrp_device_onyx_Poke5/actions/workflows/release.yml
```

Releases 页面：

```text
https://github.com/iurd/twrp_device_onyx_Poke5/releases
```

## 镜像校验

本地可用 TWRP 源码自带工具检查：

```sh
python3 system/tools/mkbootimg/unpack_bootimg.py \
  --boot_img out/target/product/Poke5/recovery.img --out /tmp/poke5-unpacked

magiskboot=external/magisk-prebuilt/prebuilt/magiskboot_x86
$magiskboot decompress /tmp/poke5-unpacked/ramdisk /tmp/poke5-ramdisk.cpio
$magiskboot cpio /tmp/poke5-ramdisk.cpio \
  "exists twres/ui.xml" \
  "exists twres/fonts/RobotoCondensed-Regular.ttf" \
  "exists twres/fonts/DroidSansMono.ttf" \
  "exists init.recovery.qcom.rc"
```

CI 还会校验预编译内核/QCDT/DTB 哈希：

```text
kernel         3c45b89edfebc063f2514540fd17e165f0967b9ce5fddbf60c3cd76940bba457
recovery_dtbo  9abe41f347215f6fb13ae0bd84f6bf5fe12bfd4bdb434e9244ceeae3a8b00a14
dtb            093e513e99fe888e4dadd6456a8d316c4d984a6c69447cfff346403f3dd47c03
```

## 刷入

Poke5 有真实的 recovery 分区，**不要刷到 `boot_a` / `boot_b`**。

优先临时启动验证：

```sh
fastboot boot out/target/product/Poke5/recovery.img
```

确认后刷入当前 slot：

```sh
adb shell getprop ro.boot.slot_suffix   # 例如 _a
fastboot flash recovery_a out/target/product/Poke5/recovery.img
fastboot reboot recovery
```

或在已 root 的 Android / 现有 TWRP 中写入：

```sh
adb push recovery.img /data/local/tmp/poke5_twrp.img
adb shell 'dd if=/data/local/tmp/poke5_twrp.img \
  of=/dev/block/by-name/recovery_a bs=4096 conv=fsync; sync'
adb reboot recovery
```

刷入前务必备份 stock recovery；镜像未签名（`BOARD_AVB_ENABLE := false`），
需要解锁 bootloader。

## 已知限制

- 非官方 TWRP，基于 Poke5 固件 `2025-04-02 v4.0` 构建；截至 2026-10-22 尚未在设备上实测。
- Data 解密依赖原厂 vendor/Keymaster，更换固件后需要重新验证。
- EBC 刷新和逻辑/物理尺寸是 Poke5 专属实现，不能直接用于其他 Onyx 机型。
- 镜像未做 AVB 签名；锁定的 bootloader 会拒绝启动。

## 致谢

- TeamWin TWRP 及 `minimal-manifest-twrp` TWRP 11 源码。
- `LGiki/twrp_device_onyx_leaf3`：ONYX EBC 刷新路径参考。
- `MollySophia/twrp_device_amazon_kindle`：单色电子纸 TWRP 主题来源。
- Onyx Poke5 原厂 recovery / `librecovery_ui.so` / minui 逆向分析。
- 主题许可见 `theme/LICENSE`。
