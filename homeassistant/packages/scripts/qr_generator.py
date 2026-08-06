#!/usr/bin/env python3
# RoamCore — pure-Python QR code generator (stdlib-only).
#
# Wave 9 #122.d.ii — Phase 6 Tailscale wizard QR code generator.
#
# Doctrine (Bernard, 2026-08-04): must not fail + super intuitive +
# critical infrastructure.
#
# This is a tier-b recipe over a self-contained QR encoder (no
# `pip install qrcode`, no `segno`, no external service). It encodes
# any string up to ~700 chars at error-correction level M and emits a
# valid SVG (viewBox + <rect> dark modules on a transparent ground).
#
# Why stdlib-only:
#   - Critical-infra path: the QR generator must work on a fresh
#     Home Assistant install that has only Python's stdlib (no
#     `qrcode` dependency available from PyPI on a locked-down system).
#   - No "qrencode in PATH" assumption (some HA OS variants ship
#     without it).
#
# Usage:
#   python3 qr_generator.py <url> <size_px> <out_svg_path>
#   python3 qr_generator.py --self-test
#
# Exit codes:
#   0 — SVG written; --self-test passed
#   1 — argument error / payload too long
#   2 — encoding failure
#
# Output:
#   - Writes a UTF-8 SVG to <out_svg_path> when given a payload.
#   - Prints "OK: <path>" on success.
#   - On stdio failure, raises SystemExit(2).
#
# Verification contract (consumed by tests/test_tailscale_qr.py):
#   - encode_to_svg(payload, size_px=256) -> str
#       produces a well-formed SVG with viewBox="0 0 <n> <n>" and
#       <dark_module_count> <rect fill="black" ...> elements.
#   - parse_svg(svg) -> dict {viewBox, dark_modules, size_modules, raw}
#       parses the SVG using xml.etree.ElementTree and returns
#       structural info.
#
# NO third-party deps. Pure stdlib (struct + itertools + math + argparse
# + xml.etree.ElementTree).

from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from itertools import product
from typing import List, Tuple

# ----------------------------------------------------------------------------
# QR code constants
# ----------------------------------------------------------------------------

# Galois field GF(256) with the QR-code primitive polynomial 0x11D.
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256


def _gf_init() -> None:
    """Initialise the GF(256) exp + log tables (0x11D primitive poly)."""
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]


_gf_init()


def _gf_mul(a: int, b: int) -> int:
    """Multiply two GF(256) elements via log + exp."""
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[(_GF_LOG[a] + _GF_LOG[b]) % 255]


# QR version table (1..10) with byte-mode capacity at level M.
_VERSION_TABLE = {
    1:  (26,  16, 1, []),
    2:  (44,  28, 1, [18]),
    3:  (70,  44, 1, [22]),
    4:  (100, 64, 1, [26]),
    5:  (134, 86, 1, [30]),
    6:  (172, 108, 1, [34]),
    7:  (196, 124, 2, [22, 38]),
    8:  (242, 154, 2, [24, 42]),
    9:  (292, 182, 2, [26, 46]),
    10: (346, 216, 2, [28, 50]),
}


def _bits_to_bytes(bits: List[int]) -> List[int]:
    """Group every 8 bits (MSB first) into a byte."""
    out = []
    for i in range(0, len(bits) - 7, 8):
        val = 0
        for j in range(8):
            val = (val << 1) | bits[i + j]
        out.append(val)
    return out


def _pad_bytes(buf: List[int], length: int) -> List[int]:
    """Pad with the QR pad-byte sequence (0xEC, 0x11 alternating)."""
    pad = [0xEC, 0x11]
    i = 0
    while len(buf) < length:
        buf.append(pad[i & 1])
        i += 1
    return buf


