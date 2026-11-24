// TypeUses for C++ (issue #5): a libTooling tool that records what Clang resolved every
// name in a body to, in the sources below a root. One JSON line per record, one output file
// per translation unit; bench/clang_oracle/oracle.py joins the translation units.
//
//   type-uses -p BUILD_DIR -root ROOT -out DIR [-names FILE] [-all] FILES...
//   type-uses -table OUT.json TU.cpp -- FLAGS      (the table of `std` classes)
//
// Only the written code is visited (a template's pattern, not its instances), and only
// names in a body: a function's body, a constructor's initializers, a default argument, a
// default member initializer, the initializer of a static member, an enumerator's value.
// Records (oracle.py reads them):
//   {"n","f","l","c","k","t","tf","pos","max","from","spec","m"}
//     the name as written, its file below root, 1-based line, 0-based byte column; the
//     kind (type, alias, tparam, var, member, global, function, method, enumconst,
//     namespace, nsalias, dependent, local, other); the target's id as ir.json writes it
//     (types and aliases) or its qualified name; the file the target is defined in; the
//     position ("type": only a type may stand there, also `Foo::`; "receiver": a value
//     may as well: `Foo(1)`, `: Base(1)`, a block-scope function declaration's parameter,
//     any name that is no type); whether it is the whole name, not a part of a longer one
//     (`A` in `A::B`); the type the code is in, as ir.json has it ("" for none: a free
//     function, namespace scope); whether a template specialisation is around it; "arg"
//     when the name is a macro argument (a name from a macro's body is not recorded).
//   {"aliasdecl","f","names":[[kind,id,file],...]}   a typedef or `using` alias below root
//     and the types and aliases its written type names, as Clang resolved them
//   {"decl","f","l","kind","anon"}   a class, struct, union or enum defined below root
//   {"cls","f","bases":[[written,id,file,dependent],...]}   a class's bases
//   {"inc"}   a file below root the translation unit entered
//   {"skip","l1","l2"}   lines the preprocessor skipped in a file below root
//   {"tu","ms","rc"}   the translation unit, how long it took, Clang's result

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/DeclTemplate.h"
#include "clang/AST/ExprCXX.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendAction.h"
#include "clang/Lex/Lexer.h"
#include "clang/Lex/PPCallbacks.h"
#include "clang/Lex/Preprocessor.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/Path.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/xxhash.h"
#include <array>
#include <chrono>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <unordered_set>
#include <vector>

using namespace clang;
using namespace clang::tooling;

static llvm::cl::OptionCategory Cat("type-uses");
static llvm::cl::opt<std::string> RootOpt("root", llvm::cl::cat(Cat));
static llvm::cl::opt<std::string> OutOpt("out", llvm::cl::cat(Cat));
static llvm::cl::opt<std::string> NamesOpt("names", llvm::cl::cat(Cat));
static llvm::cl::opt<bool> AllOpt("all", llvm::cl::cat(Cat));
static llvm::cl::opt<std::string> TableOpt("table", llvm::cl::cat(Cat));

static std::unordered_set<std::string> Names;

static std::string esc(llvm::StringRef s) {
  std::string o;
  for (char ch : s) {
    if (ch == '"' || ch == '\\') { o += '\\'; o += ch; }
    else if ((unsigned char)ch < 0x20) { char b[8]; snprintf(b, 8, "\\u%04x", ch); o += b; }
    else o += ch;
  }
  return o;
}

struct Out {
  llvm::raw_ostream *os = nullptr;
  std::string root;
  llvm::DenseMap<FileID, std::string> rel;   // file -> path below root, "" outside
  const SourceManager *SM = nullptr;

  std::string relOf(FileID fid) {
    auto it = rel.find(fid);
    if (it != rel.end()) return it->second;
    std::string r;
    if (auto fe = SM->getFileEntryRefForID(fid)) {
      llvm::SmallString<256> p(fe->getName());
      llvm::sys::fs::make_absolute(p);
      llvm::sys::path::remove_dots(p, true);
      llvm::StringRef s = p;
      if (!root.empty() && s.starts_with(root + "/")) r = s.substr(root.size() + 1).str();
    }
    rel[fid] = r;
    return r;
  }
};

static Out O;

