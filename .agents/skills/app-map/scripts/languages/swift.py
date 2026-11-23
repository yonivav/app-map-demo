"""Swift: classes, structs (SwiftUI views included), enums, protocols and extensions, with their
members. Top-level functions and variables too."""
from .base import Language, add_member, declaration, end_line, line, named, text

LEADING = {'comment', 'multiline_comment'}
KIND_BY_TOKEN = {'class': 'class', 'struct': 'struct', 'enum': 'enum', 'extension': 'extension'}
MEMBER_KINDS = {
    'property_declaration', 'function_declaration', 'init_declaration', 'deinit_declaration',
    'subscript_declaration', 'protocol_function_declaration', 'protocol_property_declaration',
    'protocol_subscript_declaration', 'enum_entry',
}


def _find_identifier(node):
    """The first simple_identifier/type_identifier under a pattern, var binding or user_type —
    patterns and protocol requirements wrap the name in extra nodes (`var count` for `count`)."""
    if node is None:
        return None
    if node.type in ('simple_identifier', 'type_identifier'):
        return node
    for child in node.named_children:
        found = _find_identifier(child)
        if found:
            return found
    return None


def _name_text(source, node):
    ident = _find_identifier(node)
    return text(source, ident) if ident is not None else text(source, node)


def _supers(source, node):
    """Parents and protocol conformances after `:` — Swift doesn't distinguish them at parse
    time, so (like Dart's mixins) all go into `supers`."""
    return [_name_text(source, spec) for spec in named(node, 'inheritance_specifier')]


def _member_name(source, node, type_name):
    if node.type == 'init_declaration':
        return type_name  # Swift has no named-constructor syntax like Dart's `Class.named`.
    if node.type == 'deinit_declaration':
        return 'deinit'
    name = node.child_by_field_name('name')
    return _name_text(source, name) if name is not None else None


def _walk_members(source, body, decl):
    start = None
    for child in body.named_children:
        if child.type in LEADING:
            start = start or line(child)
            continue
        if child.type in MEMBER_KINDS:
            name = _member_name(source, child, decl['name'])
            if name:
                add_member(decl, name, start or line(child), end_line(child))
        start = None


def _type_decl(rel, source, node, kind, begin):
    name = _name_text(source, node.child_by_field_name('name'))
    decl = declaration(rel, name, kind, begin, end_line(node), _supers(source, node))
    body = node.child_by_field_name('body')
    if body is not None:
        _walk_members(source, body, decl)
    return decl


def extract(rel, source, root):
    decls = []
    start = None
    for node in root.named_children:
        if node.type in LEADING:
            start = start or line(node)
            continue
        begin = start or line(node)
        decl = None
        if node.type == 'class_declaration':
            token = node.child_by_field_name('declaration_kind').type
            decl = _type_decl(rel, source, node, KIND_BY_TOKEN.get(token, 'class'), begin)
        elif node.type == 'protocol_declaration':
            decl = _type_decl(rel, source, node, 'protocol', begin)
        elif node.type == 'function_declaration':
            name = node.child_by_field_name('name')
            decl = declaration(rel, _name_text(source, name), 'function', begin, end_line(node))
        elif node.type == 'property_declaration':
            name = node.child_by_field_name('name')
            if name is not None:
                decl = declaration(rel, _name_text(source, name), 'top-level variable', begin,
                                   end_line(node))
        elif node.type == 'typealias_declaration':
            name = node.child_by_field_name('name')
            if name is not None:
                decl = declaration(rel, _name_text(source, name), 'typedef', begin, end_line(node))
        if decl:
            decls.append(decl)
        start = None
    return decls


class Swift(Language):
    def __init__(self):
        super().__init__('swift', ('.swift',), (), extract)


LANGUAGE = Swift()
