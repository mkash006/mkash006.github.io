#!/usr/bin/env python3
"""Put the two Snakemake rule graphs on one canvas for the software page.

Snakemake writes one rule graph per workflow and the software page shows both
as a single figure. Each export comes on opaque white with a wide margin and a
title of its own, so the matte is cleared the way the research figures are, the
baked-in title is cut off, and the two graphs are scaled to a shared height and
set side by side. The page caption names them, so nothing is drawn back on.

    python3 tools/combine_rulegraphs.py
"""

from pathlib import Path

from PIL import Image

from figure_bg_transparent import trim, whiten_to_alpha

ROOT = Path(__file__).resolve().parent.parent

SOURCES = [
    ROOT / "assets" / "gatk_rulegraph_final.png",
    ROOT / "assets" / "stacks_rulegraph_final.png",
]
OUT = ROOT / "assets" / "snakemake_rulegraphs.png"

GUTTER = 110         # px between the panels
# A row wider than this fraction of the export belongs to the title. Set well
# clear of the graph, whose widest row covers under a quarter of the export, so
# that the faint last row of the title's descenders is cut off with it.
TITLE_WIDTH = 0.3


def graph_only(img: Image.Image) -> Image.Image:
    """Cut the export's own title off, keeping the rule graph below it.

    The title is set across nearly the full width and its descenders run right
    into the first node, so there is no empty row to split on. Width is what
    separates them instead: the title's rows are wide, and no row of the graph
    comes close, since the graph is a narrow column of boxes.
    """
    # Thresholded, since the cleared matte keeps a faint alpha around type and
    # that would otherwise widen a row.
    alpha = img.split()[3].point(lambda v: 255 if v > 8 else 0)
    cutoff = img.width * TITLE_WIDTH

    for y in range(img.height):
        box = alpha.crop((0, y, img.width, y + 1)).getbbox()
        if box and box[2] - box[0] > cutoff:
            title_end = y
            break
    else:
        return img

    for y in range(title_end, img.height):
        box = alpha.crop((0, y, img.width, y + 1)).getbbox()
        if not box or box[2] - box[0] <= cutoff:
            return img.crop((0, y, img.width, img.height))
    return img


def prepare(path: Path) -> Image.Image:
    return trim(graph_only(trim(whiten_to_alpha(Image.open(path)))))


def main() -> None:
    # Both exports were rendered at the same scale, so the panels go in at
    # native size and a rule box is the same size in either graph. They are
    # hung from the top, since each graph reads downwards from its first rule.
    graphs = [prepare(path) for path in SOURCES]
    width = sum(g.width for g in graphs) + GUTTER * (len(graphs) - 1)
    canvas = Image.new("RGBA", (width, max(g.height for g in graphs)), (0, 0, 0, 0))

    x = 0
    for graph in graphs:
        canvas.paste(graph, (x, 0))
        x += graph.width + GUTTER

    canvas.save(OUT)
    kb = OUT.stat().st_size // 1024
    print(f"{OUT}: {canvas.size[0]}x{canvas.size[1]}, {kb} KB")


if __name__ == "__main__":
    main()
