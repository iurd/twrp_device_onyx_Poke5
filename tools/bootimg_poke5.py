#!/usr/bin/env python3
"""Parse/extract Android boot image v2 used by the Poke5 stock recovery."""
import argparse
import gzip
import hashlib
import os
import stat
import struct
import sys


def align(value, page):
    return (value + page - 1) // page * page


def parse_header(data):
    if data[:8] != b"ANDROID!":
        raise SystemExit("not an Android boot image")
    fields = struct.unpack_from("<10I", data, 8)
    (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size,
     second_addr, tags_addr, page_size, header_version, os_version) = fields
    name = data[48:64].split(b"\0")[0].decode("utf-8", "replace")
    cmdline = data[64:576].split(b"\0")[0].decode("utf-8", "replace")
    header = {
        "kernel_size": kernel_size,
        "kernel_addr": kernel_addr,
        "ramdisk_size": ramdisk_size,
        "ramdisk_addr": ramdisk_addr,
        "second_size": second_size,
        "second_addr": second_addr,
        "tags_addr": tags_addr,
        "page_size": page_size,
        "header_version": header_version,
        "os_version": os_version,
        "name": name,
        "cmdline": cmdline,
    }
    if header_version >= 1:
        (recovery_dtbo_size, recovery_dtbo_offset, header_size, dtb_size,
         dtb_addr) = struct.unpack_from("<IQIIQ", data, 1632)
        header.update({
            "recovery_dtbo_size": recovery_dtbo_size,
            "recovery_dtbo_offset": recovery_dtbo_offset,
            "header_size": header_size,
            "dtb_size": dtb_size,
            "dtb_addr": dtb_addr,
        })
    return header


def section_offsets(header):
    page = header["page_size"]
    kernel_off = page
    ramdisk_off = kernel_off + align(header["kernel_size"], page)
    second_off = ramdisk_off + align(header["ramdisk_size"], page)
    dtbo_off = second_off + align(header["second_size"], page)
    dtb_off = dtbo_off + align(header.get("recovery_dtbo_size", 0), page)
    end = dtb_off + align(header.get("dtb_size", 0), page)
    return {
        "kernel": (kernel_off, header["kernel_size"]),
        "ramdisk": (ramdisk_off, header["ramdisk_size"]),
        "second": (second_off, header["second_size"]),
        "recovery_dtbo": (dtbo_off, header.get("recovery_dtbo_size", 0)),
        "dtb": (dtb_off, header.get("dtb_size", 0)),
        "end": end,
    }


def avb_footer(data):
    if len(data) < 64 or data[-64:-60] != b"AVBf":
        return None
    magic, major, minor, orig, voff, vsize = struct.unpack(">4sIIQQQ", data[-64:-28])
    return {
        "magic": magic.decode(),
        "version": (major, minor),
        "original_image_size": orig,
        "vbmeta_offset": voff,
        "vbmeta_size": vsize,
        "offset": len(data) - 64,
    }


def cpio_entries(cpio):
    entries = []
    pos = 0
    while True:
        header = cpio[pos:pos + 110]
        if header[:6] not in (b"070701", b"070702"):
            raise SystemExit(f"bad cpio magic at {pos}")
        namesize = int(header[94:102], 16)
        filesize = int(header[54:62], 16)
        mode = int(header[14:22], 16)
        name = cpio[pos + 110:pos + 110 + namesize - 1].decode("utf-8", "replace")
        data_off = pos + 110 + namesize
        data_off = (data_off + 3) // 4 * 4
        entries.append({
            "name": name,
            "size": filesize,
            "mode": mode,
            "offset": data_off,
        })
        pos = (data_off + filesize + 3) // 4 * 4
        if name == "TRAILER!!!":
            break
    return entries


def safe_join(root, name):
    dest = os.path.abspath(os.path.join(root, name))
    if not dest.startswith(os.path.abspath(root) + os.sep):
        raise SystemExit(f"unsafe cpio path: {name}")
    return dest


