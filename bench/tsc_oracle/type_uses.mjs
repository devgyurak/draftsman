// The names the TypeScript compiler resolves inside bodies, one JSON object per line: the
// answer key the extractor's body relations are compared with (bench/tsc_oracle/oracle.py,
// records as bench/answer_key.py describes them).
//
//   node type_uses.mjs OUT.jsonl ROOT TSCONFIG SOURCES-FILE
//
// ROOT is the directory the extractor is given: paths and module ids are relative to it.
// TSCONFIG is the project's tsconfig.json, whose compilerOptions are used ("-" for
// defaults); SOURCES-FILE lists the source files, one per line. Only they are recorded,
// and only their types are the project's. Records:
//
//   {"use": ...}        a name in a body: a class, interface or enum (kind "type"), a type
//                       parameter, a type alias ("alias"), a class declared in a body
//                       ("local"), or, when it starts upper-case, a variable or a name
//                       that resolves to nothing ("var", "error")
//   {"declared": ...}   a class, interface or enum the extractor sees as a type: one not
//                       inside a function, by its id (module path + namespaces + name)
//   {"diagnostic": ...} a compile error; the uses around it may be missing or "error"
//
// A body is a method, constructor or accessor body, a property initializer, a static
// block or an enum member's initializer, with everything inside them (functions, classes,
// object literals); decorators are not read. "pos" is "type" where only a type can stand
// (`: Foo`, `as Foo`, `<Foo>`, `implements Foo`, `import("./m").Foo`) and "receiver"
// where a value stands, which a variable may be (`new Foo()`, `Foo.m()`, `x instanceof
// Foo`, `typeof Foo`, `<Foo />`, `Foo` passed as an argument). Of a dotted name (`ns.Foo.m()`) each part that
// is a type is recorded, "maximal" when no type part follows. Lines are 1-based, columns
// 0-based in UTF-16 code units.
//
// The names of a type's declarations are recorded too, with "pos" "declared" (issue #7):
// its heritage clauses, its properties' and property signatures' types, its methods',
// constructors', accessors' and method signatures' parameter and return types, with their
// type arguments, and the decorators on the class, its members and their parameters (the
// names in the decorator's expression, read as values). Such a record also has "role"
// ("super", "field" for a property or a constructor's parameter property, "signature",
// "annotation") and "in_args" (inside type arguments); one of a type alias also has
// "targets", the project types the alias names through any aliases it names, and
// "project" whether there is one. Type parameters' bounds, index,
// call and construct signatures are not recorded: the extractor draws nothing from them.

import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const [out, rootArg, tsconfig, sourcesFile] = process.argv.slice(2);
const root = path.resolve(rootArg);
const files = fs.readFileSync(sourcesFile, "utf8").split("\n").filter(Boolean)
  .map((f) => path.resolve(f));
const sources = new Set(files);

let options = {
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
  moduleResolution: ts.ModuleResolutionKind.Bundler, jsx: ts.JsxEmit.Preserve,
  experimentalDecorators: true, strict: true,
};
if (tsconfig !== "-") {
  const read = ts.readConfigFile(tsconfig, ts.sys.readFile);
  if (read.error) throw new Error(ts.flattenDiagnosticMessageText(read.error.messageText, "\n"));
  options = ts.parseJsonConfigFileContent(read.config, ts.sys, path.dirname(tsconfig)).options;
}
// nothing is written; project references and build info are no concern of one program
options = { ...options, noEmit: true, skipLibCheck: true, composite: false, incremental: false,
            declaration: false, declarationMap: false, tsBuildInfoFile: undefined };
const program = ts.createProgram(files, options);
const checker = program.getTypeChecker();
const lines = [];
const emit = (rec) => lines.push(JSON.stringify(rec));
// while a declaration's names are recorded: {role, args} (args: inside type arguments)
let decl = null;

const rel = (file) => path.relative(root, file).split(path.sep).join("/");

// as the extractor names a module (langs/typescript.py, _module)
function moduleId(file) {
  let id = rel(file).replace(/\.(d\.)?([cm]?[jt]sx?)$/, "");
  if (id.endsWith("/index")) id = id.slice(0, -"/index".length);
  return id;
}

const isTypeDecl = (n) => ts.isClassDeclaration(n) || ts.isInterfaceDeclaration(n) ||
  ts.isEnumDeclaration(n);

