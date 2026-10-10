"""Draws the three pictures of the vision tasks in qtasks.py (standard library only) into images/:
  shapes.png  red circle, blue square, green triangle      (vi_desc)
  ocr.png     the order code QX-4721                       (vi_ocr)
  dots.png    7 black dots                                 (vi_cnt)
The pictures of the published run were not kept; these redraw the same content, so vision scores are comparable
but not byte-identical. usage: python make_images.py [--force]"""
import os, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "images")
W, H = 480, 320
FONT = {  # 5x7 bitmap glyphs, one string per row
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    " ": ["00000"] * 7,
}


def canvas():
    return [[(255, 255, 255)] * W for _ in range(H)]


def save(img, name):
    raw = b"".join(b"\0" + bytes(c for px in row for c in px) for row in img)
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(png)


def disc(img, cx, cy, r, color):
    for y in range(max(0, cy - r), min(H, cy + r + 1)):
        for x in range(max(0, cx - r), min(W, cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                img[y][x] = color


def shapes():
    img = canvas()
    disc(img, 90, 160, 60, (220, 30, 30))
    for y in range(100, 221):
        for x in range(180, 301):
            img[y][x] = (30, 60, 220)
    for y in range(100, 221):                      # apex at (400, 100), base from 340 to 460 at y = 220
        half = (y - 100) * 60 // 120
        for x in range(400 - half, 400 + half + 1):
            img[y][x] = (30, 170, 60)
    return img


def text(img, s, x0, y0, scale):
    for i, ch in enumerate(s):
        for row, bits in enumerate(FONT[ch]):
            for col, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            img[y0 + row * scale + dy][x0 + (i * 6 + col) * scale + dx] = (0, 0, 0)


def ocr():
    img = canvas()
    text(img, "ORDER:", 40, 70, 8)
    text(img, "QX-4721", 40, 170, 8)
    return img


def dots():
    img = canvas()
    for cx, cy in [(70, 80), (190, 60), (330, 90), (420, 200), (250, 180), (110, 240), (300, 270)]:
        disc(img, cx, cy, 22, (0, 0, 0))
    return img


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, draw in [("shapes.png", shapes), ("ocr.png", ocr), ("dots.png", dots)]:
        if "--force" in sys.argv or not os.path.isfile(os.path.join(OUT, name)):
            save(draw(), name)
            print("wrote images/" + name)
