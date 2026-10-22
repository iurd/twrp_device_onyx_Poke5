#!/usr/bin/env python3
"""Package the Poke5 TWRP build as a 96 MiB recovery image with the stock AVB structure."""
import argparse
import gzip
import hashlib
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootimg_poke5 import avb_footer, cpio_entries, parse_header, section_offsets

PARTITION_SIZE = 100663296
STOCK_FINGERPRINT = "Onyx/Poke5/Poke5:11/2025-04-02_15-00_v4.0-rel_77d3ae190/10188:user/release-keys"
STOCK_CMDLINE = (
    "console=ttyMSM0,115200n8 earlycon=msm_geni_serial,0x4a90000 "
    "androidboot.hardware=qcom androidboot.console=ttyMSM0 androidboot.memcg=1 "
    "lpm_levels.sleep_disabled=1 video=vfb:640x400,bpp=32,memsize=3072000 "
    "msm_rtb.filter=0x237 service_locator.enable=1 swiotlb=2048 loop.max_part=7 "
    "buildvariant=user"
)
STOCK_HEADER = {
    "kernel_addr": 0x8000,
    "ramdisk_addr": 0x1000000,
    "tags_addr": 0x100,
    "dtb_addr": 0x1F00000,
    "page_size": 4096,
    "header_version": 2,
    "os_version": 0x16000182,
}


def run(cmd):
    print("+", " ".join(str(x) for x in cmd))
    subprocess.run([str(x) for x in cmd], check=True)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def find_hash_descriptor(blob):
    major, minor, auth_size, aux_size = struct.unpack_from(">IIQQ", blob, 4)
    aux_base = 256 + auth_size
    aux = blob[aux_base:aux_base + aux_size]
    desc_off, desc_size = struct.unpack_from(">QQ", blob, 96)
    pos = desc_off
    while pos < desc_off + desc_size:
        tag, nbf = struct.unpack_from(">QQ", aux, pos)
        body = pos + 16
        if tag == 2:
            name_len, salt_len, digest_len = struct.unpack_from(">III", aux, body + 40)
            off = body + 116
            name = aux[off:off + name_len].decode("utf-8", "replace")
            salt_off = aux_base + off + name_len
            digest_off = salt_off + salt_len
            return {
                "image_size_off": aux_base + body,
                "name": name,
                "salt_off": salt_off,
                "salt_len": salt_len,
                "digest_off": digest_off,
                "digest_len": digest_len,
                "salt": blob[salt_off:salt_off + salt_len],
            }
        pos += 16 + nbf
        pos = (pos + 7) // 8 * 8
    raise SystemExit("no AVB hash descriptor in template")


def parse_vbmeta(blob):
    if blob[:4] != b"AVB0":
        raise SystemExit("vbmeta magic missing")
    major, minor, auth_size, aux_size = struct.unpack_from(">IIQQ", blob, 4)
    algorithm = struct.unpack_from(">I", blob, 28)[0]
    aux = blob[256 + auth_size:256 + auth_size + aux_size]
    desc_off, desc_size = struct.unpack_from(">QQ", blob, 96)
    descriptors = []
    pos = desc_off
    while pos < desc_off + desc_size:
        tag, nbf = struct.unpack_from(">QQ", aux, pos)
        body = aux[pos + 16:pos + 16 + nbf]
        if tag == 0:
            key_len, value_len = struct.unpack_from(">QQ", body, 0)
            off = 16
            key = body[off:off + key_len].decode("utf-8", "replace")
            off += key_len
            if off < len(body) and body[off] == 0:
                off += 1
            value = body[off:off + value_len].decode("utf-8", "replace")
            descriptors.append(("property", key, value))
        elif tag == 2:
            image_size = struct.unpack_from(">Q", body, 0)[0]
            alg = body[8:40].split(b"\0")[0].decode("ascii", "replace")
            name_len, salt_len, digest_len = struct.unpack_from(">III", body, 40)
            off = 116
            name = body[off:off + name_len].decode("utf-8", "replace")
            off += name_len
            salt = body[off:off + salt_len]
            off += salt_len
            digest = body[off:off + digest_len]
            descriptors.append(("hash", name, alg, image_size, salt, digest))
        else:
            descriptors.append(("tag", tag, nbf))
        pos += 16 + nbf
        pos = (pos + 7) // 8 * 8
    return {
        "version": (major, minor),
        "algorithm": algorithm,
        "auth_size": auth_size,
        "aux_size": aux_size,
        "descriptors": descriptors,
    }


def cpio_names(cpio):
    return {entry["name"].rstrip("/") for entry in cpio_entries(cpio)}


def cpio_read(cpio, target):
    for entry in cpio_entries(cpio):
        if entry["name"].rstrip("/") == target:
            return cpio[entry["offset"]:entry["offset"] + entry["size"]]
    raise SystemExit(f"missing cpio file: {target}")


