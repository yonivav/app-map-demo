"""Builds <page dir>/code/<page>.js for App map pages: the source of every class a page's
diagrams draw, with the line range of each member, so the page can show code in a popup.

Usage: index_code.py <repo root> <page.html> [<page.html> ...]

Declarations are parsed with tree-sitter (see languages/) and cached per file (mtime + size) in
~/.cache/app-map/, so a rerun only parses files changed since the last one.
"""
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from languages import LANGUAGES, language_for  # noqa: E402

CACHE_VERSION = 1
SKIP_DIRS = {
    '.git', '.dart_tool', 'build', 'Pods', 'DerivedData', 'node_modules', '.gradle', '.idea',
    '.build', 'dist', '.next', 'out', 'ephemeral', '.symlinks', 'test', 'tests', 'integration_test',
    'test_driver',
    'androidTest', 'Tests', 'UITests', 'docs',
}


def excluded_paths():
    """Repo-relative folders the map leaves out: app-map.json's "exclude", passed by `app-map`."""
    return {path.strip().strip('/') for path in os.environ.get('APP_MAP_EXCLUDE', '').splitlines() if path.strip()}


def source_files(root):
    excluded = excluded_paths()
    for directory, subdirs, files in os.walk(root):
        relative = os.path.relpath(directory, root)
        subdirs[:] = [name for name in subdirs if name not in SKIP_DIRS and not name.startswith('.')
                      and os.path.normpath(os.path.join(relative, name)) not in excluded]
        for name in files:
            language = language_for(name)
            if language and not language.is_generated(name):
                yield os.path.join(directory, name), language


class Cache:
    def __init__(self, root):
        key = hashlib.sha1(root.encode()).hexdigest()[:12]
        self.path = os.path.join(os.path.expanduser('~'), '.cache', 'app-map', key + '.json')
        self.files = {}
        self.seen = set()
        try:
            with open(self.path) as handle:
                data = json.load(handle)
            if data.get('version') == CACHE_VERSION:
                self.files = data['files']
        except (OSError, ValueError):
            pass

    def lookup(self, rel, stamp):
        self.seen.add(rel)
        entry = self.files.get(rel)
        return entry['decls'] if entry and entry['stamp'] == stamp else None

    def store(self, rel, stamp, decls):
        self.files[rel] = {'stamp': stamp, 'decls': decls}

    def save(self):
        # Deleted files drop out of the cache.
        self.files = {rel: entry for rel, entry in self.files.items() if rel in self.seen}
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as handle:
            json.dump({'version': CACHE_VERSION, 'files': self.files}, handle)


DIAGRAM_SOURCE = re.compile(r'<script type="text/plain"[^>]*>([\s\S]*?)</script>')
# [ \t] rather than \s: a pattern must never run on into the next line.
CLASS_BOX = re.compile(r'^[ \t]*class[ \t]+([A-Za-z_]\w*)', re.M)
PARTICIPANT = re.compile(r'^[ \t]*(?:participant|actor)[ \t]+(\w+)(?:[ \t]+as[ \t]+(\w+))?', re.M)
RELATION = re.compile(r'^[ \t]*([A-Za-z_]\w*)[ \t]+(?:"[^"\n]*"[ \t]+)?\S*(?:--|\.\.)\S*[ \t]+(?:"[^"\n]*"[ \t]+)?([A-Za-z_]\w*)', re.M)


def names_on_page(html):
    """Class names drawn on a page: class boxes, relation ends, sequence participants, and
    classes named in flowchart node labels."""
    names = set()
    for block in DIAGRAM_SOURCE.findall(html):
        names |= names_in(block)
    return names


FLOW_NODE = re.compile(r'(\w+)\s*(?:\["?|\("?|\{"?)([^"\]\)\}]*)')
CAMEL = re.compile(r'^[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+$')


def flow_nodes(block):
    """{node id: class name} for flowchart nodes whose label names a class (`"Menu<br/>MenuPage"`)."""
    nodes = {}
    for node_id, label in FLOW_NODE.findall(block):
        words = [word for word in re.split(r'<br\s*/?>|[\s·,]+', label) if CAMEL.match(word)]
        if words:
            nodes.setdefault(node_id, words[-1])
        elif CAMEL.match(node_id):
            nodes.setdefault(node_id, node_id)
    return nodes


