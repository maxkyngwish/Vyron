"""Generate the VYRON icon (PNG + multi-size ICO) with the standard library only.

Run from the repository root:  py tools/make_assets.py
"""
import ctypes
import math
import os
import struct
import zlib
from ctypes import wintypes

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vyron", "assets")
MASTER = 1024
SIZES = (16, 32, 48, 64, 128, 256)


def _rrect_sdf(px, py, cx, cy, half_w, half_h, radius):
    qx = abs(px - cx) - (half_w - radius)
    qy = abs(py - cy) - (half_h - radius)
    ax, ay = max(qx, 0.0), max(qy, 0.0)
    return math.hypot(ax, ay) + min(max(qx, qy), 0.0) - radius


def _segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _lerp(a, b, t):
    return a + (b - a) * t


def render_master():
    """Dark rounded square with a lime V, supersampled by rendering at 1024px."""
    n = MASTER
    pixels = bytearray(n * n * 4)

    cx = cy = n / 2.0
    half = n * 0.46
    radius = n * 0.215
    border = n * 0.037

    left = (n * 0.315, n * 0.315)
    middle = (n * 0.5, n * 0.70)
    right = (n * 0.685, n * 0.315)
    stroke = n * 0.098

    for y in range(n):
        for x in range(n):
            sx = x + 0.5
            sy = y + 0.5
            index = (y * n + x) * 4

            outer = _rrect_sdf(sx, sy, cx, cy, half, half, radius)
            if outer > 0:
                continue

            inner = _rrect_sdf(sx, sy, cx, cy, half - border, half - border, radius - border)
            if inner > 0:
                red, green, blue = 182, 255, 56
            else:
                t = sy / n
                red = int(_lerp(15, 6, t))
                green = int(_lerp(24, 10, t))
                blue = int(_lerp(18, 8, t))

            distance = min(
                _segment_distance(sx, sy, *left, *middle),
                _segment_distance(sx, sy, *middle, *right),
            )
            if distance <= stroke / 2.0:
                t = max(0.0, min(1.0, (sy - left[1]) / (middle[1] - left[1])))
                red = int(_lerp(216, 128, t))
                green = int(_lerp(255, 214, t))
                blue = int(_lerp(122, 26, t))

            pixels[index] = red
            pixels[index + 1] = green
            pixels[index + 2] = blue
            pixels[index + 3] = 255
    return pixels


def downscale(source, src_size, dst_size):
    """Area-average RGBA pixels (premultiplied) from source to dst_size."""
    output = bytearray(dst_size * dst_size * 4)
    ratio = src_size / dst_size
    for y in range(dst_size):
        y0 = y * ratio
        y1 = min(y0 + ratio, src_size)
        for x in range(dst_size):
            x0 = x * ratio
            x1 = min(x0 + ratio, src_size)
            r = g = b = a = 0.0
            count = 0
            sy = int(y0)
            while sy < y1:
                span_y = min(sy + 1, y1) - max(sy, y0)
                sx = int(x0)
                while sx < x1:
                    span_x = min(sx + 1, x1) - max(sx, x0)
                    weight = span_x * span_y
                    offset = (sy * src_size + sx) * 4
                    alpha = source[offset + 3] / 255.0
                    r += source[offset] * alpha * weight
                    g += source[offset + 1] * alpha * weight
                    b += source[offset + 2] * alpha * weight
                    a += alpha * weight
                    count += weight
                    sx += 1
                sy += 1
            index = (y * dst_size + x) * 4
            if a > 0:
                output[index] = int(round(r / a))
                output[index + 1] = int(round(g / a))
                output[index + 2] = int(round(b / a))
                output[index + 3] = int(round(255 * a / count))
            else:
                output[index + 3] = 0
    return bytes(output)


