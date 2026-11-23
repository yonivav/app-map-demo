// Prints the declarations of Dart files as JSON, for app-map's code index.
//
// Usage: dart_declarations <repo root>   (reads repo-relative paths from stdin, one per line)
// Output: {"<path>": [{name, kind, file, from, to, supers, members: {name: [from, to]}}]}
//
// Uses the official parser, so it reads every syntax the installed SDK supports. Names are
// read dynamically because the AST moved them between analyzer versions (`name` → `namePart`).
import 'dart:convert';
import 'dart:io';

import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/source/line_info.dart';

void main(List<String> args) {
  final String root = args.first;
  final Map<String, Object> out = <String, Object>{};
  String? rel = stdin.readLineSync();
  final List<String> paths = <String>[];
  while (rel != null) {
    if (rel.trim().isNotEmpty) paths.add(rel.trim());
    rel = stdin.readLineSync();
  }
  for (final String path in paths) {
    try {
      out[path] = _declarations(path, File('$root/$path').readAsStringSync());
    } on Object catch (error) {
      stderr.writeln('dart_declarations: $path: $error');
      out[path] = const <Object>[];
    }
  }
  stdout.write(jsonEncode(out));
}

String _lexeme(Object? token) =>
    token == null ? '' : (token as dynamic).lexeme as String;

/// A type declaration's name: `namePart.typeName` in newer analyzers, `name` in older ones.
String _typeName(Object node) {
  try {
    return _lexeme((node as dynamic).namePart.typeName);
  } on NoSuchMethodError {
    return _lexeme((node as dynamic).name);
  }
}