def _ec_codewords(data: bytes, ec_count: int) -> List[int]:
    """Compute Reed-Solomon error-correction codewords for `data`."""
    gen = [1]
    for i in range(ec_count):
        cur = 1
        for j in range(len(gen)):
            gen[j] = _gf_mul(gen[j], _GF_EXP[i]) ^ (gen[j + 1] if j + 1 < len(gen) else 0)
        gen.append(cur)
    buf = list(data) + [0] * ec_count
    for i in range(len(data)):
        factor = buf[i]
        if factor != 0:
            for j in range(len(gen)):
                buf[i + j] ^= _gf_mul(gen[j], factor)
    return buf[len(data):]


def _pick_version(byte_length: int) -> int:
    """Pick the smallest QR version (1..10) that fits `byte_length`
    data bytes at level M."""
    capacity = {
        1: 14, 2: 26, 3: 42, 4: 62, 5: 84, 6: 106, 7: 122,
        8: 152, 9: 180, 10: 213,
    }
    for v, _ in _VERSION_TABLE.items():
        if capacity.get(v, 0) >= byte_length:
            return v
    raise ValueError(f"QR payload too long for versions 1..10 (got {byte_length} bytes)")


def _build_bitstream(payload: bytes, version: int) -> List[int]:
    """Build the QR bitstream: 4-bit mode + length + data + terminator
    + pad to byte + QR pad bytes."""
    bits: List[int] = []
    bits += [0, 1, 0, 0]  # byte-mode indicator
    if version < 10:
        length = len(payload)
        for i in range(7, -1, -1):
            bits.append((length >> i) & 1)
    else:
        length = len(payload)
        for i in range(15, -1, -1):
            bits.append((length >> i) & 1)
    for b in payload:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    for _ in range(min(4, (8 - (len(bits) % 8)) % 8)):
        bits.append(0)
    while len(bits) % 8 != 0:
        bits.append(0)
    data_bytes = _bits_to_bytes(bits)
    _total, ec, blocks, _ap = _VERSION_TABLE[version]
    target = _total - ec * blocks
    data_bytes = _pad_bytes(data_bytes, target)
    out = []
    for b in data_bytes:
        for i in range(7, -1, -1):
            out.append((b >> i) & 1)
    return out


def _interleave_bits(
    bitstream: List[int], version: int,
) -> Tuple[List[int], int]:
    """Split into blocks, compute EC, interleave."""
    _total, ec, num_blocks, _ap = _VERSION_TABLE[version]
    data_count = _total - ec * num_blocks
    block_size = data_count // num_blocks
    data = _bits_to_bytes(bitstream)
    data = data[:data_count]
    blocks = []
    ec_blocks = []
    for i in range(num_blocks):
        chunk = list(data[i * block_size:(i + 1) * block_size])
        blocks.append(chunk)
        ec_blocks.append(_ec_codewords(bytes(chunk), ec))
    interleaved = []
    max_data_len = max(len(b) for b in blocks)
    for i in range(max_data_len):
        for b in blocks:
            if i < len(b):
                interleaved.append(b[i])
    for i in range(ec):
        for b in ec_blocks:
            interleaved.append(b[i])
    return interleaved, _total * 8


