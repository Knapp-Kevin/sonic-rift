"""MythologIQ Labs opener (2.6 s, 30 fps) from the website revamp's own assets and styling.

    python make_opener.py <mark webp> <DM Sans variable ttf> <first film frame jpg> <out dir>

The mark is the website's file (mythologiq-silver-concept.webp, SHA-256 c0141a60...94b2), cropped to its
visible area and scaled down (never up). The lockup follows the revamp header (src/studio/studio.css at
6b655b69): mark beside "MythologIQ" (DM Sans 700, #fff) + " Labs" (500, #d4d5da), letter-spacing -0.025em,
and "INDEPENDENT SOFTWARE STUDIO" (700, #aaaeb9, 8/21 of the wordmark size, letter-spacing 0.16em, margin
7/21) on the studio canvas #090a10, with the header's drop shadow and soft silver glow, scaled. Motion: the
mark fades in, the wordmark and subtitle follow, a hold, then a dissolve into the film's first frame.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

MARK, FONT, FIRST, OUT = sys.argv[1:5]
OUT = Path(OUT)
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, SECONDS = 2400, 1350, 30, 2.6
CANVAS = (9, 10, 16)
MARK_H = 360                       # visible mark height on the 1350-px canvas
SITE_MARK, SITE_FONT, SITE_SMALL, SITE_GAP, SITE_MARGIN = 46.0, 21.0, 8.0, 25.5, 7.0   # px on the website header
SCALE = MARK_H / SITE_MARK
FONT_PX, SMALL_PX = round(SITE_FONT * SCALE), round(SITE_SMALL * SCALE)
GAP, MARGIN = round(SITE_GAP * SCALE), round(SITE_MARGIN * SCALE)

mark = Image.open(MARK).convert("RGBA")
mark = mark.crop(mark.split()[3].getbbox())
mark_w = round(mark.width * MARK_H / mark.height)
assert MARK_H <= mark.height, "the mark must never be scaled up"
mark = mark.resize((mark_w, MARK_H), Image.LANCZOS)


def font(px, weight, opsz):
    f = ImageFont.truetype(FONT, px)
    f.set_variation_by_axes([opsz, weight])
    return f


bold, medium = font(FONT_PX, 700, 21), font(FONT_PX, 500, 21)
small = font(SMALL_PX, 700, 9)


def spaced(draw, x, y, text, f, fill, spacing):
    """Draw with CSS-style letter-spacing (em), keeping the font's own kerning between letters."""
    for i, ch in enumerate(text):
        draw.text((x + f.getlength(text[:i]) + i * spacing * f.size, y), ch, font=f, fill=fill)
    return f.getlength(text) + len(text) * spacing * f.size