def names_in(block):
    """Class names one diagram source draws (none for state machines)."""
    names = set()
    if re.match(r'\s*(flowchart|graph)\b', block):
        return set(flow_nodes(block).values())
    if re.match(r'\s*(classDiagram|sequenceDiagram)', block):
        names.update(CLASS_BOX.findall(block))
        names.update(alias or name for name, alias in PARTICIPANT.findall(block))
        for left, right in RELATION.findall(block):
            names.update((left, right))
    return names


def where_drawn(pages):
    """{Class: [[page, section id, section title], …]} across every page of the map."""
    where = {}
    for page in pages:
        with open(page, encoding='utf-8') as handle:
            text = handle.read()
        name = os.path.splitext(os.path.basename(page))[0]
        sources = dict(re.findall(r'<script type="text/plain" id="([^"]+)">([\s\S]*?)</script>', text))
        for section in re.findall(r'<section[^>]*>([\s\S]*?)</section>', text):
            heading = re.search(r'<h2 id="([^"]+)">(.*?)</h2>', section, re.S)
            out = re.search(r'data-src="([^"]+)"', section)
            if not heading or not out or out.group(1) not in sources:
                continue
            title = re.sub(r'\s*<span>(.*?)</span>', r' · \1', heading.group(2))
            title = re.sub(r'<[^>]+>', ' ', title)
            title = ' '.join(title.replace('&amp;', '&').split())
            for drawn in names_in(sources[out.group(1)]):
                spot = [name, heading.group(1), title]
                if spot not in where.setdefault(drawn, []):
                    where[drawn].append(spot)
    return where


def state_class(name, decl, by_name):
    """A StatefulWidget's `_NameState` in the same file: where its build() and handlers live."""
    for candidate in ('_' + name + 'State', name + 'State'):
        for other in by_name.get(candidate, []):
            if other['file'] == decl['file']:
                return candidate
    return None


def write_page(root, page, by_name, source_url=None, where=None):
    with open(page) as handle:
        names = names_on_page(handle.read())
    page_dir = os.path.dirname(page)
    lines_of = {}
    classes = {}
    pending, done = set(names), set()
    while pending:
        name = pending.pop()
        done.add(name)
        found = by_name.get(name)
        if not found:
            continue
        decl = found[0]
        if decl['file'] not in lines_of:
            with open(os.path.join(root, decl['file']), encoding='utf-8', errors='replace') as handle:
                lines_of[decl['file']] = handle.read().splitlines()
        entry = {
            'file': decl['file'],
            'line': decl['from'],
            'kind': decl['kind'],
            'supers': decl['supers'],
            'code': '\n'.join(lines_of[decl['file']][decl['from'] - 1:decl['to']]),
            'members': decl['members'],
        }
        if len(found) > 1:
            entry['alsoIn'] = [other['file'] for other in found[1:]]
        # A crop of the page or widget, from crop_shots.py.
        if os.path.exists(os.path.join(page_dir, 'shots', 'code', name + '.jpg')):
            entry['shot'] = 'shots/code/' + name + '.jpg'
        # A widget's members include its State class's, so `_handleTap()` on the box clicks.
        state = state_class(name, decl, by_name)
        if state and state not in entry['supers']:
            entry['supers'] = entry['supers'] + [state]
        if where and name in where:
            entry['appearsIn'] = where[name]
        classes[name] = entry
        # Parents, mixins and the State class ride along so their members can be found too.
        pending.update(parent for parent in entry['supers'] if parent not in done and parent in by_name)

    out = os.path.join(page_dir, 'code', os.path.splitext(os.path.basename(page))[0] + '.js')
    # Popups link each excerpt to its source: a web URL (`source_url` + path + #L lines) for a
    # published map, else "Open in editor" from the page's own location on disk.
    index = {'classes': classes}
    if source_url:
        index['sourceUrl'] = source_url.rstrip('/') + '/'
    else:
        index['root'] = os.path.relpath(root, page_dir)
    body = 'window.CODE_INDEX = ' + json.dumps(index, separators=(',', ':'), sort_keys=True) + ';\n'
    same = os.path.exists(out) and open(out).read() == body
    if not same:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w') as handle:
            handle.write(body)
    missing = sorted(name for name in names if name not in by_name)
    print(f'{os.path.relpath(out, root)}: {len(classes)} classes' + (' (unchanged)' if same else '')
          + (f' · not found: {", ".join(missing)}' if missing else ''))


