from __future__ import annotations

from .base import FileScope, Import, LanguageSpec
from .cpp import CppSpec
from .csharp import CSharpSpec
from .java import JavaSpec
from .kotlin import KotlinSpec
from .python import PythonSpec
from .typescript import TsxSpec, TypeScriptSpec

LANGUAGES: dict[str, LanguageSpec] = {spec.name: spec for spec in (
    JavaSpec(), CSharpSpec(), KotlinSpec(), TypeScriptSpec(), TsxSpec(), PythonSpec(), CppSpec(),
)}


def spec_for_path(path: str) -> LanguageSpec | None:
    for spec in LANGUAGES.values():
        if path.endswith(spec.extensions):
            return spec
    return None


__all__ = ["FileScope", "Import", "LanguageSpec", "LANGUAGES", "spec_for_path"]
