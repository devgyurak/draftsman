// A Kotlin compiler plugin (K2): once a file is resolved, it walks the file's FIR and
// writes, for every name in it, what the compiler resolved that name to. One JSON line per
// name; one output file per compilation (a compilation is a Gradle compile task, or a
// fragment of one in Kotlin Multiplatform).
package org.draftsman.typeuses

import org.jetbrains.kotlin.KtFakeSourceElementKind
import org.jetbrains.kotlin.KtRealSourceElementKind
import org.jetbrains.kotlin.KtSourceElement
import org.jetbrains.kotlin.cli.common.CLIConfigurationKeys
import org.jetbrains.kotlin.cli.common.config.KotlinSourceRoot
import org.jetbrains.kotlin.cli.jvm.config.JvmClasspathRoot
import org.jetbrains.kotlin.cli.jvm.config.JavaSourceRoot
import org.jetbrains.kotlin.config.JVMConfigurationKeys
import org.jetbrains.kotlin.compiler.plugin.AbstractCliOption
import org.jetbrains.kotlin.compiler.plugin.CliOption
import org.jetbrains.kotlin.compiler.plugin.CommandLineProcessor
import org.jetbrains.kotlin.compiler.plugin.CompilerPluginRegistrar
import org.jetbrains.kotlin.config.CommonConfigurationKeys
import org.jetbrains.kotlin.config.CompilerConfiguration
import org.jetbrains.kotlin.config.CompilerConfigurationKey
import org.jetbrains.kotlin.config.languageVersionSettings
import org.jetbrains.kotlin.fir.containingClassLookupTag
import org.jetbrains.kotlin.fir.declarations.utils.isCompanion
import org.jetbrains.kotlin.fir.resolve.calls.FirSyntheticFunctionSymbol
import org.jetbrains.kotlin.descriptors.ClassKind
import org.jetbrains.kotlin.diagnostics.DiagnosticReporter
import org.jetbrains.kotlin.fir.FirElement
import org.jetbrains.kotlin.fir.FirSession
import org.jetbrains.kotlin.fir.analysis.checkers.MppCheckerKind
import org.jetbrains.kotlin.fir.analysis.checkers.context.CheckerContext
import org.jetbrains.kotlin.fir.analysis.checkers.declaration.DeclarationCheckers
import org.jetbrains.kotlin.fir.analysis.checkers.declaration.FirDeclarationChecker
import org.jetbrains.kotlin.fir.analysis.extensions.FirAdditionalCheckersExtension
import org.jetbrains.kotlin.fir.declarations.*
import org.jetbrains.kotlin.fir.expressions.*
import org.jetbrains.kotlin.fir.extensions.FirExtensionRegistrar
import org.jetbrains.kotlin.fir.extensions.FirExtensionRegistrarAdapter
import org.jetbrains.kotlin.fir.references.FirErrorNamedReference
import org.jetbrains.kotlin.fir.references.FirNamedReference
import org.jetbrains.kotlin.fir.references.FirResolvedNamedReference
import org.jetbrains.kotlin.fir.references.FirThisReference
import org.jetbrains.kotlin.fir.resolve.fullyExpandedType
import org.jetbrains.kotlin.fir.resolve.providers.symbolProvider
import org.jetbrains.kotlin.fir.scopes.impl.typeAliasConstructorInfo
import org.jetbrains.kotlin.fir.symbols.FirBasedSymbol
import org.jetbrains.kotlin.fir.symbols.impl.*
import org.jetbrains.kotlin.fir.types.*
import org.jetbrains.kotlin.fir.visitors.FirVisitorVoid
import org.jetbrains.kotlin.name.ClassId
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

val OUT = CompilerConfigurationKey<String>("draftsman.typeuses.out")

class Options : CommandLineProcessor {
    override val pluginId = "draftsman.typeuses"
    override val pluginOptions = listOf(CliOption("out", "<dir>", "where the records go", required = true))
    override fun processOption(option: AbstractCliOption, value: String, configuration: CompilerConfiguration) {
        if (option.optionName == "out") configuration.put(OUT, value)
    }
}

