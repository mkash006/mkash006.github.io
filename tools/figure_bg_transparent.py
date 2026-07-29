#!/usr/bin/env python3
"""Drop the white matte out of a figure PNG and trim its margins.

Slide exports come out on opaque white, so on the site's pale blue paper they
read as a pasted-in rectangle. Clearing the white to transparent lets the page
colour sit behind the chromosomes and labels instead.

    python3 tools/figure_bg_transparent.py assets/imprinting.png
"""

import sys
from pathlib import Path

from PIL import Image

# Anything at or above OPAQUE_BELOW stays fully painted, anything at or above
# CLEAR_ABOVE is matte. The gap between them is where anti-aliased type lives,
# and it gets a partial alpha so letter edges stay smooth rather than crunchy.
# The window is deliberately narrow so the pale grey chromosome bands, which
# run to about 240, are never mistaken for background.
OPAQUE_BELOW = 246
CLEAR_ABOVE = 252

PAD = 6  # px of breathing room left around the trimmed content


def whiten_to_alpha(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    # Distance from white is measured on the darkest channel, so a saturated
    # red or green block counts as content even though it is bright.
    r, g, b, _ = img.split()
    floor = Image.new("L", img.size)
    floor.putdata([min(p) for p in zip(r.getdata(), g.getdata(), b.getdata())])

    span = CLEAR_ABOVE - OPAQUE_BELOW
    alpha = floor.point(
        lambda v: 255 if v <= OPAQUE_BELOW
        else (0 if v >= CLEAR_ABOVE else round(255 * (CLEAR_ABOVE - v) / span))
    )
    img.putalpha(alpha)
    return img


def trim(img: Image.Image) -> Image.Image:
    box = img.split()[3].point(lambda v: 255 if v > 8 else 0).getbbox()
    if box is None:
        return img
    left, top, right, bottom = box
    w, h = img.size
    return img.crop((max(0, left - PAD), max(0, top - PAD),
                     min(w, right + PAD), min(h, bottom + PAD)))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    out = trim(whiten_to_alpha(Image.open(path)))
    out.save(path)
    print(f"{path}: {out.size[0]}x{out.size[1]}, white matte cleared")


if __name__ == "__main__":
    main()
