// app-map's Flutter adapter: drive the real app, take screenshots, and log where every class
// the map draws sits on screen. Copied into the app's integration_test/ by run_shots.sh, and
// listed in .git/info/exclude so it is never committed.
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

/// Drives the real app and takes screenshots, without the usual traps:
/// taps scroll their target into view first, waits poll for a widget instead
/// of guessing a delay, and a failed step is logged and skipped, so the
/// screenshots taken before it are still saved.
class AppMapShots {
  AppMapShots(this.tester, this.binding, {required this.diagramClasses});

  final WidgetTester tester;
  final IntegrationTestWidgetsFlutterBinding binding;

  /// Class names the map's diagrams draw; [snap] logs where each one is on screen.
  final Set<String> diagramClasses;

  /// Steps that failed, printed at the end. run_shots.sh reports them.
  final List<String> failures = <String>[];

  bool _surfaceReady = false;

  /// Pumps frames for [seconds] while timers and animations run.
  Future<void> wait(double seconds) async {
    const Duration frame = Duration(milliseconds: 250);
    final int frames = (seconds * 1000 / frame.inMilliseconds).ceil();
    for (int index = 0; index < frames; index++) {
      await tester.pump(frame);
    }
  }

  /// Waits until [finder] finds something, up to [timeout] seconds.
  /// Returns whether it appeared.
  Future<bool> waitFor(Finder finder, {double timeout = 30}) async {
    final int polls = (timeout * 4).ceil();
    for (int index = 0; index < polls; index++) {
      if (_found(finder)) return true;
      await tester.pump(const Duration(milliseconds: 250));
    }
    return _found(finder);
  }

  /// A `.first`/`.last` finder throws while nothing matches; that means "not yet".
  bool _found(Finder finder) {
    try {
      return finder.evaluate().isNotEmpty;
    } on StateError {
      return false;
    }
  }

  /// Text (plain or rich) on screen. [last] picks the last match, e.g. the
  /// shell header's "Back" over a page title with the same word.
  Finder text(String text, {bool last = false}) {
    final Finder all = find.text(text, findRichText: true);
    return last ? all.last : all.first;
  }

  /// Waits for [finder], scrolls it into view, taps it, then lets the screen
  /// settle for [settle] seconds. Throws when it never appears, which
  /// [step] turns into a logged failure.
  Future<void> tap(
    Finder finder, {
    String? label,
    double settle = 2,
    double timeout = 30,
  }) async {
    if (!await waitFor(finder, timeout: timeout)) {
      // Printing an empty `.first` finder throws, so name it by its label.
      throw StateError('not on screen after ${timeout}s: ${label ?? 'the finder'}');
    }
    await tester.ensureVisible(finder);
    await wait(0.5);
    await tester.tap(finder, warnIfMissed: false);
    await wait(settle);
  }

  /// [tap] on a text.
  Future<void> tapText(String label, {bool last = false, double settle = 2}) =>
      tap(text(label, last: last), label: '"$label"', settle: settle);

  /// Drags the innermost scrollable (or [within]) by [dy]: negative scrolls
  /// down the page.
  Future<void> scroll(double dy, {Finder? within}) async {
    await tester.drag(
      within ?? find.byType(Scrollable).last,
      Offset(0, dy),
      warnIfMissed: false,
    );
    await wait(1);
  }

  /// Saves a screenshot named [id] (the file becomes `<id>.png`).
  Future<void> shoot(String id, {double settle = 1}) async {
    if (!_surfaceReady) {
      await binding.convertFlutterSurfaceToImage();
      _surfaceReady = true;
    }
    await wait(settle);
    await binding.takeScreenshot(id);
  }

  /// Runs one named step. A failure is logged and the run goes on, so one
  /// missing widget never throws away the screenshots already taken.
  Future<void> step(String name, Future<void> Function() body) async {
    try {
      await body();
    } catch (error) {
      failures.add('$name: $error');
      debugPrint('SHOT STEP FAILED: $name: $error');
    }
  }

