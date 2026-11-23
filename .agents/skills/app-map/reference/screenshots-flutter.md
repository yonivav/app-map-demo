# Screenshots for a Flutter app

One `flutter drive` run on an iOS simulator (375×812pt, like most designs) takes each module's
screenshots and logs where every page and widget the diagrams draw sits on screen. Two scripts
then crop one picture per class for the popups.

Needs: macOS with Xcode, the app building for the iOS simulator, `integration_test` in the app's
dev dependencies.

## 1. Write the scenario

Start from `adapters/flutter/example_scenario.dart`. Fill `diagramClasses` with every class name
in the map's class diagrams (any non-widget names are simply never found on screen). Then add
one step per screen, in module order:

```dart
await shots.step('home', () async {
  await shots.tapText('Home');
  await shots.snap('home_01_carousel');      // screenshot + where every diagram widget is
  await shots.scroll(-700);
  await shots.snap('home_02_scrolled');
  await shots.revealRest('home');        // scroll each widget not yet seen whole into view
});
```

| Helper | Does |
|---|---|
| `step('name', () async {…})` | runs a step; a failure is logged and the run goes on |
| `snap('module_nn_what')` | screenshot + `SHOT RECT` lines for every diagram class on screen |
| `revealRest('prefix')` | before leaving a screen: scrolls each widget not yet seen whole into view and snaps it |
| `tapText('Label')`, `tap(finder)` | waits, scrolls into view, taps, settles |
| `byTypeName('MyWidget')` | a finder by class name, no import needed |
| `waitFor(finder, timeout: 60)` | for slow things (network, video), instead of a fixed wait |
| `scroll(-400)` | scrolls the innermost list down 400pt |
| `report()` | the last line of the test |

- Name shots `<module>_<nn>_<what>` so they sort in flow order.
- Get past first-run dialogs and sign-in with test-only state in the scenario (e.g. set the
  app's own "onboarding done" flag), never by editing app code.
- Put a step that can leave the app (an external link, a share sheet) last: a run that loses
  the app loses every screenshot.
- First-run screens (an intro) need a fresh install: `xcrun simctl uninstall <udid> <bundle id>`
  before the run.
- A native launch screen is drawn before Flutter starts, so `snap` can't see it. After the run,
  capture it from the host: `xcrun simctl terminate <udid> <bundle id>; xcrun simctl launch
  <udid> <bundle id>; sleep 0.5; xcrun simctl io <udid> screenshot splash.png`.

## 2. Run it

```bash
<skill>/scripts/app-map shots <app dir> <scenario.dart> <out dir> [--minutes 25]
```

It uses a simulator of its own (`app-map iPhone 11 Pro`), copies the helper, driver and scenario
into the app (listed in `.git/info/exclude`, never committed) and keeps the screenshots,
`small/` copies (375×812) and `drive.log` in `<out dir>`. `SHOT STEP FAILED` names a failed
step — fix that step and run again. Look at every `small/` image before using it.

## 3. Use the pictures

- **Module screenshots**: pick 2–5 per module from `small/`, save as
  `<map>/shots/<module>/NN_name.jpg` (`sips -s format jpeg -s formatOptions 70 in.png --out out.jpg`)
  and list them under `screenshots:` in the module's frontmatter (the first one is its overview card).
- **Popup crops**: `scripts/app-map crop <out dir> <map>` crops each class from its best
  shot (nothing covering it, then the largest) into `<map>/shots/code/<Class>.jpg` and re-indexes.
  Look through the crops: one that shows something wrong (a blank placeholder, a widget under a
  dialog) goes in `noCrop` in app-map.json, so no run brings it back — a missing picture beats a
  wrong one.