List<Map<String, Object?>> _declarations(String rel, String source) {
  final ParseStringResult result =
      parseString(content: source, path: rel, throwIfDiagnostics: false);
  final LineInfo lines = result.lineInfo;
  int line(int offset) => lines.getLocation(offset).lineNumber;
  Map<String, Object?> decl(
          String name, String kind, AstNode node, List<String> supers) =>
      <String, Object?>{
        'file': rel,
        'name': name,
        'kind': kind,
        'from': line(node.offset),
        'to': line(node.end),
        'supers': supers,
        'members': <String, List<int>>{},
      };
  List<String> mixins(WithClause? clause) => clause == null
      ? <String>[]
      : clause.mixinTypes
          .map((NamedType type) =>
              _namedType(type))
          .toList();

  final List<Map<String, Object?>> decls = <Map<String, Object?>>[];
  for (final CompilationUnitMember member in result.unit.declarations) {
    Map<String, Object?>? found;
    if (member is ClassDeclaration) {
      final NamedType? parent = member.extendsClause?.superclass;
      found = decl(_typeName(member), 'class', member, <String>[
        if (parent != null) _namedType(parent),
        ...mixins(member.withClause),
      ]);
    } else if (member is ClassTypeAlias) {
      found = decl(_lexeme(member.name), 'class', member, <String>[
        _namedType(member.superclass),
        ...mixins(member.withClause),
      ]);
    } else if (member is EnumDeclaration) {
      found = decl(_typeName(member), 'enum', member, <String>[]);
    } else if (member is MixinDeclaration) {
      found = decl(_lexeme(member.name), 'mixin', member, <String>[]);
    } else if (member is ExtensionTypeDeclaration) {
      found = decl(_typeName(member), 'extension type', member, <String>[]);
    } else if (member is ExtensionDeclaration && member.name != null) {
      found = decl(_lexeme(member.name), 'extension', member, <String>[]);
    } else if (member is TypeAlias) {
      found = decl(_lexeme(member.name), 'typedef', member, <String>[]);
    } else if (member is FunctionDeclaration) {
      found = decl(_lexeme(member.name), 'function', member, <String>[]);
      final TypeAnnotation? returned = member.returnType;
      if (returned is NamedType) found['returns'] = _namedType(returned);
    } else if (member is TopLevelVariableDeclaration) {
      for (final VariableDeclaration variable in member.variables.variables) {
        final Map<String, Object?> top = decl(
            _lexeme(variable.name),
            'top-level ${member.variables.keyword?.lexeme ?? 'variable'}',
            member, <String>[]);
        final TypeAnnotation? declared = member.variables.type;
        if (declared is NamedType) top['returns'] = _namedType(declared);
        decls.add(top);
      }
    }
    if (found == null) continue;
    final _References references = _References();
    member.accept(references);
    found['refs'] = <String, List<String>>{
      'types': (references.types..remove(found['name'])).toList()..sort(),
      'builds': (references.builds..remove(found['name'])).toList()..sort(),
      'calls': (references.calls..remove(found['name'])).toList()..sort(),
      'implements': _implemented(member),
      'mixins': member is ClassDeclaration
          ? mixins(member.withClause)
          : member is ClassTypeAlias
              ? mixins(member.withClause)
              : <String>[],
      'names': references.names.toList()..sort(),
    };
    final Map<String, List<int>> members =
        found['members']! as Map<String, List<int>>;
    void add(String name, AstNode node) => members.putIfAbsent(
        name, () => <int>[line(node.offset), line(node.end)]);
    // The type behind each field and getter, so `_repository.load()` reads as a call
    // on ItemRepository; and each method's calls in source order, for sequence traces.
    final Map<String, String> memberTypes = <String, String>{};
    final Map<String, List<List<String>>> flows = <String, List<List<String>>>{};
    final Map<String, String> memberKinds = <String, String>{};
    for (final AstNode node in _bodyMembers(member)) {
      if (node is MethodDeclaration) {
        add(_lexeme(node.name), node);
        memberKinds.putIfAbsent(
            _lexeme(node.name), () => node.isGetter ? 'getter' : node.isSetter ? 'setter' : 'method');
        final TypeAnnotation? returned = node.returnType;
        if (node.isGetter && returned is NamedType) memberTypes[_lexeme(node.name)] = _namedType(returned);
        final _Flow flow = _Flow();
        node.body.accept(flow);
        if (flow.steps.isNotEmpty) flows[_lexeme(node.name)] = flow.steps;
      } else if (node is FieldDeclaration) {
        for (final VariableDeclaration variable in node.fields.variables) {
          add(_lexeme(variable.name), node);
          memberKinds.putIfAbsent(_lexeme(variable.name), () => node.isStatic ? 'static' : 'field');
          final String? type = _typeOf(node.fields.type, variable.initializer);
          if (type != null) memberTypes[_lexeme(variable.name)] = type;
        }
      } else if (node is ConstructorDeclaration) {
        final String named = _lexeme(node.name);
        add(
            named.isEmpty
                ? found['name']! as String
                : '${found['name']}.$named',
            node);
      } else if (node is EnumConstantDeclaration) {
        add(_lexeme(node.name), node);
      }
    }
    found['memberTypes'] = memberTypes;
    found['memberKinds'] = memberKinds;
    found['flows'] = flows;
    decls.add(found);
  }
  return decls;
}

/// A field's type: its annotation, else what its initializer builds (`Foo.instance`, `Foo()`).
String? _typeOf(TypeAnnotation? annotation, Expression? initializer) {
  if (annotation is NamedType) {
    // `List<Card>` → `List<Card>`, so a list field can be drawn as "list of".
    final List<TypeAnnotation> args = annotation.typeArguments?.arguments ?? <TypeAnnotation>[];
    final String name = _namedType(annotation);
    if ((name == 'List' || name == 'Set' || name == 'Iterable') && args.length == 1 && args.first is NamedType) {
      return '$name<${_namedType(args.first as NamedType)}>';
    }
    return name;
  }
  final Expression? value = initializer;
  if (value is PrefixedIdentifier) return value.prefix.name;
  if (value is MethodInvocation && value.target == null) return value.methodName.name;
  if (value is MethodInvocation && value.target is SimpleIdentifier) {
    return (value.target! as SimpleIdentifier).name;
  }
  if (value is InstanceCreationExpression) return _namedType(value.constructorName.type);
  return null;
}

/// Calls and getter reads in source order: [target, member, 'call' | 'get'].
class _Flow extends RecursiveAstVisitor<void> {
  final List<List<String>> steps = <List<String>>[];

  static String _target(Expression? target) => switch (target) {
        null => '',
        SimpleIdentifier() => target.name,
        PrefixedIdentifier() => '${target.prefix.name}.${target.identifier.name}',
        PropertyAccess() => '${_target(target.target)}.${target.propertyName.name}',
        ThisExpression() => 'this',
        _ => '?',
      };

