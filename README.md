# ONYX BOOX Poke5：APatch Root 与 TWRP Recovery

> 本仓库是 ONYX BOOX Poke5 的 TWRP 3.7.0（Android 11）设备树与发布仓库，
> 同时整理了一份基于微信文章
> [《如何通过 APatch 获取文石 Poke5 root 权限》](https://mp.weixin.qq.com/s/Kd40b5glhCQy6_0KOc_FXg)
> 的 APatch / EDL root 指南。文章作者：Nosenlio（奇妙的人类调研所），2024-09-06。

所有构建、提交和 Release 都只在
[`iurd/twrp_device_onyx_Poke5`](https://github.com/iurd/twrp_device_onyx_Poke5)
仓库进行；本仓库不向其他仓库推送。

## 目录

- [设备信息](#设备信息)
- [风险与版本说明](#风险与版本说明)
- [一、APatch Root（基于文章）](#一apatch-root基于文章)
- [二、TWRP Recovery（本仓库）](#二twrp-recovery本仓库)
- [三、从源码构建](#三从源码构建)
- [四、镜像校验](#四镜像校验)
- [五、GitHub Actions 发布](#五github-actions-发布)
- [六、已知限制](#六已知限制)
- [致谢](#致谢)

## 设备信息

| 项目 | 值 |
| --- | --- |
| 型号 | ONYX BOOX Poke5 |
| 平台 | Qualcomm Scuba / QCM2290（Bengal 家族，`qcs2290`） |
| 系统 | Android 11（SDK 30） |
| 内核 | 4.19.157-perf #9（Onyx 原厂内核，2025-02-25） |
| 存储 | eMMC，A/B 分区，独立 `recovery_a` / `recovery_b` |
| 屏幕 | 6 英寸电子纸，逻辑 1072×1448，物理更新缓冲 1448×1072 |
| TWRP 测试固件 | `2025-04-02_15-00_v4.0-rel_77d3ae190` |
| TWRP 版本 | `3.7.0_11-Poke5-4.0-2025-04-02` |

## 风险与版本说明

- **APatch root 和 TWRP 是两条独立的路径**：
  - APatch root 修改并刷入 **boot 分区**（`boot_a` / `boot_b`）。
  - TWRP 刷入 **recovery 分区**（`recovery_a` / `recovery_b`）。
  - 不要把一个镜像刷到另一个分区，否则可能无法开机。
- 文章写于 **2024-09-06**，TWRP 当前基线是 **2025-04-02 v4.0**。不同固件的
  `update.upx`、boot image 和分区布局可能不同；请使用与你设备当前固件匹配的
  `update.upx`，不要跨版本刷 boot。
- EDL 刷写和 root 都有风险，可能导致数据丢失或设备无法启动。操作前必须做完整
  备份，并确认 bootloader 状态。
- 文章为作者个人经验，原文也注明“个人观点，仅供参考”。以下步骤是对文章的整理，
  请自行判断并承担风险。

---

## 一、APatch Root（基于文章）

> 本节按 Nosenlio 的文章整理，工具链接和命令以文章为准；文章未给出 `edl.exe`
> 与 APatch 的下载地址，需要从对应官方项目获取。

### 1. 准备工具

在电脑上新建一个英文路径的 `poke5` 文件夹，准备：

| 工具 | 用途 | 来源 |
| --- | --- | --- |
| Python 3 + pip | 运行解密/解包脚本 | python.org |
| `decryptBooxUpdateUpx` | 解密 Onyx `update.upx` | https://github.com/Hagb/decryptBooxUpdateUpx |
| `payload_dumper` | 从 `payload.bin` 提取 `boot.img` | https://github.com/vm03/payload_dumper |
| QCM2290 loader ELF | EDL 引导 Poke5 | https://github.com/bkerler/Loaders/blob/main/qualcomm/model_generic/qcm2290/001860e100000000_d9357db88795b5a8_Qcm2290_ddr_fhprg.elf |
| APatch | 修补 `boot.img` 获取 root | APatch 官方项目 |
| `edl.exe` | Qualcomm EDL 读写工具 | 自备（如 bkerler/edl 的 Windows 版本） |
| zadig | 安装 QUSB BULK CID 的 WINUSB 驱动 | zadig.akeo.ie |
| adb | 进入 EDL / 调试 | Android platform-tools |

将 QCM2290 的 `.elf` 文件重命名为 **`poke5.elf`**，放在同一文件夹。

### 2. 从设备获取 update.upx

1. 在 Poke5 上打开开发者选项和 USB 调试，并在应用设置中打开调试模式。
2. 设置 → 固件更新，下载最新的安装包；**下载完成后取消升级**。
3. 将 Poke5 连接电脑，把设备根目录的 `update.upx` 复制到 `poke5` 文件夹。
4. 文件夹路径不要包含中文。

### 3. 解密并提取 boot.img

在 `poke5` 文件夹打开终端（PowerShell / CMD），执行：

```powershell
python DeBooxUpx.py Poke5 update.upx update.zip
```

从 `update.zip` 中解出 `payload.bin`，然后安装依赖并解包：

```powershell
python -m pip install -r requirements.txt
python payload_dumper.py payload.bin
```

完成后在 `output/` 中得到 `boot.img`。

如果出现 `No module named 'google'`：

```powershell
pip install -i https://mirrors.aliyun.com/pypi/simple/ google-cloud
pip install -i https://mirrors.aliyun.com/pypi/simple/ google-cloud-vision
```

### 4. 用 APatch 修补 boot.img

1. 把 `output/boot.img` 传到 Poke5。
2. 在 APatch 中选择该 `boot.img` 进行修补。
3. 将修补产物重命名为 **`apatch.img`**，再复制回电脑的 `poke5` 文件夹。

### 5. 进入 EDL

```powershell
adb reboot edl
```

1. 打开 zadig，勾选所有设备，在 Device 列表中选择 **QUSB BULK CID**。
2. 驱动选择 **WINUSB**，点击安装。
3. 在 `poke5` 文件夹执行：

```powershell
.\edl.exe
```

出现 **EDL9008** 表示连接成功。加载 Poke5 loader：

```powershell
.\edl.exe /l poke5.elf
```

> 文章写作 `/lPoke5.elf`（无空格）；以你的 `edl.exe` 版本语法为准。

加载 loader 后，按文章先重启并让系统完成更新，然后再次进入 EDL：

```powershell
.\edl.exe /z
adb reboot edl
```

### 6. 全量备份（必须）

```powershell
.\edl.exe /r backup.img
```

备份文件会写入当前目录；所在磁盘至少留 **35 GB** 空闲空间（文章建议 35 GB 以上）。
不要跳过这一步。

### 7. 确认 active boot slot 并刷入

```powershell
.\edl.exe /g
```

查看当前活动的 **boot** 分区。文章示例为 `b`，即 `boot_b`。然后写入修补后的
`apatch.img`（把 `b` 换成你实际的活动 slot）：

```powershell
.\edl.exe /w /pboot_b apatch.img /z
```

刷写完成后设备自动重启。开机后打开 APatch，确认 root 状态。

### 8. 注意事项

- `/w /pboot_b` 写入的是 **boot 分区**，不是 recovery；不要写成 `recovery_b`。
- 必须使用 `/g` 显示的活动 slot；A/B 设备刷错 slot 会导致当前系统无法启动。
- 不要混用不同固件版本的 `boot.img` / `apatch.img`。
- 如果只想安装 TWRP，不一定要先做 APatch root；两者可以独立进行。
- 完整备份 `backup.img` 是出问题后的恢复手段，务必保留。

---

## 二、TWRP Recovery（本仓库）

本设备树修复了原 TWRP 镜像的黑屏问题，并提供 v4.0 基线的可构建、可发布的
Recovery。

### 最新 Release

- 发布页：https://github.com/iurd/twrp_device_onyx_Poke5/releases
- v4.0 Release：https://github.com/iurd/twrp_device_onyx_Poke5/releases/tag/v4.0-20261022
- 资产：`twrp-Poke5-3.7.0-v4.0-20261022.img`
- SHA256：`97cd23f89c883702c95adc5b0c0b408382e715d8201b70fb44a168f65ed3cbc5`
- 镜像为 **96 MiB 整分区**，带与原厂一致的 hash-only AVB footer（无签名）。

旧版 `v3.7.0-poke5` 也保留在 Releases 中，按需选择。

### 黑屏修复

原 recovery ramdisk 里有 `twres/portrait.xml`、`twres/splash.xml` 和图片，但缺少：

```text
twres/ui.xml
twres/fonts/RobotoCondensed-Regular.ttf
twres/fonts/DroidSansMono.ttf
```

TWRP 主界面入口固定是 `/twres/ui.xml`，字体从 `/twres/fonts/` 读取。缺少这些文件
时 TWRP 无法加载主题，启动后停留在黑屏；前置光也没有走到 GUI 阶段的亮度初始化。

本设备树在 `device.mk` 中用 `PRODUCT_COPY_FILES` 显式打包主题入口和字体：

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

### 刷入 TWRP

Poke5 有真实的 recovery 分区，**不要刷到 `boot_a` / `boot_b`**。

优先临时启动验证：

```sh
IMG=twrp-Poke5-3.7.0-v4.0-20261022.img
fastboot boot "$IMG"
```

确认后刷入当前 slot：

```sh
adb shell getprop ro.boot.slot_suffix   # 例如 _b
fastboot flash recovery_b "$IMG"
fastboot reboot recovery
```

或在已 root 的 Android / 现有 TWRP 中写入：

```sh
adb push "$IMG" /data/local/tmp/poke5_twrp.img
adb shell 'dd if=/data/local/tmp/poke5_twrp.img \
  of=/dev/block/by-name/recovery_b bs=4096 conv=fsync; sync'
adb reboot recovery
```

刷入前备份 stock recovery。96 MiB 整分区镜像要写入完整文件，不要截断；镜像带
hash-only AVB footer，但没有 AVB 签名，需要解锁 bootloader。

### APatch root 与 TWRP 的关系

- 两者分区不同：APatch 写 `boot_<slot>`，TWRP 写 `recovery_<slot>`。
- 同一 active slot 的 boot/recovery 通常成对使用；例如 `/g` 显示 `b`，则 root 写
  `boot_b`，TWRP 写 `recovery_b`。
- 先做 APatch root 不影响 TWRP；先刷 TWRP 也不影响 boot 上的 APatch。
- 每次系统 OTA 后，boot 可能被覆盖，APatch root 需要重新修补；TWRP 也可能被
  stock recovery 覆盖，必要时重新刷入。

### 显示与 Data 解密

Poke5 使用 ONYX 私有 EBC 接口刷新电子纸：选择 `DSI-2` connector / CRTC 112，
通过 `/dev/ebc` 的 `ONYX_EBC_GET_BUFFER_INFO`（`0x7003`）和
`ONYX_EBC_SEND_UPDATE`（`0x700c`）完成刷新；TWRP 画面为纵向 `1072×1448`，
刷新时旋转写入物理 `1448×1072` 缓冲。关键补丁：

```text
patches/0001-minuitwrp-poke5-ebc-display.patch
```

Data 使用 metadata 加密 + FBE（wrapped key）。恢复流程启动 `qseecomd` 和
Qualcomm Keymaster HAL，解开 metadata 密钥后加载 user 0 的 DE/default CE 密钥。
Data 解密依赖原厂 vendor 和固件版本，换固件后需要重新验证。

---

## 三、从源码构建

### 环境

- Linux x86_64（Ubuntu 22.04 / 24.04 / 26.04 均可）
- OpenJDK 11
- Python 3、`repo`、`git`
- 建议 **10 GB 内存 + 8 GB swap**（`soong_build` 在 8 GB 下可能 OOM）
- 约 60 GB 可用磁盘
- 常用依赖：`bc bison build-essential ccache cpio curl flex g++-multilib
  gcc-multilib gperf imagemagick lib32ncurses5-dev lib32readline-dev lib32z1-dev
  libelf-dev liblz4-tool libncurses5 libssl-dev libxml2-utils lzop rsync
  schedtool squashfs-tools unzip xz-utils xsltproc zip zlib1g-dev`

WSL2（`C:\Users\<you>\.wslconfig`）：

```ini
[wsl2]
memory=10GB
swap=8GB
```

修改后执行 `wsl --shutdown` 再进入。

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

TeamWin 仓库遇到 GitHub TLS 中断时可用 ghproxy：

```sh
git config --global url."https://ghproxy.net/https://github.com/TeamWin/".insteadOf \
  "https://github.com/TeamWin/"
```

### 编译

```sh
git clone https://github.com/iurd/twrp_device_onyx_Poke5.git device/onyx/Poke5
bash device/onyx/Poke5/apply-patches.sh

source build/envsetup.sh
export ALLOW_MISSING_DEPENDENCIES=true
lunch twrp_Poke5-eng
mka -j4 recoveryimage
```

输出 `out/target/product/Poke5/recovery.img`（约 34.5 MB 的 boot image）。首次全量
编译约 30–60 分钟（8 核）。

### 打包 96 MiB 整分区镜像

```sh
python3 device/onyx/Poke5/tools/package_poke5.py \
  --tree . \
  --template device/onyx/Poke5/tools/stock-avb-template.bin \
  --tag v4.0-20261022
```

输出：

```text
out/target/product/Poke5/twrp-Poke5-3.7.0-v4.0-20261022.img          # 96 MiB
out/target/product/Poke5/twrp-Poke5-3.7.0-v4.0-20261022.img.sha256
out/target/product/Poke5/twrp-Poke5-3.7.0-v4.0-20261022.info.txt
out/target/product/Poke5/twrp-Poke5-3.7.0-v4.0-20261022-raw.img      # 34.5 MB
```

脚本会校验 boot header、kernel/DTB/QCDT 哈希、TWRP 主题/fstab/waveform、
Keymaster 服务、v4.0 安全补丁和 AVB hash。AVB footer 与 stock 一样是 hash-only
（algorithm NONE），没有签名。

---

## 四、镜像校验

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

---

## 五、GitHub Actions 发布

工作流：`.github/workflows/release.yml`，分为两个 job。

`build`：

1. 同步 TWRP 11 minimal manifest 源码。
2. 应用本设备树的全部补丁。
3. `lunch twrp_Poke5-eng` + `mka recoveryimage`。
4. 校验原始 `recovery.img`（内核/QCDT/DTB 哈希、主题/fonts、fstab/waveform、
   `system/bin/recovery`、`libminuitwrp.so`）。
5. 使用 `tools/package_poke5.py` 打包 96 MiB 整分区镜像并套用原厂 AVB 模板。
6. 上传 artifact（保留 14 天）。

`release`：

7. 下载 artifact，校验 96 MiB 大小和 SHA256。
8. 用实际构建的 SHA256、资产名和源码提交生成 Release 正文。
9. 创建/更新 GitHub Release，附带：
   - `twrp-Poke5-3.7.0-<tag>.img`（96 MiB 整分区）
   - `twrp-Poke5-3.7.0-<tag>.img.sha256`
   - `twrp-Poke5-3.7.0-<tag>.info.txt`

手动运行参数：

- `tag`：必填的新 tag，例如 `v4.0-20261022-1`；复用已有 tag 会更新对应 Release。
- `release_name`：Release 标题，默认 `TWRP 3.7.0 for Poke5 — v4.0 (2025-04-02)`。
- `prerelease`：默认 `true`；设备实测通过后再取消。
- `make_latest`：默认 `false`；仅正式版开启。

发布策略：

- 仅保留 `workflow_dispatch` 手动触发。
- Job 限制为 `github.actor == github.repository_owner`，只有仓库所有者 `iurd` 能运行。
- 已关闭 tag 自动触发；发布只通过 Actions 页面手动运行。
- 当前已手动发布 Pre-release `v4.0-20261022`；下一次运行请使用新 tag，避免覆盖。
- Release 由 `GITHUB_TOKEN` 创建；仓库需在
  **Settings → Actions → General → Workflow permissions** 中选择
  **Read and write permissions**。

Actions 页面：

```text
https://github.com/iurd/twrp_device_onyx_Poke5/actions/workflows/release.yml
```

---

## 六、已知限制

- 非官方 TWRP，基于 Poke5 固件 `2025-04-02 v4.0` 构建；截至 2026-10-22 尚未在
  设备上实测。
- Data 解密依赖原厂 vendor/Keymaster，更换固件后需要重新验证。
- EBC 刷新和逻辑/物理尺寸是 Poke5 专属实现，不能直接用于其他 Onyx 机型。
- 镜像带 hash-only AVB footer，但没有 AVB 签名；锁定 bootloader 会拒绝启动。
- APatch root 指南基于 2024-09-06 的文章；在 v4.0 或其他固件上操作前，请确认
  `update.upx` 结构、`payload.bin` 和 boot image 与当前系统匹配。

## 致谢

- Nosenlio / 奇妙的人类调研所：
  [《如何通过 APatch 获取文石 Poke5 root 权限》](https://mp.weixin.qq.com/s/Kd40b5glhCQy6_0KOc_FXg)（2024-09-06）。
- TeamWin TWRP 及 `minimal-manifest-twrp` TWRP 11 源码。
- `LGiki/twrp_device_onyx_leaf3`：ONYX EBC 刷新路径参考。
- `MollySophia/twrp_device_amazon_kindle`：单色电子纸 TWRP 主题来源。
- Onyx Poke5 原厂 recovery / `librecovery_ui.so` / minui 逆向分析。
- 主题许可见 `theme/LICENSE`。
