"""Objective-C: @interface/@implementation classes, categories, protocols, with their methods
and properties. A category merges into its class by name, like a Dart/Swift extension."""
import re

from .base import Language, add_member, declaration, end_line, line, text

LEADING = {'comment'}
MEMBER_KINDS = {'property_declaration', 'method_declaration', 'method_definition'}
# NS_ENUM/NS_OPTIONS confuse the grammar into an ERROR node; pull the type name out by hand.
NS_ENUM = re.compile(r'\b(?:typedef\s+)?NS_(?:ENUM|OPTIONS|CLOSED_ENUM)\s*\(\s*[\w *]+,\s*(\w+)\s*\)')


def _protocol_names(node):
    names = []
    for child in node.named_children:
        if child.type in ('identifier', 'type_identifier'):
            names.append(child)
        elif child.type == 'type_name':
            names.extend(c for c in child.named_children if c.type in ('identifier', 'type_identifier'))
    return names


def _declared_identifier(node):
    """The last identifier in a declarator — the variable name, after any `*`/generics."""
    last = None
    for child in node.named_children:
        if child.type == 'identifier':
            last = child
        else:
            found = _declared_identifier(child)
            if found is not None:
                last = found
    return last


def _property_name(source, node):
    declarator = None
    for child in node.named_children:
        if child.type in ('struct_declaration', 'declaration'):
            declarator = child
    if declarator is None:
        return None
    name = _declared_identifier(declarator)
    return text(source, name) if name is not None else None


def _selector_name(source, node):
    """A method's full selector: `tableView:didSelectRowAtIndexPath:` for a multi-keyword one,
    or the bare name for a no-argument one."""
    keywords = [child for child in node.children if child.type == 'identifier']
    if not keywords:
        return None
    has_params = any(child.type == 'method_parameter' for child in node.children)
    if not has_params:
        return text(source, keywords[0])
    return ':'.join(text(source, keyword) for keyword in keywords) + ':'


def _member_name(source, node):
    if node.type == 'property_declaration':
        return _property_name(source, node)
    return _selector_name(source, node)


def _walk_members(source, node, decl):
    start = None
    for child in node.named_children:
        if child.type in LEADING:
            start = start or line(child)
            continue
        if child.type in MEMBER_KINDS:
            name = _member_name(source, child)
            if name:
                add_member(decl, name, start or line(child), end_line(child))
        start = None


def _class_decl(rel, source, node, begin, kind):
    identifiers = [child for child in node.children if child.type == 'identifier']
    if not identifiers:
        return None
    name = text(source, identifiers[0])
    category = node.child_by_field_name('category')
    supers = []
    superclass = node.child_by_field_name('superclass')
    if superclass is not None:
        supers.append(text(source, superclass))
    for child in node.children:
        if child.type in ('parameterized_arguments', 'protocol_reference_list'):
            supers.extend(text(source, proto) for proto in _protocol_names(child))
    decl = declaration(rel, name, 'category' if category is not None else kind, begin,
                       end_line(node), supers)
    _walk_members(source, node, decl)
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
        if node.type == 'class_interface':
            decl = _class_decl(rel, source, node, begin, 'class')
        elif node.type == 'class_implementation':
            identifiers = [child for child in node.children if child.type == 'identifier']
            if identifiers:
                name = text(source, identifiers[0])
                impl = declaration(rel, name, 'implementation', begin, end_line(node))
                for section in node.named_children:
                    if section.type == 'implementation_definition':
                        _walk_members(source, section, impl)
                decl = impl
        elif node.type == 'protocol_declaration':
            decl = _class_decl(rel, source, node, begin, 'protocol')
        elif node.type == 'type_definition':
            # NS_ENUM/NS_OPTIONS: the grammar doesn't parse the macro form, so look at the text.
            match = NS_ENUM.search(text(source, node))
            if match:
                decl = declaration(rel, match.group(1), 'enum', begin, end_line(node))
        if decl:
            decls.append(decl)
        start = None
    return decls


class ObjC(Language):
    def __init__(self):
        super().__init__('objc', ('.m', '.mm', '.h'), (), extract)


LANGUAGE = ObjC()