class PP : public PPCallbacks {
public:
  explicit PP(SourceManager &SM) : SM(SM) {}
  void FileChanged(SourceLocation Loc, FileChangeReason Reason, SrcMgr::CharacteristicKind,
                   FileID) override {
    if (Reason != EnterFile) return;
    std::string r = O.relOf(SM.getFileID(Loc));
    if (!r.empty() && seen.insert(r).second) *O.os << "{\"inc\":\"" << esc(r) << "\"}\n";
  }
  void SourceRangeSkipped(SourceRange R, SourceLocation EndifLoc) override {
    SourceLocation b = SM.getExpansionLoc(R.getBegin()), e = SM.getExpansionLoc(EndifLoc);
    std::string r = O.relOf(SM.getFileID(b));
    if (r.empty()) return;
    *O.os << "{\"skip\":\"" << esc(r) << "\",\"l1\":" << SM.getSpellingLineNumber(b)
          << ",\"l2\":" << SM.getSpellingLineNumber(e) << "}\n";
  }
  SourceManager &SM;
  std::set<std::string> seen;
};

// ---- ids as ir.json writes them -------------------------------------------------------

static bool isLocal(const Decl *D) {
  for (const DeclContext *DC = D->getDeclContext(); DC; DC = DC->getParent())
    if (DC->isFunctionOrMethod()) return true;
  return false;
}

// the name ir.json gives a tag: its own, or the typedef that names an anonymous one
static std::string tagName(const TagDecl *T) {
  if (T->getIdentifier()) return T->getName().str();
  if (auto *TD = T->getTypedefNameForAnonDecl()) return TD->getName().str();
  return "";
}

// `a::b::Outer::Inner`: namespaces (not anonymous ones), outer types, the name; a class
// template's specialisation is the template; "" for a local or an unnamed type
static std::string idOf(const NamedDecl *D) {
  if (!D) return "";
  if (auto *CT = dyn_cast<ClassTemplateDecl>(D)) D = CT->getTemplatedDecl();
  if (auto *TA = dyn_cast<TypeAliasTemplateDecl>(D)) D = TA->getTemplatedDecl();
  if (auto *S = dyn_cast<ClassTemplateSpecializationDecl>(D))
    D = S->getSpecializedTemplate()->getTemplatedDecl();
  if (isLocal(D)) return "";
  std::string name;
  if (auto *T = dyn_cast<TagDecl>(D)) name = tagName(T);
  else if (D->getIdentifier()) name = D->getName().str();
  if (name.empty()) return "";
  std::vector<std::string> parts{name};
  for (const DeclContext *DC = D->getDeclContext(); DC; DC = DC->getParent()) {
    if (auto *N = dyn_cast<NamespaceDecl>(DC)) {
      if (!N->isAnonymousNamespace()) parts.push_back(N->getName().str());
    } else if (auto *T = dyn_cast<TagDecl>(DC)) {
      if (auto *S = dyn_cast<ClassTemplateSpecializationDecl>(T))
        T = S->getSpecializedTemplate()->getTemplatedDecl();
      std::string n = tagName(T);
      if (n.empty()) return "";
      parts.push_back(n);
    } else if (DC->isFunctionOrMethod()) {
      return "";
    }
  }
  std::string out;
  for (auto it = parts.rbegin(); it != parts.rend(); ++it) {
    if (!out.empty()) out += "::";
    out += *it;
  }
  return out;
}

static std::string fileOf(const Decl *D) {
  if (!D) return "";
  if (auto *CT = dyn_cast<ClassTemplateDecl>(D)) D = CT->getTemplatedDecl();
  if (auto *T = dyn_cast<TagDecl>(D))
    if (auto *Def = T->getDefinition()) D = Def;
  SourceLocation L = O.SM->getExpansionLoc(D->getLocation());
  if (L.isInvalid()) return "";
  return O.relOf(O.SM->getFileID(L));
}

// a typedef that names an anonymous struct is that struct (`typedef struct {} Point;`)
static const NamedDecl *throughAnonTypedef(const NamedDecl *D) {
  if (auto *TD = dyn_cast<TypedefNameDecl>(D))
    if (auto *T = TD->getUnderlyingType()->getAsTagDecl())
      if (T->getTypedefNameForAnonDecl() == TD) return T;
  return D;
}

static const char *kindOf(const Decl *D) {
  if (isa<TagDecl>(D) || isa<ClassTemplateDecl>(D))
    return idOf(cast<NamedDecl>(D)).empty() ? "local" : "type";
  if (isa<TypedefNameDecl>(D) || isa<TypeAliasTemplateDecl>(D))
    return idOf(cast<NamedDecl>(D)).empty() ? "local" : "alias";
  if (isa<TemplateTypeParmDecl>(D) || isa<TemplateTemplateParmDecl>(D) || isa<NonTypeTemplateParmDecl>(D))
    return "tparam";
  if (isa<ParmVarDecl>(D)) return "var";
  if (auto *V = dyn_cast<VarDecl>(D)) {
    if (V->isStaticDataMember()) return "member";
    if (V->isLocalVarDecl()) return "var";
    return "global";
  }
  if (isa<BindingDecl>(D)) return "var";
  if (isa<FieldDecl>(D) || isa<IndirectFieldDecl>(D)) return "member";
  if (isa<CXXMethodDecl>(D)) return "method";
  if (isa<FunctionDecl>(D)) return "function";
  if (auto *FT = dyn_cast<FunctionTemplateDecl>(D))
    return isa<CXXMethodDecl>(FT->getTemplatedDecl()) ? "method" : "function";
  if (isa<EnumConstantDecl>(D)) return "enumconst";
  if (isa<NamespaceDecl>(D)) return "namespace";
  if (isa<NamespaceAliasDecl>(D)) return "nsalias";
  if (isa<VarTemplateDecl>(D)) return "global";
  if (isa<UnresolvedUsingValueDecl>(D) || isa<UnresolvedUsingTypenameDecl>(D)) return "dependent";
  if (isa<ConceptDecl>(D)) return "concept";
  return "other";
}