  /// Prints the summary run_shots.sh looks for.
  void report() {
    debugPrint(
      failures.isEmpty
          ? 'SHOTS DONE: all steps passed'
          : 'SHOTS DONE: ${failures.length} step(s) failed:\n${failures.join('\n')}',
    );
  }

  // ---- App map: where each diagram class is on screen -------------------------------

  /// Diagram classes seen whole (nothing covering them) in some shot so far.
  final Set<String> seenWhole = <String>{};

  static String typeName(Widget widget) {
    final String name = widget.runtimeType.toString();
    final int generic = name.indexOf('<');
    return generic < 0 ? name : name.substring(0, generic);
  }

  Finder get _drawn => find.byWidgetPredicate(
        (Widget widget) => diagramClasses.contains(typeName(widget)),
      );

  /// A finder for the widgets of one class, by name: no import of the class needed.
  Finder byTypeName(String name) =>
      find.byWidgetPredicate((Widget widget) => typeName(widget) == name);

  // A point shows [box] when its topmost hit is [box], inside it, or behind it (an
  // ancestor: [box] ignores taps). A hit in another branch (a panel, a dialog) covers it.
  bool _shows(RenderObject top, RenderBox box) {
    for (RenderObject? node = top; node != null; node = node.parent) {
      if (node == box) return true;
    }
    for (RenderObject? node = box.parent; node != null; node = node.parent) {
      if (node == top) return true;
    }
    return false;
  }

  /// How many of 5 points (centre and inset corners) of [rect] show [box].
  int _visiblePoints(RenderBox box, Rect rect) {
    final Rect inset = rect.deflate(rect.shortestSide < 16 ? rect.shortestSide / 4 : 4);
    final Size screen = tester.view.physicalSize / tester.view.devicePixelRatio;
    int hits = 0;
    for (final Offset point in <Offset>[
      inset.center, inset.topLeft, inset.topRight, inset.bottomLeft, inset.bottomRight,
    ]) {
      if (!(Offset.zero & screen).contains(point)) continue;
      final HitTestResult result = HitTestResult();
      WidgetsBinding.instance.hitTestInView(result, point, tester.view.viewId);
      final RenderObject? top =
          result.path.map((HitTestEntry entry) => entry.target).whereType<RenderObject>().firstOrNull;
      if (top != null && _shows(top, box)) hits++;
    }
    return hits;
  }

  /// Saves a screenshot named [id] and logs every diagram class on screen as
  /// `SHOT RECT <id> <Class> <left> <top> <width> <height> <visible points of 5>`,
  /// which crop_shots.py turns into one picture per class.
  Future<void> snap(String id) async {
    await shoot(id);
    for (final Element element in _drawn.evaluate()) {
      final RenderObject? box = element.renderObject;
      if (box is! RenderBox || !box.attached || !box.hasSize) continue;
      final Rect rect = box.localToGlobal(Offset.zero) & box.size;
      final int hits = _visiblePoints(box, rect);
      if (hits == 5) seenWhole.add(typeName(element.widget));
      debugPrint('SHOT RECT $id ${typeName(element.widget)} '
          '${rect.left.toStringAsFixed(1)} ${rect.top.toStringAsFixed(1)} '
          '${rect.width.toStringAsFixed(1)} ${rect.height.toStringAsFixed(1)} $hits');
    }
  }

  /// Scrolls each diagram class on this screen that no shot has shown whole into view
  /// and snaps it. Call it before leaving a screen.
  Future<void> revealRest(String prefix) async {
    final Set<String> pending = _drawn
        .evaluate()
        .map((Element element) => typeName(element.widget))
        .where((String name) => !seenWhole.contains(name))
        .toSet();
    for (final String name in pending) {
      if (seenWhole.contains(name)) continue;
      final List<Element> matches = byTypeName(name).evaluate().toList();
      if (matches.isEmpty) continue;
      await step('reveal $name', () async {
        await Scrollable.ensureVisible(matches.first, alignment: 0.1);
        await wait(1);
        await snap('${prefix}_reveal_$name');
      });
    }
  }
}