class Registrar : CompilerPluginRegistrar() {
    override val supportsK2 = true
    override val pluginId = "draftsman.typeuses"

    override fun ExtensionStorage.registerExtensions(configuration: CompilerConfiguration) {
        val out = configuration.get(OUT) ?: return
        val sink = Sink(File(out), configuration)
        FirExtensionRegistrarAdapter.registerExtension(object : FirExtensionRegistrar() {
            override fun ExtensionRegistrarContext.configurePlugin() {
                +FirAdditionalCheckersExtension.Factory { session -> Checkers(session, sink) }
            }
        })
    }
}

/** One compilation's records: a file of JSON lines, its first line saying what was compiled. */
class Sink(dir: File, configuration: CompilerConfiguration) {
    val comp: String = (configuration.get(CommonConfigurationKeys.MODULE_NAME) ?: "module") + "#" +
        UUID.randomUUID().toString().take(8)
    private val stream: FileOutputStream

    init {
        dir.mkdirs()
        stream = FileOutputStream(File(dir, comp.replace(Regex("[^A-Za-z0-9_.#-]"), "_") + ".jsonl"), true)
        val roots = configuration.getList(CLIConfigurationKeys.CONTENT_ROOTS)
        write(obj(
            "compilation" to comp,
            "sources" to roots.filterIsInstance<KotlinSourceRoot>().map {
                obj("path" to it.path, "common" to it.isCommon, "fragment" to it.hmppModuleName)
            },
            "classpath" to roots.filterIsInstance<JvmClasspathRoot>().map { it.file.path },
            "java" to roots.filterIsInstance<JavaSourceRoot>().map { it.file.path },
            "jdk" to configuration.get(JVMConfigurationKeys.JDK_HOME)?.path,
            "nojdk" to configuration.getBoolean(JVMConfigurationKeys.NO_JDK),
            "hmpp" to configuration.get(CommonConfigurationKeys.HMPP_MODULE_STRUCTURE)?.toString(),
            "language" to configuration.languageVersionSettings.languageVersion.versionString,
        ))
    }

    @Synchronized
    fun write(line: String) {
        stream.write((line + "\n").toByteArray())
        stream.flush()
    }
}

class Checkers(session: FirSession, sink: Sink) : FirAdditionalCheckersExtension(session) {
    private val file = FileChecker(sink)
    override val declarationCheckers = object : DeclarationCheckers() {
        override val fileCheckers: Set<FirDeclarationChecker<FirFile>> = setOf(file)
    }
}

class FileChecker(private val sink: Sink) : FirDeclarationChecker<FirFile>(MppCheckerKind.Common) {
    context(context: CheckerContext, reporter: DiagnosticReporter)
    override fun check(declaration: FirFile) {
        val path = declaration.sourceFile?.path ?: return
        // the compiler reads a file with its line breaks made \n: offsets count in that text
        val text = File(path).readText().replace("\r\n", "\n").replace('\r', '\n')
        val walker = Walker(path, text, context.session, sink.comp)
        walker.walk(declaration)
        sink.write(walker.out.joinToString("\n"))
    }
}

class Walker(val path: String, val text: String, val session: FirSession, val comp: String) : FirVisitorVoid() {
    val out = ArrayList<String>()
    private val seen = HashSet<Pair<Int, String>>()
    private val lineStarts = IntArray(text.count { it == '\n' } + 1).also { starts ->
        var n = 1
        text.forEachIndexed { i, c -> if (c == '\n') starts[n++] = i + 1 }
    }
    private val parents = ArrayList<FirElement>()
    private val owners = ArrayList<String>()     // the classes around, innermost last
    private val callables = ArrayList<String>()  // functions and properties around
    private var body = 0

    fun walk(file: FirFile) {
        out.add(obj("file" to path, "comp" to comp, "package" to file.packageDirective.packageFqName.asString()))
        file.accept(this)
    }