// where the name of a type stands in the code
static SourceLocation nameLoc(TypeLoc TL) {
  if (TL.isNull()) return {};
  if (auto T = TL.getAs<TagTypeLoc>()) return T.getNameLoc();
  if (auto T = TL.getAs<TypedefTypeLoc>()) return T.getNameLoc();
  if (auto T = TL.getAs<UsingTypeLoc>()) return T.getNameLoc();
  if (auto T = TL.getAs<TemplateSpecializationTypeLoc>()) return T.getTemplateNameLoc();
  if (auto T = TL.getAs<DeducedTemplateSpecializationTypeLoc>()) return T.getTemplateNameLoc();
  if (auto T = TL.getAs<TemplateTypeParmTypeLoc>()) return T.getNameLoc();
  if (auto T = TL.getAs<DependentNameTypeLoc>()) return T.getNameLoc();
  if (auto T = TL.getAs<QualifiedTypeLoc>()) return nameLoc(T.getUnqualifiedLoc());
  if (auto T = TL.getAs<PointerTypeLoc>()) return nameLoc(T.getPointeeLoc());
  if (auto T = TL.getAs<ReferenceTypeLoc>()) return nameLoc(T.getPointeeLoc());
  return {};
}

static NestedNameSpecifierLoc qualifierOf(TypeLoc TL) {
  if (auto T = TL.getAs<TagTypeLoc>()) return T.getQualifierLoc();
  if (auto T = TL.getAs<TypedefTypeLoc>()) return T.getQualifierLoc();
  if (auto T = TL.getAs<UsingTypeLoc>()) return T.getQualifierLoc();
  if (auto T = TL.getAs<TemplateSpecializationTypeLoc>()) return T.getQualifierLoc();
  if (auto T = TL.getAs<DependentNameTypeLoc>()) return T.getQualifierLoc();
  return {};
}

static NestedNameSpecifierLoc prefixOf(NestedNameSpecifierLoc L) {
  switch (L.getNestedNameSpecifier().getKind()) {
  case NestedNameSpecifier::Kind::Namespace:
    return L.castAsNamespaceAndPrefix().Prefix;
  case NestedNameSpecifier::Kind::Type:
    return qualifierOf(L.castAsTypeLoc());
  default:
    return {};
  }
}

// the components of a nested-name-specifier, last first
static void nnsLocs(NestedNameSpecifierLoc L, std::vector<SourceLocation> &out) {
  while (L) {
    NestedNameSpecifier N = L.getNestedNameSpecifier();
    if (N.getKind() == NestedNameSpecifier::Kind::Namespace) out.push_back(L.getLocalBeginLoc());
    else if (N.getKind() == NestedNameSpecifier::Kind::Type) out.push_back(nameLoc(L.castAsTypeLoc()));
    L = prefixOf(L);
  }
}

// the types and aliases a typedef's written type names, as Clang resolved them
class AliasNames : public RecursiveASTVisitor<AliasNames> {
public:
  // `lib::Channel::Ptr` names Ptr, not Channel (as the declared relations read it)
  bool TraverseNestedNameSpecifierLoc(NestedNameSpecifierLoc) { return true; }
  bool VisitTypeLoc(TypeLoc TL) {
    const NamedDecl *D = nullptr;
    if (auto T = TL.getAs<TagTypeLoc>()) D = T.getDecl();
    else if (auto T = TL.getAs<TypedefTypeLoc>()) D = T.getDecl();
    else if (auto T = TL.getAs<UsingTypeLoc>()) D = T.getDecl();
    else if (auto T = TL.getAs<TemplateSpecializationTypeLoc>())
      D = T.getTypePtr()->getTemplateName().getAsTemplateDecl();
    if (!D) return true;
    if (auto *U = dyn_cast<UsingShadowDecl>(D)) D = U->getTargetDecl();
    D = throughAnonTypedef(D);
    const char *k = kindOf(D);
    if (!strcmp(k, "type") || !strcmp(k, "alias")) out.push_back({k, idOf(D), fileOf(D)});
    return true;
  }
  std::vector<std::array<std::string, 3>> out;
};

