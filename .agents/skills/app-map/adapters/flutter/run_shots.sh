#!/usr/bin/env bash
# Runs an app-map screenshot scenario on an iOS simulator of its own (375x812pt, iPhone 11 Pro)
# and keeps the screenshots plus the SHOT RECT log that crop_shots.py reads.
#
# Usage: run_shots.sh <flutter app dir> <scenario.dart> <out dir> [--minutes N] [--device NAME]
set -uo pipefail

appdir="$(cd "${1:?usage: run_shots.sh <app dir> <scenario.dart> <out dir>}" && pwd)"
scenario="${2:?scenario.dart}"
out="${3:?out dir}"
shift 3
minutes=20 model="iPhone 11 Pro"
while [ $# -gt 0 ]; do
  case "$1" in
    --minutes) minutes="$2"; shift ;;
    --device) model="$2"; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
here="$(cd "$(dirname "$0")" && pwd)"
[ -f "$appdir/pubspec.yaml" ] || { echo "No Flutter app at $appdir" >&2; exit 2; }
[ -f "$scenario" ] || { echo "No scenario: $scenario" >&2; exit 2; }

# 1. A simulator of its own, so other work on the machine never shares the device.
name="app-map $model"
udid="$(xcrun simctl list devices -j | python3 -c "
import json, sys
for devs in json.load(sys.stdin)['devices'].values():
    for d in devs:
        if d['name'] == sys.argv[1] and d.get('isAvailable', True):
            print(d['udid']); sys.exit()" "$name")"
if [ -z "$udid" ]; then
  runtime="$(xcrun simctl list runtimes -j | python3 -c "
import json, sys
ios = [r for r in json.load(sys.stdin)['runtimes'] if r['platform'] == 'iOS' and r['isAvailable']]
print(sorted(ios, key=lambda r: [int(x) for x in r['version'].split('.')])[-1]['identifier'])")"
  udid="$(xcrun simctl create "$name" "com.apple.CoreSimulator.SimDeviceType.${model// /-}" "$runtime")" ||
    { echo "Could not create simulator $name" >&2; exit 1; }
fi
xcrun simctl boot "$udid" 2>/dev/null || true
xcrun simctl bootstatus "$udid" -b >/dev/null
for _ in $(seq 1 24); do flutter devices 2>/dev/null | grep -q "$udid" && break; sleep 5; done
echo "Simulator: $name ($udid)"

# 2. The helper, driver and scenario go into the app, kept out of git.
mkdir -p "$appdir/integration_test" "$appdir/test_driver"
cp "$here/app_map_shots.dart" "$appdir/integration_test/app_map_shots.dart"
cp "$here/app_map_driver.dart" "$appdir/test_driver/app_map_driver.dart"
cp "$scenario" "$appdir/integration_test/app_map_scenario_test.dart"
if git -C "$appdir" rev-parse --git-dir >/dev/null 2>&1; then
  exclude="$(git -C "$appdir" rev-parse --path-format=absolute --git-common-dir)/info/exclude"
  prefix="$(git -C "$appdir" rev-parse --show-prefix)"
  for f in integration_test/app_map_shots.dart integration_test/app_map_scenario_test.dart \
           test_driver/app_map_driver.dart; do
    grep -qxF "$prefix$f" "$exclude" 2>/dev/null || echo "$prefix$f" >>"$exclude"
  done
fi

# 3. Run it, and stop it after the time limit (macOS has no `timeout`).
mkdir -p "$out/small"
out="$(cd "$out" && pwd)"
echo "Running (up to $minutes min). Log: $out/drive.log"
( cd "$appdir" && SCREENSHOTS_DIR="$out" exec flutter drive -d "$udid" \
    --driver test_driver/app_map_driver.dart \
    --target integration_test/app_map_scenario_test.dart ) >"$out/drive.log" 2>&1 &
pid=$!
( sleep $(( minutes * 60 )); kill "$pid" 2>/dev/null && echo "STOPPED: over $minutes min" >>"$out/drive.log" ) \
  </dev/null >/dev/null 2>&1 &
watchdog=$!
disown "$watchdog" 2>/dev/null
wait "$pid"; status=$?
pkill -P "$watchdog" 2>/dev/null; kill "$watchdog" 2>/dev/null

# 4. Screen-size copies (375x812) for module pages, and a short report.
shopt -s nullglob
for f in "$out"/*.png; do sips -Z 812 "$f" --out "$out/small/$(basename "$f")" >/dev/null; done
pngs=("$out"/*.png)
echo "Screenshots: ${#pngs[@]} in $out"
grep -E 'SHOT STEP FAILED|SHOTS DONE|STOPPED:|Some tests failed' "$out/drive.log" | head -20
echo "Rects logged: $(grep -c 'SHOT RECT' "$out/drive.log")"
[ $status -eq 0 ] || echo "flutter drive exited with $status (see drive.log)"
[ ${#pngs[@]} -gt 0 ]
