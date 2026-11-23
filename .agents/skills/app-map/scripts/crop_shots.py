"""Crops every page and widget the App map draws out of a shots run.

Usage: python3 crop_shots.py <shots run dir> <out dir> [<map dir>]
Reads the `SHOT RECT <shot> <Type> <l> <t> <w> <h> <hits>` lines a screenshot adapter logs to
drive.log, picks the best view of each type (uncovered and fully on screen first, then clearly
larger, then nearest the middle of the screen) and saves it as <out dir>/<Type>.jpg at 2x. Rects are in the screen's logical units (points, dp):
`SHOT SCREEN <w> <h>` in the log gives the screen's size in them (default 375×812, the Flutter
adapter's iPhone).
"""
import json
import math
import os
import re
import sys

from PIL import Image

SCREEN_W, SCREEN_H = 375.0, 812.0
PAD = 6.0
OUT_SCALE = 2.0
MIN_SIDE = 12.0

run_dir, out_dir = sys.argv[1], sys.argv[2]
map_dir = sys.argv[3] if len(sys.argv) > 3 else None
UI_STEREOTYPES = ('page', 'widget', 'modal', 'dialog', 'screen', 'view', 'cell', 'split view', 'sheet')
line = re.compile(r'SHOT RECT (\S+) (\S+) (-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)(?: (\d))?')
best = {}
with open(os.path.join(run_dir, 'drive.log'), errors='replace') as log:
    text = log.read()
screen = re.search(r'SHOT SCREEN ([\d.]+) ([\d.]+)', text)
if screen:
    SCREEN_W, SCREEN_H = float(screen.group(1)), float(screen.group(2))
for match in line.finditer(text):
    shot, name = match.group(1), match.group(2)
    left, top, width, height = (float(value) for value in match.groups()[2:6])
    # Points of 5 that hit the widget: fewer means something covers part of it.
    hits = int(match.group(7) or 0)
    if match.group(7) is not None and hits == 0:
        continue
    if not os.path.exists(os.path.join(run_dir, shot + '.png')):
        continue
    right, bottom = min(left + width, SCREEN_W), min(top + height, SCREEN_H)
    left, top = max(left, 0.0), max(top, 0.0)
    if right - left < MIN_SIDE or bottom - top < MIN_SIDE:
        continue
    visible = (right - left) * (bottom - top) / (width * height)
    # Bigger wins only when it's clearly bigger (1.5×); among copies of about the same size, the
    # one nearest the middle of the screen, away from the bars at its edges.
    size = int(math.log((right - left) * (bottom - top), 1.5))
    middle = -abs((top + bottom) / 2 - SCREEN_H / 2)
    score = (hits, visible >= 0.95, size, middle)
    if name not in best or score > best[name][0]:
        best[name] = (score, shot, (left, top, right, bottom))

# "noCrop" in the map's app-map.json: classes whose best shot still shows them wrong (a sliver,
# a blank placeholder), kept out on every run.
skip = set()
if map_dir and os.path.exists(os.path.join(map_dir, 'app-map.json')):
    skip = set(json.load(open(os.path.join(map_dir, 'app-map.json'))).get('noCrop') or [])
for name in skip:
    best.pop(name, None)

os.makedirs(out_dir, exist_ok=True)
images = {}  # each screenshot is opened once, however many crops come from it
for name, (_, shot, (left, top, right, bottom)) in sorted(best.items()):
    if shot not in images:
        images[shot] = Image.open(os.path.join(run_dir, shot + '.png'))
    image = images[shot]
    scale = image.width / SCREEN_W
    box = (
        int(max(left - PAD, 0) * scale), int(max(top - PAD, 0) * scale),
        int(min(right + PAD, SCREEN_W) * scale), int(min(bottom + PAD, SCREEN_H) * scale),
    )
    crop = image.crop(box).convert('RGB')
    size = (round(crop.width * OUT_SCALE / scale), round(crop.height * OUT_SCALE / scale))
    crop.resize(size, Image.LANCZOS).save(os.path.join(out_dir, name + '.jpg'), quality=72, optimize=True)
print(f'{len(best)} crops in {out_dir}')

# Coverage: every page and widget the map draws should have a picture. List those without one,
# so the scenario gets the steps that show them.
if map_dir:
    drawn = set()
    for name in os.listdir(map_dir):
        if name.endswith('.md'):
            text = open(os.path.join(map_dir, name)).read()
            for type_name, stereotype in re.findall(r'class ([A-Za-z_]\w*)\s*\{\s*<<([^>]+)>>', text):
                if stereotype.strip() in UI_STEREOTYPES:
                    drawn.add(type_name)
    have = {name[:-4] for name in os.listdir(out_dir) if name.endswith('.jpg')}
    missing = sorted(drawn - have - skip)
    if missing:
        print(f'no picture yet for {len(missing)} page(s)/widget(s): {", ".join(missing)}')
        print('  add scenario steps that show them (or a snap with the screen named, for SwiftUI);')
        print('  leave out only what never shows on its own (a transient view, a tablet-only pane)')
