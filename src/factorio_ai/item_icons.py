from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
import struct
import zlib

from .config import AppConfig


ITEM_ICON_FALLBACK = "unknown"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COLOR_CHANNELS = {
    0: 1,
    2: 3,
    3: 1,
    4: 2,
    6: 4,
}


def resolve_item_icon(cfg: AppConfig, item_name: str) -> Path | None:
    factorio_root = cfg.factorio_exe.parent.parent.parent
    return _resolve_icon(str(factorio_root), _safe_item_name(item_name))


def read_item_icon_png(cfg: AppConfig, item_name: str) -> bytes | None:
    icon_path = resolve_item_icon(cfg, item_name)
    if icon_path is None:
        return None
    return _read_cropped_icon(str(icon_path))


@lru_cache(maxsize=512)
def _resolve_icon(factorio_root: str, item_name: str) -> Path | None:
    if not item_name:
        return None

    root = Path(factorio_root)
    data_dir = root / "data"
    candidates = [
        data_dir / "base" / "graphics" / "icons" / f"{item_name}.png",
        data_dir / "base" / "graphics" / "icons" / "fluid" / f"{item_name}.png",
        data_dir / "space-age" / "graphics" / "icons" / f"{item_name}.png",
        data_dir / "space-age" / "graphics" / "icons" / "fluid" / f"{item_name}.png",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    if data_dir.exists():
        matches = list(data_dir.rglob(f"{item_name}.png"))
        for match in matches:
            if "\\graphics\\icons\\" in str(match).lower() or "/graphics/icons/" in str(match).lower():
                return match
        if matches:
            return matches[0]

    if item_name != ITEM_ICON_FALLBACK:
        return _resolve_icon(factorio_root, ITEM_ICON_FALLBACK)
    return None


def _safe_item_name(value: str) -> str:
    return "".join(character for character in value.strip().lower() if character.isalnum() or character in {"-", "_"})


@lru_cache(maxsize=512)
def _read_cropped_icon(icon_path: str) -> bytes:
    data = Path(icon_path).read_bytes()
    return crop_largest_mipmap_png(data) or data


def crop_largest_mipmap_png(data: bytes) -> bytes | None:
    """Crop Factorio mipmap-strip icons to the largest leftmost square image."""
    if not data.startswith(PNG_SIGNATURE):
        return None

    try:
        chunks = _read_png_chunks(data)
    except ValueError:
        return None
    ihdr = next((chunk_data for chunk_type, chunk_data in chunks if chunk_type == b"IHDR"), None)
    if ihdr is None or len(ihdr) != 13:
        return None

    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", ihdr)
    if width <= height or height <= 0:
        return None
    if compression != 0 or filter_method != 0 or interlace != 0:
        return None

    channels = PNG_COLOR_CHANNELS.get(color_type)
    if channels is None:
        return None
    bits_per_pixel = channels * bit_depth
    if bits_per_pixel % 8 != 0:
        return None

    row_bytes = math.ceil(width * bits_per_pixel / 8)
    crop_width = height
    crop_row_bytes = math.ceil(crop_width * bits_per_pixel / 8)
    filter_bpp = max(1, bits_per_pixel // 8)
    idat = b"".join(chunk_data for chunk_type, chunk_data in chunks if chunk_type == b"IDAT")
    if not idat:
        return None

    try:
        raw = zlib.decompress(idat)
        rows = _unfilter_png_rows(raw, height, row_bytes, filter_bpp)
    except (ValueError, zlib.error):
        return None

    cropped_raw = b"".join(b"\x00" + row[:crop_row_bytes] for row in rows)
    new_ihdr = struct.pack(">IIBBBBB", crop_width, height, bit_depth, color_type, compression, filter_method, interlace)

    output = bytearray(PNG_SIGNATURE)
    output.extend(_png_chunk(b"IHDR", new_ihdr))
    for chunk_type, chunk_data in chunks:
        if chunk_type in {b"IHDR", b"IDAT", b"IEND"}:
            continue
        output.extend(_png_chunk(chunk_type, chunk_data))
    output.extend(_png_chunk(b"IDAT", zlib.compress(cropped_raw, level=9)))
    output.extend(_png_chunk(b"IEND", b""))
    return bytes(output)


def _read_png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    chunks: list[tuple[bytes, bytes]] = []
    offset = len(PNG_SIGNATURE)
    while offset + 8 <= len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(data):
            raise ValueError("truncated PNG chunk")
        chunks.append((chunk_type, data[chunk_start:chunk_end]))
        offset = chunk_end + 4
        if chunk_type == b"IEND":
            break
    return chunks


def _unfilter_png_rows(raw: bytes, height: int, row_bytes: int, bpp: int) -> list[bytes]:
    expected = height * (row_bytes + 1)
    if len(raw) < expected:
        raise ValueError("truncated PNG image data")

    rows: list[bytes] = []
    previous = bytearray(row_bytes)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        scanline = bytearray(raw[offset : offset + row_bytes])
        offset += row_bytes
        reconstructed = _unfilter_png_row(filter_type, scanline, previous, bpp)
        rows.append(bytes(reconstructed))
        previous = reconstructed
    return rows


def _unfilter_png_row(filter_type: int, scanline: bytearray, previous: bytearray, bpp: int) -> bytearray:
    if filter_type == 0:
        return scanline
    if filter_type == 1:
        for index, value in enumerate(scanline):
            left = scanline[index - bpp] if index >= bpp else 0
            scanline[index] = (value + left) & 0xFF
        return scanline
    if filter_type == 2:
        for index, value in enumerate(scanline):
            scanline[index] = (value + previous[index]) & 0xFF
        return scanline
    if filter_type == 3:
        for index, value in enumerate(scanline):
            left = scanline[index - bpp] if index >= bpp else 0
            up = previous[index]
            scanline[index] = (value + ((left + up) // 2)) & 0xFF
        return scanline
    if filter_type == 4:
        for index, value in enumerate(scanline):
            left = scanline[index - bpp] if index >= bpp else 0
            up = previous[index]
            upper_left = previous[index - bpp] if index >= bpp else 0
            scanline[index] = (value + _paeth_predictor(left, up, upper_left)) & 0xFF
        return scanline
    raise ValueError(f"unsupported PNG filter: {filter_type}")


def _paeth_predictor(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _png_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(chunk_data, crc) & 0xFFFFFFFF
    return len(chunk_data).to_bytes(4, "big") + chunk_type + chunk_data + crc.to_bytes(4, "big")