// the id the extractor gives a declaration, or null when it is inside a function (the
// extractor does not see it as a type)
function typeId(decl) {
  if (!decl.name) return null;
  const names = [decl.name.text];
  for (let p = decl.parent; !ts.isSourceFile(p); p = p.parent) {
    if (ts.isModuleDeclaration(p)) {
      if (ts.isIdentifier(p.name) && !(p.flags & ts.NodeFlags.GlobalAugmentation)) {
        names.unshift(p.name.text);
      }
    } else if (!ts.isModuleBlock(p)) {
      return null;
    }
  }
  return `${moduleId(decl.getSourceFile().fileName)}.${names.join(".")}`;
}

function resolved(sym) {
  if (sym && sym.flags & ts.SymbolFlags.Alias) {
    const target = checker.getAliasedSymbol(sym);
    return target && target.declarations ? target : null;
  }
  return sym;
}

function asType(decl, sym) {
  const file = decl.getSourceFile().fileName;
  if (!sources.has(file)) {
    return { kind: "type", target: checker.getFullyQualifiedName(sym), project: false };
  }
  const id = typeId(decl);
  return id ? { kind: "type", target: id, project: true } : { kind: "local" };
}

// what a name stands for: in a value position its value meaning, else its type meaning
function classify(sym, value) {
  const s = resolved(sym);
  if (!s) return { kind: "error" };
  const decls = s.declarations ?? [];
  const cls = decls.find((d) => ts.isClassDeclaration(d)) ?? decls.find(ts.isEnumDeclaration);
  if (cls) return asType(cls, s);
  // the standard library's classes are a variable and an interface (`Map`, `Error`)
  const outside = decls.length && decls.every((d) => !sources.has(d.getSourceFile().fileName));
  if (!value || outside) {
    const iface = decls.find(ts.isInterfaceDeclaration);
    if (iface) return asType(iface, s);
    if (decls.some(ts.isTypeParameterDeclaration)) return { kind: "tparam" };
    if (decls.some(ts.isTypeAliasDeclaration)) return { kind: "alias" };
  }
  if (decls.some((d) => ts.isModuleDeclaration(d) || ts.isSourceFile(d))) {
    return { kind: "namespace" };
  }
  return { kind: value ? "var" : "error" };
}

// record the parts of a dotted name from its head: each part that is a type, and the head
// when it is an upper-case variable or nothing; a part that is no type or namespace ends it
function chain(parts, value, pos, from, firstSymbol) {
  const got = [];
  for (let i = 0; i < parts.length; i++) {
    const sym = i === 0 && firstSymbol !== undefined ? firstSymbol
      : checker.getSymbolAtLocation(parts[i]);
    const c = classify(sym, value);
    got.push(c);
    if (c.kind !== "type" && c.kind !== "namespace") break;
  }
  got.forEach((c, i) => {
    const part = parts[i];
    const name = part.text;
    const upper = /^[A-Z]/.test(name);
    if (c.kind === "namespace") return;
    if ((c.kind === "var" || c.kind === "error") && (i > 0 || !upper)) return;
    const sf = part.getSourceFile();
    const { line, character } = sf.getLineAndCharacterOfPosition(part.getStart(sf));
    const rec = { use: name, file: rel(sf.fileName), line: line + 1, col: character,
                  pos: decl ? "declared" : pos, kind: c.kind, target: c.target ?? null,
                  project: c.project ?? false,
                  maximal: !(got[i + 1] && got[i + 1].kind === "type"), from };
    if (decl) Object.assign(rec, { role: decl.role, in_args: decl.args > 0 });
    if (decl && c.kind === "alias") {
      rec.targets = aliasTargets(resolved(i === 0 && firstSymbol !== undefined ? firstSymbol
        : checker.getSymbolAtLocation(part)));
      rec.project = rec.targets.length > 0;
    }
    emit(rec);
  });
}