// ---- the visitor ----------------------------------------------------------------------

class V : public RecursiveASTVisitor<V> {
public:
  explicit V(ASTContext &Ctx) : Ctx(Ctx), SM(Ctx.getSourceManager()) {}
  bool shouldVisitTemplateInstantiations() const { return false; }
  bool shouldVisitImplicitCode() const { return false; }

  bool TraverseDecl(Decl *D) {
    if (!D) return true;
    Stack.push_back(D);
    bool r = RecursiveASTVisitor::TraverseDecl(D);
    Stack.pop_back();
    return r;
  }
  bool TraverseStmt(Stmt *S, DataRecursionQueue * = nullptr) {
    Depth++;
    bool r = RecursiveASTVisitor::TraverseStmt(S, nullptr);
    Depth--;
    return r;
  }
  bool TraverseConstructorInitializer(CXXCtorInitializer *I) {
    Depth++;
    if (I && I->isWritten()) {
      if (I->isAnyMemberInitializer() && I->getMemberLocation().isValid())
        rec(I->getMemberLocation(), I->getAnyMember(), "receiver");
      if (I->isBaseInitializer() && I->getTypeSourceInfo())
        Calls.insert(nameLoc(I->getTypeSourceInfo()->getTypeLoc()).getRawEncoding());
    }
    bool r = RecursiveASTVisitor::TraverseConstructorInitializer(I);
    Depth--;
    return r;
  }

  // `Foo(1)`: a function of the name may be called as well
  bool VisitCXXFunctionalCastExpr(CXXFunctionalCastExpr *E) {
    if (!E->isListInitialization() && E->getTypeInfoAsWritten())
      Calls.insert(nameLoc(E->getTypeInfoAsWritten()->getTypeLoc()).getRawEncoding());
    return true;
  }
  bool VisitCXXTemporaryObjectExpr(CXXTemporaryObjectExpr *E) {
    if (!E->isListInitialization() && E->getTypeSourceInfo())
      Calls.insert(nameLoc(E->getTypeSourceInfo()->getTypeLoc()).getRawEncoding());
    return true;
  }
  bool VisitCXXUnresolvedConstructExpr(CXXUnresolvedConstructExpr *E) {
    if (!E->isListInitialization() && E->getTypeSourceInfo())
      Calls.insert(nameLoc(E->getTypeSourceInfo()->getTypeLoc()).getRawEncoding());
    return true;
  }
  // `Lock l(Tag);` in a block, with Tag a type: a function declaration, whose parameters'
  // types stand where a variable could
  bool VisitFunctionDecl(FunctionDecl *F) {
    if (F->getLexicalDeclContext()->isFunctionOrMethod())
      for (ParmVarDecl *P : F->parameters())
        if (P->getTypeSourceInfo()) {
          TypeLoc TL = P->getTypeSourceInfo()->getTypeLoc();
          Calls.insert(nameLoc(TL).getRawEncoding());
          std::vector<SourceLocation> q;   // and its qualifier: `Base b(Base::Tag)`
          nnsLocs(qualifierOf(TL), q);
          for (SourceLocation L : q) Calls.insert(L.getRawEncoding());
        }
    return true;
  }

