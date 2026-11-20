"""Annotations, attributes and decorators as relations (issue #4).

An annotation whose type is the project's is a dependency of the annotated type, and so
is every project type named in its arguments (`X.class`, `typeof(X)`, `X::class`,
`Kind.A`, a class passed to a decorator), `via` the annotation. Annotations on members
and parameters count for the enclosing type; framework annotations stay names only.
"""

from conftest import extract_source

from draftsman.scene import build_scene
from draftsman.view import View


def facts(ir):
    def short(tid):
        return tid.replace("::", ".").replace("/", ".").rsplit(".", 1)[-1]
    return {(short(r.from_), short(r.to), r.via) for r in ir.relations
            if (r.via or "").startswith("@")}


def test_java(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Handler.java": "package p; public interface Handler { @interface Sharable { } }",
        "p/Hints.java": "package p; class Hints { }",
        "p/Kind.java": "package p; enum Kind { A }",
        "p/Conv.java": "package p; class Conv { }",
        "p/G.java": "package p; interface G { }",
        "p/Inner.java": "package p; @interface Inner { Class<?> value(); }",
        "p/Y.java": "package p; class Y { }",
        "p/Mark.java": "package p; @interface Mark { Kind value(); }",
        "p/Enc.java": """package p;
import p.Handler.Sharable;
import org.springframework.context.annotation.ImportRuntimeHints;
import javax.persistence.*;
@Sharable
@ImportRuntimeHints({Hints.class, Y[].class})
@Entity
class Enc {
    @Convert(converter = Conv.class) @Mark(Kind.A) String f;
    void m(@javax.validation.Valid(groups = G.class) String s) {
        @SuppressWarnings(Body.class) int local = 0;
    }
    @org.x.Outer(@Inner(Y.class)) void n() {}
    @Missing(Gone.class) void o() {}
}
"""})
    assert facts(ir) == {
        ("Enc", "Sharable", "@Sharable"),             # an imported nested annotation type
        ("Enc", "Hints", "@ImportRuntimeHints"),      # framework annotation, project argument
        ("Enc", "Y", "@ImportRuntimeHints"),          # `Y[].class`
        ("Enc", "Conv", "@Convert"),                  # on a field: the enclosing type's
        ("Enc", "Mark", "@Mark"),
        ("Enc", "Kind", "@Mark"),                     # `Kind.A`: an enum constant of Kind
        ("Enc", "G", "@javax.validation.Valid"),      # on a parameter
        ("Enc", "Inner", "@Inner"),                   # a nested annotation is its own entry
        ("Enc", "Y", "@Inner"),
    }
    # `@Entity`, `@Convert` and `@Missing` stay names; `Gone.class` names a type nobody
    # declares, so it is unresolved like a signature type; `Body.class` in a method body
    # is not part of the declaration
    assert {(u.raw_type, u.via, u.reason) for u in ir.unresolved} == {
        ("Gone", "@Missing", "outside")}
    enc = next(t for t in ir.types if t.name == "Enc")
    assert enc.annotations == ["Sharable", "ImportRuntimeHints", "Entity"]


