// The names Roslyn resolves inside C# bodies, one JSON object per line: the answer key the
// extractor's body relations are compared with (bench/roslyn_oracle/oracle.py, records as
// bench/answer_key.py describes them). One record per name per compilation: oracle.py
// joins the compilations a file is in.
//
//   dotnet TypeUses.dll OUT ROOT SOURCES-FILE LANGVERSION CONFIGURATION LOAD...
//
// LOAD is a solution (.sln, .slnx, .slnf) or a project, with the MSBuild global properties
// to load it with after it: `path;Name=Value;...`. Each is opened in a workspace of its own
// and every C# project in it (one per target framework) is compiled; a project's language
// version is lowered to LANGVERSION when it asks for more (`latest` is what the compiler
// running here knows, not what the repository's SDK knows). ROOT is the directory the
// extractor is given: paths are relative to it. SOURCES-FILE lists the source files, one
// per line: only they are recorded, and a type is the project's when one of them declares
// it. Records:
//
//   {"compilation": NAME, ...}  a compilation: its language version, configuration,
//                               preprocessor symbols and error count
//   {"workspace": MESSAGE}      what the workspace reported while loading
//   {"declared": ID, "file"}    a class, struct, interface, record or enum a source declares,
//                               with "parts": the sources declaring it (a partial type's)
//   {"disabled": FILE, "lines"} the lines of a source the compilation does not compile
//                               (an inactive #if branch): every source it compiles has one
//   {"diagnostic": ...}         a compile error in a source
//   {"use": ...}                a name in a body (below)
//
//   dotnet TypeUses.dll framework OUT.json LABEL DIR...
//
// writes instead what the reference assemblies in DIR... declare that names in bodies can
// meet: each namespace's public types ("namespaces"), and per public class what a subclass
// or `using static` sees: its base class ("b"), the public and protected fields, properties
// and events it declares itself, instance ("f", not for a sealed or static class) and static
// ("s"), and its public and protected nested types ("n") (langs/csharp_framework.json;
// CSharpSpec reads it).
//
// A body is a method, constructor, accessor, operator or local function body, a
// constructor initializer (`: base(...)`), a field's, property's or enum member's
// initializer, a primary constructor's base arguments (`: Base(x)`) or a top-level
// statement, with everything inside them; attributes and parameter defaults are no body.
// Each dotted name in one (`Shop.Orders.Order.Create`) is read from its head: each part
// that is a type is recorded, "maximal" when no type part follows; the head is recorded
// too when it is something else (a variable, a method, nothing), and the parts after the
// first that is neither a type nor a namespace are not read. "pos" is "type" where only a
// type or namespace can stand (`new Foo()`, `Foo x`, `(Foo)x`, `typeof(Foo)`, `List<Foo>`,
// `is Foo f`, `is Foo` when Foo is a type) and "receiver" where an expression does
// (`Foo.Create()`, `nameof(Foo)`, `case Foo:`, a switch arm's `Foo =>`, `is Status.Closed`). A single name in an expression is recorded only in nameof, as a constant pattern
// or a case label, or when it is a type. "kind" is "type" (with "target", its id as
// ir.json writes it: namespaces and outer types by `.`, no type arguments, "project",
// "files": the sources that declare it), "tparam", "var" (a local, parameter, field,
// property, event or range variable: "decl" says which, "owner" whose member, "generated"
// whether only generated code declares it), "method", "label" or "error"; "alias" when
// the name is a using alias. "from" is the id of the type around the name (`Program` in
// top-level statements, the static class around a C# 14 extension block). Lines are 1-based, columns 0-based in UTF-16 code units.

using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.MSBuild;

if (args[0] == "framework")
{
    Framework.Write(args[1], args[2], args.Skip(3));
    return;
}
var (outPath, root, sourcesFile, langArg, configuration) = (args[0], Path.GetFullPath(args[1]), args[2], args[3], args[4]);
if (!LanguageVersionFacts.TryParse(langArg, out var maxLang))
    throw new ArgumentException($"no language version {langArg}");