  bool VisitTypeLoc(TypeLoc TL) {
    // the qualifier of a type's name is part of it
    std::vector<SourceLocation> q;
    nnsLocs(qualifierOf(TL), q);
    for (SourceLocation L : q) Parts.insert(L.getRawEncoding());
    if (auto T = TL.getAs<TagTypeLoc>()) rec(T.getNameLoc(), T.getDecl(), "type");
    else if (auto T = TL.getAs<TypedefTypeLoc>()) rec(T.getNameLoc(), T.getDecl(), "type");
    else if (auto T = TL.getAs<UsingTypeLoc>()) rec(T.getNameLoc(), T.getDecl(), "type");
    else if (auto T = TL.getAs<TemplateSpecializationTypeLoc>()) {
      if (TemplateDecl *TD = T.getTypePtr()->getTemplateName().getAsTemplateDecl())
        rec(T.getTemplateNameLoc(), TD, "type");
      else recKind(T.getTemplateNameLoc(), "dependent", "type");
    } else if (auto T = TL.getAs<DeducedTemplateSpecializationTypeLoc>()) {
      if (TemplateDecl *TD = T.getTypePtr()->getTemplateName().getAsTemplateDecl())
        rec(T.getTemplateNameLoc(), TD, "type");
    } else if (auto T = TL.getAs<TemplateTypeParmTypeLoc>()) {
      rec(T.getNameLoc(), T.getDecl(), "type");
    } else if (auto T = TL.getAs<DependentNameTypeLoc>()) {
      recKind(T.getNameLoc(), "dependent", "type");
    }
    return true;
  }
  bool TraverseNestedNameSpecifierLoc(NestedNameSpecifierLoc L) {
    if (L) {
      // the components before the last are parts of a longer name
      std::vector<SourceLocation> q;
      nnsLocs(prefixOf(L), q);
      for (SourceLocation S : q) Parts.insert(S.getRawEncoding());
      if (L.getNestedNameSpecifier().getKind() == NestedNameSpecifier::Kind::Namespace)
        rec(L.getLocalBeginLoc(), L.castAsNamespaceAndPrefix().Namespace, "type");
    }
    return RecursiveASTVisitor::TraverseNestedNameSpecifierLoc(L);
  }
  bool TraverseTemplateArgumentLoc(const TemplateArgumentLoc &A) {
    if (A.getArgument().getKind() == TemplateArgument::Template)
      if (TemplateDecl *TD = A.getArgument().getAsTemplate().getAsTemplateDecl())
        rec(A.getTemplateNameLoc(), TD, "type");
    return RecursiveASTVisitor::TraverseTemplateArgumentLoc(A);
  }
  bool VisitDeclRefExpr(DeclRefExpr *E) {
    rec(E->getLocation(), E->getFoundDecl(), "receiver");
    return true;
  }
  bool VisitMemberExpr(MemberExpr *E) {
    // a member after `.` or `->` is no name of the scope; `x` for `this->x` is
    if (E->isImplicitAccess() && E->getMemberLoc().isValid())
      rec(E->getMemberLoc(), E->getFoundDecl().getDecl(), "receiver");
    return true;
  }
  bool VisitUnresolvedLookupExpr(UnresolvedLookupExpr *E) {
    recKind(E->getNameLoc(), "dependent", "receiver");
    return true;
  }
  bool VisitUnresolvedMemberExpr(UnresolvedMemberExpr *E) {
    if (E->isImplicitAccess()) recKind(E->getMemberLoc(), "dependent", "receiver");
    return true;
  }
  bool VisitDependentScopeDeclRefExpr(DependentScopeDeclRefExpr *E) {
    recKind(E->getLocation(), "dependent", "receiver");
    return true;
  }
  bool VisitCXXDependentScopeMemberExpr(CXXDependentScopeMemberExpr *E) {
    if (E->isImplicitAccess()) recKind(E->getMemberLoc(), "dependent", "receiver");
    return true;
  }
  bool VisitUsingDecl(UsingDecl *D) {
    for (auto *S : D->shadows()) { rec(D->getNameInfo().getLoc(), S->getTargetDecl(), "type"); break; }
    return true;
  }

  bool VisitNamedDecl(NamedDecl *D) {
    if (auto *T = dyn_cast<TagDecl>(D)) {
      if (T->isThisDeclarationADefinition()) recDecl(T);
    } else if (auto *TD = dyn_cast<TypedefNameDecl>(D)) {
      recAlias(TD);
    }
    return true;
  }

  // ---- output ----------------------------------------------------------------------
  void recDecl(TagDecl *D) {
    if (isa<ClassTemplateSpecializationDecl>(D)) return;
    std::string id = idOf(D);
    SourceLocation L = SM.getExpansionLoc(D->getLocation());
    std::string r = O.relOf(SM.getFileID(L));
    if (id.empty() || r.empty()) return;
    *O.os << "{\"decl\":\"" << esc(id) << "\",\"f\":\"" << esc(r) << "\",\"l\":"
          << SM.getSpellingLineNumber(L) << ",\"kind\":\"" << D->getKindName() << "\",\"anon\":"
          << (D->getQualifiedNameAsString().find("(anonymous namespace)") != std::string::npos)
          << "}\n";
    if (auto *C = dyn_cast<CXXRecordDecl>(D)) {
      *O.os << "{\"cls\":\"" << esc(id) << "\",\"f\":\"" << esc(r) << "\",\"bases\":[";
      bool first = true;
      for (auto &B : C->bases()) {
        QualType T = B.getType();
        const CXXRecordDecl *BD = T->getAsCXXRecordDecl();
        if (!first) *O.os << ",";
        first = false;
        *O.os << "[\"" << esc(T.getAsString()) << "\",\"" << esc(BD ? idOf(BD) : "") << "\",\""
              << esc(BD ? fileOf(BD) : "") << "\"," << T->isDependentType() << "]";
      }
      *O.os << "]}\n";
    }
  }

