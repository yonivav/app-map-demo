"""What the code says a class is connected to — the raw material for a module's diagrams.

Usage: facts.py <repo root> <Class> [<Class> ...]
       facts.py <repo root> --dir <folder>     every class declared under a folder

For each class: its role, file and parents, then the project classes it builds (widgets/views it
constructs) and uses (types it mentions), grouped by role. Framework classes are left out. A
StatefulWidget's State class is folded into the widget, since that's where its build() lives.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_code import load_declarations  # noqa: E402

WIDGET_BASES = {
    'StatelessWidget', 'StatefulWidget', 'Widget', 'HookWidget', 'HookConsumerWidget',
    'ConsumerWidget', 'ConsumerStatefulWidget', 'InheritedWidget', 'RenderObjectWidget',
    'LeafRenderObjectWidget', 'SingleChildRenderObjectWidget', 'StatelessComponent',
    # Framework widgets apps commonly extend.
    'AppBar', 'Scaffold', 'Container', 'Text', 'TextField', 'TextFormField', 'ListView',
    'ScrollView', 'CustomScrollView', 'AnimatedWidget', 'ImplicitlyAnimatedWidget', 'Dialog',
    'AlertDialog', 'ElevatedButton', 'TextButton', 'IconButton', 'InkWell', 'GestureDetector',
    'CustomPaint', 'PageView', 'TabBar', 'BottomNavigationBar', 'Card', 'ListTile',
    'PreferredSizeWidget', 'StatefulHookWidget', 'GetView', 'GetWidget',
    # UIKit and SwiftUI.
    'UIViewController', 'UIView', 'UITableViewCell', 'UICollectionViewCell', 'UIControl',
    'UITableViewController', 'UICollectionViewController', 'View',
    # Android views and SwiftUI/Compose screens.
    'Activity', 'AppCompatActivity', 'FragmentActivity', 'ComponentActivity', 'Fragment',
    'DialogFragment', 'ViewGroup', 'RecyclerView', 'ViewHolder',
}
# Flutter State and similar: where a StatefulWidget's build() lives, folded into the widget.
STATE_BASES = {'State', 'ConsumerState', 'GetItState'}
ROLE_SUFFIXES = [
    ('page', ('Page', 'Screen', 'ViewController', 'Activity', 'Fragment')),
    ('view-model', ('VM', 'ViewModel', 'Controller', 'Bloc', 'Cubit', 'Notifier', 'Presenter',
                    'Logic', 'Store')),
    ('service', ('Service', 'Manager', 'Repository', 'Repo', 'Api', 'Client', 'Handler', 'Source',
                 'Provider', 'Scheduler', 'Interactor', 'UseCase')),
    ('model', ('Model', 'State', 'Data', 'Entity', 'Dto', 'Item', 'Config')),
]
# A widget-ish base that doesn't name every framework subclass (a custom `BaseViewController`).
WIDGET_SUFFIXES = ('Widget', 'Page', 'ViewController', 'Activity', 'Fragment', 'View', 'Cell',
                   'ViewHolder')
ROLE_ORDER = ['page', 'view-model', 'model', 'service', 'widget', 'enum', 'data', 'other', 'style']
# Design tokens and asset tables: real dependencies, but noise in a diagram.
STYLE = re.compile(r'(TextStyle|Colors?|Theme|ThemeData|Assets?|Sizes?|Spacing|Paddings?|Radius'
                   r'|Radii|Insets|Fonts?|Icons|Strings|Styles?|Dimens|Durations?)$')


def chain(name, by_name, seen=None):
    """Every parent and mixin name up the hierarchy, project classes followed."""
    seen = seen if seen is not None else set()
    for decl in by_name.get(name, [])[:1]:
        for parent in decl['supers']:
            if parent not in seen:
                seen.add(parent)
                chain(parent, by_name, seen)
    return seen


TYPE_KINDS = ('class', 'mixin', 'extension type', 'struct', 'protocol', 'extension', 'interface',
              'object', 'data class', 'record', 'implementation', 'category')


def role(name, by_name):
    decl = by_name[name][0]
    if STYLE.search(name) or re.match(r'^[A-Z]\w*(TextStyle|Style)$', name):
        return 'style'
    if decl['kind'] == 'enum':
        return 'enum'
    # A `@Composable fun Foo(...)` is a Compose screen/widget, not a plain function.
    if decl['kind'] == 'composable function':
        return 'widget'
    if decl['kind'] not in TYPE_KINDS:
        return 'other'
    parents = chain(name, by_name)
    if parents & STATE_BASES:
        return 'state'
    for label, suffixes in ROLE_SUFFIXES[:1]:
        if name.endswith(suffixes):
            return label
    if parents & WIDGET_BASES or any(parent.endswith(WIDGET_SUFFIXES) for parent in parents):
        return 'widget'
    for label, suffixes in ROLE_SUFFIXES[1:]:
        if name.endswith(suffixes):
            return label
    return 'data'


def state_of(name, by_name):
    """`_FooState extends State<Foo>` in Foo's file: where a StatefulWidget builds."""
    decl = by_name[name][0]
    for other_name, found in by_name.items():
        for other in found:
            if other['file'] == decl['file'] \
                    and re.fullmatch(r'_?' + re.escape(name) + r'State', other_name) \
                    and STATE_BASES & (chain(other_name, by_name) | set(other['supers'])):
                return other
    return None


