"""Frosted-glass look for the PokeSync window, drawn with Pillow.

Tk widgets can't be see-through, so the glass is faked: one image holds a soft
colour wallpaper plus every panel (shadow, smoked fill, light edge), and the real
widgets sit on top of the flat middle of each panel. Each panel's fill is the
wallpaper underneath it mixed with a dark tint, so it reads as tinted glass.
"""
from PIL import Image, ImageChops, ImageDraw, ImageFilter

TINT = (16, 18, 34)   # smoked glass
TINT_AMOUNT = 0.78    # 1.0 = opaque tint, 0.0 = clear glass
EDGE_TOP = 70         # alpha of the light edge at the top of a panel ...
EDGE_BOTTOM = 18      # ... fading to this at the bottom

BASE_TOP = (17, 13, 40)
BASE_BOTTOM = (7, 18, 36)
# (x, y, radius) relative to the window, and colour
BLOBS = [
    (0.10, 0.15, 0.40, (124, 58, 237)),
    (0.88, 0.10, 0.34, (219, 39, 119)),
    (0.72, 0.92, 0.44, (8, 145, 178)),
    (0.22, 0.95, 0.30, (37, 99, 235)),
]


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def wallpaper(width, height):
    # Drawn tiny, blurred and scaled up: smooth gradients for almost no work.
    small = (160, 100)
    grad = Image.linear_gradient("L").resize(small)
    img = Image.composite(Image.new("RGB", small, BASE_BOTTOM), Image.new("RGB", small, BASE_TOP), grad)
    for rx, ry, rr, colour in BLOBS:
        mask = Image.new("L", small, 0)
        r, cx, cy = rr * small[0], rx * small[0], ry * small[1]
        ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=120)
        mask = mask.filter(ImageFilter.GaussianBlur(small[0] * 0.12))
        img = Image.composite(Image.new("RGB", small, colour), img, mask)
    return img.resize((max(1, width), max(1, height)), Image.BICUBIC)


def glass_fill(wall, rect):
    """Flat colour of a glass panel at rect: the average of what's behind it, tinted."""
    x0, y0, x1, y1 = (int(v) for v in rect)
    behind = wall.crop((x0, y0, max(x0 + 1, x1), max(y0 + 1, y1))).resize((1, 1), Image.BOX).getpixel((0, 0))
    return mix(behind, TINT, TINT_AMOUNT)


def _rounded_mask(size, radius, inset=0.0, ss=4):
    """Anti-aliased rounded-rectangle mask (drawn at ss x and scaled down)."""
    w, h = size
    mask = Image.new("L", (w * ss, h * ss), 0)
    box = (inset * ss, inset * ss, (w - inset) * ss - 1, (h - inset) * ss - 1)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=max(0.0, radius - inset) * ss, fill=255)
    return mask.resize(size, Image.LANCZOS)


def render(width, height, panels, scale=1.0):
    """Backdrop image (width x height px) with the panels drawn in.

    panels: [(rect, radius, fill_rgb)] with rect = (x0, y0, x1, y1) in logical units;
    `scale` converts them to pixels (Tk window scaling).
    """
    img = wallpaper(width, height)

    # Soft shadow under every panel
    shadow = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(shadow)
    for (x0, y0, x1, y1), radius, _ in panels:
        off = 6 * scale
        draw.rounded_rectangle((x0 * scale, y0 * scale + off, x1 * scale, y1 * scale + off),
                               radius=radius * scale, fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(14 * scale))
    img = Image.composite(Image.new("RGB", img.size, (0, 0, 0)), img, shadow)

    for (x0, y0, x1, y1), radius, fill in panels:
        box = tuple(round(v * scale) for v in (x0, y0, x1, y1))
        size = (box[2] - box[0], box[3] - box[1])
        if size[0] <= 2 or size[1] <= 2:
            continue
        r = radius * scale
        outer = _rounded_mask(size, r)
        img.paste(Image.new("RGB", size, fill), box[:2], outer)
        # Light edge, brighter at the top like light catching the glass
        ring = ImageChops.subtract(outer, _rounded_mask(size, r, inset=1.2 * scale))
        fade = Image.linear_gradient("L").resize(size).point(
            lambda v: round(EDGE_TOP + (EDGE_BOTTOM - EDGE_TOP) * v / 255))
        img.paste(Image.new("RGB", size, (255, 255, 255)), box[:2], ImageChops.multiply(ring, fade))
    return img
