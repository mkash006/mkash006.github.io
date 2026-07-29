#!/usr/bin/env python3
"""Convert the R pedigree plots in assets/ into the JS the research page loads.

The SVGs come out of R's cairo device, so they have no semantic structure at
all: every individual and every parent-offspring line is an anonymous <path>,
and the labels are <use> refs into an anonymous glyph table. This script
recovers the graph (who is whose parent) so the page can render it as an
interactive network. Re-run it if either plot is regenerated:

    python3 tools/pedigree_to_js.py
"""
import hashlib
import math
import re
from collections import defaultdict

# Both plots come off the same device with the same palette, so one set of
# rules covers them.
FIGURES = [
    {"src": "assets/pedigree.svg",
     "out": "assets/pedigree-data.js",
     "var": "PEDIGREE"},
    {"src": "assets/guppyped.svg",
     "out": "assets/pedigree-guppy.js",
     "var": "PEDIGREE_GUPPY"},
]

NUM = r"-?[\d.]+"
GREEN = "rgb(0%, 61.960784%, 45.098039%)"    # dams, drawn as circles
ORANGE = "rgb(83.529412%, 36.862745%, 0%)"   # sires, drawn as squares

# Cairo subsets the font per file, so glyph ids mean nothing across files and
# nothing on their own. The outlines are stable though, so each character is
# keyed by a hash of its path data. Anything not in here is not label text,
# which is how the plot title gets skipped.
GLYPHS = {
    "2ad6197990": "/", "0f3d27c252": "0", "b05f222de1": "1",
    "e845d63256": "2", "572d0e2543": "3", "1590dd75e4": "4",
    "b4a82c5886": "5", "34ca2be20b": "6", "6708443ba1": "7",
    "34f6f59ac8": "8", "6ee933e7e8": "9", "9e5fdb5d7f": "A",
    "873b3b24f7": "C", "bfb60144ba": "F", "d8a1ef361b": "G",
    "fd401982b8": "H", "7f50b77dd1": "K", "9de105446b": "L",
    "51a7e4d745": "M", "49c2c89c25": "N", "c75e3bb364": "Q",
    "3ff5bf4f7e": "R", "22019b57f6": "S", "d0981e63cc": "T",
    "8faff04960": "W", "c234181150": "X", "f1a187af79": "Y",
    "8d64aecf73": "_",
}


def attrs(tag):
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', tag))


def font(svg):
    """Map this file's glyph ids to characters, by outline."""
    defs = svg[:svg.find("</defs>")]
    table = {}
    for m in re.finditer(r'<g id="glyph-([\d-]+)">\s*<path d="(.*?)"', defs,
                         re.S):
        key = hashlib.sha1(re.sub(r"\s+", " ", m.group(2)).strip().encode())
        char = GLYPHS.get(key.hexdigest()[:10])
        if char:
            table[m.group(1)] = char
    return table


def parse(path):
    svg = open(path).read()
    chars = font(svg)
    body = svg[svg.find("</defs>"):]
    nodes, segments = [], []

    for tag in re.findall(r"<path[^>]*>", body):
        a = attrs(tag)
        coords = [float(v) for v in re.findall(NUM, a["d"])]
        if "fill-rule" not in a:                  # a parent -> offspring line
            segments.append((coords[0], coords[1], coords[2], coords[3],
                             "d" if a["stroke"] == GREEN else "s"))
            continue
        xs, ys = coords[0::2], coords[1::2]
        kind = {GREEN: "dam", ORANGE: "sire"}.get(a["fill"], "off")
        nodes.append({"x": (min(xs) + max(xs)) / 2,
                      "y": (min(ys) + max(ys)) / 2,
                      "r": (max(xs) - min(xs)) / 2,
                      "k": kind, "id": ""})

    label(nodes, body, chars)
    return nodes, segments


