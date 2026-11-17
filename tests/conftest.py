from __future__ import annotations

from pathlib import Path

import pytest

from draftsman.extractor import Extractor
from draftsman.langs import spec_for_path
from draftsman.resolve import build_ir
from draftsman.wrappers import Wrappers

FIXTURES = Path(__file__).parent / "fixtures"


def extract_dir(root: Path):
    raw = []
    for p in sorted(root.rglob("*")):
        spec = spec_for_path(p.name)
        if p.is_file() and spec is not None:
            raw.append(Extractor(spec).extract(p, p.relative_to(root).as_posix(), root))
    return build_ir(root.name, raw, Wrappers.load())


def extract_source(tmp_path: Path, files: dict[str, str]):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return extract_dir(tmp_path)


@pytest.fixture(scope="session")
def shop_ir():
    return extract_dir(FIXTURES / "java" / "shop")