def describe(name, by_name):
    decl = by_name[name][0]
    refs = decl.get('refs') or {}
    state = state_of(name, by_name)
    sources = [refs] + ([state.get('refs') or {}] if state else [])
    gather = lambda key: set().union(*[set(source.get(key, [])) for source in sources])  # noqa: E731
    builds, types, calls = gather('builds'), gather('types'), gather('calls')
    # A top-level getter or variable (`settingsLogic`, get_it style) stands for its type.
    for item in gather('names'):
        for top in by_name.get(item, [])[:1]:
            if top.get('returns'):
                types.add(top['returns'])
    implemented = set(refs.get('implements', []))
    project = lambda names: {item for item in names if item in by_name and item != name}  # noqa: E731
    # `Foo.named(...)` builds Foo when Foo is a widget; otherwise it's a static call.
    builds |= {item for item in project(calls) if role(item, by_name) in ('widget', 'page')}
    parents = chain(name, by_name) | (set(state['supers']) if state else set()) | implemented
    builds, uses = project(builds) - parents, project(types) - project(builds) - parents
    uses = {item for item in uses if role(item, by_name) != 'state'}
    mixins = refs.get('mixins', [])
    parent = [item for item in decl['supers'] if item not in mixins]
    lines = [f'{name} ({role(name, by_name)}) {decl["file"]}:{decl["from"]}'
             + (f' · extends {", ".join(parent)}' if parent else '')
             + (f' · with {", ".join(mixins)}' if mixins else '')
             + (f' · implements {", ".join(sorted(implemented))}' if implemented else '')]
    built_widgets = sorted(item for item in builds if role(item, by_name) in ('widget', 'page'))
    if built_widgets:
        lines.append('  builds: ' + ', '.join(built_widgets))
    grouped = {}
    for item in uses | (builds - set(built_widgets)):
        grouped.setdefault(role(item, by_name), []).append(item)
    for label in ROLE_ORDER:
        if grouped.get(label):
            prefix = 'style (leave out of diagrams)' if label == 'style' else f'uses {label}'
            lines.append(f'  {prefix}: ' + ', '.join(sorted(grouped[label])))
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root = os.path.realpath(sys.argv[1])
    by_name, _, _ = load_declarations(root)
    names = sys.argv[2:]
    if names[0] == '--dir':
        # Relative to the repo root (or absolute).
        folder = os.path.relpath(os.path.realpath(os.path.join(root, names[1])), root)
        names = sorted({decl['name'] for found in by_name.values() for decl in found
                        if decl['file'].startswith(folder + os.sep)
                        and decl['kind'] in TYPE_KINDS + ('enum', 'composable function')
                        and role(decl['name'], by_name) != 'state'})
    for name in names:
        print(describe(name, by_name) if name in by_name else f'{name}: not found')
        print()


if __name__ == '__main__':
    main()