def test_kotlin(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Types.kt": """package p
annotation class Dispatcher(val d: Dispatchers)
enum class Dispatchers { IO }
@RequiresOptIn annotation class InternalApi
class Ser
class Entity
object Migrations { class Schema2to3 }
class Holder { companion object { class Serializer } }
""",
        "p/Db.kt": """package p
import kotlinx.serialization.Serializable
@Serializable(with = Ser::class)
@androidx.room.Database(entities = [Entity::class], migrations = [AutoMigration(spec = Migrations.Schema2to3::class)])
@OptIn(InternalApi::class)
class Db(@Dispatcher(Dispatchers.IO) val io: String) {
    @Serializable(with = Holder.Companion.Serializer::class) val h: String = ""
    fun f() { listOf(Ser::class) }
}
"""})
    assert facts(ir) == {
        ("Db", "Ser", "@Serializable"),
        ("Db", "Entity", "@androidx.room.Database"),
        ("Db", "Schema2to3", "@androidx.room.Database"),   # `Outer.Inner::class`
        ("Db", "InternalApi", "@OptIn"),
        ("Db", "Dispatcher", "@Dispatcher"),               # on a constructor property
        ("Db", "Dispatchers", "@Dispatcher"),
        ("Db", "Serializer", "@Serializable"),             # through `Companion`
    }
    assert not ir.unresolved


def test_csharp(tmp_path):
    ir = extract_source(tmp_path, {
        "Types.cs": """namespace App {
public class MarkerAttribute : System.Attribute { }
public class Conv { }
public static class Consts { public const string Admin = "a"; }
public class Q { }
public static class Route { }
}""",
        "Api.cs": """using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Mvc;
namespace App {
[Marker, JsonConverter(typeof(Conv))]
[Route("api")]
public class Api {
    [Authorize(Roles = Consts.Admin)] public int F;
    public void M([FromServices] Q q, [Bind(nameof(Q))] int x) { }
}
}"""})
    assert facts(ir) == {
        ("Api", "MarkerAttribute", "@Marker"),   # `[Marker]` is MarkerAttribute
        ("Api", "Conv", "@JsonConverter"),
        ("Api", "Consts", "@Authorize"),
        ("Api", "Q", "@Bind"),                   # `nameof(Q)`
    }
    # `[Route]` is ASP.NET's: the project's static class Route is no attribute
    assert not ir.unresolved


def test_python(tmp_path):
    ir = extract_source(tmp_path, {
        "app/__init__.py": "",
        "app/models.py": "class Model:\n    pass\n\nclass Other:\n    pass\n",
        "app/util.py": "class classproperty:\n    def __init__(self, f):\n        self.f = f\n",
        "app/admin.py": """from django.contrib import admin
from .models import Model, Other
from .util import classproperty

@admin.register(Model, site=admin.site)
class ModelAdmin(admin.ModelAdmin):
    @classproperty
    def label(cls):
        return "x"

    @validates(Other, kind=Model)
    def check(self):
        @inner(Other)
        def local():
            pass
"""})
    assert facts(ir) == {
        ("ModelAdmin", "Model", "@admin.register"),
        ("ModelAdmin", "classproperty", "@classproperty"),   # a class used as a decorator
        ("ModelAdmin", "Other", "@validates"),
        ("ModelAdmin", "Model", "@validates"),
    }
    assert not ir.unresolved


def test_typescript(tmp_path):
    ir = extract_source(tmp_path, {
        "src/users.ts": "export class UsersModule {}\nexport class UsersService {}\n"
                        "export class User {}\nexport const TOKEN = 'x';\n",
        "src/app.module.ts": """import { Module, Inject } from '@nestjs/common';
import { Type } from 'class-transformer';
import { InjectRepository } from '@nestjs/typeorm';
import { UsersModule, UsersService, User, TOKEN } from './users';
import * as users from './users';

@Module({ imports: [UsersModule], providers: [users.UsersService] })
export class AppModule {
  @Type(() => User) @Inject(TOKEN) user: User;
  constructor(@InjectRepository(UsersService) private repo: unknown) {}
}
"""})
    assert facts(ir) == {
        ("AppModule", "UsersModule", "@Module"),
        ("AppModule", "UsersService", "@Module"),           # `users.UsersService`
        ("AppModule", "User", "@Type"),                     # `() => User`
        ("AppModule", "UsersService", "@InjectRepository"),
    }
    assert not ir.unresolved


def test_view_can_leave_annotation_relations_out(tmp_path):
    ir = extract_source(tmp_path, {
        "p/Mark.java": "package p; @interface Mark { }",
        "p/Hints.java": "package p; class Hints { }",
        "p/A.java": "package p; @Mark @org.x.Import(Hints.class) class A { Hints h() { return null; } }"})
    drawn = build_scene(ir, View.from_dict({}))
    assert {r.to.rsplit(".", 1)[-1] for r in drawn.relations} == {"Mark", "Hints"}
    plain = build_scene(ir, View.from_dict({"annotations": False}))
    # A -> Hints stays: h() names it too
    assert {(r.to.rsplit(".", 1)[-1], r.via) for r in plain.relations} == {("Hints", "h")}
    focus = build_scene(ir, View.from_dict({"focus": "Mark", "hops": 1, "annotations": False}))
    assert [t.name for t in focus.types] == ["Mark"]
