# Screenshots for a native iOS app

An XCUITest run taps through the app on a simulator of its own ("app-map iPhone 17") and takes
each module's screenshots. At every snap, lldb reads which views and view controllers are on
screen and where (UIKit, and the SwiftUI view a hosting controller shows), so `app-map crop`
can cut one picture per class for the popups. The app's own project isn't touched: the test
drives it by bundle id.

Needs: macOS with Xcode, the app built for the simulator (a Debug build, so lldb can attach).

## 1. Build the app for the simulator

```bash
xcodebuild -project App.xcodeproj -scheme App -sdk iphonesimulator -configuration Debug \
  -derivedDataPath build/app-map CODE_SIGNING_ALLOWED=NO build
```

- Follow the app's own README for generated files or secrets it needs first.
- If installing fails on an app extension ("Failed to create app extension placeholder"),
  remove the extensions you don't map from `PlugIns/`. For one you map (a share extension), sign
  it and then the app ad hoc, with the app group they share, so it can start:
  ```bash
  codesign -f -s - --entitlements groups.entitlements "App.app/PlugIns/Share.appex"
  codesign -f -s - --entitlements groups.entitlements App.app
  ```
  `groups.entitlements` lists the group from the target's `.entitlements` file under
  `com.apple.security.application-groups`.

## 2. Write the scenario

Start from `adapters/ios/example_scenario.swift`. One step per screen, in module order:

```swift
shots.step("timeline") {
    try shots.tapContaining("NetNewsWire Blog")   // a cell by part of its label
    shots.snap("timeline_01_feed")                // screenshot + every view, with its class
    try shots.tap("Mark All as Read")             // a button's label or identifier
    shots.snap("timeline_02_confirm")
    shots.tapOutside()                            // closes a popover or menu
}
```

| Helper | Does |
|---|---|
| `step("name") { … }` | runs a step; a failure is logged and the run goes on |
| `snap("module_nn_what")` | screenshot + `SHOT RECT` lines for every class of the map on screen |
| `describe("name")` | saves the screen's labels to `requests/<name>.tree`: read it to write the next taps |
| `tap("Label")`, `tapContaining("text")`, `tapCell(0)` | waits for the element, taps, settles |
| `answerAlert("Allow")` | answers a system prompt (notifications, paste) if one shows |
| `open("https://…")`, `other("com.apple.mobilesafari")` | opens a URL the system way; drives another app (to reach a share sheet) |
| `snap("name", process: "Share Extension")` | for an app extension: it runs in its own process, named by part of its path |
| `snap("name", shows: ["GeneralSettingsView"])` | names the SwiftUI screen on show: SwiftUI screens pushed inside one hosting controller have no view class of their own, so their crop is the visible SwiftUI area |
| `tapOutside()`, `back()`, `swipeUp()`, `swipeDown()`, `wait(2)` | |
| `report()` | the last line of the test |

- Pass `--app <path.app>` so every run starts from a fresh install: an app that restores its
  last screen otherwise starts wherever the previous run ended.
- A system prompt blocks the app until it's answered (a paste prompt can make every later tap
  time out): answer it right after the step that triggers it.
- Prefer content the app owns (its own blog, demo data) over live third-party content.

## 3. Run it

```bash
<skill>/scripts/app-map shots ios --bundle <bundle id> --map <map> --app <path.app> \
  <Scenario.swift> <out dir> [--minutes 20]
```

The first run builds the driver (a minute); each snap takes about 5 s (lldb attaches, reads
the views, detaches). `SHOT STEP FAILED` names a failed step; `<out>/xcodebuild.log` has the
test's own errors.

## 4. Use the pictures

As for Flutter ([screenshots-flutter.md](screenshots-flutter.md) §3): pick 2–5 per module into
`<map>/shots/<module>/` (at the screen's point size, e.g. 402 px wide), list them in the
frontmatter, then `scripts/app-map crop <out dir> <map>` and look through every crop (a wrong one goes in
`noCrop` in app-map.json).
