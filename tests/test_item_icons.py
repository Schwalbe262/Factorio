import struct
import unittest
import zlib

from factorio_ai.item_icons import PNG_SIGNATURE, crop_largest_mipmap_png


class ItemIconTests(unittest.TestCase):
    def test_crop_largest_mipmap_png_keeps_leftmost_square(self):
        png = _rgba_png(
            3,
            2,
            [
                [(255, 0, 0, 255), (255, 0, 0, 255), (0, 0, 255, 255)],
                [(255, 0, 0, 255), (255, 0, 0, 255), (0, 0, 255, 255)],
            ],
        )
        cropped = crop_largest_mipmap_png(png)
        self.assertIsNotNone(cropped)
        self.assertEqual(_png_dimensions(cropped or b""), (2, 2))

    def test_square_png_is_not_reencoded(self):
        png = _rgba_png(2, 2, [[(0, 0, 0, 0), (0, 0, 0, 0)], [(0, 0, 0, 0), (0, 0, 0, 0)]])
        self.assertIsNone(crop_largest_mipmap_png(png))


def _rgba_png(width, height, rows):
    raw_rows = []
    for row in rows:
        raw_rows.append(b"\x00" + b"".join(bytes(pixel) for pixel in row))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return PNG_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(b"".join(raw_rows))) + _chunk(b"IEND", b"")


def _png_dimensions(data):
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def _chunk(chunk_type, chunk_data):
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(chunk_data, crc) & 0xFFFFFFFF
    return len(chunk_data).to_bytes(4, "big") + chunk_type + chunk_data + crc.to_bytes(4, "big")


if __name__ == "__main__":
    unittest.main()