var sources = File.ReadAllLines(sourcesFile).Where(l => l.Length > 0).Select(Path.GetFullPath).ToHashSet();
using var output = new StreamWriter(outPath);
void Emit(object rec) => output.WriteLine(JsonSerializer.Serialize(rec));
string Rel(string file) => Path.GetRelativePath(root, file).Replace('\\', '/');

foreach (var (load, loadIndex) in args.Skip(5).Select((l, i) => (l, i)))
{
    var fields = load.Split(';');
    var props = new Dictionary<string, string> { ["Configuration"] = configuration };
    foreach (var f in fields.Skip(1))
    {
        var eq = f.IndexOf('=');
        props[f[..eq]] = f[(eq + 1)..];
    }
    using var ws = MSBuildWorkspace.Create(props);
    ws.RegisterWorkspaceFailedHandler(e => Emit(new { workspace = e.Diagnostic.Message, kind = e.Diagnostic.Kind.ToString(), load }));
    var path = fields[0];
    var solution = path.EndsWith("proj")
        ? (await ws.OpenProjectAsync(path)).Solution
        : await ws.OpenSolutionAsync(path);
    foreach (var pid in solution.ProjectIds)
    {
        if (solution.GetProject(pid)!.ParseOptions is CSharpParseOptions po
            && po.LanguageVersion.MapSpecifiedToEffectiveVersion() > maxLang)
            solution = solution.WithProjectParseOptions(pid, po.WithLanguageVersion(maxLang));
    }
    foreach (var project in solution.Projects.Where(p => p.Language == LanguageNames.CSharp).OrderBy(p => p.Name))
    {
        var compilation = (await project.GetCompilationAsync())!;
        var generated = (await project.GetSourceGeneratedDocumentsAsync())
            .Select(d => d.FilePath).Where(p => p != null).ToHashSet();
        var comp = $"{loadIndex}:{project.Name}";
        var parse = (CSharpParseOptions)project.ParseOptions!;
        var errors = compilation.GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error).ToList();
        Emit(new
        {
            compilation = comp, load, langversion = parse.LanguageVersion.ToDisplayString(),
            configuration, symbols = parse.PreprocessorSymbolNames, errors = errors.Count,
            documents = project.Documents.Count(), generated = generated.Count,
        });
        foreach (var d in errors)
        {
            var at = d.Location.GetLineSpan();
            if (d.Location.SourceTree is { } t && sources.Contains(t.FilePath))
                Emit(new { diagnostic = d.GetMessage(), id = d.Id, file = Rel(t.FilePath), line = at.StartLinePosition.Line + 1, comp });
        }
        foreach (var tree in compilation.SyntaxTrees.Where(t => sources.Contains(t.FilePath)))
            new Reader(compilation.GetSemanticModel(tree), sources, generated, Rel, comp, Emit).Read();
    }
}