    override fun visitElement(element: FirElement) {
        val parent = parents.lastOrNull()
        val entersBody = parent != null && entersBody(parent, element)
        if (entersBody) body++
        parents.add(element)
        var owner: String? = null
        var callable: String? = null
        when (element) {
            is FirRegularClass -> {
                val id = element.symbol.classId
                owner = if (id.isLocal) "<local>" else id.asString()
                declared(id, kindOf(element.classKind, element.isCompanion), element,
                    "supertypes" to element.superTypeRefs.count { real(it.source) })
            }
            is FirAnonymousObject -> owner = "<anonymous>"
            is FirTypeAlias -> declared(element.symbol.classId, "typealias", element)
            is FirFunction -> (element.symbol as? FirNamedFunctionSymbol)?.let { callable = "fun " + it.name.asString() }
            is FirProperty -> if (!element.isLocal) callable = "val " + element.name.asString()
            else -> {}
        }
        owner?.let(owners::add)
        callable?.let(callables::add)
        val descend = when (element) {
            is FirResolvedTypeRef -> { typeRef(element); false }
            is FirResolvedQualifier -> { qualifier(element); true }
            is FirQualifiedAccessExpression -> { access(element); true }
            else -> true
        }
        if (descend) element.acceptChildren(this)
        owner?.let { owners.removeAt(owners.size - 1) }
        callable?.let { callables.removeAt(callables.size - 1) }
        parents.removeAt(parents.size - 1)
        if (entersBody) body--
    }

    /** Whether ``child`` of ``parent`` is code (a body) rather than a declaration's header. */
    private fun entersBody(parent: FirElement, child: FirElement): Boolean = when {
        parent is FirFunction && child === parent.body -> true
        parent is FirVariable && (child === parent.initializer || child === parent.delegate) -> true
        parent is FirValueParameter && child === parent.defaultValue -> true
        parent is FirAnonymousInitializer && child === parent.body -> true
        parent is FirConstructor && child === parent.delegatedConstructor -> true
        else -> false
    }

    // -- records ---------------------------------------------------------------------------

    private fun emit(name: String, offset: Int, pos: String, kind: String, target: String?,
                     vararg extra: Pair<String, Any?>) {
        if (!seen.add(offset to pos)) return
        var line = lineStarts.binarySearch(offset)
        if (line < 0) line = -line - 2
        out.add(obj("use" to name, "line" to line + 1, "col" to offset - lineStarts[line], "pos" to pos,
            "kind" to kind, "target" to target, "body" to (body > 0), "owners" to owners.toList(),
            "callables" to callables.toList(), *extra))
    }

    private fun declared(id: ClassId, kind: String, d: FirMemberDeclaration, vararg extra: Pair<String, Any?>) {
        if (id.isLocal) return
        out.add(obj("declared" to id.asString(), "kind" to kind, "expect" to d.status.isExpect,
            "actual" to d.status.isActual, "line" to lineOf(d.source), *extra))
    }

    private fun lineOf(s: KtSourceElement?): Int? {
        s ?: return null
        var line = lineStarts.binarySearch(s.startOffset)
        if (line < 0) line = -line - 2
        return line + 1
    }

    private fun real(s: KtSourceElement?) = s != null && s.kind is KtRealSourceElementKind

    /** Written in the source: real, or the receiver of an implicit `invoke` (`foo` of `foo(1)`). */
    private fun written(s: KtSourceElement?) = real(s) || s?.kind is KtFakeSourceElementKind.ImplicitInvokeCall

    private fun kindOf(k: ClassKind, companion: Boolean = false) = when (k) {
        ClassKind.CLASS -> "class"
        ClassKind.INTERFACE -> "interface"
        ClassKind.ENUM_CLASS -> "enum"
        ClassKind.ENUM_ENTRY -> "enumEntry-class"
        ClassKind.ANNOTATION_CLASS -> "annotation"
        ClassKind.OBJECT -> if (companion) "companion" else "object"
    }

    private fun classKind(id: ClassId): String = if (id.isLocal) "local-class" else
        when (val s = session.symbolProvider.getClassLikeSymbolByClassId(id)) {
            is FirRegularClassSymbol -> kindOf(s.classKind, s.isCompanion)
            is FirTypeAliasSymbol -> "typealias"
            null -> "unknown-class"
            else -> "class?"
        }

