"""Checks an App map before it's handed over. Run it after `app-map index`.

Usage: verify.py <map dir>

Per page it reports:
  - template placeholders ({{…}}) left in the page
  - Mermaid pitfalls that break rendering (HTML entities in a source, a colon inside a relation
    label, a sequence alias that is a Mermaid keyword, a subgraph id equal to a node id)
  - members, relation labels and sequence calls that name nothing in the code (they won't click)
  - diagrams that fail to render, by loading the page in headless Chrome (when installed)
Errors (✗) fail the run; names that won't click (?) are listed to check — stale, or a
deliberate description such as a widget's role.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SOURCE = re.compile(r'<script type="text/plain" id="([^"]+)">([\s\S]*?)</script>')
SEQUENCE_KEYWORDS = {
    'end', 'loop', 'alt', 'else', 'opt', 'par', 'and', 'rect', 'critical', 'break', 'box', 'link',
    'links', 'note', 'over', 'participant', 'actor', 'activate', 'deactivate', 'autonumber',
    'create', 'destroy', 'title', 'details', 'properties', 'option', 'as', 'left', 'right', 'of',
}
CHROME_PATHS = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome',
]


def load_index(map_dir, page):
    path = os.path.join(map_dir, 'code', page + '.js')
    if not os.path.exists(path):
        return None
    with open(path) as handle:
        text = handle.read()
    return json.loads(text[text.index('=') + 1:].rstrip().rstrip(';'))['classes']


def owner(index, class_name, word):
    queue, seen = [class_name], set()
    while queue:
        name = queue.pop(0)
        if name in seen or name not in index:
            continue
        seen.add(name)
        members = index[name]['members']
        if word in members or f'{name}.{word}' in members:
            return name
        queue += index[name].get('supers', [])
    return None


def lint(source_id, source):
    problems = []
    if re.search(r'&(amp|lt|gt|quot|#\d+);', source):
        problems.append(f'{source_id}: HTML entity in a Mermaid source — write the plain character')
    kind = (re.match(r'\s*(\S+)', source) or [None, ''])[1]
    if kind == 'classDiagram':
        for match in re.finditer(r'^[ \t]*\w+[ \t]+\S*(?:--|\.\.)\S*[ \t]+\w+[ \t]*:(.*)$', source, re.M):
            if ':' in match.group(1):
                problems.append(f'{source_id}: colon inside a relation label: "{match.group(1).strip()}"')
    if kind == 'sequenceDiagram':
        for name, alias in re.findall(r'^[ \t]*(?:participant|actor)[ \t]+(\w+)(?:[ \t]+as[ \t]+(\w+))?',
                                      source, re.M):
            if name.lower() in SEQUENCE_KEYWORDS:
                problems.append(f'{source_id}: participant id "{name}" is a Mermaid keyword — rename it')
    if kind in ('flowchart', 'graph'):
        subgraphs = set(re.findall(r'^[ \t]*subgraph[ \t]+(\w+)', source, re.M))
        nodes = set(re.findall(r'^[ \t]*(\w+)[ \t]*[\[\(\{]', source, re.M))
        for clash in sorted(subgraphs & nodes):
            problems.append(f'{source_id}: subgraph id "{clash}" is also a node id')
    return problems


def unresolved(index, source_id, source):
    bad = []
    kind = (re.match(r'\s*(\S+)', source) or [None, ''])[1]
    if kind == 'classDiagram':
        for class_name, body in re.findall(r'^[ \t]*class[ \t]+(\w+)[ \t]*\{([^}]*)\}', source, re.M):
            if class_name not in index:
                continue
            for line in body.splitlines():
                line = re.sub(r'<<[^>]*>>', '', line).strip()
                if not line:
                    continue
                for part in re.split(r'\s+·\s+', line):
                    part = part.split(' : ')[0].strip().lstrip('+-#~ ')
                    match = re.match(r'([A-Za-z_]\w*)(?:\(.*\))?$', part)
                    if match and not owner(index, class_name, match.group(1)):
                        bad.append(f'{class_name}.{match.group(1)}')
        relation = r'^[ \t]*(\w+)[ \t]+\S*(?:--|\.\.)\S*[ \t]+(\w+)[ \t]*:(.*)$'
        for left, right, label in re.findall(relation, source, re.M):
            for word in re.findall(r'([A-Za-z_]\w*)\(', label):
                if not (owner(index, right, word) or owner(index, left, word)):
                    bad.append(f'{left} → {right} : {word}()')
    elif kind == 'sequenceDiagram':
        alias = {name: real or name for name, real in
                 re.findall(r'^[ \t]*(?:participant|actor)[ \t]+(\w+)(?:[ \t]+as[ \t]+(\w+))?', source, re.M)}
        for _, receiver, label in re.findall(r'^[ \t]*(\w+)[ \t]*->>?\+?[ \t]*(\w+)[ \t]*:(.*)$', source, re.M):
            target = alias.get(receiver, receiver)
            if target not in index:
                continue
            for word in re.findall(r'([A-Za-z_]\w*)\(', label):
                if not owner(index, target, word):
                    bad.append(f'→ {target} : {word}()')
    return [f'{source_id}: won\'t click: {item}' for item in bad]


def chrome():
    for candidate in CHROME_PATHS:
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.exists(path):
            return path
    return None


def render_errors(browser, page):
    with tempfile.TemporaryDirectory() as profile:
        result = subprocess.run(
            [browser, '--headless=new', '--disable-gpu', f'--user-data-dir={profile}',
             # CI containers can't use Chrome's sandbox.
             *(['--no-sandbox'] if os.environ.get('CI') else []),
             '--virtual-time-budget=20000', '--dump-dom', 'file://' + os.path.abspath(page)],
            capture_output=True, text=True, timeout=120)
    # The render script holds the error template itself; only rendered markup counts.
    dom = re.sub(r'<script[\s\S]*?</script>', '', result.stdout)
    errors = re.findall(r'<p class="err">([^<]*)</p>', dom)
    if not dom.strip():
        return ['page did not load in headless Chrome']
    rendered = len(re.findall(r'<svg', dom))
    expected = len(re.findall(r'class="out"', dom))
    problems = [f'diagram failed to render: {error[:160]}' for error in errors]
    if not errors and rendered < expected:
        problems.append(f'only {rendered} of {expected} diagrams rendered')
    return problems


def main():
    map_dir = sys.argv[1]
    browser = chrome()
    failed = False
    for page in sorted(glob.glob(os.path.join(map_dir, '*.html'))):
        name = os.path.splitext(os.path.basename(page))[0]
        with open(page) as handle:
            html = handle.read()
        problems = [f'placeholder left: {item}' for item in sorted(set(re.findall(r'\{\{[^}]*\}\}', html)))]
        index = load_index(map_dir, name) if name != 'index' else None
        if name != 'index' and index is None:
            problems.append('no code index — run `app-map index` first')
        warnings = []
        for source_id, source in SOURCE.findall(html):
            problems += lint(source_id, source)
            if index:
                warnings += unresolved(index, source_id, source)
        if browser:
            problems += render_errors(browser, page)
        failed |= bool(problems)
        status = 'OK' if not problems else f'{len(problems)} to fix'
        print(f'{name}: {status}' + (f' · {len(warnings)} to check' if warnings else ''))
        for problem in problems:
            print('  ✗ ' + problem)
        # A name that won't click is either stale (fix it) or a deliberate description
        # (a widget's role, like `logo`): check each one.
        for warning in warnings:
            print('  ? ' + warning)
    if not browser:
        print('(Chrome not found: rendering not checked — open the pages in a browser)')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