  void recAlias(TypedefNameDecl *TD) {
    if (throughAnonTypedef(TD) != TD || !TD->getTypeSourceInfo()) return;
    std::string id = idOf(TD);
    SourceLocation L = SM.getExpansionLoc(TD->getLocation());
    std::string r = O.relOf(SM.getFileID(L));
    if (id.empty() || r.empty()) return;
    AliasNames A;
    A.TraverseTypeLoc(TD->getTypeSourceInfo()->getTypeLoc());
    *O.os << "{\"aliasdecl\":\"" << esc(id) << "\",\"f\":\"" << esc(r) << "\",\"names\":[";
    bool first = true;
    for (auto &n : A.out) {
      if (n[1].empty()) continue;
      if (!first) *O.os << ",";
      first = false;
      *O.os << "[\"" << n[0] << "\",\"" << esc(n[1]) << "\",\"" << esc(n[2]) << "\"]";
    }
    *O.os << "]}\n";
  }

  // where a name stands: (file, line, column, macro), false when not below root
  bool where(SourceLocation Loc, std::string &file, unsigned &line, unsigned &col, const char *&macro) {
    macro = "";
    if (Loc.isInvalid()) return false;
    SourceLocation L = Loc;
    if (Loc.isMacroID()) {
      // a macro argument is written in the file; a name from a macro's body is not
      if (!SM.isMacroArgExpansion(Loc)) return false;
      L = SM.getSpellingLoc(Loc);
      macro = "arg";
      if (L.isMacroID()) return false;
    }
    file = O.relOf(SM.getFileID(L));
    if (file.empty()) return false;
    line = SM.getSpellingLineNumber(L);
    col = SM.getSpellingColumnNumber(L) - 1;
    return true;
  }

  std::string spelled(SourceLocation Loc) {
    return Lexer::getSpelling(SM.getSpellingLoc(Loc), Buf, SM, Ctx.getLangOpts()).str();
  }

  // the type the code is in (README: from), and whether a specialisation is around it
  std::string fromOf(bool &spec) {
    spec = false;
    for (const Decl *D : Stack) {
      if (isa<ClassTemplateSpecializationDecl>(D)) spec = true;
      if (auto *F = dyn_cast<FunctionDecl>(D)) {
        if (F->getTemplateSpecializationKind() == TSK_ExplicitSpecialization) spec = true;
        if (auto *M = dyn_cast<CXXMethodDecl>(F))
          if (isa<ClassTemplateSpecializationDecl>(M->getParent())) spec = true;
      }
      if (auto *Vd = dyn_cast<VarDecl>(D))
        if (Vd->isStaticDataMember() && isa<ClassTemplateSpecializationDecl>(Vd->getDeclContext()))
          spec = true;
    }
    for (auto it = Stack.rbegin(); it != Stack.rend(); ++it) {
      const Decl *D = *it;
      if (auto *R = dyn_cast<CXXRecordDecl>(D)) {
        if (R->isLambda() || isLocal(R)) continue;
        return idOf(R);
      }
      if (auto *E = dyn_cast<EnumDecl>(D)) {
        if (isLocal(E) || idOf(E).empty()) continue;   // an unnamed enum's: the class's
        return idOf(E);
      }
      if (auto *M = dyn_cast<CXXMethodDecl>(D)) {
        const CXXRecordDecl *P = M->getParent();
        if (P->isLambda() || isLocal(P)) continue;   // a local class's: the function's around it
        return idOf(P);
      }
      if (auto *F = dyn_cast<FunctionDecl>(D)) {
        // a friend defined in a class is the class's, where it is written
        if (F->getFriendObjectKind() != Decl::FOK_None)
          if (auto *R = dyn_cast<CXXRecordDecl>(F->getLexicalDeclContext()))
            if (!isLocal(R)) return idOf(R);
        // a block-scope declaration (`Lock l(Tag);` read as one) is the block's
        if (isLocal(F) || F->getLexicalDeclContext()->isFunctionOrMethod()) continue;
        return "";
      }
      if (auto *Vd = dyn_cast<VarDecl>(D)) {
        if (Vd->isStaticDataMember()) return idOf(cast<CXXRecordDecl>(Vd->getDeclContext()));
        if (isa<ParmVarDecl>(Vd) || Vd->isLocalVarDecl() || isLocal(Vd)) continue;
        return "";   // a variable of a namespace
      }
      if (isa<NamespaceDecl>(D) || isa<TranslationUnitDecl>(D)) return "";
    }
    return "";
  }

