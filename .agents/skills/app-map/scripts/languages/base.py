"""Shared helpers for tree-sitter language modules."""
import hashlib
import inspect
import os

from tree_sitter_language_pack import get_parser


class Language:
    def __init__(self, name, extensions, generated_suffixes, extract):
        self.name = name
        self.extensions = extensions
        self._generated = generated_suffixes
        self._extract = extract
        self._parser = None
        # The parser that produced the cached declarations; a change re-parses every file. The
        # code that reads the tree counts too, so a fix here reaches files already cached.
        code = b''.join(open(path, 'rb').read() for path in (__file__, inspect.getsourcefile(extract)))
        self.backend = 'tree-sitter-' + hashlib.sha1(code).hexdigest()[:10]

    def is_generated(self, filename):
        return filename.endswith(self._generated)

    def declarations(self, rel, source):
        if self._parser is None:
            self._parser = get_parser(self.name)
        tree = self._parser.parse(source)
        return self._extract(rel, source, tree.root_node)

    def batch(self, root, rels):
        """Declarations of many files at once: {rel: [declaration]}."""
        out = {}
        for rel in rels:
            with open(os.path.join(root, rel), 'rb') as handle:
                out[rel] = self.declarations(rel, handle.read())
        return out


def line(node):
    return node.start_point[0] + 1


def end_line(node):
    # A node ending at column 0 ends on the line before (its trailing newline).
    row, column = node.end_point
    return row if column == 0 and row > node.start_point[0] else row + 1


def text(source, node):
    return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')


def named(node, *types):
    return [child for child in node.named_children if child.type in types]


def first(node, *types):
    for child in node.named_children:
        if child.type in types:
            return child
    return None


def declaration(rel, name, kind, start, end, supers=()):
    return {'file': rel, 'name': name, 'kind': kind, 'from': start, 'to': end,
            'supers': list(supers), 'members': {}}


def add_member(decl, name, start, end):
    # The first declaration wins, like a getter before its setter.
    decl['members'].setdefault(name, [start, end])