// the project types a type alias names, through the aliases it names (in a declared
// position the extractor draws those)
function aliasTargets(sym, seen = new Set()) {
  const out = [];
  if (!sym || seen.has(sym)) return out;
  seen.add(sym);
  const alias = (sym.declarations ?? []).find(ts.isTypeAliasDeclaration);
  if (!alias || !sources.has(alias.getSourceFile().fileName)) return out;
  const walk = (n) => {
    let name = null;
    if (ts.isTypeReferenceNode(n)) name = n.typeName;
    else if (ts.isImportTypeNode(n) && !n.isTypeOf) name = n.qualifier;
    else if (ts.isExpressionWithTypeArguments(n)) name = n.expression;
    if (name) {
      // as a name written in a declared position is recorded (chain): the last part that
      // is a type, after namespaces and types (`HttpStatus.OK`, an enum member's type,
      // names HttpStatus)
      const parts = ts.isQualifiedName(name) ? entityParts(name)
        : ts.isPropertyAccessExpression(name) ? (accessParts(name) ?? [name.name]) : [name];
      let last = null;
      for (const part of parts) {
        const s = resolved(checker.getSymbolAtLocation(part));
        const c = classify(s, false);
        if (c.kind === "type" || c.kind === "alias") last = [s, c];
        else if (c.kind !== "namespace") break;
      }
      if (last && last[1].kind === "type" && last[1].project) out.push(last[1].target);
      else if (last && last[1].kind === "alias") out.push(...aliasTargets(last[0], seen));
    }
    ts.forEachChild(n, walk);
  };
  walk(alias.type);
  return [...new Set(out)];
}

function entityParts(name) {   // `ns.Foo` in a type
  return ts.isQualifiedName(name) ? [...entityParts(name.left), name.right] : [name];
}

function accessParts(expr) {   // `ns.Foo.m` as an expression, or null if no dotted name
  if (ts.isIdentifier(expr)) return [expr];
  if (ts.isPropertyAccessExpression(expr) && ts.isIdentifier(expr.name)) {
    const left = accessParts(expr.expression);
    return left && [...left, expr.name];
  }
  return null;
}

// the head of a dotted value: the identifier and the property names after it
function valueHead(id) {
  const parts = [id];
  let cur = id;
  while (ts.isPropertyAccessExpression(cur.parent) && cur.parent.expression === cur &&
         ts.isIdentifier(cur.parent.name)) {
    parts.push(cur.parent.name);
    cur = cur.parent;
  }
  return parts;
}

// an identifier that names a value here, not a declaration, a property or a label
function isValueReference(id) {
  const p = id.parent;
  if (p.name === id || p.propertyName === id || p.label === id) return false;
  if (ts.isQualifiedName(p) || ts.isJsxAttribute(p) || ts.isMetaProperty(p)) return false;
  if (ts.isJsxOpeningElement(p) || ts.isJsxSelfClosingElement(p) ||
      ts.isJsxClosingElement(p)) return false;   // read as the element's tag
  return true;
}

function heritage(clause, from) {
  // a class extends an expression; `implements` and an interface's `extends` name types
  const value = clause.token === ts.SyntaxKind.ExtendsKeyword &&
    !ts.isInterfaceDeclaration(clause.parent);
  for (const t of clause.types) {
    const parts = accessParts(t.expression);
    if (parts) chain(parts, value, value ? "receiver" : "type", from);
    typeArgs(t.typeArguments, from);
  }
}

function typeArgs(args, from) {
  if (decl) decl.args++;
  for (const a of args ?? []) visit(a, from, true);
  if (decl) decl.args--;
}

function visit(node, from, inType) {
  if (ts.isDecorator(node) || ts.isJsxClosingElement(node)) return;
  if (ts.isHeritageClause(node)) return heritage(node, from);
  if (!inType && ts.isTypeNode(node) && !ts.isExpressionWithTypeArguments(node)) inType = true;
  if (inType) {
    if (ts.isTypeReferenceNode(node)) {
      chain(entityParts(node.typeName), false, "type", from);
      typeArgs(node.typeArguments, from);
      return;
    }
    if (ts.isTypeQueryNode(node)) {   // `typeof Foo`: a value
      chain(entityParts(node.exprName), true, "receiver", from);
      typeArgs(node.typeArguments, from);
      return;
    }
    if (ts.isImportTypeNode(node)) {   // `import("./m").Foo`, `typeof import("./m").Foo`
      if (node.qualifier) {
        chain(entityParts(node.qualifier), node.isTypeOf, node.isTypeOf ? "receiver" : "type",
              from);
      }
      typeArgs(node.typeArguments, from);
      return;
    }
    if (ts.isComputedPropertyName(node)) return;
    return ts.forEachChild(node, (c) => visit(c, from, true));
  }
  if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
    const parts = accessParts(node.tagName);
    if (parts && /^[A-Z]/.test(parts[0].text) || parts && parts.length > 1) {
      chain(parts, true, "receiver", from);
    }
  } else if (ts.isShorthandPropertyAssignment(node)) {   // `{ Foo }`
    chain([node.name], true, "receiver", from,
          checker.getShorthandAssignmentValueSymbol(node) ?? null);
    if (node.objectAssignmentInitializer) visit(node.objectAssignmentInitializer, from, false);
    return;
  } else if (ts.isIdentifier(node) && isValueReference(node)) {
    chain(valueHead(node), true, "receiver", from);
    return;
  }
  ts.forEachChild(node, (c) => visit(c, from, false));
}

