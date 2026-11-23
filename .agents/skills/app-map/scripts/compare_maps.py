"""Compares the structure of two App maps: the same modules, and on each module page the same
classes, relations and members in each diagram. Wording (captions, labels) is ignored.

Usage: compare_maps.py <expected map dir> <actual map dir>
"""
import os
import re
import sys

SOURCE = re.compile(r'<script type="text/plain" id="([^"]+)">([\s\S]*?)</script>')
CLASS_BOX = re.compile(r'^\s*class\s+(\w+)\s*(\{[^}]*\})?', re.M)
RELATION = re.compile(r'^\s*(\w+)\s+(?:"[^"]*"\s+)?(\S*(?:--|\.\.)\S*)\s+(?:"[^"]*"\s+)?(\w+)', re.M)
PARTICIPANT = re.compile(r'^\s*(?:participant|actor)\s+(\w+)(?:\s+as\s+(\w+))?', re.M)
MESSAGE = re.compile(r'^\s*(\w+)\s*-{1,2}[>x)]{1,2}[+-]?\s*(\w+)\s*:', re.M)
MODULE_CARD = re.compile(r'<li><a href="([\w-]+)\.html">')


def diagram_kind(source):
    match = re.match(r'\s*(\w+)', source)
    return match.group(1) if match else ''


def structure(page):
    """{diagram kind: {'classes': set, 'relations': set, 'members': {class: set}, ...}}"""
    with open(page) as handle:
        html = handle.read()
    found = {}
    for _, source in SOURCE.findall(html):
        kind = diagram_kind(source)
        entry = found.setdefault(kind, {'classes': set(), 'relations': set(), 'members': {},
                                        'participants': set(), 'messages': set()})
        if kind == 'classDiagram':
            for name, body in CLASS_BOX.findall(source):
                entry['classes'].add(name)
                words = set(re.findall(r'[A-Za-z_]\w*', re.sub(r'<<[^>]*>>', '', body or '')))
                entry['members'].setdefault(name, set()).update(words)
            # Members written on their own lines inside a multi-line box.
            for name, block in re.findall(r'class\s+(\w+)\s*\{([^}]*)\}', source):
                words = set(re.findall(r'[A-Za-z_]\w*', re.sub(r'<<[^>]*>>', '', block)))
                entry['members'].setdefault(name, set()).update(words)
            for left, arrow, right in RELATION.findall(source):
                entry['classes'].update((left, right))
                entry['relations'].add((left, arrow, right))
        elif kind == 'sequenceDiagram':
            aliases = {name: alias or name for name, alias in PARTICIPANT.findall(source)}
            entry['participants'].update(aliases.values())
            for sender, receiver in MESSAGE.findall(source):
                entry['messages'].add((aliases.get(sender, sender), aliases.get(receiver, receiver)))
        elif kind == 'stateDiagram-v2':
            entry['classes'].update(re.findall(r'^\s*(\w+)\s*-->', source, re.M))
    return found


def score(expected, actual):
    if not expected and not actual:
        return 1.0, set(), set()
    return len(expected & actual) / len(expected | actual), expected - actual, actual - expected


def main():
    expected_dir, actual_dir = sys.argv[1], sys.argv[2]
    with open(os.path.join(expected_dir, 'index.html')) as handle:
        expected_modules = MODULE_CARD.findall(handle.read())
    with open(os.path.join(actual_dir, 'index.html')) as handle:
        actual_modules = MODULE_CARD.findall(handle.read())
    # A module may be named differently (settings / preferences): pair it by shared classes.
    def all_classes(page):
        return set().union(*[entry['classes'] for entry in structure(page).values()] or [set()])
    pairs = {module: module for module in expected_modules if module in actual_modules}
    spare = [module for module in actual_modules if module not in pairs.values()]
    for module in expected_modules:
        if module in pairs or not spare:
            continue
        mine = all_classes(os.path.join(expected_dir, module + '.html'))
        best = max(spare, key=lambda other: score(mine, all_classes(os.path.join(actual_dir, other + '.html')))[0])
        if score(mine, all_classes(os.path.join(actual_dir, best + '.html')))[0] >= 0.2:
            pairs[module] = best
            spare.remove(best)
    module_score = len(pairs) / len(set(expected_modules) | set(actual_modules) - set(pairs.values()) | set(pairs))
    renamed = {module: other for module, other in pairs.items() if module != other}
    print(f'Modules: {module_score:.0%} match'
          + (f' · renamed {renamed}' if renamed else '')
          + (f' · missing {sorted(set(expected_modules) - set(pairs))}' if set(expected_modules) - set(pairs) else '')
          + (f' · extra {sorted(spare)}' if spare else ''))
    totals = []
    for module in expected_modules:
        actual_page = os.path.join(actual_dir, pairs.get(module, module) + '.html')
        if not os.path.exists(actual_page):
            print(f'\n{module}: no page')
            totals.append(0.0)
            continue
        expected, actual = structure(os.path.join(expected_dir, module + '.html')), structure(actual_page)
        print(f'\n{module}' + (f' (as {pairs[module]})' if pairs.get(module, module) != module else ''))
        for kind in sorted(set(expected) | set(actual)):
            mine, theirs = expected.get(kind), actual.get(kind)
            if not mine or not theirs:
                print(f'  {kind}: only in {"expected" if mine else "actual"}')
                totals.append(0.0)
                continue
            for part in ('classes', 'relations', 'participants', 'messages'):
                if not mine[part] and not theirs[part]:
                    continue
                value, gone, added = score(mine[part], theirs[part])
                totals.append(value)
                detail = ''
                if gone:
                    detail += f' · missing {sorted(map(str, gone))[:6]}'
                if added:
                    detail += f' · extra {sorted(map(str, added))[:6]}'
                print(f'  {kind} {part}: {value:.0%}{detail}')
            shared = set(mine['members']) & set(theirs['members'])
            if shared:
                values = [score(mine['members'][name], theirs['members'][name])[0] for name in shared]
                totals.append(sum(values) / len(values))
                print(f'  {kind} members of shared classes: {sum(values) / len(values):.0%}')
    print(f'\nOverall structure match: {sum(totals) / max(len(totals), 1):.0%}')


if __name__ == '__main__':
    main()
