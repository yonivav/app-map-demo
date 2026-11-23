---
name: app-map
description: >
  Builds and keeps current an "App map" of a mobile app repo (Flutter, native iOS, native
  Android): Markdown UML pages per module, built into a clickable site where every class, member
  and arrow opens its real source and widgets show a crop from the running app. Use when the user
  asks for an app map, architecture map, UML of the app, a visual tour of a codebase or
  onboarding docs, or to update the map after code changes ("update the app map", "is the map
  current").
license: MIT
compatibility: Flutter/Dart, native iOS (Swift/Objective-C) or native Android (Kotlin/Java) repos. Needs Python 3.9+ and git; Dart SDK recommended for Flutter; Chrome for verify; for screenshots, macOS + Xcode (Flutter, iOS) or the Android SDK (Android).
---

# App map

The map's source of truth is Markdown in the repo, default `docs/app-map/`: `index.md` and one
`<module>.md` per module ([reference/markdown.md](reference/markdown.md)). GitHub shows them as
they are. `app-map build` turns them into the clickable site next to them. You write and update
the Markdown; the scripts do everything mechanical.

`scripts/app-map` (in this skill's folder) is the only command; it sets up its own environment.
Run `scripts/app-map` with no arguments for the list.

**First, look for an existing map** (`docs/app-map/index.md`, or another folder the user names):
- found → **Update** (below). Never rewrite a page that exists: the map's choices are the
  user's; change only what the code changed.
- an older map of `.html` pages without `.md` → `app-map convert <map>` turns it into Markdown
  sources (the rebuilt pages are identical); then Update.
- none → **First build**.

## First build

### 1. Find the modules

Read the entry point, router/route table and top-level feature folders, then list modules the way
a user names the app's areas: launch/splash, onboarding, the navigation shell and menu, each main
tab or feature, cross-cutting areas a user notices (notifications, settings, sign-in). 6–12.
- Split only where the user sees separate areas (a tab, a menu entry, a top-level route), never
  by code size: a detail screen opened from one area belongs to that area's page.
- Name each with the app's own word for it (tab label or route name), kebab-case.
- A screen used by several modules lives on the page of the module that owns it.
- Tell the user the list before writing pages.

### 2. Write each module

Create the folder with `app-map.json` (`{}` is enough when the map is inside the repo; see
reference/markdown.md for `repo`, `sourceUrl`, `external`). Copy `assets/module.md` to
`<map>/<module>.md` per module and `assets/index.md` to `<map>/index.md`.

Start each module from the facts, then read:

```bash
scripts/app-map facts <map> HomeScreen WondersLogic SettingsLogic
scripts/app-map facts <map> --dir lib/ui/screens/home       # every class in a folder
```

`facts` lists each class's role, parents and conformances; for Dart with the Dart SDK also what
it **builds** and **uses**. Use it as a checklist, then read every file end to end: it can't see
framework widgets that carry meaning, or UI built from data (follow a component registry by
hand). **Diagram what the code does, never what names suggest.**

| Section | Contains |
|---|---|
| What it does | 3–6 plain sentences: what the user gets, the rules with their real numbers |
| Logic · class diagram | page → view-model → model, the services it calls, the data they hold |
| Screen · widget composition | the widgets/views the page builds and the models they read |
| … · state machine | only for a real phase/state enum with transitions |
| … · sequence | the module's main user flow, 8–15 messages, titled as a user would say it |
| Key files | one line per important file or folder: path · what it holds |

Drop a section that doesn't apply; never add filler. Mermaid rules and pitfalls:
[reference/diagrams.md](reference/diagrams.md) — read it before the first diagram.

The overview (`index.md`): module order, a **Screens** flowchart (where the app opens, how the
user moves; one subgraph per module) and a **Services** flowchart (services shared by two or
more modules, 12–20 service nodes, arrows labelled with the method), with `links` so tapping a
box opens its module.

### 3. Build, verify, sync

```bash
scripts/app-map build <map>     # pages, code popups, search
scripts/app-map verify <map>    # headless render + checks
scripts/app-map sync <map>      # record the commit the map now describes
```

`verify` fails (✗) on a diagram that doesn't render, a `{{placeholder}}` or a Mermaid pitfall,
and lists (?) names that match nothing in the code: fix stale ones, keep deliberate descriptions
(a widget's role, like `logo`). `build` prints `not found:` for drawn names with no declaration:
framework classes and actors go in `external` in app-map.json; anything else is a typo. Then
check every number in the text against its constant in the code.

### 4. Screenshots

Take them whenever Xcode (Flutter, iOS) or the Android SDK (Android) is installed: no simulator
needs to be running, the scenario creates and boots its own. Follow the platform's guide:
[Flutter](reference/screenshots-flutter.md), [iOS](reference/screenshots-ios.md),
[Android](reference/screenshots-android.md). Pick module screenshots into
`<map>/shots/<module>/`, then `app-map crop` cuts a picture for every page and widget. Visit
every screen the diagrams name, and show states before changing them (an empty list before
adding to it). `crop` ends with **no picture yet for …**: add steps for those; leave out only
what never shows on its own.

## Update

```bash
scripts/app-map changes <map>
```

It compares the code with the commit the map was synced to and lists, per module: classes the
page draws whose file changed (**review**), names that no longer exist (**fix**), and new classes
in the module's key files that no page draws (**consider**). For each listed module:
- Read the changed code. Edit only what it changed in that module's `.md`: a renamed method, a
  new service, a new screen, a number in the text. Leave every other line as it is.
- A new area of the app → a new module file and a card in `index.md`.
- Screens that look different → rerun the screenshot scenario for them and `app-map crop`.

Then `build`, `verify`, `sync`. Commit the Markdown and the built site with the code change.

To keep the map current without asking (offer it at the hand-over of a first build):
[reference/automatic.md](reference/automatic.md).

## Code → map

- In the site: every popup shows where else the class appears; the overview's **Find in the
  map** box takes a class or file name.
- In the terminal: `scripts/app-map where <map> <Class or path/to/file.dart>`.

## Hand over

Tell the user where the map is: the Markdown on GitHub, and `<map>/index.html` opened in a
browser (it loads Mermaid and fonts from the web). Mention modules without screenshots and
anything `build`/`verify` left for them to decide.