    // -- type references -------------------------------------------------------------------

    private fun typeRef(ref: FirResolvedTypeRef) {
        val s = ref.source ?: return
        if (s.kind is KtFakeSourceElementKind.ArrayTypeFromVarargParameter) {
            // `vararg xs: Foo`: the parameter's type is an Array of this one, the Foo written
            pair(ref.delegatedTypeRef, ref.coneType)
            return
        }
        if (!real(s)) return
        // the annotations on a type (`@Composable () -> Unit`) and their arguments
        ref.annotations.forEach { it.accept(this) }
        pair(ref.delegatedTypeRef, ref.coneType)
    }

    private fun pair(d: FirTypeRef?, cone: ConeKotlinType?) {
        when (d) {
            null -> {}
            is FirResolvedTypeRef -> typeRef(d)
            is FirUserTypeRef -> if (cone != null) { annotations(cone); userType(d, cone) }
            is FirFunctionTypeRef -> {
                if (cone != null) annotations(cone)
                // kotlin.FunctionN<receiver?, parameters..., return>, context parameters first
                val args = (cone?.lowerBoundIfFlexible() as? ConeClassLikeType)?.typeArguments.orEmpty()
                val refs = d.contextParameterTypeRefs + listOfNotNull(d.receiverTypeRef) +
                    d.parameters.map { it.returnTypeRef } + d.returnTypeRef
                refs.forEachIndexed { i, r -> pair(r, args.getOrNull(i)?.type) }
            }
            else -> {}
        }
    }

    /** A type argument's annotations (`List<@Ann Foo>`): resolved only in its cone type. */
    private fun annotations(cone: ConeKotlinType) {
        cone.customAnnotations.forEach { if (real(it.source)) it.accept(this) }
    }

    private fun userType(d: FirUserTypeRef, cone0: ConeKotlinType) {
        var cone = cone0.lowerBoundIfFlexible()
        if (cone is ConeDefinitelyNotNullType) cone = cone.original
        val written = cone.abbreviatedType ?: cone
        val parts = d.qualifier
        when (written) {
            is ConeTypeParameterType -> parts.lastOrNull()?.let {
                part(it, "tparam", written.lookupTag.name.asString(), "part" to 0)
            }
            is ConeErrorType -> parts.forEach { part(it, "error", null) }
            is ConeClassLikeType -> {
                var id: ClassId? = written.lookupTag.classId
                var args = written.typeArguments.toList()
                for ((i, p) in parts.asReversed().withIndex()) {
                    if (id == null) { part(p, "package", null, "part" to i); continue }
                    val alias = written !== cone && id == written.lookupTag.classId
                    part(p, classKind(id), id.asString(), "alias" to alias, "part" to i,
                        "expanded" to if (alias) (cone as? ConeClassLikeType)?.lookupTag?.classId?.asString() else null)
                    val own = p.typeArgumentList.typeArguments
                    own.forEachIndexed { i, a ->
                        if (a is FirTypeProjectionWithVariance) pair(a.typeRef, args.getOrNull(i)?.type)
                    }
                    args = args.drop(own.size)
                    id = id.outerClassId
                }
            }
            else -> parts.forEach { part(it, "type?", written.toString()) }
        }
    }

    private fun part(p: FirQualifierPart, kind: String, target: String?, vararg extra: Pair<String, Any?>) {
        val s = p.source ?: return
        emit(p.name.asString(), s.startOffset, "type", kind, target, *extra)
    }

    // -- expressions -----------------------------------------------------------------------

    private val ident = Regex("`[^`]+`|[\\p{L}_][\\p{L}\\p{N}_]*")

