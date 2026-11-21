import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.tree.LineMap;
import com.sun.source.tree.MemberReferenceTree;
import com.sun.source.tree.MemberSelectTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.NewClassTree;
import com.sun.source.tree.Tree;
import com.sun.source.tree.VariableTree;
import com.sun.source.tree.AnnotationTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.SourcePositions;
import com.sun.source.util.TreePath;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.Trees;

import java.io.IOException;
import java.io.PrintWriter;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.lang.model.element.Element;
import javax.lang.model.element.ElementKind;
import javax.lang.model.element.NestingKind;
import javax.lang.model.element.PackageElement;
import javax.lang.model.element.TypeElement;
import javax.lang.model.type.DeclaredType;
import javax.lang.model.type.TypeKind;
import javax.lang.model.type.TypeMirror;
import javax.lang.model.util.Elements;
import javax.lang.model.util.Types;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;

/**
 * The names javac resolves inside bodies, one JSON object per line: the answer key the
 * extractor's body relations are compared with (bench/javac_oracle/oracle.py).
 *
 *   java TypeUses OUT.jsonl ROOT OPTIONS-FILE SOURCES-FILE [CONTEXT-FILE [STUBS-FILE [PEERS-FILE]]]
 *
 * OPTIONS-FILE holds javac options, SOURCES-FILE the source files, one per line.
 * CONTEXT-FILE lists files javac needs that are not among the sources the extractor reads
 * (generated ones): compiled, never recorded, and their types count as outside.
 * STUBS-FILE is the reverse, "NAME<tab>FILE" per line: a top-level type the extractor
 * reads from FILE that javac only has as a class file (Netty's stubs of JDK types); it and
 * its nested types count as in the sources. PEERS-FILE lists sources recorded by another
 * run (a module built for another release): compiled, never recorded, still sources. Records:
 *
 *   {"use": ...}       a name in a body that javac resolved to a type, a type parameter or
 *                      a local class anywhere, or to a variable in a receiver position
 *                      (upper-case names only: no type is named otherwise)
 *   {"declared": ...}  a type declared in the sources (not local or anonymous)
 *   {"static_star": ...} an `import static T.*;`, and whether T is outside the sources
 *   {"diagnostic": ...} a compile error; the uses around it may be missing or "error"
 *
 * A body is a method or constructor body, an initializer block, a field initializer, an
 * enum constant's arguments and body, and everything inside them (lambdas, anonymous and
 * local classes). Annotations are not read. Lines are 1-based, columns 0-based in chars.
 */
