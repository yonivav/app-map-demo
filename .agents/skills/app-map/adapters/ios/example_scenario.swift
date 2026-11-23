import XCTest

/// One pass through every module of the map: a few `snap`s per screen, in module order.
/// Run it with `app-map shots ios --bundle <id> --map <map> [--app <.app>] <this file> <out>`.
final class AppMapScenario: XCTestCase {
    func testAppMap() {
        continueAfterFailure = true
        let shots = AppMapShots()
        shots.app.launch()
        shots.answerAlert("Allow")          // a first-run permission prompt, if any
        shots.wait(3)

        shots.step("home") {
            shots.snap("home_01_list")       // screenshot + every view on it, with its class
            shots.describe("home")           // labels on screen → requests/home.tree, for the next taps
        }
        shots.step("detail") {
            try shots.tapCell(0)
            shots.snap("detail_01_item")
            shots.swipeUp()
            shots.snap("detail_02_scrolled")
            shots.back()
        }
        shots.step("settings") {
            try shots.tap("Settings")        // a button's label or accessibility identifier
            shots.snap("settings_01_settings")
        }
        shots.report()
    }
}