sealed class Reader(SemanticModel model, HashSet<string> sources, HashSet<string?> generated,
                    Func<string, string> rel, string comp, Action<object> emit)
{
    readonly string file = rel(model.SyntaxTree.FilePath);

    public void Read()
    {
        var root = model.SyntaxTree.GetRoot();
        var text = model.SyntaxTree.GetText();
        var off = new SortedSet<int>();
        foreach (var tr in root.DescendantTrivia(descendIntoTrivia: true).Where(t => t.IsKind(SyntaxKind.DisabledTextTrivia)))
        {
            var span = text.Lines.GetLinePositionSpan(tr.Span);
            var last = span.End.Character == 0 && span.End.Line > span.Start.Line ? span.End.Line - 1 : span.End.Line;
            for (var l = span.Start.Line; l <= last; l++) off.Add(l + 1);
        }
        emit(new { disabled = file, lines = off, comp });
        foreach (var decl in root.DescendantNodes().OfType<BaseTypeDeclarationSyntax>())
            // not a C# 14 extension block, a type with no name of its own
            if (model.GetDeclaredSymbol(decl) is INamedTypeSymbol { Name.Length: > 0 } t)
                emit(new { declared = Id(t), file, parts = Parts(t), comp });
        foreach (var name in root.DescendantNodes().OfType<SimpleNameSyntax>())
            if (InBody(name))
                Chain(name);
    }

    static bool InBody(SyntaxNode node)
    {
        for (var cur = node; cur != null; cur = cur.Parent)
        {
            switch (cur)
            {
                case AttributeSyntax:
                    return false;
                case GlobalStatementSyntax or ConstructorInitializerSyntax:
                    return true;
                case ArgumentListSyntax when cur.Parent is PrimaryConstructorBaseTypeSyntax:
                    return true;
                case BlockSyntax or ArrowExpressionClauseSyntax when cur.Parent is BaseMethodDeclarationSyntax
                        or AccessorDeclarationSyntax or BasePropertyDeclarationSyntax or LocalFunctionStatementSyntax:
                    return true;
                case EqualsValueClauseSyntax when cur.Parent is PropertyDeclarationSyntax or EnumMemberDeclarationSyntax
                        or VariableDeclaratorSyntax { Parent.Parent: BaseFieldDeclarationSyntax }:
                    return true;
                case MemberDeclarationSyntax or CompilationUnitSyntax:
                    return false;
            }
        }
        return false;
    }

    // the identifiers of a dotted name, or null for an expression (`x().Foo`, `this.Foo`)
    static List<SimpleNameSyntax>? Parts(ExpressionSyntax e) => e switch
    {
        SimpleNameSyntax s => [s],
        QualifiedNameSyntax q => Parts(q.Left) is { } l ? [.. l, q.Right] : null,
        AliasQualifiedNameSyntax a => [a.Name],   // global::A
        MemberAccessExpressionSyntax m when m.IsKind(SyntaxKind.SimpleMemberAccessExpression)
            => Parts(m.Expression) is { } l ? [.. l, m.Name] : null,
        _ => null,
    };

    static ExpressionSyntax Top(SimpleNameSyntax name)
    {
        ExpressionSyntax cur = name;
        while (true)
        {
            switch (cur.Parent)
            {
                case QualifiedNameSyntax q:
                    cur = q;
                    continue;
                case AliasQualifiedNameSyntax a when a.Name == cur:
                    cur = a;
                    continue;
                case MemberAccessExpressionSyntax m when m.IsKind(SyntaxKind.SimpleMemberAccessExpression) && Parts(m) != null:
                    cur = m;
                    continue;
            }
            return cur;
        }
    }

    void Chain(SimpleNameSyntax name)
    {
        var top = Top(name);
        var parts = Parts(top);
        if (parts == null || parts[0] != name)
            return;
        // a member's name after an expression (`x().Foo`, `a?.Foo`), a named argument, an
        // initializer's or a pattern's member: no name of the scope
        if (top == name && name.Parent is MemberAccessExpressionSyntax { Name: var n } && n == name
            || name.Parent is MemberBindingExpressionSyntax or NameColonSyntax or NameEqualsSyntax
            || name is IdentifierNameSyntax { IsVar: true } or IdentifierNameSyntax { IsNint: true }
                or IdentifierNameSyntax { IsNuint: true } or IdentifierNameSyntax { IsUnmanaged: true }
                or IdentifierNameSyntax { IsNotNull: true })
            return;
        // `is A.B` is a type when A.B is one; else the name is read as an expression
        // (`x is Status.Closed`), where a variable comes first
        var typeContext = top is TypeSyntax ts && SyntaxFacts.IsInNamespaceOrTypeContext(ts)
            && !(top.Parent is BinaryExpressionSyntax { RawKind: (int)SyntaxKind.IsExpression }
                 && Bound(model.GetSymbolInfo(top)) is not ITypeSymbol);
        var got = new List<Dictionary<string, object?>>();
        foreach (var part in parts)
        {
            var c = Classify(part);
            got.Add(c);
            if ((string)c["kind"]! is not ("type" or "namespace"))
                break;
        }
        if (parts.Count == 1 && !typeContext && (string)got[0]["kind"]! != "type" && !ConstantPlace(top))
            return;   // a variable, a method, a label: no type could stand there
        var from = From(name.SpanStart);
        for (var i = 0; i < got.Count; i++)
        {
            var c = got[i];
            var part = parts[i];
            var kind = (string)c["kind"]!;
            if (kind == "namespace")
                continue;
            if (kind != "type" && (i > 0 || !char.IsUpper(part.Identifier.ValueText[0])))
                continue;
            var at = part.GetLocation().GetLineSpan().StartLinePosition;
            c["use"] = part.Identifier.ValueText;
            c["file"] = file;
            c["line"] = at.Line + 1;
            c["col"] = at.Character;
            c["pos"] = typeContext ? "type" : "receiver";
            c["maximal"] = !(i + 1 < got.Count && (string)got[i + 1]["kind"]! == "type");
            c["from"] = from;
            c["comp"] = comp;
            emit(c);
        }
    }

    // where a constant may stand as well as a type: `nameof(Foo)`, `case Foo:`, `is Foo`
    // read as a constant pattern
    bool ConstantPlace(ExpressionSyntax e) => e.Parent switch
    {
        ConstantPatternSyntax or CaseSwitchLabelSyntax => true,
        BinaryExpressionSyntax b when b.IsKind(SyntaxKind.IsExpression) => b.Right == e,
        ArgumentSyntax { Parent.Parent: InvocationExpressionSyntax inv }
            => inv.Expression is IdentifierNameSyntax { Identifier.ValueText: "nameof" }
               && model.GetSymbolInfo(inv).Symbol == null,
        _ => false,
    };

    Dictionary<string, object?> Classify(SimpleNameSyntax part)
    {
        var info = model.GetSymbolInfo(part);
        var sym = Bound(info);
        var rec = new Dictionary<string, object?> { ["kind"] = "error", ["target"] = null, ["project"] = false };
        if (info.Symbol == null && info.CandidateSymbols.Length > 0)
        {
            rec["candidates"] = info.CandidateReason.ToString();
            if (info.CandidateSymbols.All(c => c is IMethodSymbol))
                rec["kind"] = "method";   // `nameof(Save)` of an overloaded method
        }
        if (model.GetAliasInfo(part) is { } alias)
            rec["alias"] = alias.Name;
        switch (sym)
        {
            case INamedTypeSymbol t when t.TypeKind != TypeKind.Error:
                var def = t.OriginalDefinition;
                var files = Parts(def);
                rec["kind"] = "type";
                rec["target"] = Id(def);
                // a delegate is no type to the extractor
                rec["project"] = files.Count > 0 && def.TypeKind != TypeKind.Delegate;
                rec["files"] = files;
                break;
            case ITypeParameterSymbol:
                rec["kind"] = "tparam";
                break;
            case INamespaceSymbol:
                rec["kind"] = "namespace";
                break;
            case IMethodSymbol:
                rec["kind"] = "method";
                break;
            case ILabelSymbol:
                rec["kind"] = "label";
                break;
            case ILocalSymbol or IParameterSymbol or IFieldSymbol or IPropertySymbol or IEventSymbol or IRangeVariableSymbol:
                rec["kind"] = "var";
                rec["decl"] = sym.Kind.ToString();
                if (sym is IFieldSymbol or IPropertySymbol or IEventSymbol)
                {
                    rec["owner"] = Id(sym.ContainingType.OriginalDefinition);
                    var refs = sym.DeclaringSyntaxReferences;
                    rec["generated"] = refs.Length > 0 && refs.All(r => generated.Contains(r.SyntaxTree.FilePath));
                    rec["external"] = refs.Length == 0;
                }
                break;
        }
        return rec;
    }

    // the sources that declare a type: one, or each part of a partial type
    List<string> Parts(INamedTypeSymbol t) => t.DeclaringSyntaxReferences.Select(r => r.SyntaxTree.FilePath)
        .Where(sources.Contains).Select(rel).Distinct().Order().ToList();

    // the symbol, or the one candidate (a lambda bound for several overloads)
    static ISymbol? Bound(SymbolInfo info) =>
        info.Symbol ?? (info.CandidateSymbols.Length == 1 ? info.CandidateSymbols[0] : null);

    string From(int position)
    {
        var s = model.GetEnclosingSymbol(position);
        while (s != null && s is not INamedTypeSymbol { IsAnonymousType: false, Name.Length: > 0 })
            s = s.ContainingSymbol;
        return s is INamedTypeSymbol t ? Id(t) : "";
    }

    // as ir.json writes a type's id: its namespace and outer types by `.`, no type arguments
    static string Id(INamedTypeSymbol t)
    {
        var names = new List<string>();
        for (var cur = t; cur != null; cur = cur.ContainingType)
            names.Insert(0, cur.Name);
        var ns = t.ContainingNamespace;
        return ns == null || ns.IsGlobalNamespace ? string.Join(".", names) : $"{ns.ToDisplayString()}.{string.Join(".", names)}";
    }
}