public class TypeUses {
    public static void main(String[] args) throws IOException {
        Path out = Path.of(args[0]);
        Path root = Path.of(args[1]).toAbsolutePath().normalize();
        List<String> options = lines(Path.of(args[2]));
        List<String> files = lines(Path.of(args[3]));
        List<String> context = args.length > 4 ? lines(Path.of(args[4])) : List.of();
        Map<String, String> stubs = new HashMap<>();
        for (String line : args.length > 5 ? lines(Path.of(args[5])) : List.<String>of()) {
            String[] f = line.split("\t");
            stubs.put(f[0], f[1]);
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        DiagnosticCollector<JavaFileObject> diags = new DiagnosticCollector<>();
        StandardJavaFileManager fm = compiler.getStandardFileManager(diags, null,
                StandardCharsets.UTF_8);
        List<String> peers = args.length > 6 ? lines(Path.of(args[6])) : List.of();
        List<String> all = new ArrayList<>(files);
        all.addAll(context);
        all.addAll(peers);
        JavacTask task = (JavacTask) compiler.getTask(null, fm, diags, options, null,
                fm.getJavaFileObjectsFromStrings(all));
        Iterable<? extends CompilationUnitTree> units = task.parse();
        task.analyze();

        Trees trees = Trees.instance(task);
        try (PrintWriter w = new PrintWriter(Files.newBufferedWriter(out, StandardCharsets.UTF_8))) {
            for (Diagnostic<? extends JavaFileObject> d : diags.getDiagnostics()) {
                if (d.getKind() != Diagnostic.Kind.ERROR) {
                    continue;
                }
                String file = d.getSource() == null ? "" : rel(root, Path.of(d.getSource().toUri()));
                w.println("{\"diagnostic\": " + str(d.getMessage(null).split("\n")[0])
                        + ", \"file\": " + str(file) + ", \"line\": " + d.getLineNumber() + "}");
            }
            Set<URI> outside = new HashSet<>();
            for (String f : context) {
                outside.add(Path.of(f).toAbsolutePath().normalize().toUri());
            }
            Set<URI> skipped = new HashSet<>(outside);
            for (String f : peers) {
                skipped.add(Path.of(f).toAbsolutePath().normalize().toUri());
            }
            Scanner scanner = new Scanner(trees, task.getTypes(), task.getElements(), root,
                    outside, stubs.keySet(), w);
            for (Map.Entry<String, String> stub : stubs.entrySet()) {
                scanner.declared(task.getElements().getTypeElement(stub.getKey()), stub.getValue());
            }
            for (CompilationUnitTree cu : units) {
                if (!skipped.contains(cu.getSourceFile().toUri())) {
                    scanner.unit(cu);
                }
            }
        }
    }

    static List<String> lines(Path p) throws IOException {
        List<String> out = new ArrayList<>();
        for (String line : Files.readAllLines(p, StandardCharsets.UTF_8)) {
            if (!line.isBlank()) {
                out.add(line.strip());
            }
        }
        return out;
    }

    static String rel(Path root, Path file) {
        Path abs = file.toAbsolutePath().normalize();
        return abs.startsWith(root) ? root.relativize(abs).toString() : abs.toString();
    }

    static String str(String s) {
        if (s == null) {
            return "null";
        }
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"' -> b.append("\\\"");
                case '\\' -> b.append("\\\\");
                case '\n' -> b.append("\\n");
                case '\t' -> b.append("\\t");
                default -> {
                    if (c < 0x20) {
                        b.append(String.format("\\u%04x", (int) c));
                    } else {
                        b.append(c);
                    }
                }
            }
        }
        return b.append('"').toString();
    }

    static final class Scanner extends TreePathScanner<Void, Void> {
        final Trees trees;
        final Types types;
        final Elements elements;
        final Path root;
        final Set<URI> outside;   // the context files
        final Set<String> stubs;
        final PrintWriter w;
        final Map<TypeElement, boolean[]> supers = new HashMap<>();
        final Set<Long> recorded = new HashSet<>();   // an anonymous class reuses its `new X`
        CompilationUnitTree cu;
        String file;
        boolean body;

        Scanner(Trees trees, Types types, Elements elements, Path root, Set<URI> outside,
                Set<String> stubs, PrintWriter w) {
            this.trees = trees;
            this.types = types;
            this.elements = elements;
            this.root = root;
            this.outside = outside;
            this.stubs = stubs;
            this.w = w;
        }

        /** Whether a type is declared in the sources (a stub, not context). */
        boolean inSources(TypeElement te) {
            TreePath p = trees.getPath(te);
            if (p != null) {
                return !outside.contains(p.getCompilationUnit().getSourceFile().toUri());
            }
            TypeElement top = te;
            while (top.getEnclosingElement() instanceof TypeElement o) {
                top = o;
            }
            return stubs.contains(top.getQualifiedName().toString());
        }

        /** A stub type and its nested types, as declared in ``file``. */
        void declared(TypeElement te, String file) {
            if (te == null) {
                return;
            }
            w.println("{\"declared\": " + str(te.getQualifiedName().toString())
                    + ", \"file\": " + str(file) + "}");
            for (Element e : te.getEnclosedElements()) {
                if (e instanceof TypeElement nested) {
                    declared(nested, file);
                }
            }
        }

        void unit(CompilationUnitTree unit) {
            cu = unit;
            recorded.clear();
            file = rel(root, Path.of(unit.getSourceFile().toUri()));
            TreePath top = new TreePath(unit);
            for (ImportTree imp : unit.getImports()) {
                if (!imp.isStatic() || !(imp.getQualifiedIdentifier() instanceof MemberSelectTree ms)
                        || !ms.getIdentifier().contentEquals("*")) {
                    continue;
                }
                TreePath ip = new TreePath(new TreePath(top, imp), ms);
                Element owner = trees.getElement(new TreePath(ip, ms.getExpression()));
                boolean outside = !(owner instanceof TypeElement te) || !inSources(te);
                w.println("{\"static_star\": " + str(ms.getExpression().toString())
                        + ", \"file\": " + str(file) + ", \"line\": " + line(pos(imp))
                        + ", \"outside\": " + outside + "}");
            }
            for (Tree t : unit.getTypeDecls()) {
                scan(new TreePath(top, t), null);
            }
        }

        long pos(Tree t) {
            return trees.getSourcePositions().getStartPosition(cu, t);
        }

        long line(long pos) {
            return cu.getLineMap().getLineNumber(pos);
        }

        void inBody(TreePath p) {
            boolean was = body;
            body = true;
            scan(p, null);
            body = was;
        }

        @Override
        public Void visitClass(ClassTree c, Void v) {
            if (body) {
                return super.visitClass(c, v);
            }
            TreePath cp = getCurrentPath();
            if (trees.getElement(cp) instanceof TypeElement te) {
                w.println("{\"declared\": " + str(te.getQualifiedName().toString())
                        + ", \"file\": " + str(file) + "}");
            }
            // only the bodies: the header and the member declarations are declarations
            for (Tree m : c.getMembers()) {
                TreePath mp = new TreePath(cp, m);
                if (m instanceof MethodTree mt) {
                    if (mt.getBody() != null) {
                        inBody(new TreePath(mp, mt.getBody()));
                    }
                } else if (m instanceof VariableTree vt) {
                    ExpressionTree init = vt.getInitializer();
                    if (init == null) {
                        continue;
                    }
                    Element e = trees.getElement(mp);
                    if (e != null && e.getKind() == ElementKind.ENUM_CONSTANT
                            && init instanceof NewClassTree nc) {
                        // `A(args) { body }`: the `new Kind(...)` around them is javac's
                        TreePath np = new TreePath(mp, nc);
                        for (ExpressionTree a : nc.getArguments()) {
                            inBody(new TreePath(np, a));
                        }
                        if (nc.getClassBody() != null) {
                            inBody(new TreePath(np, nc.getClassBody()));
                        }
                    } else {
                        inBody(new TreePath(mp, init));
                    }
                } else if (m.getKind() == Tree.Kind.BLOCK) {
                    inBody(mp);
                } else if (m instanceof ClassTree) {
                    scan(mp, null);
                }
            }
            return null;
        }

        @Override
        public Void visitAnnotation(AnnotationTree a, Void v) {
            return null;
        }

        @Override
        public Void visitIdentifier(IdentifierTree id, Void v) {
            if (body) {
                record(getCurrentPath(), id.getName().toString(), pos(id));
            }
            return null;
        }

        @Override
        public Void visitMemberSelect(MemberSelectTree ms, Void v) {
            if (body) {
                String name = ms.getIdentifier().toString();
                SourcePositions sp = trees.getSourcePositions();
                record(getCurrentPath(), name, sp.getEndPosition(cu, ms) - name.length());
            }
            return super.visitMemberSelect(ms, v);
        }

        void record(TreePath path, String name, long at) {
            if (at < 0 || trees.getSourcePositions().getEndPosition(cu, path.getLeaf()) < 0) {
                return;   // javac's own trees (an anonymous class's constructor)
            }
            if (name.isEmpty() || !Character.isUpperCase(name.charAt(0))) {
                return;   // keeps the records to names a type could have; `class`, `this`
            }
            if (recorded.contains(at)) {
                return;
            }
            Element e = trees.getElement(path);
            TypeMirror tm = trees.getTypeMirror(path);
            String position = position(path);
            String kind;
            String target = null;
            boolean project = false;
            boolean maximal = true;
            String declaredIn = null;   // a field's type: is the variable one the extractor sees?
            if (e == null || (tm != null && tm.getKind() == TypeKind.ERROR)) {
                kind = "error";
            } else if (e instanceof TypeElement te) {
                NestingKind nk = te.getNestingKind();
                if (nk == NestingKind.LOCAL || nk == NestingKind.ANONYMOUS) {
                    kind = "local";
                } else {
                    kind = "type";
                    target = te.getQualifiedName().toString();
                    project = inSources(te);
                }
                Tree parent = path.getParentPath().getLeaf();
                maximal = !(parent instanceof MemberSelectTree ps && ps.getExpression() == path.getLeaf()
                        && trees.getElement(path.getParentPath()) instanceof TypeElement);
            } else if (e.getKind() == ElementKind.TYPE_PARAMETER) {
                kind = "tparam";
            } else if (e.getKind().isVariable() && position.equals("receiver")) {
                kind = "var";
                if (e.getEnclosingElement() instanceof TypeElement owner) {
                    declaredIn = owner.getQualifiedName().toString();
                    project = inSources(owner);
                }
            } else {
                return;   // a method, a package, or a variable that is no receiver
            }

            TypeElement from = null;
            boolean nested = false;   // inside an anonymous or local class
            List<TypeElement> around = new ArrayList<>();
            for (TreePath p = path; p != null; p = p.getParentPath()) {
                if (p.getLeaf() instanceof ClassTree && trees.getElement(p) instanceof TypeElement te) {
                    around.add(te);
                    NestingKind nk = te.getNestingKind();
                    if (nk == NestingKind.LOCAL || nk == NestingKind.ANONYMOUS) {
                        if (from == null) {
                            nested = true;
                        }
                    } else if (from == null) {
                        from = te;
                    }
                }
            }
            boolean outside = false;
            boolean outsideNotLang = false;
            for (TypeElement te : around) {
                boolean[] s = outsideSupers(te);
                outside |= s[0];
                outsideNotLang |= s[1];
            }

            recorded.add(at);
            LineMap lm = cu.getLineMap();
            long line = lm.getLineNumber(at);
            long col = at - lm.getStartPosition(line);
            w.println("{\"use\": " + str(name) + ", \"file\": " + str(file)
                    + ", \"line\": " + line + ", \"col\": " + col
                    + ", \"pos\": " + str(position) + ", \"kind\": " + str(kind)
                    + ", \"target\": " + str(target) + ", \"project\": " + project
                    + ", \"maximal\": " + maximal
                    + ", \"declared_in\": " + str(declaredIn)
                    + ", \"from\": " + str(from == null ? null : from.getQualifiedName().toString())
                    + ", \"in_nested\": " + nested
                    + ", \"outside_super\": " + outside
                    + ", \"outside_super_not_lang\": " + outsideNotLang + "}");
        }

        /** "receiver" where a variable of the name would win over a type (`X.m()`, `X.F`,
         *  `X::m`, also `X.Inner.m()`); "type" where only a type can stand (`new X`, a
         *  cast, `X.class`, `X.Inner` as a type). */
        String position(TreePath path) {
            TreePath cur = path;
            while (cur.getParentPath() != null) {
                Tree parent = cur.getParentPath().getLeaf();
                if (parent instanceof MemberSelectTree ms && ms.getExpression() == cur.getLeaf()) {
                    String n = ms.getIdentifier().toString();
                    if (n.equals("class") || n.equals("this") || n.equals("super")) {
                        return "type";
                    }
                    Element pe = trees.getElement(cur.getParentPath());
                    if (pe instanceof TypeElement || pe instanceof PackageElement) {
                        cur = cur.getParentPath();   // still a type name: look at what it is in
                        continue;
                    }
                    return "receiver";
                }
                if (parent instanceof MemberReferenceTree mr && mr.getQualifierExpression() == cur.getLeaf()) {
                    return "receiver";
                }
                return "type";
            }
            return "type";
        }

        /** {any supertype outside the sources but Object, one outside java.lang}. */
        boolean[] outsideSupers(TypeElement te) {
            boolean[] cached = supers.get(te);
            if (cached != null) {
                return cached;
            }
            boolean[] out = new boolean[2];
            Set<String> seen = new HashSet<>();
            ArrayDeque<TypeMirror> queue = new ArrayDeque<>(types.directSupertypes(te.asType()));
            while (!queue.isEmpty()) {
                TypeMirror t = queue.pop();
                if (!(t instanceof DeclaredType dt) || !(dt.asElement() instanceof TypeElement s)) {
                    continue;
                }
                String qn = s.getQualifiedName().toString();
                if (!seen.add(qn)) {
                    continue;
                }
                if (!inSources(s) && !qn.equals("java.lang.Object")) {
                    out[0] = true;
                    if (!elements.getPackageOf(s).getQualifiedName().contentEquals("java.lang")) {
                        out[1] = true;
                    }
                }
                queue.addAll(types.directSupertypes(t));
            }
            supers.put(te, out);
            return out;
        }
    }
}
