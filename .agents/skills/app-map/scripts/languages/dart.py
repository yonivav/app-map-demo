"""Dart: classes, mixins, enums, extensions, extension types, typedefs, top-level functions and
variables, with their members."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

from .base import Language, add_member, declaration, end_line, first, line, named, text

# Doc comments and annotations belong to the declaration after them.
LEADING = {'documentation_comment', 'annotation'}
SIGNATURES = {
    'function_signature', 'getter_signature', 'setter_signature', 'constructor_signature',
    'constant_constructor_signature', 'factory_constructor_signature',
    'redirecting_factory_constructor_signature', 'operator_signature',
}


def _supers(source, node):
    """Parent and mixins of a class: `extends Base with A, B` or `= Base with A, B`."""
    names = []
    for child in node.named_children:
        if child.type == 'type_identifier':
            names.append(text(source, child))
        elif child.type == 'mixins':
            names.extend(text(source, mixin) for mixin in named(child, 'type_identifier'))
    return names


def _signature_names(source, signature, class_name):
    """Names a member signature declares; constructors are `Class` or `Class.named`."""
    kind = signature.type
    if kind in ('constructor_signature', 'constant_constructor_signature',
                'factory_constructor_signature', 'redirecting_factory_constructor_signature'):
        parts = [text(source, part) for part in named(signature, 'identifier')]
        return [class_name if len(parts) < 2 else f'{class_name}.{parts[-1]}']
    if kind == 'operator_signature':
        return []
    name = signature.child_by_field_name('name') or first(signature, 'identifier')
    return [text(source, name)] if name else []


def _variable_names(source, node):
    names = []
    for item in node.named_children:
        if item.type in ('initialized_identifier', 'static_final_declaration'):
            identifier = first(item, 'identifier')
            if identifier:
                names.append(text(source, identifier))
        elif item.type == 'identifier':
            names.append(text(source, item))
    return names


def _member_names(source, node, class_name):
    if node.type == 'enum_constant':
        name = node.child_by_field_name('name')
        return [text(source, name)] if name else []
    if node.type in SIGNATURES:
        return _signature_names(source, node, class_name)
    names = []
    for child in node.named_children:
        if child.type in SIGNATURES:
            names.extend(_signature_names(source, child, class_name))
        elif child.type in ('initialized_identifier_list', 'static_final_declaration_list'):
            names.extend(_variable_names(source, child))
    return names


def _walk_members(source, body, decl):
    children = body.named_children
    start = None
    for index, child in enumerate(children):
        if child.type in LEADING:
            start = start or line(child)
            continue
        if child.type in ('declaration', 'method_signature', 'enum_constant'):
            end = end_line(child)
            following = children[index + 1] if index + 1 < len(children) else None
            if following is not None and following.type == 'function_body':
                end = end_line(following)
            for name in _member_names(source, child, decl['name']):
                add_member(decl, name, start or line(child), end)
        if child.type != 'function_body':
            start = None


def extract(rel, source, root):
    decls = []
    children = root.named_children
    start = None
    for index, node in enumerate(children):
        if node.type in LEADING:
            start = start or line(node)
            continue
        begin = start or line(node)
        decl = None
        body = None
        if node.type == 'class_definition':
            alias = first(node, 'mixin_application_class')
            if alias:
                name = first(alias, 'identifier')
                application = first(alias, 'mixin_application')
                supers = _supers(source, application) if application else []
                decl = declaration(rel, text(source, name), 'class', begin, end_line(node), supers)
            else:
                name = node.child_by_field_name('name')
                parent = node.child_by_field_name('superclass')
                decl = declaration(rel, text(source, name), 'class', begin, end_line(node),
                                   _supers(source, parent) if parent else [])
                body = node.child_by_field_name('body')
        elif node.type == 'mixin_declaration':
            name = first(node, 'identifier')
            decl = declaration(rel, text(source, name), 'mixin', begin, end_line(node))
            body = first(node, 'class_body')
        elif node.type == 'enum_declaration':
            decl = declaration(rel, text(source, node.child_by_field_name('name')), 'enum', begin,
                               end_line(node))
            body = node.child_by_field_name('body')
        elif node.type == 'extension_declaration':
            name = node.child_by_field_name('name')
            if name:
                decl = declaration(rel, text(source, name), 'extension', begin, end_line(node))
                body = node.child_by_field_name('body')
        elif node.type == 'type_alias':
            name = first(node, 'type_identifier', 'identifier')
            decl = declaration(rel, text(source, name), 'typedef', begin, end_line(node))
        elif node.type == 'function_signature':
            name = node.child_by_field_name('name')
            following = children[index + 1] if index + 1 < len(children) else None
            end = end_line(following) if following is not None and following.type == 'function_body' \
                else end_line(node)
            decl = declaration(rel, text(source, name), 'function', begin, end)
        elif node.type in ('static_final_declaration_list', 'initialized_identifier_list'):
            for variable in _variable_names(source, node):
                decls.append(declaration(rel, variable, 'top-level variable', begin, end_line(node)))
        elif node.type == 'ERROR':
            # The grammar doesn't know `extension type X(...)` yet.
            match = re.match(r'extension\s+type\s+(?:const\s+)?(\w+)', text(source, node))
            if match:
                decl = declaration(rel, match.group(1), 'extension type', begin, end_line(node))
        if decl:
            if body is not None:
                _walk_members(source, body, decl)
            decls.append(decl)
        # Builtins like `const`/`final` start a top-level variable; keep their line.
        if node.type in ('const_builtin', 'final_builtin', 'type_identifier', 'inferred_type'):
            start = start or line(node)
        elif node.type != 'function_body':
            start = None
    return decls


class Dart(Language):
    """Uses Dart's own parser (dart_declarations/) when a Dart SDK is installed: tree-sitter's
    Dart grammar trails the language (dot shorthands, newer patterns) and loses whole classes."""

    def __init__(self):
        super().__init__('dart', ('.dart',), ('.g.dart', '.freezed.dart', '.gr.dart', '.config.dart'),
                         extract)
        self._binary = None
        self._tool = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  'dart_declarations')
        digest = hashlib.sha1()
        for name in ('pubspec.yaml', os.path.join('bin', 'dart_declarations.dart')):
            with open(os.path.join(self._tool, name), 'rb') as handle:
                digest.update(handle.read())
        self._version = digest.hexdigest()[:10]
        # A new build of the parser re-parses every file.
        self.backend = 'analyzer-' + self._version if shutil.which('dart') else 'tree-sitter'

    def _compiled(self):
        if self._binary:
            return self._binary
        tool = self._tool
        binary = os.path.join(os.path.expanduser('~'), '.cache', 'app-map', 'bin',
                              'dart_declarations-' + self._version)
        if not os.path.exists(binary):
            os.makedirs(os.path.dirname(binary), exist_ok=True)
            print('index_code: compiling the Dart parser (first run only)…', file=sys.stderr)
            subprocess.run(['dart', 'pub', 'get'], cwd=tool, check=True, capture_output=True)
            subprocess.run(['dart', 'compile', 'exe', 'bin/dart_declarations.dart', '-o', binary],
                           cwd=tool, check=True, capture_output=True)
        self._binary = binary
        return binary

    def batch(self, root, rels):
        if self.backend == 'tree-sitter' or not rels:
            return super().batch(root, rels)
        try:
            result = subprocess.run([self._compiled(), root], input='\n'.join(rels), text=True,
                                    capture_output=True, check=True)
            return json.loads(result.stdout)
        except (OSError, subprocess.CalledProcessError, ValueError) as error:
            print(f'index_code: Dart parser unavailable ({error}); using tree-sitter', file=sys.stderr)
            self.backend = 'tree-sitter'
            return super().batch(root, rels)


LANGUAGE = Dart()
