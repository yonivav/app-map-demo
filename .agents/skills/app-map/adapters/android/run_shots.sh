#!/usr/bin/env bash
# Runs an App map screenshot scenario on an Android emulator of its own.
#
#   run_shots.sh <app module dir> <Scenario.kt> <out dir> [--variant Debug] [--minutes 20] [--real-app]
#
# <app module dir> is the Gradle module of the app (e.g. app/). The scenario is an
# instrumented test in package `appmap` (see example_scenario.kt); it and AppMapShots.kt are
# copied into the module's androidTest (listed in .git/info/exclude, never committed). The run
# uses the emulator "app-map_Pixel" (created on first use), installs the app and its test APK,
# runs the scenario with `am instrument`, and copies the screenshots and drive.log to <out dir>.
# --real-app runs it under the app's own Application instead of the project's test runner's
# (which often swaps in fake data or drops app-level setup such as an image loader).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
module="$(cd "${1:?app module dir}" && pwd)"; scenario="$(cd "$(dirname "${2:?scenario}")" && pwd)/$(basename "$2")"
out="${3:?out dir}"; shift 3
variant=Debug minutes=20 real_app=no
while [ $# -gt 0 ]; do
  case "$1" in
    --variant) variant="$2"; shift ;;
    --minutes) minutes="$2"; shift ;;
    --real-app) real_app=yes ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
sdk="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
adb="$sdk/platform-tools/adb"
if [ -z "${JAVA_HOME:-}" ] && [ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home" ]; then
  export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
fi
export ANDROID_HOME="$sdk"

# The Gradle project holding the module.
root="$module"; while [ ! -x "$root/gradlew" ] && [ "$root" != / ]; do root="$(dirname "$root")"; done
[ -x "$root/gradlew" ] || { echo "no gradlew above $module" >&2; exit 2; }
gradle_path=":$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]).replace(os.sep, ":"))' "$module" "$root")"

# 1. The helper and the scenario, in the module's androidTest, kept out of git.
dest="$module/src/androidTest/kotlin/appmap"
mkdir -p "$dest"
cp "$here/AppMapShots.kt" "$dest/AppMapShots.kt"
cp "$scenario" "$dest/AppMapScenario.kt"
if git -C "$module" rev-parse --git-dir >/dev/null 2>&1; then
  exclude="$(git -C "$module" rev-parse --path-format=absolute --git-common-dir)/info/exclude"
  entry="/$(git -C "$module" rev-parse --show-prefix)src/androidTest/kotlin/appmap/"
  grep -qxF "$entry" "$exclude" 2>/dev/null || echo "$entry" >>"$exclude"
fi

# 2. An emulator of its own.
avd=app-map_Pixel
serial=""
for device in $("$adb" devices | awk '/^emulator-/{print $1}'); do
  [ "$("$adb" -s "$device" emu avd name 2>/dev/null | head -1 | tr -d '\r')" = "$avd" ] && serial="$device"
done
if [ -z "$serial" ]; then
  if ! "$sdk/emulator/emulator" -list-avds | grep -qx "$avd"; then
    image="$(ls -d "$sdk"/system-images/android-*/google_apis/* 2>/dev/null | sort -V | tail -1)"
    [ -n "$image" ] || { echo "no google_apis system image in $sdk/system-images" >&2; exit 2; }
    package="system-images;$(echo "${image#"$sdk"/system-images/}" | tr / ';')"
    echo no | "$(ls "$sdk"/cmdline-tools/*/bin/avdmanager | head -1)" create avd -n "$avd" -k "$package" -d pixel_7 >/dev/null
  fi
  before="$("$adb" devices | awk '/^emulator-/{print $1}')"
  nohup "$sdk/emulator/emulator" -avd "$avd" -no-window -no-audio -no-boot-anim -no-snapshot-save >/dev/null 2>&1 &
  for _ in $(seq 90); do
    sleep 2
    serial="$(comm -13 <(echo "$before" | sort) <("$adb" devices | awk '/^emulator-/{print $1}' | sort) | head -1)"
    [ -n "$serial" ] && break
  done
fi
[ -n "$serial" ] || { echo "the emulator didn't start" >&2; exit 1; }
export ANDROID_SERIAL="$serial"
"$adb" wait-for-device
until [ "$("$adb" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do sleep 2; done
"$adb" shell settings put global window_animation_scale 0
"$adb" shell settings put global transition_animation_scale 0
"$adb" shell settings put global animator_duration_scale 0

# 3. Build, install, run.
echo "building $gradle_path ($variant)…"
init=()
if [ "$real_app" = yes ]; then
  cp "$here/AppMapRunner.kt" "$dest/AppMapRunner.kt"
  init=(-I "$here/app-map.init.gradle")
fi
(cd "$root" && ./gradlew -q ${init[@]+"${init[@]}"} "$gradle_path:assemble$variant" "$gradle_path:assemble${variant}AndroidTest")
outputs="$module/build/outputs/apk"
suffix="$(python3 -c 'import re,sys; print(re.sub(r"(?<!^)([A-Z])", r"-\1", sys.argv[1]).lower())' "$variant")"
app_apk="$(find "$outputs" -name "*-$suffix.apk" -not -path '*androidTest*' | head -1)"
test_apk="$(find "$outputs" -name "*-$suffix-androidTest.apk" | head -1)"
aapt="$(ls "$sdk"/build-tools/*/aapt | sort -V | tail -1)"
app_id="$("$aapt" dump badging "$app_apk" | sed -n "s/^package: name='\([^']*\)'.*/\1/p")"
"$adb" install -r -t "$app_apk" >/dev/null
"$adb" install -r -t "$test_apk" >/dev/null
test_id="$("$aapt" dump badging "$test_apk" | sed -n "s/^package: name='\([^']*\)'.*/\1/p")"
if [ "$real_app" = yes ]; then runner="$test_id/appmap.AppMapRunner"
else runner="$("$adb" shell pm list instrumentation | tr -d '\r' | grep "^instrumentation:$test_id/" | sed 's/^instrumentation:\([^ ]*\) .*/\1/' | head -1)"; fi
"$adb" shell pm clear "$app_id" >/dev/null
echo "running the scenario on $serial ($app_id)…"
"$adb" shell am instrument -w -e class appmap.AppMapScenario "$runner" >"$out.instrument.log" 2>&1 &
pid=$!
for _ in $(seq $((minutes * 30))); do kill -0 "$pid" 2>/dev/null || break; sleep 2; done
kill "$pid" 2>/dev/null || true

# 4. The screenshots and the log.
rm -rf "$out"; mkdir -p "$out"
"$adb" exec-out run-as "$app_id" tar c -C files app-map-shots | tar x -C "$out" --strip-components 1
mv "$out.instrument.log" "$out/instrument.log"
grep -E 'SHOT (STEP FAILED|DONE)' "$out/drive.log" || tail -20 "$out/instrument.log"
echo "$(ls "$out"/*.png 2>/dev/null | wc -l | tr -d ' ') screenshots in $out"
