// app-map screenshot scenario. Copy it, replace the app import and the steps, and run it with
// `app-map shots <app dir> <this file> <out dir>`.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:my_app/main.dart' as app; // ← the app's entry point

import 'app_map_shots.dart';

/// Every class name in the map's class diagrams. Non-widgets are simply never on screen.
const Set<String> diagramClasses = <String>{
  'HomeScreen',
  'ItemCard',
  // …
};

void main() {
  final IntegrationTestWidgetsFlutterBinding binding =
      IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('app map', (WidgetTester tester) async {
    final AppMapShots shots = AppMapShots(
      tester,
      binding,
      diagramClasses: diagramClasses,
    );

    app.main();
    await shots.step('launch', () async {
      await shots.waitFor(shots.byTypeName('SplashPage'), timeout: 30);
      await shots.snap('launch_01_splash');
    });
    await shots.wait(5);

    await shots.step('home', () async {
      await shots.waitFor(shots.byTypeName('HomeScreen'));
      await shots.snap('home_01_top');
      await shots.scroll(-700);
      await shots.snap('home_02_scrolled');
      await shots.revealRest('home');
    });

    await shots.step('details', () async {
      await shots.tap(shots.byTypeName('ItemCard').first, label: 'first card');
      await shots.snap('details_01_open');
      await shots.revealRest('details');
    });

    shots.report();
  });
}
