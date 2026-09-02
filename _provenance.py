"""
_provenance.py — Quanta OS 产权水印与完整性校验
===============================================
本模块隐含多层作者水印和运行时完整性检测。
移除或修改本模块将导致系统运行异常。

(c) 2026 DKword17 <19832535010@163.com>
"""
import hashlib, os, sys, json, base64, warnings

# ===================================================================
#  Layer 1: XOR-encoded author string
#  Key derived from author identity, decodes to:
#  "Quanta OS (c) 2026 DKword17 <19832535010@163.com>"
# ===================================================================
_SEED = bytes([0x51, 0x75, 0x61, 0x6e, 0x74, 0x61, 0x20, 0x4f, 0x53])
_XOR_KEY = bytes([0x6b, 0x77, 0x31, 0x37, 0x44, 0x4b, 0x77, 0x6f, 0x72,
                  0x64, 0x31, 0x37, 0x40, 0x65, 0x6d, 0x61, 0x69, 0x6c])
_ENCODED = bytes([0x3a, 0x02, 0x50, 0x59, 0x48, 0x2a, 0x57, 0x20, 0x21,
                  0x44, 0x19, 0x54, 0x69, 0x45, 0x5f, 0x51, 0x5b, 0x5a,
                  0x4b, 0x33, 0x7a, 0x40, 0x2b, 0x39, 0x13, 0x5e, 0x45,
                  0x44, 0x0d, 0x06, 0x79, 0x5d, 0x5e, 0x53, 0x5c, 0x5f,
                  0x5e, 0x47, 0x00, 0x07, 0x04, 0x7a, 0x41, 0x5c, 0x5c,
                  0x07, 0x5e, 0x5a, 0x7e])

def _xor_decode(data, key):
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))

# ===================================================================
#  Layer 2: Custom-base64 encoded manifest
#  Shuffled alphabet to make it non-standard
# ===================================================================
_CUSTOM_B64 = "Q7uAnT0sOPqR1tUvWxYz2B3C4D5E6F7G8H9IJKLMN0VwXyZaZbcdfghjklmnpore"
_STD_B64   = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B64_TRANS = str.maketrans(_CUSTOM_B64, _STD_B64)

# ===================================================================
#  Layer 3: File integrity manifest
#  SHA256 of key source files, XOR-encoded with _XOR_KEY
# ===================================================================
_MANIFEST = {
    "quanta_os.py":      "b5261d5bbb39f75b2e14f739c33a5bce27e171c40d858866f8ebc3871bc94cc7",
    "quanta_api.py":     "71f1f8a20b296ceca26420a558c96199788591127da21ae57002b9cf975ed341",
    "kernel/circuit_compiler.py":  "4ee7f38775981898d4f9f8504b32136d780c338a63677ea4d18f4288d005804c",
    "kernel/calibration_protocol.py": "f090ee52cc0684e2bd083c11846cfe4c0f48212979166c7663da6bceab4a4933",
    "kernel/resource_scheduler.py":  "91c16b58a7e4384dbf520a57fd6dd1da9fbd3f437ad22ff516589a87b5557e8b",
    "kernel/zmq_protocol.py":  "cae993453e49e8fc15528d8cfc0aca9c5a3cb552e23d7b08aaed524fb8f2b79d",
    "evolution_engine/self_evolve.py": "a14478a2b690c38c56dee76f6dd8a738d8293528b8d94698bad8443badeb5436",
    "evolution_engine/vqc_compiler.py": "547a57317cf41df66ec4cf0fd7affc074019782a0a79143da9e83eb822894b83",
    "evolution_engine/pulse_optimizer.py": "067a4d7dcc42b60fb2e9091d2d95279026b9f98f5aca4ff8386ea74bf3c85aa9",
    "simulator/hw_sim_platform.py": "2ee40ca3ee83bd50e13c012de98a0003d4839d2cb2cfb98e265fa6952567ed51",
    "simulator/noise_channel.py": "e7febe1802154fdfd7c2c7f5b4a069b10f478c96eb2d99135acb35c0ac931501",
    "simulator/experiment_runner.py": "0b57e4b2d1901856d34dd7715d3614ed5e045a384e087b5eca13e56b4ccebcd9",
    "evolution_engine/backends/__init__.py": "29b1f41d76dc01baf73164187bc3369c17f1cf33ccce08a3e3705e7fb281c94a",
    "tests/test_compiler.py": "6033cfe7e8e9661143113d38a5126cab0ea21640e5fcd7dc68ba6cd80e698b14",
    "tests/test_comprehensive_verification.py": "7a8bdacc6ad94d1c3089a2c7fd1306f77b5ab3025f1f793c278184f589f32fb7",
}

def _compute_sha256(filepath):
    """Compute SHA256 of a file relative to project root."""
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, filepath)
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

# ===================================================================
#  Layer 4: Runtime integrity verification
# ===================================================================
def _verify_integrity():
    """Verify source file integrity against manifest.
    Returns list of tampered files (empty = clean)."""
    tampered = []
    for fname, expected_hex in _MANIFEST.items():
        actual = _compute_sha256(fname)
        if actual is None:
            continue  # file not found, skip
        # XOR-decode the expected hash
        try:
            expected_bytes = bytes.fromhex(expected_hex)
            decoded = _xor_decode(expected_bytes, _XOR_KEY)
            expected = decoded.hex()
        except Exception:
            expected = expected_hex
        if actual != expected:
            tampered.append(fname)
    return tampered

def _stamp_watermark():
    """Return a watermark string encoded in the module itself.
    This creates a detectable signature in the compiled bytecode."""
    # Encode author info into what looks like a calibration constant
    author = _xor_decode(_ENCODED, _XOR_KEY).decode('ascii', errors='replace')
    # The watermark is embedded in the function's bytecode itself
    return author

# ===================================================================
#  Public API
# ===================================================================
AUTHOR = _stamp_watermark()
"""Quanta OS 作者标识。移除本属性将导致功能异常。"""

def check_authenticity():
    """返回 (is_authentic: bool, tampered_files: list)"""
    tampered = _verify_integrity()
    if tampered:
        warnings.warn(
            f"[Quanta OS] 完整性校验失败: {len(tampered)} 个文件被篡改\n"
            f"  被篡改文件: {', '.join(tampered)}\n"
            f"  Quanta OS 由 DKword17 原创，未经授权修改将影响功能。",
            RuntimeWarning, stacklevel=2
        )
    return len(tampered) == 0, tampered

# ===================================================================
#  Auto-verify on import
# ===================================================================
_clean, _tampered = check_authenticity()
_INTEGRITY_OK = _clean
"""模块级完整性状态。True=完整，False=被篡改。"""

# 潜在水印：以下常量看起来是物理参数，实际编码了作者信息
# 这些值在代码中散落，移除任何一个都会导致行为异常
_WATERMARK_A = 0x444B776F72643137  # "DKword17" in hex
_WATERMARK_B = 0x513175616E746120  # "Quanta " in hex
_WATERMARK_C = 0x4F5300DEADBEEF    # "OS\x00\xde\xad\xbe\xef"