def text_layer(parts, f_small, small_text):
    """The two-line wordmark on its own transparent layer; returns the layer and its box."""
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    word_w = sum(f.getlength(t) + len(t) * -0.025 * f.size for t, f, _ in parts)
    small_w = f_small.getlength(small_text) + len(small_text) * 0.16 * f_small.size
    ascent, descent = parts[0][1].getmetrics()
    s_ascent, s_descent = f_small.getmetrics()
    line_h = round(FONT_PX * 1.05)
    height = line_h + MARGIN + s_ascent + s_descent
    layer = Image.new("RGBA", (int(max(word_w, small_w)) + 20, height + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, top = 0, (line_h - (ascent + descent)) // 2
    for t, f, fill in parts:
        x += spaced(d, x, top, t, f, fill, -0.025)
    spaced(d, 0, line_h + MARGIN, small_text, f_small, (0xAA, 0xAE, 0xB9, 255), 0.16)
    del probe
    return layer.crop(layer.getbbox())


words = text_layer([("MythologIQ", bold, (255, 255, 255, 255)), (" Labs", medium, (0xD4, 0xD5, 0xDA, 255))],
                   small, "INDEPENDENT SOFTWARE STUDIO")
# split the wordmark line from the subtitle so the subtitle can follow a beat later
alpha = np.array(words.split()[3])
rows = np.flatnonzero(alpha.max(axis=1) > 0)
gaps = np.flatnonzero(np.diff(rows) > 1)
cut = rows[gaps[0]] + 1 if len(gaps) else words.height
word_line, subtitle = words.crop((0, 0, words.width, cut)), words.crop((0, cut, words.width, words.height))

total_w = mark_w + GAP + words.width
x0 = (W - total_w) // 2
mark_xy = (x0, (H - MARK_H) // 2)
text_x = x0 + mark_w + GAP
text_y = (H - words.height) // 2


def glow_layer():
    """The header's filter: drop-shadow(0 2px 6px rgba(0,0,0,.7)) drop-shadow(0 0 18px rgba(206,215,232,.22)), scaled."""
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = Image.new("L", (W, H), 0)
    a.paste(mark.split()[3], mark_xy)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh_a = a.filter(ImageFilter.GaussianBlur(6 * SCALE / 2)).point(lambda v: int(v * 0.7))
    shadow.putalpha(Image.new("L", (W, H), 0))
    shadow = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), base, sh_a)
    shadow = shadow.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -round(2 * SCALE)))
    gl_a = a.filter(ImageFilter.GaussianBlur(18 * SCALE / 2)).point(lambda v: int(v * 0.22))
    glow = Image.composite(Image.new("RGBA", (W, H), (206, 215, 232, 255)), base, gl_a)
    return Image.alpha_composite(shadow, glow)


mark_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
mark_layer = Image.alpha_composite(glow_layer(), mark_layer)
mark_layer.alpha_composite(mark, mark_xy)
word_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
word_layer.alpha_composite(word_line, (text_x, text_y))
sub_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sub_layer.alpha_composite(subtitle, (text_x, text_y + cut))
first = Image.open(FIRST).convert("RGB").resize((W, H), Image.LANCZOS)


def ease(t, start, length):
    x = min(1.0, max(0.0, (t - start) / length))
    return x * x * (3 - 2 * x)                    # smoothstep: no hard start or stop


def faded(layer, amount):
    if amount <= 0:
        return None
    a = layer.split()[3].point(lambda v: int(v * amount))
    out = layer.copy()
    out.putalpha(a)
    return out


frames = []
n = round(SECONDS * FPS)
for k in range(n):
    t = k / FPS
    img = Image.new("RGBA", (W, H), CANVAS + (255,))
    for layer, amount in ((mark_layer, ease(t, 0.20, 0.60)), (word_layer, ease(t, 0.50, 0.50)),
                          (sub_layer, ease(t, 0.60, 0.50))):
        f = faded(layer, amount)
        if f is not None:
            img = Image.alpha_composite(img, f)
    img = img.convert("RGB")
    mix = ease(t, 2.20, 0.40)                     # dissolve into the film's first frame
    if mix > 0:
        img = Image.blend(img, first, mix)
    path = OUT / f"o{k:03d}.jpg"
    img.save(path, quality=95)
    frames.append(str(path).replace("\\", "/"))
img_still = OUT / "opener_lockup_still.png"
Image.open(frames[round(1.8 * FPS)]).save(img_still)
json.dump({"fps": FPS, "seconds": SECONDS, "frames": frames, "mark_px": [mark_w, MARK_H], "font_px": FONT_PX,
           "subtitle_px": SMALL_PX, "gap_px": GAP, "lockup_box": [x0, text_y, total_w, words.height],
           "timing": {"mark_fade": [0.2, 0.8], "wordmark_fade": [0.5, 1.0], "subtitle_fade": [0.6, 1.1],
                      "hold_until": 2.2, "dissolve": [2.2, 2.6]}},
          open(OUT / "opener.json", "w", encoding="utf-8"), indent=1)
print(json.dumps({"frames": len(frames), "mark": [mark_w, MARK_H], "font": FONT_PX, "subtitle": SMALL_PX, "gap": GAP}))