  void emit(SourceLocation Loc, const char *kind, const std::string &target, const std::string &tf,
            const char *pos) {
    if (Depth == 0) return;   // no body
    std::string file, name;
    unsigned line, col;
    const char *macro;
    if (!where(Loc, file, line, col, macro)) return;
    name = spelled(Loc);
    if (!AllOpt && !Names.count(name) && strcmp(kind, "type") && strcmp(kind, "alias")) return;
    if (Calls.count(Loc.getRawEncoding())) pos = "receiver";
    bool spec;
    std::string from = fromOf(spec);
    Line.clear();
    llvm::raw_string_ostream s(Line);
    s << "{\"n\":\"" << esc(name) << "\",\"f\":\"" << esc(file) << "\",\"l\":" << line
      << ",\"c\":" << col << ",\"k\":\"" << kind << "\",\"t\":\"" << esc(target)
      << "\",\"tf\":\"" << esc(tf) << "\",\"pos\":\"" << pos << "\",\"max\":"
      << !Parts.count(Loc.getRawEncoding()) << ",\"from\":\"" << esc(from) << "\",\"spec\":"
      << spec << ",\"m\":\"" << macro << "\"}\n";
    s.flush();
    if (Seen.insert(Line).second) *O.os << Line;
  }

  void rec(SourceLocation Loc, const NamedDecl *D, const char *pos) {
    if (!D || Loc.isInvalid()) return;
    if (auto *U = dyn_cast<UsingShadowDecl>(D)) D = U->getTargetDecl();
    D = throughAnonTypedef(D);
    const char *k = kindOf(D);
    bool named = !strcmp(k, "type") || !strcmp(k, "alias");
    emit(Loc, k, named ? idOf(D) : D->getQualifiedNameAsString(), named ? fileOf(D) : "", pos);
  }
  void recKind(SourceLocation Loc, const char *kind, const char *pos) { emit(Loc, kind, "", "", pos); }

  ASTContext &Ctx;
  SourceManager &SM;
  std::vector<const Decl *> Stack;
  int Depth = 0;
  std::unordered_set<unsigned> Calls, Parts;   // raw locations
  llvm::SmallVector<char, 64> Buf;
  std::string Line;
  std::unordered_set<std::string> Seen;
};

// ---- the table of `std` classes ---------------------------------------------------------
// {"aliases": {id: id}, "types": {id: {"bases": [id...], "members": [name...]}}}: every
// class of namespace std (and std's inline namespaces) the translation unit defines, with
// its public and protected members' names (fields, functions, nested types and aliases,
// enumerators of unscoped nested enums, using-declarations) and public and protected
// bases, without reserved names (`_M_x`, `__x`, `_Up`); and the typedefs and `using`
// aliases of namespace std that name such a class (`std::ostream`).

static bool reserved(llvm::StringRef n) {
  return n.starts_with("__") || (n.size() > 1 && n[0] == '_' && isupper(n[1])) || n.starts_with("_M_")
         || n.starts_with("_S_");
}

static bool inStd(const DeclContext *DC) {
  for (; DC; DC = DC->getParent()) {
    if (auto *N = dyn_cast<NamespaceDecl>(DC)) {
      if (N->getName() == "std" && isa<TranslationUnitDecl>(N->getParent())) return true;
      if (!N->isInline()) return false;
    } else if (!isa<TagDecl>(DC) && !isa<LinkageSpecDecl>(DC)) {
      return false;
    }
  }
  return false;
}

static std::string stdId(const NamedDecl *D) {
  // without std's inline namespaces (`std::__cxx11::basic_string` is std::basic_string)
  std::string id = idOf(D);
  size_t p;
  while ((p = id.find("::__")) != std::string::npos) {
    size_t e = id.find("::", p + 2);
    if (e == std::string::npos) break;
    id.erase(p, e - p);
  }
  return id;
}

class Table : public RecursiveASTVisitor<Table> {
public:
  bool VisitCXXRecordDecl(CXXRecordDecl *R) {
    if (!R->isThisDeclarationADefinition() || isa<ClassTemplateSpecializationDecl>(R) || !R->getIdentifier())
      return true;
    if (!inStd(R->getDeclContext()) || reserved(R->getName())) return true;
    for (const DeclContext *DC = R->getDeclContext(); isa<TagDecl>(DC); DC = DC->getParent())
      if (reserved(cast<TagDecl>(DC)->getName())) return true;
    std::string id = stdId(R);
    if (id.empty() || types.count(id)) return true;
    std::set<std::string> members;
    for (Decl *D : R->decls()) {
      auto *N = dyn_cast<NamedDecl>(D);
      if (!N || D->getAccess() == AS_private) continue;
      if (auto *E = dyn_cast<EnumDecl>(D))
        if (!E->isScoped())
          for (auto *C : E->enumerators())
            if (!reserved(C->getName())) members.insert(C->getName().str());
      if (!N->getIdentifier() || reserved(N->getName())) continue;
      if (isa<FieldDecl>(D) || isa<VarDecl>(D) || isa<CXXMethodDecl>(D) || isa<FunctionTemplateDecl>(D)
          || isa<TagDecl>(D) || isa<TypedefNameDecl>(D) || isa<ClassTemplateDecl>(D)
          || isa<TypeAliasTemplateDecl>(D) || isa<UsingDecl>(D) || isa<VarTemplateDecl>(D))
        members.insert(N->getName().str());
    }
    std::vector<std::string> bases;
    for (auto &B : R->bases())
      if (B.getAccessSpecifier() != AS_private)
        if (auto *BD = B.getType()->getAsCXXRecordDecl()) bases.push_back(stdId(BD));
    types[id] = {bases, members};
    return true;
  }
  bool VisitTypedefNameDecl(TypedefNameDecl *TD) {
    if (!isa<NamespaceDecl>(TD->getDeclContext()) || !inStd(TD->getDeclContext()) || reserved(TD->getName()))
      return true;
    if (auto *R = TD->getUnderlyingType()->getAsCXXRecordDecl()) aliases[stdId(TD)] = stdId(R);
    return true;
  }
  std::map<std::string, std::pair<std::vector<std::string>, std::set<std::string>>> types;
  std::map<std::string, std::string> aliases;
};

