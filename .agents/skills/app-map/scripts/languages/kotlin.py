"""Kotlin: classes, interfaces, objects, enums, data classes, with their members. Top-level
functions and properties too; a `@Composable` function is a widget, not a plain function."""
import re

from .base import Language, add_member, declaration, end_line, first, line, text

LEADING = {'line_comment', 'multiline_comment'}
TYPE_KINDS = {'class_declaration', 'object_declaration'}
MEMBER_KINDS = {
    'property_declaration', 'function_declaration', 'secondary_constructor', 'enum_entry',
    'class_declaration', 'object_declaration',
}
# A top-level `@Annotation(…)\n@Annotation\nprivate fun foo() {…}` that the grammar sometimes
# misparses as an expression (an annotated declaration can look ambiguous to it depending on what
# follows in the file) — pulled out by text instead, like Dart's `extension type` workaround.
ANNOTATION = r'@[\w.]+(?:\([^()]*(?:\([^()]*\)[^()]*)*\))?\s*'
FUN_FALLBACK = re.compile(
    r'^(?:' + ANNOTATION + r')*(?:private\s+|internal\s+|public\s+|protected\s+)*'
    r'fun\s+(?:<[^>]*>\s*)?(?:[\w.]+\.)?(\w+)\s*\(')
COMPOSABLE = re.compile(r'@Composable\b')


def _modifiers_text(source, node):
    modifiers = first(node, 'modifiers')
    return text(source, modifiers) if modifiers is not None else ''


def is_composable(source, node):
    return '@Composable' in _modifiers_text(source, node)


def _supers(source, node):
    return [text(source, spec) for spec in node.named_children if spec.type == 'delegation_specifier']


def _class_kind(source, node):
    if node.type == 'object_declaration':
        return 'object'
    tokens = {child.type for child in node.children if not child.is_named}
    if 'interface' in tokens:
        return 'interface'
    if 'enum' in tokens:
        return 'enum'
    if 'data' in _modifiers_text(source, node):
        return 'data class'
    return 'class'


def _member_name(source, node):
    if node.type == 'secondary_constructor':
        return 'constructor'
    if node.type in ('class_declaration', 'object_declaration', 'enum_entry'):
        name = first(node, 'type_identifier', 'simple_identifier')
        return text(source, name) if name is not None else None
    if node.type == 'function_declaration':
        name = first(node, 'simple_identifier')
        return text(source, name) if name is not None else None
    if node.type == 'property_declaration':
        variable = first(node, 'variable_declaration', 'multi_variable_declaration')
        name = first(variable, 'simple_identifier') if variable is not None else None
        return text(source, name) if name is not None else None
    return None


def _walk_members(source, body, decl):
    start = None
    for child in body.named_children:
        if child.type in LEADING:
            start = start or line(child)
            continue
        if child.type == 'companion_object':
            # `companion object { fun create() }` is called as `Foo.create()`: Foo's members.
            body = first(child, 'class_body')
            if body is not None:
                _walk_members(source, body, decl)
        elif child.type in MEMBER_KINDS:
            name = _member_name(source, child)
            if name:
                add_member(decl, name, start or line(child), end_line(child))
        start = None


def _class_parameters(source, node, decl):
    """`class Foo(val a: Int, val b: String)` — a data class's fields are its constructor params."""
    constructor = first(node, 'primary_constructor')
    if constructor is None:
        return
    for param in constructor.named_children:
        if param.type == 'class_parameter':
            name = first(param, 'simple_identifier')
            if name is not None:
                add_member(decl, text(source, name), line(param), end_line(param))


def extract(rel, source, root):
    decls = []
    start = None
    for node in root.named_children:
        if node.type in LEADING:
            start = start or line(node)
            continue
        begin = start or line(node)
        decl = None
        if node.type in TYPE_KINDS:
            name = first(node, 'type_identifier')
            if name is not None:
                decl = declaration(rel, text(source, name), _class_kind(source, node), begin,
                                   end_line(node), _supers(source, node))
                _class_parameters(source, node, decl)
                body = first(node, 'class_body', 'enum_class_body')
                if body is not None:
                    _walk_members(source, body, decl)
        elif node.type == 'function_declaration':
            name = first(node, 'simple_identifier')
            if name is not None:
                kind = 'composable function' if is_composable(source, node) else 'function'
                decl = declaration(rel, text(source, name), kind, begin, end_line(node))
        elif node.type == 'property_declaration':
            variable = first(node, 'variable_declaration', 'multi_variable_declaration')
            name = first(variable, 'simple_identifier') if variable is not None else None
            if name is not None:
                decl = declaration(rel, text(source, name), 'top-level variable', begin,
                                   end_line(node))
        elif node.type == 'type_alias':
            name = first(node, 'type_identifier')
            if name is not None:
                decl = declaration(rel, text(source, name), 'typedef', begin, end_line(node))
        elif node.type not in ('import_list', 'package_header'):
            match = FUN_FALLBACK.match(text(source, node))
            if match:
                kind = 'composable function' if COMPOSABLE.search(match.group(0)) else 'function'
                decl = declaration(rel, match.group(1), kind, begin, end_line(node))
        if decl:
            decls.append(decl)
        start = None
    return decls


class Kotlin(Language):
    def __init__(self):
        super().__init__('kotlin', ('.kt', '.kts'), (), extract)


LANGUAGE = Kotlin()