static class Framework
{
    public static void Write(string outPath, string label, IEnumerable<string> dirs)
    {
        var refs = dirs.SelectMany(d => Directory.GetFiles(d, "*.dll")).OrderBy(p => p)
            .Select(p => MetadataReference.CreateFromFile(p));
        var compilation = CSharpCompilation.Create("framework", references: refs);
        var namespaces = new SortedDictionary<string, SortedSet<string>>(StringComparer.Ordinal);
        var types = new SortedDictionary<string, object>(StringComparer.Ordinal);
        void Walk(INamespaceSymbol ns)
        {
            foreach (var t in ns.GetTypeMembers().Where(Public))
            {
                var key = ns.IsGlobalNamespace ? "" : ns.ToDisplayString();
                if (!namespaces.TryGetValue(key, out var names))
                    namespaces[key] = names = new SortedSet<string>(StringComparer.Ordinal);
                names.Add(t.Name);
                Type(t);
            }
            foreach (var inner in ns.GetNamespaceMembers())
                Walk(inner);
        }
        void Type(INamedTypeSymbol t)
        {
            var members = t.GetMembers().Where(m => !m.IsImplicitlyDeclared && Visible(m)
                && m is IFieldSymbol or IPropertySymbol { IsIndexer: false } or IEventSymbol).ToList();
            var nested = t.GetTypeMembers().Where(Visible).ToList();
            var entry = new SortedDictionary<string, object>(StringComparer.Ordinal);
            // a class: what a subclass inherits; a sealed or static one only what `using static`
            // brings in (static members, nested types); no other kind is extended in C#
            var extended = t.TypeKind == TypeKind.Class && !t.IsSealed && !t.IsStatic;
            if (t.TypeKind != TypeKind.Class)
                members.Clear();
            if (!extended)
                members.RemoveAll(m => !m.IsStatic && m is not IFieldSymbol { IsConst: true });
            if (extended && t.BaseType is { SpecialType: not SpecialType.System_Object } b)
                entry["b"] = Id(b.OriginalDefinition);
            var inst = members.Where(m => !m.IsStatic && m is not IFieldSymbol { IsConst: true })
                .Select(m => m.Name).Distinct().Order(StringComparer.Ordinal).ToList();
            var stat = members.Where(m => m.IsStatic || m is IFieldSymbol { IsConst: true })
                .Select(m => m.Name).Distinct().Order(StringComparer.Ordinal).ToList();
            if (inst.Count > 0) entry["f"] = inst;
            if (stat.Count > 0) entry["s"] = stat;
            if (nested.Count > 0 && t.TypeKind == TypeKind.Class)
                entry["n"] = nested.Select(n => n.Name).Distinct().Order(StringComparer.Ordinal).ToList();
            if (entry.Count > 0)
                types[Id(t)] = entry;
            foreach (var n in nested)
                Type(n);
        }
        Walk(compilation.GlobalNamespace);
        var doc = new SortedDictionary<string, object>(StringComparer.Ordinal)
        {
            ["framework"] = label,
            ["namespaces"] = namespaces,
            ["types"] = types,
        };
        File.WriteAllText(outPath, JsonSerializer.Serialize(doc) + "\n");
    }

    static bool Public(INamedTypeSymbol t) => t.DeclaredAccessibility == Accessibility.Public;

    // what a subclass in another assembly sees
    static bool Visible(ISymbol m) => m.DeclaredAccessibility is Accessibility.Public
        or Accessibility.Protected or Accessibility.ProtectedOrInternal;

    static string Id(INamedTypeSymbol t)
    {
        var names = new List<string>();
        for (var cur = t; cur != null; cur = cur.ContainingType)
            names.Insert(0, cur.Name);
        var ns = t.ContainingNamespace;
        return ns == null || ns.IsGlobalNamespace ? string.Join(".", names) : $"{ns.ToDisplayString()}.{string.Join(".", names)}";
    }
}