  @override
  void visitMethodInvocation(MethodInvocation node) {
    // Arguments run before the call itself.
    node.target?.accept(this);
    node.argumentList.accept(this);
    if (steps.length < 120) steps.add(<String>[_target(node.target), node.methodName.name, 'call']);
  }

  @override
  void visitPrefixedIdentifier(PrefixedIdentifier node) {
    if (steps.length < 120) steps.add(<String>[node.prefix.name, node.identifier.name, 'get']);
  }

  @override
  void visitPropertyAccess(PropertyAccess node) {
    node.target?.accept(this);
    if (steps.length < 120) {
      steps.add(<String>[_target(node.target), node.propertyName.name, 'get']);
    }
  }
}

String _namedType(NamedType type) {
  try {
    return _lexeme((type as dynamic).name2);
  } on NoSuchMethodError {
    return _lexeme((type as dynamic).name);
  }
}

/// The member nodes inside a declaration's body, whatever the body node is called.
List<AstNode> _bodyMembers(AstNode node) {
  bool isMember(AstNode child) => child is ClassMember || child is EnumConstantDeclaration;
  final List<AstNode> members = <AstNode>[];
  for (final AstNode child in node.childEntities.whereType<AstNode>()) {
    if (isMember(child)) {
      members.add(child);
    } else {
      members.addAll(child.childEntities.whereType<AstNode>().where(isMember));
    }
  }
  return members;
}

/// Type names a declaration mentions, and the constructors it calls (`Foo(...)` parses as a
/// method call named `Foo` without type information, so an upper-case call counts as one).
class _References extends RecursiveAstVisitor<void> {
  final Set<String> types = <String>{};
  final Set<String> builds = <String>{};

  /// `Foo.bar(...)`: a named constructor or a static call — the caller decides by Foo's role.
  final Set<String> calls = <String>{};

  // `[Foo]` in a doc comment is a mention, not a use.
  @override
  void visitComment(Comment node) {}

  /// `Foo` or a private `_Foo`.
  static bool _isTypeName(String name) {
    final String bare = name.startsWith('_') ? name.substring(1) : name;
    return bare.isNotEmpty && bare[0].toUpperCase() == bare[0] && bare[0].toLowerCase() != bare[0];
  }

  /// Lower-case names: a top-level getter like `settingsLogic` hides the type it returns.
  final Set<String> names = <String>{};

  @override
  void visitNamedType(NamedType node) {
    final String name = _namedType(node);
    if (_isTypeName(name)) types.add(name);
    super.visitNamedType(node);
  }

  @override
  void visitInstanceCreationExpression(InstanceCreationExpression node) {
    final String name = _namedType(node.constructorName.type);
    if (_isTypeName(name)) builds.add(name);
    super.visitInstanceCreationExpression(node);
  }

  @override
  void visitMethodInvocation(MethodInvocation node) {
    final String name = node.methodName.name;
    final Expression? target = node.target;
    if (target == null && _isTypeName(name)) {
      builds.add(name);
    } else if (target is SimpleIdentifier && _isTypeName(target.name)) {
      // `Foo.named(...)` or a static call: without types the two look the same.
      types.add(target.name);
      calls.add(target.name);
    }
    super.visitMethodInvocation(node);
  }

  @override
  void visitPrefixedIdentifier(PrefixedIdentifier node) {
    if (_isTypeName(node.prefix.name)) types.add(node.prefix.name);
    super.visitPrefixedIdentifier(node);
  }

  @override
  void visitSimpleIdentifier(SimpleIdentifier node) {
    if (_isTypeName(node.name) && node.parent is! PrefixedIdentifier) {
      types.add(node.name);
    } else if (!_isTypeName(node.name)) {
      names.add(node.name);
    }
    super.visitSimpleIdentifier(node);
  }
}

List<String> _implemented(AstNode member) {
  final Object? clause = member is ClassDeclaration
      ? member.implementsClause
      : member is ClassTypeAlias
          ? member.implementsClause
          : null;
  if (clause is! ImplementsClause) return <String>[];
  return clause.interfaces.map(_namedType).toList();
}