class Consumer : public ASTConsumer {
public:
  void HandleTranslationUnit(ASTContext &Ctx) override {
    if (TableOpt.empty()) {
      V v(Ctx);
      v.TraverseDecl(Ctx.getTranslationUnitDecl());
      return;
    }
    Table t;
    t.TraverseDecl(Ctx.getTranslationUnitDecl());
    *O.os << "{\"aliases\": {";
    bool first = true;
    for (auto &[a, to] : t.aliases) {
      if (!t.types.count(to)) continue;
      *O.os << (first ? "" : ",") << "\n\"" << esc(a) << "\": \"" << esc(to) << "\"";
      first = false;
    }
    *O.os << "},\n\"types\": {";
    first = true;
    for (auto &[id, v] : t.types) {
      *O.os << (first ? "" : ",") << "\n\"" << esc(id) << "\": {\"bases\": [";
      for (size_t i = 0; i < v.first.size(); ++i) *O.os << (i ? ", " : "") << "\"" << esc(v.first[i]) << "\"";
      *O.os << "], \"members\": [";
      size_t i = 0;
      for (auto &m : v.second) *O.os << (i++ ? ", " : "") << "\"" << esc(m) << "\"";
      *O.os << "]}";
      first = false;
    }
    *O.os << "}}\n";
  }
};

class Action : public ASTFrontendAction {
public:
  bool BeginSourceFileAction(CompilerInstance &CI) override {
    O.SM = &CI.getSourceManager();
    O.rel.clear();
    if (TableOpt.empty())
      CI.getPreprocessor().addPPCallbacks(std::make_unique<PP>(CI.getSourceManager()));
    return true;
  }
  std::unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &, StringRef) override {
    return std::make_unique<Consumer>();
  }
};

int main(int argc, const char **argv) {
  auto P = CommonOptionsParser::create(argc, argv, Cat);
  if (!P) { llvm::errs() << P.takeError(); return 1; }
  if (!TableOpt.empty()) {
    std::error_code ec;
    llvm::raw_fd_ostream os(TableOpt.getValue(), ec);
    if (ec) { llvm::errs() << TableOpt.getValue() << ": " << ec.message() << "\n"; return 1; }
    O.os = &os;
    ClangTool Tool(P->getCompilations(), P->getSourcePathList());
    return Tool.run(newFrontendActionFactory<Action>().get());
  }
  llvm::SmallString<256> root(RootOpt.getValue());
  llvm::sys::fs::make_absolute(root);
  llvm::sys::path::remove_dots(root, true);
  O.root = root.str().str();
  if (!NamesOpt.empty()) {
    std::ifstream in(NamesOpt.getValue());
    for (std::string n; std::getline(in, n);) if (!n.empty()) Names.insert(n);
  }
  llvm::sys::fs::create_directories(OutOpt.getValue());
  int failed = 0;
  for (const std::string &file : P->getSourcePathList()) {
    std::string out = OutOpt.getValue() + "/" + llvm::utohexstr(llvm::xxh3_64bits(file)) + ".jsonl";
    std::error_code ec;
    llvm::raw_fd_ostream os(out, ec);
    if (ec) { llvm::errs() << out << ": " << ec.message() << "\n"; return 1; }
    O.os = &os;
    auto t0 = std::chrono::steady_clock::now();
    ClangTool Tool(P->getCompilations(), {file});
    int rc = Tool.run(newFrontendActionFactory<Action>().get());
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t0).count();
    os << "{\"tu\":\"" << esc(file) << "\",\"ms\":" << ms << ",\"rc\":" << rc << "}\n";
    failed += rc != 0;
  }
  return failed ? 2 : 0;
}
