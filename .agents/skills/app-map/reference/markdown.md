# The map's Markdown sources

The map is its Markdown: `index.md` plus one `<module>.md` per module, committed next to the
code. GitHub shows them as they are (it renders Mermaid). `app-map build` turns them into the
clickable site next to them: `<module>.html`, `index.html`, `code/`, `code-popup.js`. Never edit
the `.html` files: the next build overwrites them.

## A module file

```markdown
---
title: Home Module                  # the page's <h1>
sub: "A looping carousel of the…"   # one line under it (the "← App map" link is added)
card_title: Home                    # the overview card
card: Carousel of the eight wonders
card_image: shots/home/02_next.jpg  # optional; default is the first screenshot
screenshots:                        # optional; shown first, in this order
  - file: shots/home/01_carousel.jpg
    caption: A wonder in the carousel
---

## What it does
Plain paragraphs. Inline `code`, **bold** and [links](other.html) work.

## Logic · class diagram {#classes}
Caption: the first paragraph(s) before the diagram.

```mermaid
classDiagram
  …
```

- `──▷` holds          ← a list after the diagram is its legend: `symbol` meaning
- `┄┄▷` uses

## Key files {#files}
- `lib/ui/screens/home/wonders_home_screen.dart` · carousel   ← a list in a section without a diagram
```

- `## Title · label`: the label is the small grey text after the title (`class diagram`,
  `sequence`). `{#id}` at the end sets the section's anchor (default: from the title); keep
  anchors stable, other pages and popups link to them.
- One diagram per section. Sections appear in file order, after the screenshots.
- `## Key files` lists the paths `app-map changes` watches for new classes: list folders
  (ending in `/`) and files.

## index.md

```markdown
---
title: My App App Map
sub: How the app works, one module at a time · **tap a module or a box** to open its map
modules: [launch, onboarding, home]      # module files, in card order
links:                                   # per section anchor: flowchart node id → module
  screens: {Splash: launch, Home: home}
---

## Screens · how the user moves
…a flowchart, its legend…
```

The overview's "Modules" cards (from each module's `card_*` and first screenshot) and its
"Find in the map" search are generated; everything else comes from the sections.

## app-map.json

```json
{
  "repo": "..",                       // the app's repo, relative to the map (default: git root)
  "sourceUrl": "https://github.com/o/r/blob/<commit>",   // popups link here instead of the editor
  "external": ["TextButton", "OS"],   // names drawn on purpose that aren't in the code
  "exclude": ["Mac"],                 // repo folders to leave out, e.g. another platform's target
  "noCrop": ["ScrollBar"],            // classes whose best screenshot still shows them wrong
  "exclude": ["Mac"],                 // repo folders to leave out, e.g. another platform's target
  "noCrop": ["ScrollBar"],            // classes whose best screenshot still shows them wrong
  "synced": {"commit": "…", "date": "…", "uncommitted": {…}}   // written by `app-map sync`:
                                      // the commit, and code it followed that wasn't committed yet
}
```
