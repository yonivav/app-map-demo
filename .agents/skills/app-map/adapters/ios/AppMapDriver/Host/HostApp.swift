// The UI tests need a host app to build against; the scenario drives the app under test by its
// bundle id, never this one.
import SwiftUI

@main
struct HostApp: App {
    var body: some Scene {
        WindowGroup { Text("App map driver") }
    }
}