def extract_cpio(cpio, outdir):
    os.makedirs(outdir, exist_ok=True)
    manifest = []
    for entry in cpio_entries(cpio):
        name = entry["name"]
        if name == "TRAILER!!!":
            continue
        dest = safe_join(outdir, name.rstrip("/"))
        mode = entry["mode"]
        is_dir = stat.S_ISDIR(mode) or (mode == 0 and name.endswith("/"))
        is_link = stat.S_ISLNK(mode)
        if is_dir:
            os.makedirs(dest, exist_ok=True)
        elif is_link:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            target = cpio[entry["offset"]:entry["offset"] + entry["size"]].decode("utf-8", "replace")
            if os.path.lexists(dest):
                os.unlink(dest)
            os.symlink(target, dest)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                fh.write(cpio[entry["offset"]:entry["offset"] + entry["size"]])
            os.chmod(dest, stat.S_IMODE(mode) | 0o200)
        manifest.append(f"{entry['size']:10d} {mode:08o} {name}")
    with open(os.path.join(outdir, "..", "ramdisk-manifest.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(manifest) + "\n")


def decompress_if_gzip(src, dst):
    with open(src, "rb") as fh:
        blob = fh.read()
    if blob[:2] != b"\x1f\x8b":
        return False
    with gzip.open(src, "rb") as fh:
        out = fh.read()
    with open(dst, "wb") as fh:
        fh.write(out)
    return True


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(path):
    data = open(path, "rb").read()
    header = parse_header(data)
    offsets = section_offsets(header)
    footer = avb_footer(data)
    print(f"file: {path}")
    print(f"size: {len(data)} bytes")
    print(f"sha256: {hashlib.sha256(data).hexdigest()}")
    for key, value in header.items():
        if isinstance(value, int):
            print(f"{key}: {value} (0x{value:x})")
        else:
            print(f"{key}: {value!r}")
    print(f"image payload end: {offsets['end']} (0x{offsets['end']:x})")
    for key in ("kernel", "ramdisk", "second", "recovery_dtbo", "dtb"):
        off, size = offsets[key]
        print(f"{key}: offset {off} (0x{off:x}), size {size}, sha256 {hashlib.sha256(data[off:off + size]).hexdigest()}")
    if footer:
        print("avb footer:", footer)
        print("avb vbmeta magic:", data[footer["vbmeta_offset"]:footer["vbmeta_offset"] + 4])
    else:
        print("avb footer: none")
    return header, offsets, footer


def extract(path, outdir):
    data = open(path, "rb").read()
    header = parse_header(data)
    offsets = section_offsets(header)
    os.makedirs(outdir, exist_ok=True)
    for key in ("kernel", "ramdisk", "second", "recovery_dtbo", "dtb"):
        off, size = offsets[key]
        if not size:
            continue
        dest = os.path.join(outdir, key)
        with open(dest, "wb") as fh:
            fh.write(data[off:off + size])
        print(f"wrote {dest} ({size} bytes)")
    kernel = os.path.join(outdir, "kernel")
    image = os.path.join(outdir, "Image")
    if decompress_if_gzip(kernel, image):
        print(f"decompressed {kernel} -> {image} ({os.path.getsize(image)} bytes)")
    ramdisk = os.path.join(outdir, "ramdisk")
    cpio = os.path.join(outdir, "ramdisk.cpio")
    if decompress_if_gzip(ramdisk, cpio):
        print(f"decompressed {ramdisk} -> {cpio} ({os.path.getsize(cpio)} bytes)")
    extract_cpio(open(cpio, "rb").read(), os.path.join(outdir, "root"))
    print(f"extracted ramdisk to {os.path.join(outdir, 'root')}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("image")
    p_extract = sub.add_parser("extract")
    p_extract.add_argument("image")
    p_extract.add_argument("outdir")
    args = parser.parse_args()
    if args.cmd == "inspect":
        inspect(args.image)
    elif args.cmd == "extract":
        inspect(args.image)
        extract(args.image, args.outdir)


if __name__ == "__main__":
    main()
