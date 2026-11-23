// Run by run_shots.py inside the app with lldb (`expr -l swift`): every visible view, the view
// controller that owns it, its frame in window points, and how many of 5 points inside it
// reach it (or a view inside it) — fewer means something covers it.
import UIKit
var out = ""
var windows: [UIWindow] = []
for scene in UIApplication.shared.connectedScenes { if let windowScene = scene as? UIWindowScene { windows += windowScene.windows } }
// An app extension runs in a hosted scene the list above doesn't have: ask UIWindow itself.
if windows.isEmpty { windows = (UIWindow.perform(NSSelectorFromString("allWindowsIncludingInternalWindows:onlyVisibleWindows:"), with: nil, with: NSNumber(value: true))?.takeUnretainedValue() as? [UIWindow]) ?? [] }
do {
  for window in windows where !window.isHidden {
    out += "W \(window.bounds.width) \(window.bounds.height)\n"
    var stack: [UIView] = [window]
    while let view = stack.popLast() {
      if view.isHidden || view.alpha < 0.01 { continue }
      let r = view.convert(view.bounds, to: nil)
      var hits = 0
      for (x, y) in [(0.5, 0.5), (0.15, 0.15), (0.85, 0.15), (0.15, 0.85), (0.85, 0.85)] {
        let point = CGPoint(x: r.minX + r.width * x, y: r.minY + r.height * y)
        let hit = window.hitTest(point, with: nil)
        if hit == nil || hit!.isDescendant(of: view) || view.isDescendant(of: hit!) { hits += 1 }
      }
      var name = NSStringFromClass(type(of: view))
      if let owner = view.next as? UIViewController, owner.view === view { name += "|" + NSStringFromClass(type(of: owner)) }
      out += "V \(name) \(r.minX) \(r.minY) \(r.width) \(r.height) \(hits)\n"
      stack.append(contentsOf: view.subviews)
    }
  }
}
out as NSString