// the bodies of a type's members
function regions(decl) {
  const out = [];
  if (ts.isEnumDeclaration(decl)) {
    for (const m of decl.members) if (m.initializer) out.push(m.initializer);
    return out;
  }
  if (!ts.isClassDeclaration(decl)) return out;
  for (const m of decl.members) {
    if ((ts.isMethodDeclaration(m) || ts.isConstructorDeclaration(m) ||
         ts.isGetAccessorDeclaration(m) || ts.isSetAccessorDeclaration(m) ||
         ts.isClassStaticBlockDeclaration(m)) && m.body) {
      out.push(m.body);
    } else if (ts.isPropertyDeclaration(m) && m.initializer) {
      out.push(m.initializer);
    }
  }
  return out;
}

// the names of a declaration's ``node`` (a type, a decorator, a heritage clause)
function inDecl(node, from, role) {
  if (!node) return;
  const was = decl;
  decl = { role, args: 0 };
  if (ts.isDecorator(node)) visit(node.expression, from, false);
  else if (ts.isHeritageClause(node)) heritage(node, from);
  else visit(node, from, true);
  decl = was;
}

function decorators(node, from) {
  for (const d of (ts.canHaveDecorators(node) && ts.getDecorators(node)) || []) {
    inDecl(d, from, "annotation");
  }
}

// what the extractor reads of a type's declarations (module comment)
function declarationNames(type, id) {
  decorators(type, id);
  for (const h of type.heritageClauses ?? []) inDecl(h, id, "super");
  if (ts.isEnumDeclaration(type)) return;
  for (const m of type.members) {
    decorators(m, id);
    if (ts.isPropertyDeclaration(m) || ts.isPropertySignature(m)) {
      inDecl(m.type, id, "field");
    } else if (ts.isMethodDeclaration(m) || ts.isConstructorDeclaration(m) ||
               ts.isGetAccessorDeclaration(m) || ts.isSetAccessorDeclaration(m) ||
               ts.isMethodSignature(m)) {
      for (const p of m.parameters) {
        decorators(p, id);
        const property = ts.isConstructorDeclaration(m) &&
          (ts.getCombinedModifierFlags(p) & (ts.ModifierFlags.ParameterPropertyModifier));
        inDecl(p.type, id, property ? "field" : "signature");
      }
      inDecl(m.type, id, "signature");
    }
  }
}

const declared = new Set();
function declarations(node, sf) {
  if (isTypeDecl(node)) {
    const id = typeId(node);
    if (id) {
      const key = `${id}\t${rel(sf.fileName)}`;
      if (!declared.has(key)) {
        declared.add(key);
        emit({ declared: id, file: rel(sf.fileName) });
      }
      for (const r of regions(node)) visit(r, id, false);
      declarationNames(node, id);
    }
  }
  if (ts.isSourceFile(node) || ts.isModuleDeclaration(node) || ts.isModuleBlock(node) ||
      isTypeDecl(node)) {
    ts.forEachChild(node, (c) => declarations(c, sf));
  }
}

for (const file of files) {
  const sf = program.getSourceFile(file);
  if (!sf) continue;
  declarations(sf, sf);
  const diags = [...program.getSyntacticDiagnostics(sf), ...program.getSemanticDiagnostics(sf)];
  for (const d of diags) {
    if (d.category !== ts.DiagnosticCategory.Error || d.start === undefined) continue;
    emit({ diagnostic: ts.flattenDiagnosticMessageText(d.messageText, "\n").split("\n")[0],
           file: rel(file), line: sf.getLineAndCharacterOfPosition(d.start).line + 1 });
  }
}
fs.writeFileSync(out, lines.length ? lines.join("\n") + "\n" : "");
