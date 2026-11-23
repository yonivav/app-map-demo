import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

/// Saves each screenshot `the app-map scenario` takes, to
/// `$SCREENSHOTS_DIR` or, when that isn't set, `build/screenshots`.
Future<void> main() => integrationDriver(
      onScreenshot: (String name, List<int> bytes,
          [Map<String, Object?>? args]) async {
        final String directory =
            Platform.environment['SCREENSHOTS_DIR'] ?? 'build/screenshots';
        final File file = File('$directory/$name.png');
        file.parent.createSync(recursive: true);
        file.writeAsBytesSync(bytes);
        return true;
      },
    );
