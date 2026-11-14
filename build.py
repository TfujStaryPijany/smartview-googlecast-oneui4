#!/usr/bin/env python3
"""Build a Magisk module that brings Google Cast (Chromecast) back to Samsung
Smart View on One UI 4.1 / Android 12.

Usage: python3 build.py <Smart View 8.2.20.14 APK>

The APK is NOT part of this repository. Download it yourself (see README),
this script verifies its SHA-256, patches it and packs the module zip.
"""
import hashlib
import os
import struct
import sys
import zipfile
import zlib

APK_SHA256 = "0e2d8eeae64f0755558f4cb571498fc7465675ae84daada13c264af638461c19"
# SHA-256 of the patched APK that was tested on a Galaxy S10 (G973FXXSGHWC1)
PATCHED_SHA256 = "75842ce6be7fddff25490640c7b1c024edf693263c9826fb684214c394b1e065"

# (offset inside classes.dex, original bytes, replacement bytes, what it does)
PATCHES = [
    (0x306CC4, "1a012a36", "12100f00",
     "Nearby Service permission check: always return true "
     "(it asks for NEARBY_WIFI_DEVICES, which does not exist on Android 12)"),
    (0x30706C, "6e5228804035", "000000000000",
     "skip SemWifiP2pManager.unsetInUsePackage() (Android 13 only API)"),
    (0x30707C, "6e5227804035", "000000000000",
     "skip SemWifiP2pManager.setInUsePackage() (Android 13 only API)"),
    (0x2BC798, "6e207f0701000a01", "1201000000000000",
     "SemWifiDisplay.isSupported(\"high_resolution_mode\") -> false (Android 13 only API)"),
]

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.join(HERE, "module")
APK_PATH_IN_MODULE = "system/app/SmartMirroring/SmartMirroring.apk"
OUT_ZIP = "smartview-googlecast-module.zip"


def patch_apk(apk: bytes) -> bytes:
    """Patch classes.dex in place. Sizes and offsets stay the same, the APK
    Signing Block is not touched, so the Samsung platform certificate is still
    readable when the system scans /system/app."""
    b = bytearray(apk)
    eocd = b.rfind(b"PK\x05\x06")
    cd_size, cd_off = struct.unpack_from("<II", b, eocd + 12)
    p, entry = cd_off, None
    while p < cd_off + cd_size:
        if b[p:p + 4] != b"PK\x01\x02":
            raise SystemExit("broken zip central directory")
        flags, method = struct.unpack_from("<HH", b, p + 8)
        crc, csize, usize, nlen, elen, clen = struct.unpack_from("<IIIHHH", b, p + 16)
        lho = struct.unpack_from("<I", b, p + 42)[0]
        if bytes(b[p + 46:p + 46 + nlen]) == b"classes.dex":
            entry = (p, flags, method, crc, csize, usize, lho)
        p += 46 + nlen + elen + clen
    if entry is None:
        raise SystemExit("classes.dex not found")
    p, flags, method, crc, csize, usize, lho = entry
    if method != 0 or csize != usize or flags & 8:
        raise SystemExit("classes.dex is not stored uncompressed, cannot patch in place")
    lnlen, lelen = struct.unpack_from("<HH", b, lho + 26)
    data = lho + 30 + lnlen + lelen
    dex = b[data:data + usize]
    if dex[:4] != b"dex\n" or zlib.crc32(dex) != crc:
        raise SystemExit("classes.dex does not match its zip CRC")

    for off, old, new, what in PATCHES:
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        if dex[off:off + len(old)] != old:
            raise SystemExit("unexpected bytes at %#x, wrong APK?" % off)
        dex[off:off + len(new)] = new
        print("  patched %#x: %s" % (off, what))

    # dex header: SHA-1 signature, then Adler-32 checksum
    dex[12:32] = hashlib.sha1(dex[32:]).digest()
    struct.pack_into("<I", dex, 8, zlib.adler32(dex[12:]) & 0xFFFFFFFF)
    new_crc = zlib.crc32(dex) & 0xFFFFFFFF
    b[data:data + usize] = dex
    struct.pack_into("<I", b, lho + 14, new_crc)  # local file header
    struct.pack_into("<I", b, p + 16, new_crc)    # central directory
    return bytes(b)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    apk = open(sys.argv[1], "rb").read()
    digest = hashlib.sha256(apk).hexdigest()
    if digest != APK_SHA256:
        raise SystemExit("wrong APK.\n  expected sha256 %s\n  got             %s" % (APK_SHA256, digest))
    print("input APK ok: sha256 %s" % digest)

    patched = patch_apk(apk)
    patched_digest = hashlib.sha256(patched).hexdigest()
    if patched_digest != PATCHED_SHA256:
        raise SystemExit("patched APK has unexpected sha256 %s" % patched_digest)
    print("patched APK ok: sha256 %s" % patched_digest)

    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(MODULE_DIR):
            for name in sorted(files):
                full = os.path.join(root, name)
                z.write(full, os.path.relpath(full, MODULE_DIR).replace(os.sep, "/"))
        # .replace makes Magisk replace the whole stock directory (drops the stale .prof)
        z.writestr("system/app/SmartMirroring/.replace", b"")
        z.writestr(zipfile.ZipInfo(APK_PATH_IN_MODULE), patched, zipfile.ZIP_STORED)
    print("wrote %s" % OUT_ZIP)


if __name__ == "__main__":
    main()