def label(nodes, body, chars):
    """Read the parent names and give one to each parent.

    Nearest node on its own is not enough: where two parents sit close
    together a name can be marginally nearer the wrong one. Every parent
    carries exactly one name, so the pairs are taken in order of distance and
    each side is used once, which lets the confident matches settle first.
    """
    labels = []
    for g in re.finditer(r"<g fill[^>]*>(.*?)</g>", body, re.S):
        uses = re.findall(
            r'xlink:href="#glyph-([\d-]+)" x="(%s)" y="(%s)"' % (NUM, NUM),
            g.group(1))
        if not uses or any(u[0] not in chars for u in uses):
            continue                              # the plot title, not a label
        xs = [float(u[1]) for u in uses]
        labels.append(("".join(chars[u[0]] for u in uses),
                       (min(xs) + max(xs)) / 2, float(uses[0][2])))

    named = [n for n in nodes if n["k"] != "off"]
    pairs = sorted((math.hypot(n["x"] - lx, n["y"] - ly), j, n)
                   for j, (_, lx, ly) in enumerate(labels)
                   for n in named)
    used = set()
    for _, j, n in pairs:
        if j in used or n["id"]:
            continue
        used.add(j)
        n["id"] = labels[j][0]


def wire(nodes, segments):
    """Attach each line to the offspring dot and parent shape it touches."""
    off = [i for i, n in enumerate(nodes) if n["k"] == "off"]
    pools = {"d": [i for i, n in enumerate(nodes) if n["k"] == "dam"],
             "s": [i for i, n in enumerate(nodes) if n["k"] == "sire"]}

    def centre_dist(i, px, py):
        return math.hypot(nodes[i]["x"] - px, nodes[i]["y"] - py)

    def edge_dist(i, px, py):
        """Distance from a point to the node's outline: lines stop there."""
        n = nodes[i]
        dx, dy = abs(n["x"] - px), abs(n["y"] - py)
        reach = math.hypot(dx, dy) if n["k"] == "dam" else max(dx, dy)
        return abs(reach - n["r"])

    seen, links = set(), []
    for x1, y1, x2, y2, kind in segments:
        a = min(off, key=lambda i: centre_dist(i, x1, y1))
        b = min(off, key=lambda i: centre_dist(i, x2, y2))
        if centre_dist(a, x1, y1) <= centre_dist(b, x2, y2):
            child, px, py = a, x2, y2
        else:
            child, px, py = b, x1, y1
        parent = min(pools[kind], key=lambda i: edge_dist(i, px, py))
        if (parent, child) not in seen:
            seen.add((parent, child))
            links.append([parent, child])
    return links


def write(fig, nodes, links):
    pad = 6
    x0 = min(n["x"] - n["r"] for n in nodes) - pad
    y0 = min(n["y"] - n["r"] for n in nodes) - pad
    x1 = max(n["x"] + n["r"] for n in nodes) + pad
    y1 = max(n["y"] + n["r"] for n in nodes) + pad

    rows = ",".join(
        "[%s,%s,%s,%d,%s]" % (round(n["x"] - x0, 1), round(n["y"] - y0, 1),
                              round(n["r"], 2),
                              {"dam": 0, "sire": 1, "off": 2}[n["k"]],
                              '"%s"' % n["id"] if n["id"] else "0")
        for n in nodes)
    edge_rows = ",".join("[%d,%d]" % (p, c) for p, c in links)

    with open(fig["out"], "w") as fh:
        fh.write("/* Generated by tools/pedigree_to_js.py - do not edit. */\n")
        fh.write("/* node = [x, y, r, kind(0 dam, 1 sire, 2 offspring), id] */\n")
        fh.write("window.%s = {\n" % fig["var"])
        fh.write('  w: %s, h: %s,\n' % (round(x1 - x0, 1), round(y1 - y0, 1)))
        fh.write("  nodes: [%s],\n" % rows)
        fh.write("  links: [%s]\n" % edge_rows)
        fh.write("};\n")


def main():
    for fig in FIGURES:
        nodes, segments = parse(fig["src"])
        links = wire(nodes, segments)
        write(fig, nodes, links)

        per_child = defaultdict(int)
        for _, c in links:
            per_child[c] += 1
        kinds = defaultdict(int)
        for n in nodes:
            kinds[n["k"]] += 1
        print("%s: %d dams, %d sires, %d offspring (%d named), %d links, "
              "%d offspring with both parents"
              % (fig["out"], kinds["dam"], kinds["sire"], kinds["off"],
                 sum(1 for n in nodes if n["id"]), len(links),
                 sum(1 for v in per_child.values() if v == 2)))


if __name__ == "__main__":
    main()
