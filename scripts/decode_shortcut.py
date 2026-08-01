#!/usr/bin/env python3
"""Decode a signed iOS .shortcut (AEA) into its WFWorkflow plist dict.

Brute-forces the compression: tries each algorithm (zlib/LZFSE/Brotli/LZ4/LZMA)
at every file offset, 1-stage and 2-stage (outer decode -> scan inner for the
LZFSE-compressed WFWorkflow plist). No pip needed (ctypes -> libcompression).
"""
import ctypes
import io
import plistlib

_LIB = ctypes.CDLL("/usr/lib/libcompression.dylib")
ALGS = {
    "ZLIB": 0x205,
    "LZFSE": 0x801,
    "BROTLI": 0xB02,
    "LZ4": 0x100,
    "LZMA": 0x306,
}

# 复用同一块缓冲，避免每次调用都分配 8MB（之前 11 万次分配会 OOM 被 SIGKILL）
_BUF = ctypes.create_string_buffer(16_000_000)


def _decode(buf, alg):
    n = _LIB.compression_decode_buffer(_BUF, len(_BUF), buf, len(buf), None, alg)
    return _BUF.raw[:n] if n > 0 else b""


def _try_find_wf(buf):
    """Scan buf for an LZFSE(etc)-compressed WFWorkflow plist."""
    # 完整扫描（缓冲已复用，不会 OOM）；但 2-stage 的 outer 可能很大，单独限制
    max_start = len(buf)
    for alg in ALGS.values():
        for start in range(0, max(1, max_start - 200)):
            out = _decode(buf[start:], alg)
            if len(out) > 400 and b"WFWorkflowActions" in out:
                i = out.find(b"bplist00")
                try:
                    pl = plistlib.load(io.BytesIO(out[i:]))
                except Exception:
                    continue
                if "WFWorkflowActions" in pl:
                    return pl
                # root may be wrapped; search nested bplist00
                s = 0
                while True:
                    j = out.find(b"bplist00", s)
                    if j < 0:
                        break
                    try:
                        p2 = plistlib.load(io.BytesIO(out[j:]))
                        if "WFWorkflowActions" in p2:
                            return p2
                    except Exception:
                        pass
                    s = j + 1
    return None


def decode_shortcut(path):
    data = open(path, "rb").read()
    if data[:4] != b"AEA1":
        pl = plistlib.load(io.BytesIO(data))
        return pl.get("WFWorkflow", pl)
    # 1-stage: scan whole file
    wf = _try_find_wf(data)
    if wf:
        return wf
    # 2-stage: outer decode then scan
    for alg in ALGS.values():
        outer = _decode(data, alg)
        if outer:
            wf = _try_find_wf(outer)
            if wf:
                return wf
    raise RuntimeError("could not locate WFWorkflow plist")


if __name__ == "__main__":
    import sys, json
    wf = decode_shortcut(sys.argv[1])
    print("NAME:", wf.get("WFWorkflowName"))
    print("num actions:", len(wf.get("WFWorkflowActions", [])))
    for a in wf.get("WFWorkflowActions", []):
        print(" -", a.get("WFWorkflowActionIdentifier"))
        print("    ", json.dumps(a.get("WFWorkflowActionParameters", {}), ensure_ascii=False)[:500])
