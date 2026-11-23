// App map screenshots for an iOS app, driven with XCUITest by bundle id: any installed app,
// no change to its project. At each snap the test asks the host (run_shots.py) to take the
// screenshot and to read, with lldb, which views and view controllers are on screen and where.
import XCTest

final class AppMapShots {
    let app: XCUIApplication
    private let requests: URL
    private var failed: [String] = []
    private var shots = 0

    init() {
        let environment = ProcessInfo.processInfo.environment
        app = XCUIApplication(bundleIdentifier: environment["APP_MAP_BUNDLE"] ?? "")
        requests = URL(fileURLWithPath: environment["APP_MAP_OUT"] ?? NSTemporaryDirectory())
            .appendingPathComponent("requests")
        try? FileManager.default.createDirectory(at: requests, withIntermediateDirectories: true)
    }

    /// Runs one step of the scenario; a failure is logged and the run goes on.
    func step(_ name: String, _ block: () throws -> Void) {
        do {
            try block()
        } catch {
            fail(name, "\(error)")
        }
    }

    /// A screenshot, and where every view and view controller of the app sits on it. `process`
    /// reads another process instead, by part of its executable's path: an app extension (a
    /// share sheet, a widget's configuration) runs in a process of its own. `shows` names the
    /// SwiftUI views filling the screen: SwiftUI screens pushed inside one hosting controller
    /// have no view class of their own, so the crop takes the visible SwiftUI area for them.
    func snap(_ name: String, process: String? = nil, shows: [String] = []) {
        Thread.sleep(forTimeInterval: 1.0)
        let request = requests.appendingPathComponent(name)
        let done = requests.appendingPathComponent(name + ".done")
        try? Data(((process ?? "") + "\n" + shows.joined(separator: ",")).utf8).write(to: request)
        let deadline = Date().addingTimeInterval(120)
        while !FileManager.default.fileExists(atPath: done.path), Date() < deadline {
            Thread.sleep(forTimeInterval: 0.3)
        }
        shots += 1
    }

    /// Taps the first element with this label or identifier (a button, a cell, a tab, text).
    func tap(_ label: String, timeout: TimeInterval = 15) throws {
        try tap(NSPredicate(format: "label == %@ OR identifier == %@", label, label), named: label, timeout: timeout)
    }

    /// Taps the first element whose label contains this text.
    func tapContaining(_ text: String, timeout: TimeInterval = 15) throws {
        try tap(NSPredicate(format: "label CONTAINS[c] %@", text), named: text, timeout: timeout)
    }

    /// Taps a cell of the visible list, by position.
    func tapCell(_ index: Int, timeout: TimeInterval = 15) throws {
        let cell = app.cells.element(boundBy: index)
        guard cell.waitForExistence(timeout: timeout), cell.isHittable else { throw Missing("cell \(index)") }
        cell.tap()
        settle()
    }

    /// Answers a system alert (notifications, tracking…) if one is showing.
    func answerAlert(_ button: String = "Allow") {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let choice = springboard.alerts.buttons[button]
        if choice.waitForExistence(timeout: 3) { choice.tap(); settle() }
    }

    /// Saves what's on screen (labels, identifiers, types) to requests/<name>.tree, for writing
    /// the next taps of a scenario.
    func describe(_ name: String, of other: XCUIApplication? = nil) {
        let tree = (other ?? app).debugDescription
        try? Data(tree.utf8).write(to: requests.appendingPathComponent(name + ".tree"))
    }

    /// Dismisses a popover or menu by tapping the top edge of the screen.
    func tapOutside() {
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.07)).tap()
        settle()
    }

    /// Opens a URL the way the system does (a web page in Safari, a deep link in its app).
    func open(_ url: String) {
        XCUIDevice.shared.system.open(URL(string: url)!)
        settle()
    }

    /// Another app on the device, e.g. Safari to reach the app's share extension.
    func other(_ bundleIdentifier: String) -> XCUIApplication {
        XCUIApplication(bundleIdentifier: bundleIdentifier)
    }

    func swipeUp() { app.swipeUp(); settle() }
    func swipeDown() { app.swipeDown(); settle() }
    /// The back button of the screen on top (a sheet's own navigation bar, not the one under it).
    func back() {
        let button = app.navigationBars.buttons.matching(identifier: "BackButton").allElementsBoundByIndex.last(where: { $0.isHittable })
            ?? app.navigationBars.buttons.element(boundBy: 0)
        button.tap()
        settle()
    }
    func wait(_ seconds: TimeInterval) { Thread.sleep(forTimeInterval: seconds) }

    /// The last line of the scenario: what ran and what didn't.
    func report() {
        let line = "SHOT DONE \(shots) shots, \(failed.count) failed step(s)"
            + (failed.isEmpty ? "" : ": " + failed.joined(separator: ", "))
        try? Data((line + "\n").utf8).write(to: requests.appendingPathComponent("report"))
    }

    private func fail(_ name: String, _ reason: String) {
        failed.append(name)
        let line = "SHOT STEP FAILED: \(name): \(reason)\n"
        let file = requests.appendingPathComponent("failures")
        let old = (try? String(contentsOf: file, encoding: .utf8)) ?? ""
        try? (old + line).write(to: file, atomically: true, encoding: .utf8)
    }

    private func tap(_ predicate: NSPredicate, named name: String, timeout: TimeInterval) throws {
        let element = app.descendants(matching: .any).matching(predicate).firstMatch
        guard find(element, timeout: timeout) else { throw Missing(name) }
        if !element.isHittable { scrollTo(element) }
        element.tap()
        settle()
    }

    /// Waits for the element; if it isn't there, scrolls down to it (a lazy list only has the
    /// rows on screen).
    private func find(_ element: XCUIElement, timeout: TimeInterval) -> Bool {
        if element.waitForExistence(timeout: min(timeout, 4)) { return true }
        for _ in 0..<6 {
            app.swipeUp()
            if element.waitForExistence(timeout: 1) { return true }
        }
        return element.waitForExistence(timeout: max(timeout - 4, 1))
    }

    private func scrollTo(_ element: XCUIElement) {
        for _ in 0..<8 where !element.isHittable { app.swipeUp() }
    }

    private func settle() { Thread.sleep(forTimeInterval: 1.2) }

    struct Missing: Error, CustomStringConvertible {
        let label: String
        init(_ label: String) { self.label = label }
        var description: String { "no element \"\(label)\" on screen" }
    }
}
