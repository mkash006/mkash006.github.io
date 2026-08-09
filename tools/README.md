# Pedigree figure pipeline

The two interactive pedigrees on the research page are a redraw of the R plots
in `assets/`, not embeds of them. Four pieces, in order:

| File | Role |
| --- | --- |
| `assets/pedigree.svg`, `assets/guppyped.svg` | The original figures out of R's cairo device, for *Heterandria formosa* and *Poecilia reticulata*. Source of truth for coordinates, shapes and sizes. |
| `tools/pedigree_to_js.py` | Recovers both graphs and writes `assets/pedigree-data.js` and `assets/pedigree-guppy.js`. |
| `assets/pedigree-figure.js` | Draws each recovered graph as live SVG and runs the reveal and highlight behaviour. |
| `styles.css` (`.ped-*` rules) | Colours, shapes, dim/lit states, reveal keyframes, the side-by-side layout. |

## Why a converter

Cairo throws away all structure: the individuals and parent-offspring lines are
anonymous `<path>` elements, and the names are `<use>` refs into an unnamed
glyph table. The converter puts each graph back together:

1. Every filled path becomes a node. Fill colour gives its role, since R drew
   dams green and sires orange, and the bounding box gives centre and radius.
2. Every stroked path is a parent-offspring line. Its colour says whether it
   came from the dam or the sire.
3. Each line is matched to the offspring dot nearest one end and, among
   parents of the right sex, to the shape whose *outline* the other end stops
   at. Lines terminate on the shape's edge, not its centre, so the outline
   distance is what identifies large parents correctly.
4. Names are decoded glyph by glyph. Cairo subsets the font per file, so the
   glyph ids mean nothing across files; the outlines are stable, so `GLYPHS`
   keys each character by a hash of its path data. Anything that hash misses is
   not label text, which is how the plot title is skipped.
5. Names are then handed out one per parent, taken in order of distance. Plain
   nearest-node picks the wrong parent where two sit close together, and each
   parent carries exactly one name, so letting the confident matches settle
   first resolves the rest.

Re-run it whenever either SVG is regenerated:

```sh
python3 tools/pedigree_to_js.py
```

It prints a sanity line per figure: dam, sire, offspring, name and link counts,
plus how many offspring came out with both parents assigned. That last count is
the check that matters — it should stay near the total.

A new plot may use characters no existing one does. The script simply drops a
glyph it cannot place, so a name coming out short is the signal to add the
missing character to `GLYPHS`.

## Output format

Each output is a plain global, kept terse because it ships to every visitor:

```js
window.PEDIGREE = {                // PEDIGREE_GUPPY for the guppy design
  w, h,                            // viewBox, origin shifted to the bbox
  nodes: [[x, y, r, kind, id]],    // kind: 0 dam, 1 sire, 2 offspring
  links: [[parent, child]]         // indices into nodes
};
```

## Drawing side

`pedigree-figure.js` builds an SVG per panel and keeps the R plot's encoding:
teal circles for dams, orange squares for sires, black dots for offspring,
lines coloured by the parent they leave, everything sized by brood. A panel
names the dataset it wants in `data-ped`, so the same script serves both
species, and the two panels run independently. Name size and pointer slack are
taken as a fraction of the plot's viewBox, since the two designs were plotted
in boxes of different sizes and would otherwise not match on screen.

Two behaviours sit on top.

- **Reveal.** Lines are grouped per family and each group's transform origin is
  its parent, so a staggered scale-up makes each family bloom out of its
  parent. Families go largest brood first. The animation is a one-shot: once it
  has played, the script swaps `is-drawing` for `is-settled`, because a filled
  CSS animation would keep overriding the transforms the highlight needs.
- **Highlight.** Pointing at anyone dims the network and lights their immediate
  family. Since nearly every node is barely a pixel wide, picking is done by
  nearest-node search over pointer coordinates rather than per-element hit
  targets, with `getScreenCTM()` doing the screen-to-viewBox conversion so it
  survives any panel size. With no pointer, an ambient loop walks through
  random parents until a visitor takes over.

`prefers-reduced-motion` skips the reveal and the ambient loop; hover still
works.

# Figure background removal

`tools/figure_bg_transparent.py` prepares a slide-exported figure for the page.
Slide decks export on opaque white, which on the site's pale blue paper
(`#f2f6f9`) reads as a pasted-in rectangle no matter how the surrounding CSS is
styled. The script clears the matte instead of recolouring it, so the page
colour itself shows through the figure.

```sh
python3 tools/figure_bg_transparent.py assets/imprinting.png
```

Two details carry the result:

1. Distance from white is measured on the *darkest* of the three channels, so a
   saturated red or green block counts as content even though it is bright.
2. Only a narrow window near white becomes background: fully painted at 246 and
   below, fully clear at 252 and above, ramped in between. The ramp keeps
   anti-aliased type edges smooth, and the tight window keeps the pale grey
   chromosome bands, which run to about 240, from being read as background.

WebP input is written back as WebP: the colour is re-encoded lossily at quality
92 while the alpha channel is stored losslessly, which is what keeps a
print-resolution photographic figure like the phylogeny under a megabyte where
PNG would run to several.

JPEG input is written out as a PNG beside it, since JPEG has no alpha channel;
the original is left in place for you to delete once the new file is wired up.

It then crops to the alpha bounding box with a few pixels of padding, because
slide exports carry a wide empty margin that CSS would otherwise have to
absorb. The file is rewritten in place, so keep the original export elsewhere if
you may want to re-run with different thresholds.

`.figure-inset` in `styles.css` does the layout: floated left at 42% of the
column with no card or border, going full width below 700px.

# Combined rule graph figure

`tools/combine_rulegraphs.py` builds `assets/snakemake_rulegraphs.png`, the
single figure on the software page that carries both Snakemake workflows.

```sh
python3 tools/combine_rulegraphs.py
```

It reuses `whiten_to_alpha` and `trim` from the background-removal script, so
the panels sit on the page colour like every other figure, then does two things
of its own:

1. **Cuts the exported title off.** Each rule graph was exported with its own
   title, set at whatever size that export used, and the page caption names the
   workflows instead. There is no empty row to split title from graph, since
   the descenders run straight into the first rule box, so the split is made on
   width: the title spans most of the export and no row of the graph covers
   more than about a quarter of it. Rows wider than `TITLE_WIDTH` are title,
   and the graph starts at the first row that is not.
2. **Pastes the panels at native size, hung from the top.** Both exports came
   off the same renderer at the same scale, so leaving them unscaled is what
   keeps a rule box the same size in either graph; scaling them to a shared
   height would instead inflate whichever workflow has fewer steps.

Re-run it whenever either rule graph is re-exported. `.figure-wide` in
`styles.css` does the layout, capped at 620px and centred, because across the
full 900px column the rule boxes come out larger than the prose beside them.