def resize_rgba(source, src_w, src_h, dst_w, dst_h):
    """Area-average RGBA pixels from any size to any other size."""
    output = bytearray(dst_w * dst_h * 4)
    ratio_x = src_w / dst_w
    ratio_y = src_h / dst_h
    for y in range(dst_h):
        y0 = y * ratio_y
        y1 = min(y0 + ratio_y, src_h)
        for x in range(dst_w):
            x0 = x * ratio_x
            x1 = min(x0 + ratio_x, src_w)
            r = g = b = a = 0.0
            count = 0.0
            sy = int(y0)
            while sy < y1:
                span_y = min(sy + 1, y1) - max(sy, y0)
                sx = int(x0)
                while sx < x1:
                    span_x = min(sx + 1, x1) - max(sx, x0)
                    weight = span_x * span_y
                    offset = (sy * src_w + sx) * 4
                    alpha = source[offset + 3] / 255.0
                    r += source[offset] * alpha * weight
                    g += source[offset + 1] * alpha * weight
                    b += source[offset + 2] * alpha * weight
                    a += alpha * weight
                    count += weight
                    sx += 1
                sy += 1
            index = (y * dst_w + x) * 4
            if a > 0:
                output[index] = int(round(r / a))
                output[index + 1] = int(round(g / a))
                output[index + 2] = int(round(b / a))
                output[index + 3] = int(round(255 * a / count))
            else:
                output[index + 3] = 0
    return bytes(output)


def png_bytes(pixels, width, height=None):
    height = width if height is None else height
    raw = b"".join(
        b"\x00" + pixels[y * width * 4:(y + 1) * width * 4] for y in range(height)
    )

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def bmp_entry(pixels, size):
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0)
    rows = []
    for y in range(size - 1, -1, -1):
        row = bytearray()
        for x in range(size):
            offset = (y * size + x) * 4
            row += bytes((pixels[offset + 2], pixels[offset + 1], pixels[offset], pixels[offset + 3]))
        rows.append(bytes(row))
    mask_row = bytes(((size + 31) // 32) * 4)
    return header + b"".join(rows) + mask_row * size


def ico_bytes(images):
    count = len(images)
    directory = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = []
    payload = []
    for size, data in images:
        dimension = 0 if size >= 256 else size
        entries.append(struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset,
        ))
        payload.append(data)
        offset += len(data)
    return directory + b"".join(entries) + b"".join(payload)


# --------------------------------------------------------------------- wordmark
# Tk draws small bold text with hard hinting, which looks blocky on a dark
# background. Render the wordmark once with GDI, high resolution and grayscale
# antialiasing, then area-average it down to the exact display size.

_WORDMARK_FACES = (
    "Bahnschrift SemiCondensed", "Bahnschrift SemiBold", "Bahnschrift",
    "Segoe UI Semibold", "Segoe UI", "Arial",
)


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", ctypes.c_ubyte * 4)]


def _gdi_text(text, face, pixel_height, tracking):
    """Render *text* white on transparent black; return (pixels, width, height)."""
    gdi32 = ctypes.WinDLL("gdi32")
    user32 = ctypes.WinDLL("user32")

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC, ctypes.POINTER(_BITMAPINFO), wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
    ]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.DWORD]
    gdi32.SetTextCharacterExtra.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.CreateFontW.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.BYTE, wintypes.BYTE, wintypes.BYTE, wintypes.BYTE,
        wintypes.BYTE, wintypes.BYTE, wintypes.BYTE, wintypes.BYTE,
        wintypes.LPCWSTR,
    ]
    gdi32.CreateFontW.restype = wintypes.HFONT
    gdi32.GetTextExtentPoint32W.argtypes = [
        wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.SIZE),
    ]
    gdi32.TextOutW.argtypes = [
        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int,
    ]
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]

    screen = user32.GetDC(None)
    memdc = gdi32.CreateCompatibleDC(screen)

    font = gdi32.CreateFontW(
        -pixel_height, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 3, 0, face,
    )
    old_font = gdi32.SelectObject(memdc, font)
    gdi32.SetBkMode(memdc, 1)
    gdi32.SetTextColor(memdc, 0x00FFFFFF)
    gdi32.SetTextCharacterExtra(memdc, int(round(pixel_height * tracking)))

    size = wintypes.SIZE()
    gdi32.GetTextExtentPoint32W(memdc, text, len(text), ctypes.byref(size))
    pad = pixel_height // 3
    width = int(size.cx) + pad * 2
    height = int(size.cy) + pad * 2

    info = _BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0
    bits = ctypes.c_void_p()
    bitmap = gdi32.CreateDIBSection(memdc, ctypes.byref(info), 0, ctypes.byref(bits), None, 0)
    old_bitmap = gdi32.SelectObject(memdc, bitmap)

    gdi32.TextOutW(memdc, pad, pad, text, len(text))

    buffer = ctypes.string_at(bits, width * height * 4)
    pixels = bytearray(width * height * 4)
    for index in range(0, len(buffer), 4):
        # White text on transparent black: the red channel is the coverage.
        coverage = buffer[index + 2]
        pixels[index] = pixels[index + 1] = pixels[index + 2] = 255
        pixels[index + 3] = coverage

    gdi32.SelectObject(memdc, old_bitmap)
    gdi32.SelectObject(memdc, old_font)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteObject(font)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(None, screen)
    return bytes(pixels), width, height