def parse_props(blob):
    props = {}
    for line in blob.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key] = value
    return props


def load_template(path):
    blob = path.read_bytes()
    if len(blob) < 64 or blob[:4] != b"AVB0" or blob[-64:-60] != b"AVBf":
        raise SystemExit(f"invalid AVB template: {path}")
    vbmeta = bytearray(blob[:-64])
    footer = bytearray(blob[-64:])
    vbmeta_size = struct.unpack_from(">Q", footer, 28)[0]
    if vbmeta_size != len(vbmeta):
        raise SystemExit(f"template vbmeta size {vbmeta_size} != {len(vbmeta)}")
    return vbmeta, footer


def verify_stock_header(path):
    header = parse_header(path.read_bytes())
    if header["cmdline"] != STOCK_CMDLINE:
        raise SystemExit("stock image cmdline differs from the expected v4.0 cmdline")
    for key, value in STOCK_HEADER.items():
        if header[key] != value:
            raise SystemExit(f"stock image {key} differs: {header[key]:#x} != {value:#x}")
    print("stock image header: verified")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", type=Path, default=Path("."))
    parser.add_argument("--template", type=Path)
    parser.add_argument("--stock", type=Path, help="optional original image for header verification")
    parser.add_argument("--tag", default="v4.0-20261022")
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-dir", type=Path)
    args = parser.parse_args()

    tree = args.tree.resolve()
    device = tree / "device/onyx/Poke5"
    out = tree / "out/target/product/Poke5"
    template_path = args.template or device / "tools/stock-avb-template.bin"
    mkbootimg = tree / "out/host/linux-x86/bin/mkbootimg"
    kernel = device / "prebuilt/Image.gz"
    dtb = device / "prebuilt/dtb"
    dtbo = device / "prebuilt/recovery_dtbo"
    ramdisk = out / "ramdisk-recovery.img"
    for path in (template_path, mkbootimg, kernel, dtb, dtbo, ramdisk):
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")
    if args.stock:
        verify_stock_header(args.stock)

    outdir = (args.outdir or out).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    final = (args.output or (outdir / f"twrp-Poke5-3.7.0-{args.tag}.img")).resolve()
    final.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = (args.raw_dir or final.parent).resolve()
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / f"{final.stem}-raw.img"

    run([
        mkbootimg,
        "--kernel", kernel,
        "--ramdisk", ramdisk,
        "--dtb", dtb,
        "--recovery_dtbo", dtbo,
        "--base", "0x00000000",
        "--pagesize", "4096",
        "--header_version", "2",
        "--os_version", "11.0.0",
        "--os_patch_level", "2024-02",
        "--cmdline", STOCK_CMDLINE,
        "--output", raw,
    ])

    raw_data = raw.read_bytes()
    header = parse_header(raw_data)
    offsets = section_offsets(header)
    for key, value in STOCK_HEADER.items():
        if header[key] != value:
            raise SystemExit(f"header {key} mismatch: {header[key]:#x} != {value:#x}")
    if header["cmdline"] != STOCK_CMDLINE:
        raise SystemExit("cmdline differs from the stock v4.0 cmdline")
    print("boot header: matches stock addresses, patch level and cmdline")

    expected = {
        "kernel": sha256(kernel.read_bytes()),
        "dtb": sha256(dtb.read_bytes()),
        "recovery_dtbo": sha256(dtbo.read_bytes()),
        "ramdisk": sha256(ramdisk.read_bytes()),
    }
    for key, digest in expected.items():
        off, size = offsets[key]
        actual = sha256(raw_data[off:off + size])
        if actual != digest:
            raise SystemExit(f"{key} mismatch: {actual} != {digest}")
        print(f"{key}: {size} bytes, sha256 {actual}")

    vbmeta, footer = load_template(template_path)
    desc = find_hash_descriptor(vbmeta)
    struct.pack_into(">Q", vbmeta, desc["image_size_off"], len(raw_data))
    digest = hashlib.sha256(desc["salt"] + raw_data).digest()
    vbmeta[desc["digest_off"]:desc["digest_off"] + desc["digest_len"]] = digest

    final_bytes = bytearray(raw_data)
    final_bytes += vbmeta
    if len(final_bytes) > PARTITION_SIZE - 64:
        raise SystemExit("raw image plus vbmeta does not fit the recovery partition")
    final_bytes += b"\0" * (PARTITION_SIZE - 64 - len(final_bytes))
    struct.pack_into(">Q", footer, 12, len(raw_data))
    struct.pack_into(">Q", footer, 20, len(raw_data))
    struct.pack_into(">Q", footer, 28, len(vbmeta))
    final_bytes += footer
    final.write_bytes(final_bytes)
    final_data = bytes(final_bytes)

    if len(final_data) != PARTITION_SIZE:
        raise SystemExit(f"final size {len(final_data)} != {PARTITION_SIZE}")
    parsed_footer = avb_footer(final_data)
    if not parsed_footer:
        raise SystemExit("final image has no AVB footer")
    if parsed_footer["original_image_size"] != len(raw_data):
        raise SystemExit("AVB original image size mismatch")
    if parsed_footer["vbmeta_offset"] != len(raw_data):
        raise SystemExit("AVB vbmeta offset mismatch")
    meta = parse_vbmeta(final_data[parsed_footer["vbmeta_offset"]:
                                   parsed_footer["vbmeta_offset"] + parsed_footer["vbmeta_size"]])
    hash_desc = next((d for d in meta["descriptors"] if d[0] == "hash"), None)
    if not hash_desc:
        raise SystemExit("no AVB hash descriptor")
    _, name, alg, image_size, salt, avb_digest = hash_desc
    if image_size != len(raw_data):
        raise SystemExit("AVB hash descriptor image size mismatch")
    if hashlib.new(alg, salt + final_data[:image_size]).hexdigest() != avb_digest.hex():
        raise SystemExit("AVB hash descriptor does not verify")
    print(f"avb: {name} {image_size} bytes {alg} verified (algorithm {meta['algorithm']})")

    final_header = parse_header(final_data)
    final_offsets = section_offsets(final_header)
    ramdisk_off, ramdisk_size = final_offsets["ramdisk"]
    ramdisk_blob = final_data[ramdisk_off:ramdisk_off + ramdisk_size]
    if ramdisk_blob[:2] != b"\x1f\x8b":
        raise SystemExit("unexpected ramdisk compression (expected gzip)")
    ramdisk_cpio = gzip.decompress(ramdisk_blob)
    names = cpio_names(ramdisk_cpio)
    required = {
        "twres/ui.xml",
        "twres/portrait.xml",
        "twres/splash.xml",
        "twres/fonts/RobotoCondensed-Regular.ttf",
        "twres/fonts/DroidSansMono.ttf",
        "system/etc/twrp.fstab",
        "system/etc/fstab.poke5",
        "waveform/eink_waveform.wbf",
        "init.recovery.qcom.rc",
        "system/bin/recovery",
        "system/lib64/libminuitwrp.so",
    }
    missing = sorted(required - names)
    if missing:
        raise SystemExit(f"missing ramdisk files: {missing}")
    initrc = cpio_read(ramdisk_cpio, "init.recovery.qcom.rc").decode("utf-8", "replace")
    for marker in ("install_keyring", "poke5-keymaster", "poke5-qseecomd"):
        if marker not in initrc:
            raise SystemExit(f"init.recovery.qcom.rc missing {marker}")
    props = parse_props(cpio_read(ramdisk_cpio, "prop.default"))
    for key, value in {
        "ro.twrp.device": "Poke5",
        "ro.build.version.security_patch": "2024-02-01",
        "ro.vendor.build.security_patch": "2024-02-01",
    }.items():
        if props.get(key) != value:
            raise SystemExit(f"prop.default {key}={props.get(key)!r}, expected {value!r}")
    if "ro.build.display.id=2025-04-02_15-00_v4.0-rel_77d3ae190" not in (device / "device.mk").read_text():
        raise SystemExit("device.mk is missing the v4.0 display id override")
    print("ramdisk: theme, fstab, waveform, keymaster and v4.0 props verified")

    final_data_sha = sha256(final_data)
    (final.parent / f"{final.name}.sha256").write_text(f"{final_data_sha}  {final.name}\n", encoding="utf-8")
    (final.parent / f"{final.stem}.info.txt").write_text(
        "\n".join([
            f"stock fingerprint: {STOCK_FINGERPRINT}",
            f"cmdline: {STOCK_CMDLINE}",
            f"header: base=0x0 kernel=0x{final_header['kernel_addr']:x} "
            f"ramdisk=0x{final_header['ramdisk_addr']:x} tags=0x{final_header['tags_addr']:x} "
            f"dtb=0x{final_header['dtb_addr']:x}",
            f"os_version: 0x{final_header['os_version']:x}",
            f"kernel sha256: {expected['kernel']}",
            f"dtb sha256: {expected['dtb']}",
            f"recovery_dtbo sha256: {expected['recovery_dtbo']}",
            f"ramdisk sha256: {expected['ramdisk']}",
            f"final sha256: {final_data_sha}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(f"raw image:   {raw} ({len(raw_data)} bytes)")
    print(f"final image: {final} ({len(final_data)} bytes)")
    print(f"sha256:      {final_data_sha}")


if __name__ == "__main__":
    main()
