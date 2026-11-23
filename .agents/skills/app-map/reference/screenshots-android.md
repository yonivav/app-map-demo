# Screenshots for a native Android app

An instrumented test taps through the app on an emulator of its own ("app-map_Pixel") and
takes each module's screenshots. At every snap it logs where each class of the map sits on
screen: Activities, Fragments and Views by class name, and `@Composable` functions by name,
from Compose's own inspector data (what Android Studio's Layout Inspector reads). `app-map crop`
then cuts one picture per class for the popups.

Needs: the Android SDK with an emulator system image, a JDK (Android Studio's is found), and
the app's module building with Gradle. For Compose, a debug build with `ui-tooling` (most apps
have `debugImplementation("androidx.compose.ui:ui-tooling")`; add it if missing).

## 1. Write the scenario

Start from `adapters/android/example_scenario.kt`: a JUnit test in package `appmap` that
launches the app's activity with `createAndroidComposeRule` (or `ActivityScenarioRule`), and
calls `AppMapShots.enable()` in `init`, before the activity starts. One step per screen:

```kotlin
shots.step("bookmarks") {
    compose.onNodeWithText("Saved").performClick()
    settle()
    shots.snap("bookmarks_01_saved")   // screenshot + every class of the map on screen
}
```

| Helper | Does |
|---|---|
| `AppMapShots(listOf(…))` | the classes the map draws; names never on screen are simply not found |
| `step("name") { … }` | runs a step; a failure is logged and the run goes on |
| `snap("module_nn_what")` | screenshot + `SHOT RECT` lines (dp) for every class of the map on screen |
| `report()` | the last line of the test |

Navigate with the app's own test tools: Compose test (`onNodeWithText`, `onNodeWithTag`,
`performClick`, `performTextInput`), Espresso (`pressBack`, `closeSoftKeyboard`).

- Prefer `--real-app` (below): the scenario then runs under the app's own Application, with
  its real dependency injection, data and image loading. A project's test runner often swaps in
  a test Application with fake data (empty search results) and without app-level setup (an image
  loader that decodes SVG icons). Without it, a Hilt app needs `@HiltAndroidTest`,
  `HiltAndroidRule` (order 0) and `hiltRule.inject()`, like its other instrumented tests.
- Wait for the first data load before the first snap (e.g. `compose.waitUntil { … }` until a
  loading indicator is gone), so screenshots don't catch a spinner.
- Images loaded from the network may not arrive in time: wait for them (`Thread.sleep`) before
  the snap; a crop that still shows a placeholder goes in `noCrop` in app-map.json.

## 2. Run it

```bash
<skill>/scripts/app-map shots android <app module dir> <Scenario.kt> <out dir> [--variant DemoDebug] [--real-app]
```

It copies `AppMapShots.kt` and the scenario into the module's `src/androidTest/kotlin/appmap/`
(listed in `.git/info/exclude`, never committed), starts the emulator (creating it on first
use), builds and installs the app and its test APK, runs the scenario with `am instrument`
(not Gradle's task, which uninstalls the app and its screenshots) and copies the screenshots
and `drive.log` to `<out dir>`. `instrument.log` has the test's own output. `--real-app` adds
`AppMapRunner` (a plain `AndroidJUnitRunner`) and, for that build only, points the module's test
runner at it with a Gradle init script; the project's build files aren't touched.

## 3. Use the pictures

As for Flutter ([screenshots-flutter.md](screenshots-flutter.md) §3): pick 2–5 per module into
`<map>/shots/<module>/` (at the screen's dp size, e.g. 411 px wide), list them in the
frontmatter, then `scripts/app-map crop <out dir> <map>` and look through every crop (a wrong one goes in
`noCrop` in app-map.json).
