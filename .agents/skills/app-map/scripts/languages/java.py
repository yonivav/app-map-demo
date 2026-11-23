"""Java: classes, interfaces, enums and records, with their members."""
from .base import Language, add_member, declaration, end_line, line, named, text

LEADING = {'line_comment', 'block_comment'}
TYPE_NODES = {
    'class_declaration': 'class', 'interface_declaration': 'interface',
    'enum_declaration': 'enum', 'record_declaration': 'record',
}
MEMBER_KINDS = {
    'field_declaration', 'method_declaration', 'constructor_declaration', 'enum_constant',
    'class_declaration', 'interface_declaration', 'enum_declaration', 'record_declaration',
}


def _supers(source, node):
    names = []
    superclass = node.child_by_field_name('superclass')
    if superclass is not None:
        names.append(text(source, superclass.named_children[0]))
    interfaces = node.child_by_field_name('interfaces')
    type_list = (named(interfaces, 'type_list')[0] if interfaces is not None
                and named(interfaces, 'type_list') else interfaces)
    if type_list is not None:
        names.extend(text(source, iface) for iface in named(type_list, 'type_identifier',
                                                             'generic_type', 'scoped_type_identifier'))
    return names


def _member_names(source, node):
    if node.type in TYPE_NODES:
        name = node.child_by_field_name('name')
        return [text(source, name)] if name is not None else []
    if node.type == 'enum_constant':
        name = node.child_by_field_name('name')
        return [text(source, name)] if name is not None else []
    if node.type == 'constructor_declaration':
        name = node.child_by_field_name('name')
        return [text(source, name)] if name is not None else []
    if node.type == 'method_declaration':
        name = node.child_by_field_name('name')
        return [text(source, name)] if name is not None else []
    if node.type == 'field_declaration':
        return [text(source, decl.child_by_field_name('name'))
                for decl in node.children if decl.type == 'variable_declarator'
                and decl.child_by_field_name('name') is not None]
    return []


def _record_components(source, node, decl):
    """`record Foo(String a, int b)` — a record's fields are its component parameters."""
    params = node.child_by_field_name('parameters')
    if params is None:
        return
    for param in params.named_children:
        name = param.child_by_field_name('name')
        if name is not None:
            add_member(decl, text(source, name), line(param), end_line(param))


def _walk_members(source, body, decl):
    start = None
    for child in body.named_children:
        if child.type in LEADING:
            start = start or line(child)
            continue
        if child.type in MEMBER_KINDS:
            end = end_line(child)
            for name in _member_names(source, child):
                add_member(decl, name, start or line(child), end)
        start = None


def extract(rel, source, root):
    decls = []
    start = None
    for node in root.named_children:
        if node.type in LEADING:
            start = start or line(node)
            continue
        begin = start or line(node)
        decl = None
        kind = TYPE_NODES.get(node.type)
        if kind is not None:
            name = node.child_by_field_name('name')
            if name is not None:
                decl = declaration(rel, text(source, name), kind, begin, end_line(node),
                                   _supers(source, node))
                if node.type == 'record_declaration':
                    _record_components(source, node, decl)
                body = node.child_by_field_name('body')
                if body is not None:
                    _walk_members(source, body, decl)
        elif node.type == 'method_declaration':
            name = node.child_by_field_name('name')
            if name is not None:
                decl = declaration(rel, text(source, name), 'function', begin, end_line(node))
        if decl:
            decls.append(decl)
        start = None
    return decls


class Java(Language):
    def __init__(self):
        super().__init__('java', ('.java',), (), extract)


LANGUAGE = Java()