def _crop(pixels, width, height):
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            if pixels[row + x * 4 + 3] > 6:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
    if max_x < min_x:
        return pixels, width, height
    new_w, new_h = max_x - min_x + 1, max_y - min_y + 1
    out = bytearray(new_w * new_h * 4)
    for y in range(new_h):
        source = ((y + min_y) * width + min_x) * 4
        out[y * new_w * 4:(y + 1) * new_w * 4] = pixels[source:source + new_w * 4]
    return bytes(out), new_w, new_h


def wordmark_png(text, cap_height, color, face="Bahnschrift", tracking=0.06):
    """Return PNG bytes for *text* whose capital letters are *cap_height* px."""
    render = 260
    pixels, width, height = _gdi_text(text, face, render, tracking)
    pixels, width, height = _crop(pixels, width, height)
    # Capitals are about 0.72 em tall; the crop already removed the padding, so
    # the ink height is the cap height.
    target_h = max(1, round(cap_height))
    target_w = max(1, round(width * target_h / height))
    pixels = bytearray(resize_rgba(pixels, width, height, target_w, target_h))
    red, green, blue = color
    for index in range(0, len(pixels), 4):
        pixels[index] = red
        pixels[index + 1] = green
        pixels[index + 2] = blue
    return png_bytes(pixels, target_w, target_h), target_w, target_h


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    master = render_master()
    print("master rendered")

    images = []
    for size in SIZES:
        pixels = master if size == MASTER else downscale(master, MASTER, size)
        if size == 256:
            with open(os.path.join(OUT_DIR, "vyron.png"), "wb") as handle:
                handle.write(png_bytes(pixels, size))
        images.append((size, bmp_entry(pixels, size)))

    # Exact display sizes: no nearest-neighbour subsample in the app.
    for size in (36, 96):
        pixels = downscale(master, MASTER, size)
        with open(os.path.join(OUT_DIR, f"vyron-{size}.png"), "wb") as handle:
            handle.write(png_bytes(pixels, size))
        print("logo", size, "ok")

    white = (239, 247, 239)
    for cap, name in ((19, "vyron-wordmark.png"), (52, "vyron-wordmark-xl.png")):
        data, width, height = wordmark_png("VYRON", cap, white)
        with open(os.path.join(OUT_DIR, name), "wb") as handle:
            handle.write(data)
        print(name, f"{width}x{height}", "ok")

    with open(os.path.join(OUT_DIR, "vyron.ico"), "wb") as handle:
        handle.write(ico_bytes(images))
    print("written to", OUT_DIR)


if __name__ == "__main__":
    main()