MERGE_KINDS = {'extension', 'category', 'implementation'}


def merge_reopened(by_name):
    """A Swift `extension`, Objective-C `category` or `@implementation` reopens a type under its
    own name rather than declaring a new one — so unlike a real duplicate name, it should never
    outrank the real declaration, and its members belong with it."""
    for name, found in by_name.items():
        primaries = [decl for decl in found if decl['kind'] not in MERGE_KINDS]
        reopenings = [decl for decl in found if decl['kind'] in MERGE_KINDS]
        if not primaries or not reopenings:
            continue
        primary = primaries[0]
        for reopening in reopenings:
            for member, span in reopening['members'].items():
                primary['members'].setdefault(member, span)
            for parent in reopening['supers']:
                if parent not in primary['supers']:
                    primary['supers'].append(parent)
        by_name[name] = [primary] + [decl for decl in found if decl is not primary]


def load_declarations(root):
    """{name: [declaration, …]} for every declaration in the repo, best match first."""
    cache = Cache(root)
    by_name = {}
    changed = {}
    for path, language in source_files(root):
        rel = os.path.relpath(path, root)
        stat = os.stat(path)
        stamp = f'{language.backend}:{stat.st_mtime_ns}:{stat.st_size}'
        decls = cache.lookup(rel, stamp)
        if decls is None:
            changed.setdefault(language, []).append((rel, stamp))
            continue
        for decl in decls:
            by_name.setdefault(decl['name'], []).append(decl)
    parsed = 0
    for language, files in changed.items():
        results = language.batch(root, [rel for rel, _ in files])
        for rel, stamp in files:
            decls = results.get(rel, [])
            # The backend may have fallen back to tree-sitter during the batch.
            cache.store(rel, language.backend + stamp[stamp.index(':'):], decls)
            parsed += 1
            for decl in decls:
                by_name.setdefault(decl['name'], []).append(decl)
    cache.save()
    # Prefer app code over a same-named declaration in a sample or tool folder. The file path
    # itself breaks a tie deterministically — two files of the same length (e.g. a parallel
    # iOS/Mac target's same-named class) would otherwise order however the filesystem happened
    # to walk them, which differs by OS and made the committed output non-reproducible.
    for found in by_name.values():
        found.sort(key=lambda decl: (decl['file'].count('example'), len(decl['file']), decl['file']))
    merge_reopened(by_name)
    return by_name, parsed, len(cache.seen)


def main():
    args = sys.argv[1:]
    source_url = None
    if '--source-url' in args:
        at = args.index('--source-url')
        source_url = args[at + 1]
        del args[at:at + 2]
    if len(args) < 2:
        sys.exit('usage: index_code.py [--source-url <url>] <repo root> <page.html> [...]')
    started = time.time()
    root = os.path.realpath(args[0])
    by_name, parsed, cached = load_declarations(root)
    pages = [os.path.realpath(page) for page in args[1:]]
    where = where_drawn(pages)
    for page in pages:
        write_page(root, page, by_name, source_url, where)
    # The overview's search and `app-map where` read every class's places from one file.
    if pages:
        found = {name: spots for name, spots in where.items() if name in by_name}
        files = {name: by_name[name][0]['file'] for name in found}
        out = os.path.join(os.path.dirname(pages[0]), 'code', '_where.js')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w') as handle:
            handle.write('window.APP_MAP_WHERE = ' + json.dumps({'classes': found, 'files': files},
                         separators=(',', ':'), sort_keys=True) + ';\n')
    print(f'index_code: parsed {parsed} changed file(s), {cached} cached, '
          f'{int((time.time() - started) * 1000)} ms')


if __name__ == '__main__':
    main()