    private fun qualifier(q: FirResolvedQualifier) {
        val s = q.source ?: return
        if (!written(s)) return
        // the names written, `a.b.Foo.Bar` (type arguments `<...>` cut off)
        val written = text.substring(s.startOffset, s.endOffset).substringBefore('<')
        val names = ident.findAll(written).toList()
        val classes = q.relativeClassFqName?.pathSegments()?.size ?: 0
        // the package is written only when the name is qualified with it
        val parent = parents.getOrNull(parents.size - 2)
        // `Foo::class`: Foo is an argument of the call getting the class
        val call = parents.asReversed().drop(1).firstOrNull { it !is FirArgumentList }
        val role = when {
            // `Foo("s")`, the operator `invoke` of Foo's companion (or of an object Foo)
            parent is FirImplicitInvokeCall && parent.explicitReceiver === q -> "invoke"
            // `Outer.Inner()`: Outer is a part of the name of the class constructed
            parent is FirFunctionCall && parent.explicitReceiver === q && names(parent) -> "outer"
            parent is FirQualifiedAccessExpression && parent.explicitReceiver === q -> "receiver"
            call is FirGetClassCall -> "class-literal"
            parent is FirResolvedQualifier -> "receiver"
            else -> "value"
        }
        var id = q.classId
        names.asReversed().forEachIndexed { i, m ->
            val at = s.startOffset + m.range.first
            if (i < classes && id != null) {
                val kind = if (i == 0 && q.symbol is FirTypeAliasSymbol) "typealias" else classKind(id!!)
                val sym = q.symbol
                val expanded = if (i == 0 && sym is FirTypeAliasSymbol)
                    (sym.resolvedExpandedTypeRef.coneType.fullyExpandedType(session) as? ConeClassLikeType)?.lookupTag?.classId?.asString()
                else null
                emit(m.value.trim('`'), at, "value", kind, id!!.asString(),
                    "companion" to (i == 0 && q.resolvedToCompanionObject), "qualifier" to true,
                    "role" to if (i == 0) role else "receiver", "part" to i, "expanded" to expanded)
                id = id!!.outerClassId
            } else emit(m.value.trim('`'), at, "value", "package", null, "qualifier" to true, "part" to i)
        }
    }

    /** Whether a call names a type: a constructor, a SAM constructor. */
    private fun names(call: FirFunctionCall): Boolean {
        val sym = (call.calleeReference as? FirResolvedNamedReference)?.resolvedSymbol
        return sym is FirConstructorSymbol || sym is FirSyntheticFunctionSymbol
    }

    private fun access(e: FirQualifiedAccessExpression) {
        val ref = e.calleeReference
        if (ref is FirThisReference) {
            val label = ref.labelName
            val s = e.source
            if (label != null && real(s)) {
                val at = text.indexOf("@", s!!.startOffset) + 1
                val bound = ref.boundSymbol
                emit(label, at, "label", "label", (bound as? FirClassLikeSymbol<*>)?.classId?.asString())
            }
            return
        }
        // `foo(1)` calling foo's operator `invoke`: the name written is foo's (its receiver)
        if (e is FirImplicitInvokeCall) return
        // a property's reference has no source of its own: its name ends the expression
        val name = (ref as? FirNamedReference)?.name?.asString() ?: return
        val es = e.source
        val at = ref.source?.takeIf { written(it) }?.startOffset
            ?: es?.takeIf { written(it) && e is FirPropertyAccessExpression }?.let { src ->
                val written = text.substring(src.startOffset, src.endOffset)
                if (written.endsWith(name)) src.endOffset - name.length
                else if (written.endsWith("`$name`")) src.endOffset - name.length - 1 else null
            } ?: return
        // a name the compiler wrote for an operator (`plus` of `a + b`, `get` of `a[i]`,
        // `getValue` of `by`, `component1` of a destructuring) is no name written there
        if (!text.startsWith(name, at) && !text.startsWith("`$name`", at)) return
        val explicit = e.explicitReceiver
        val extra = arrayOf<Pair<String, Any?>>(
            "dotted" to (explicit != null && real(explicit.source)),
            "implicit" to implicitReceiver(e),
            "call" to (e is FirFunctionCall),
            "reference" to (e is FirCallableReferenceAccess),
        )
        when (ref) {
            is FirResolvedNamedReference -> symbol(name, at, ref.resolvedSymbol, *extra)
            is FirErrorNamedReference -> emit(name, at, "value", "error",
                ref.diagnostic.reason, *extra)
            else -> {}
        }
    }