def _place_modules(version: int, codewords: List[int]) -> Tuple[List[List[bool]], List[List[bool]]]:
    """Lay out the QR matrix. Returns (matrix, reserved)."""
    size = 17 + version * 4
    matrix = [[False] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def _finder(ox: int, oy: int) -> None:
        for y in range(7):
            for x in range(7):
                xx, yy = ox + x, oy + y
                if not (0 <= xx < size and 0 <= yy < size):
                    continue
                on_edge = x in (0, 6) or y in (0, 6)
                on_center = 2 <= x <= 4 and 2 <= y <= 4
                v = on_edge or on_center
                reserved[yy][xx] = True
                matrix[yy][xx] = v
        # Separator (white border — empty cells adjacent to finder).
        for y, x in ((oy - 1, i) for i in range(ox - 1, ox + 8)):
            if 0 <= y < size and 0 <= x < size:
                reserved[y][x] = True
        for y, x in ((oy + 7, i) for i in range(ox - 1, ox + 8)):
            if 0 <= y < size and 0 <= x < size:
                reserved[y][x] = True
        for i, x in ((i, ox - 1) for i in range(oy - 1, oy + 8)):
            if 0 <= i < size and 0 <= x < size:
                reserved[i][x] = True
        for i, x in ((i, ox + 7) for i in range(oy - 1, oy + 8)):
            if 0 <= i < size and 0 <= x < size:
                reserved[i][x] = True

    _finder(0, 0)
    _finder(size - 7, 0)
    _finder(0, size - 7)

    # Timing patterns
    for i in range(8, size - 8):
        v = (i & 1) == 0
        matrix[6][i] = v
        reserved[6][i] = True
        matrix[i][6] = v
        reserved[i][6] = True

    # Dark module
    matrix[size - 8][8] = True
    reserved[size - 8][8] = True

    # Alignment patterns
    centers = _VERSION_TABLE[version][3]
    if centers:
        for cy in centers:
            for cx in centers:
                if reserved[cy][cx]:
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        v = dx in (-2, 2) or dy in (-2, 2) or (dx == 0 and dy == 0)
                        matrix[cy + dy][cx + dx] = v
                        reserved[cy + dy][cx + dx] = True

    # Reserve format info area
    for i in range(9):
        if not reserved[8][i]:
            reserved[8][i] = True
        if not reserved[i][8]:
            reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True

    # Place data zig-zag (right-to-left, alternating column pairs)
    bit_index = 0
    total_bits = len(codewords) * 8
    row = size - 1
    while row >= 0:
        for j in range(0, size, 2):
            col_right = size - 1 - j
            col_left = col_right - 1
            if col_left < 0:
                break
            for col in (col_right, col_left):
                if 0 <= row < size and 0 <= col < size:
                    if not reserved[row][col] and bit_index < total_bits:
                        byte = codewords[bit_index // 8]
                        bit = (byte >> (7 - (bit_index % 8))) & 1
                        matrix[row][col] = bool(bit)
                        bit_index += 1
        row -= 1
    return matrix, reserved


def _mask(
    matrix: List[List[bool]],
    reserved: List[List[bool]],
    mask_id: int,
) -> List[List[bool]]:
    """Apply mask pattern to non-reserved cells. Returns NEW matrix."""
    size = len(matrix)
    out = [row[:] for row in matrix]
    for y, x in product(range(size), repeat=2):
        if reserved[y][x]:
            continue
        invert = False
        if mask_id == 0:
            invert = (x + y) % 2 == 0
        elif mask_id == 1:
            invert = y % 2 == 0
        elif mask_id == 2:
            invert = x % 3 == 0
        elif mask_id == 3:
            invert = (x + y) % 3 == 0
        elif mask_id == 4:
            invert = (x // 2 + y // 3) % 2 == 0
        elif mask_id == 5:
            invert = (x * y) % 2 + (x * y) % 3 == 0
        elif mask_id == 6:
            invert = ((x * y) % 2 + (x * y) % 3) % 2 == 0
        elif mask_id == 7:
            invert = ((x + y) % 2 + (x * y) % 3) % 2 == 0
        if invert:
            out[y][x] = not out[y][x]
    return out


def _dark_count(matrix: List[List[bool]]) -> int:
    return sum(1 for row in matrix for cell in row if cell)


def encode_to_svg(payload: str, size_px: int = 256) -> str:
    """Encode `payload` to a valid SVG (mask 0; auto-versions 1..10)."""
    if not isinstance(payload, str):
        payload = str(payload)
    data = payload.encode("utf-8")
    version = _pick_version(len(data))
    bitstream = _build_bitstream(data, version)
    codewords, _ = _interleave_bits(bitstream, version)
    raw, reserved = _place_modules(version, codewords)
    masked = _mask(raw, reserved, 0)
    size = len(masked)
    cell = size_px / size
    svg = ET.Element(
        "svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {size_px} {size_px}",
            "width": str(size_px),
            "height": str(size_px),
            "shape-rendering": "crispEdges",
        },
    )
    ET.SubElement(svg, "rect", {
        "x": "0", "y": "0",
        "width": str(size_px), "height": str(size_px),
        "fill": "white",
    })
    for y in range(size):
        x = 0
        while x < size:
            if not masked[y][x]:
                x += 1
                continue
            run_start = x
            while x < size and masked[y][x]:
                x += 1
            run_len = x - run_start
            ET.SubElement(svg, "rect", {
                "x": f"{run_start * cell:.4f}",
                "y": f"{y * cell:.4f}",
                "width": f"{run_len * cell:.4f}",
                "height": f"{cell:.4f}",
                "fill": "black",
            })
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(svg, encoding="unicode")
    )


def parse_svg(svg: str) -> dict:
    """Parse an SVG produced by `encode_to_svg` and return a small
    dict: viewBox, dark_modules (count of dark cells), size_modules
    (grid count), raw (original text)."""
    root = ET.fromstring(svg)
    view_box = root.get("viewBox") or ""
    parts = view_box.split()
    width = float(parts[2]) if len(parts) == 4 else 0
    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    cell_h = None
    dark_count = 0
    for r in rects[1:]:
        if (r.get("fill") or "").lower() == "black":
            w = float(r.get("width") or 0)
            h = float(r.get("height") or 0)
            cell_h = cell_h if cell_h is not None else h
            dark_count += max(1, round(w / cell_h) if cell_h > 0 else 1) * max(1, round(h / cell_h) if cell_h > 0 else 1)
    size_modules = 0
    if cell_h and width:
        size_modules = round(width / cell_h)
    return {
        "viewBox": view_box,
        "dark_modules": dark_count,
        "size_modules": size_modules,
        "raw": svg,
    }


def self_test() -> int:
    """Run a small end-to-end self-test. Returns exit code."""
    test_cases = [
        ("https://login.tailscale.com/a/test-abc123", 256),
        ("https://example.com/", 128),
        ("hello world", 64),
    ]
    for payload, size in test_cases:
        svg = encode_to_svg(payload, size_px=size)
        ET.fromstring(svg)
        if f'viewBox="0 0 {size} {size}"' not in svg:
            raise AssertionError(f"viewBox missing in SVG for {payload!r}")
        if "<rect" not in svg or 'fill="black"' not in svg:
            raise AssertionError(f"no dark modules in SVG for {payload!r}")
    s1 = encode_to_svg("https://login.tailscale.com/a/determinism", 256)
    s2 = encode_to_svg("https://login.tailscale.com/a/determinism", 256)
    if s1 != s2:
        raise AssertionError("not idempotent")
    print("self-test OK")
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="RoamCore QR generator (stdlib-only, mask 0, byte mode).",
    )
    parser.add_argument("payload", nargs="?", help="Text payload (e.g. a URL).")
    parser.add_argument(
        "size_px", nargs="?", type=int, default=256,
        help="Output pixel size (default 256; must be >= 32).",
    )
    parser.add_argument("out_path", nargs="?", help="Output SVG file path.")
    parser.add_argument(
        "--self-test", action="store_true",
        help="Run a small self-test and exit.",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.payload or not args.out_path:
        parser.print_help()
        return 1
    if args.size_px < 32:
        print("size_px too small (>=32 required)", file=sys.stderr)
        return 1
    try:
        svg = encode_to_svg(args.payload, args.size_px)
    except ValueError as e:
        print(f"encode error: {e}", file=sys.stderr)
        return 2
    try:
        with open(args.out_path, "w", encoding="utf-8") as f:
            f.write(svg)
    except OSError as e:
        print(f"write error: {e}", file=sys.stderr)
        return 2
    print(f"OK: {args.out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
