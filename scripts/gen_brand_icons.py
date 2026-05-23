"""Generate flat icon + logo for codex_proxy.

Concept: a "token pool" that funnels into a single proxied output.
- Left: three dots stacked vertically (the pool)
- Middle: lines converging to a point
- Right: single dot (the proxied output)

Flat design (no gradients, no shadows, single primary color + white).
Background: rounded square, sky-blue (#0EA5E9 — accessible against both
light/dark HA themes).  Foreground: white.

Outputs:
- icon.png      256x256 (square, used in HA device card)
- icon@2x.png   512x512 (HiDPI variant)
- logo.png     1021x256 (horizontal, used in HACS card)
- logo@2x.png  2041x512 (HiDPI variant)
"""

from PIL import Image, ImageDraw, ImageFont


SKY_BLUE = (14, 165, 233, 255)  # #0EA5E9 — flat, accessible
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def _draw_pool_arrow(draw: ImageDraw.ImageDraw, x0: int, y0: int, size: int) -> None:
    """Draw the pool→arrow→output graphic centred in a `size x size` box at (x0, y0).

    Layout (proportional to size):
    - 3 dots on the left, vertically centred, separated by 22% of size
    - 3 thin lines from each dot converging to a point in the centre
    - 1 large dot on the right (= the output)
    - All in white on transparent background
    """
    s = size
    cx = x0 + s // 2
    cy = y0 + s // 2

    # Pool dots: left-side, vertical column
    pool_dot_r = int(s * 0.07)
    pool_x = x0 + int(s * 0.18)
    pool_dy = int(s * 0.22)
    pool_centers = [
        (pool_x, cy - pool_dy),
        (pool_x, cy),
        (pool_x, cy + pool_dy),
    ]

    # Output dot: right-side, centred
    out_dot_r = int(s * 0.13)
    out_x = x0 + int(s * 0.82)

    # Convergence point: between pool and output, slightly biased toward output
    converge_x = x0 + int(s * 0.55)
    converge_y = cy

    # Draw connecting lines from each pool dot to the convergence point,
    # then a single line from convergence point to the output dot.
    line_w = max(2, int(s * 0.028))
    for px, py in pool_centers:
        draw.line([(px, py), (converge_x, converge_y)], fill=WHITE, width=line_w)
    draw.line(
        [(converge_x, converge_y), (out_x, cy)],
        fill=WHITE,
        width=line_w,
    )

    # Draw the pool dots (over the lines so the line endpoints look clean)
    for px, py in pool_centers:
        draw.ellipse(
            [(px - pool_dot_r, py - pool_dot_r), (px + pool_dot_r, py + pool_dot_r)],
            fill=WHITE,
        )

    # Draw the larger output dot (last so it sits on top of the converging line)
    draw.ellipse(
        [(out_x - out_dot_r, cy - out_dot_r), (out_x + out_dot_r, cy + out_dot_r)],
        fill=WHITE,
    )


def _rounded_square(size: int, radius_pct: float = 0.22) -> Image.Image:
    """Return an `size`x`size` RGBA image: rounded-square sky-blue background.

    `radius_pct` is the HA convention (0.22 = ~22% of the side — roughly the
    iOS app-icon corner radius)."""
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)
    r = int(size * radius_pct)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=r, fill=SKY_BLUE)
    return img


def gen_icon(size: int, out_path: str) -> None:
    """Generate icon.png — square, rounded background, centred glyph."""
    img = _rounded_square(size)
    draw = ImageDraw.Draw(img)
    # Glyph occupies ~70% of the icon (10% padding on each side)
    pad = int(size * 0.15)
    glyph_size = size - 2 * pad
    _draw_pool_arrow(draw, pad, pad, glyph_size)
    img.save(out_path, "PNG", optimize=True)
    print(f"wrote {out_path} ({size}x{size})")


def gen_logo(width: int, height: int, out_path: str) -> None:
    """Generate logo.png — horizontal layout: square mark + wordmark.

    The mark is a square the height of the logo (so it visually balances);
    the wordmark "Codex Token Pool" sits to the right in flat blue.
    """
    img = Image.new("RGBA", (width, height), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # 1. The square mark on the left
    mark_size = height
    mark = _rounded_square(mark_size)
    mark_draw = ImageDraw.Draw(mark)
    pad = int(mark_size * 0.15)
    glyph_size = mark_size - 2 * pad
    _draw_pool_arrow(mark_draw, pad, pad, glyph_size)
    img.paste(mark, (0, 0), mark)

    # 2. Wordmark on the right.  Auto-shrink the font so the text fits the
    # available horizontal space — for the standard 1021x256 logo, the
    # wordmark has ~765 px to play with after the 256-px square mark + gap.
    wordmark = "Codex Token Pool"
    gap = int(height * 0.12)
    text_x = mark_size + gap
    text_box_w = width - text_x - gap

    font = None

    def _load_font(size: int) -> ImageFont.FreeTypeFont | None:
        for font_path in (
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ):
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
        return None

    # Binary-search the largest font size that keeps the wordmark within
    # text_box_w (with a 10% safety margin so a different system font's
    # metrics don't push the text off the right edge).
    target_w = int(text_box_w * 0.90)
    lo, hi = int(height * 0.15), int(height * 0.55)
    best_font = None
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = _load_font(mid)
        if candidate is None:
            font = ImageFont.load_default()
            break
        bbox = draw.textbbox((0, 0), wordmark, font=candidate)
        if bbox[2] - bbox[0] <= target_w:
            best_font = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    if best_font is not None:
        font = best_font
    if font is None:
        font = ImageFont.load_default()

    # Measure text with the final font and centre vertically
    bbox = draw.textbbox((0, 0), wordmark, font=font)
    text_h = bbox[3] - bbox[1]
    text_y = (height - text_h) // 2 - bbox[1]
    draw.text((text_x, text_y), wordmark, font=font, fill=SKY_BLUE)

    img.save(out_path, "PNG", optimize=True)
    print(f"wrote {out_path} ({width}x{height})")


if __name__ == "__main__":
    import sys

    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/icons"
    import os

    os.makedirs(out_dir, exist_ok=True)
    gen_icon(256, f"{out_dir}/icon.png")
    gen_icon(512, f"{out_dir}/icon@2x.png")
    gen_logo(1021, 256, f"{out_dir}/logo.png")
    gen_logo(2041, 512, f"{out_dir}/logo@2x.png")