    /** The implicit receiver a member was found on: a class (or object) around, or a lambda's. */
    private fun implicitReceiver(e: FirQualifiedAccessExpression): String? {
        for (r in listOf(e.dispatchReceiver, e.extensionReceiver)) {
            val t = r as? FirThisReceiverExpression ?: continue
            if (!t.isImplicit) continue
            return when (val b = t.calleeReference.boundSymbol) {
                is FirClassSymbol<*> -> "class " + b.classId.asString()
                is FirReceiverParameterSymbol -> (if (b.containingDeclarationSymbol is FirAnonymousFunctionSymbol) "lambda " else "receiver ") + (t.resolvedType as? ConeClassLikeType)?.lookupTag?.classId?.asString()
                else -> "other " + b?.javaClass?.simpleName + " " + (t.resolvedType as? ConeClassLikeType)?.lookupTag?.classId?.asString()
            }
        }
        return null
    }

    private fun symbol(name: String, at: Int, sym: FirBasedSymbol<*>, vararg extra: Pair<String, Any?>) {
        when (sym) {
            is FirConstructorSymbol -> {
                val alias = sym.typeAliasConstructorInfo?.typeAliasSymbol
                val cls = sym.containingClassLookupTag()?.classId
                if (alias != null) emit(name, at, "value", "alias-constructor", alias.classId.asString(),
                    "expanded" to cls?.asString(), *extra)
                else emit(name, at, "value", if (cls?.isLocal == true) "local-class" else "constructor",
                    cls?.asString(), *extra)
            }
            is FirSyntheticFunctionSymbol -> emit(name, at, "value", "sam-constructor",
                (sym.resolvedReturnType as? ConeClassLikeType)?.lookupTag?.classId?.asString(), *extra)
            is FirNamedFunctionSymbol -> emit(name, at, "value", if (sym.callableId?.classId == null) {
                if (sym.callableId?.isLocal == true) "local-function" else "function"
            } else "member-function", sym.callableId.toString(), *extra)
            is FirEnumEntrySymbol -> emit(name, at, "value", "enumEntry", sym.callableId?.classId?.asString(), *extra)
            is FirValueParameterSymbol -> emit(name, at, "value", "param", null, *extra)
            is FirPropertySymbol -> emit(name, at, "value", when {
                sym.isLocal -> "local"
                sym.callableId?.classId == null -> if (sym.receiverParameterSymbol != null) "extension-property" else "property"
                else -> "member-property"
            }, if (sym.isLocal) null else sym.callableId.toString(), *extra)
            is FirFieldSymbol -> emit(name, at, "value", "field", sym.callableId.toString(), *extra)
            is FirBackingFieldSymbol -> emit(name, at, "value", "field", null, *extra)
            is FirClassLikeSymbol<*> -> emit(name, at, "value", classKind(sym.classId), sym.classId.asString(), *extra)
            else -> emit(name, at, "value", sym.javaClass.simpleName, null, *extra)
        }
    }
}

// -- JSON ----------------------------------------------------------------------------------

fun obj(vararg fields: Pair<String, Any?>): String =
    fields.joinToString(",", "{", "}") { (k, v) -> json(k) + ":" + value(v) }

private fun value(v: Any?): String = when (v) {
    null -> "null"
    is Boolean, is Int -> v.toString()
    is String -> if (v.startsWith("{")) v else json(v)
    is List<*> -> v.joinToString(",", "[", "]") { value(it) }
    else -> json(v.toString())
}

private fun json(s: String): String {
    val b = StringBuilder("\"")
    for (c in s) when {
        c == '"' -> b.append("\\\"")
        c == '\\' -> b.append("\\\\")
        c < ' ' -> b.append(String.format("\\u%04x", c.code))
        else -> b.append(c)
    }
    return b.append('"').toString()
}
