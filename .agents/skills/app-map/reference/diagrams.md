# Writing the diagrams

## Rendering rules (these broke before — don't change them)

- Each diagram's source lives in its own `<script type="text/plain" id="src-…">`, pointed at by a
  `<div class="out" data-src="src-…">`. Never `<pre class="mermaid">`: in HTML, `<<page>>`
  starts a tag and the source breaks.
- The page renders Mermaid itself (cdnjs `mermaid/10.9.1`, `theme: 'base'`, colors from the CSS
  tokens) and re-renders on theme change. Don't rely on a host's built-in Mermaid.
- Keep the first three lines (`<!doctype html>`, `<meta charset="utf-8">`, viewport): opened
  from disk without the charset, `→ · ◇` turn into garbage.
- Inside a source, write plain characters: `&`, not `&amp;` — entities reach Mermaid literally.
- No `:` inside a relation label (`"1:1 Support"` breaks the parse): `A ..> B : opens 1-to-1 support`.
- A sequence participant id can't be a Mermaid keyword (`end`, `loop`, `alt`, `opt`, `par`,
  `box`, `link`, `links`, `note`, `rect`, `critical`, `break`): use `participant Lnk as Links`.
- In a flowchart, a `subgraph` id must differ from every node id.
- `app-map verify` catches all of these.

## Class diagrams

- A box's first line is its role as a stereotype: `<<page>>`, `<<view-model>>`, `<<model>>`,
  `<<service>>`, `<<interface>>`, `<<enum>>`, `<<data>>`, `<<widget>>`, `<<atom>>`.
- A box with only a stereotype may stay on one line: `class HomeScreen { <<page>> }`. A box with a
  stereotype **and** members puts each on its own line — `class X { <<model>> foo() }` renders
  the tag as `&lt;&gt;`.
- Members: only the ones that explain the design — key fields, public methods, getters the view
  reads. One per line; group short related fields with ` · ` (`title · subtitle`). Write
  methods as `name(args)` and getters/fields as bare names, so the popup can find them.
- No types unless they matter (`phase : QaPhase`).
- Relations, each labelled where it helps — these match the pages' legends:
  - Logic: `A --> B : field` holds · `A o-- B : field` list of · `A ..> B : method()` uses ·
    `B <|-- A` extends · `I <|.. A` implements · `AVM ..> BPage : opens` opens a screen (add
    `<li><b>┄┄▷</b> uses · opens</li>` to the legend when you use it)
  - Screen: `A *-- B` contains · `A --> BModel` reads model · `Model ..> BModel : builds`
- In `A ..> B : method()`, the method is **B's** — the one A calls (the popup opens it on B).
  When A creates B (a model building a widget model), write `A ..> B : builds` without
  parentheses, or name A's factory method as a member of A's box instead.
- Named constructors: write them as members, `compact()` for `Header.compact` — the popup finds
  them. Private members (`_refresh()`) are fine when they're where the logic is.
- Class names must be the real names in the code (the popups and `app-map build` look them up).
  For a framework widget used as-is, name the real class and give it a stereotype that says
  what it is for: `class TextButton { <<Settings link>> }`.

## State machines

`stateDiagram-v2` with the enum's values as states. Label each transition with its trigger and
any timing (`after 1.5 s`, `+1 word / 50 ms`). Only for a real enum/phase with transitions.

## Sequences

- `actor User`, then `participant Short as RealClassName` for each class, in call order.
- 8–15 messages: the module's main flow as a user would describe it ("open a wonder's details").
- A call's label names the method called on the receiver (`getData()`), so it opens in the
  popup. Replies (`-->>`) describe the result in words — including a view-model telling its
  page to rebuild (`VM-->>Page: rebuilds with the new cards`), since `notify()` is the VM's own
  method, not the page's.
- One `Note over` for a rule the flow depends on ("stops here if the data is already loaded").

## Captions and text

- One sentence under each `<h2>`, in plain words, naming the main idea — not listing boxes.
- "What it does": what the user gets and the rules the code enforces, with the real numbers.
- Key files: real paths (folders end with `/`), each with 2–5 words on what it holds.
