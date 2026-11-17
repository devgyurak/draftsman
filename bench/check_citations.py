"""Check every declared and body-only label's citation (RUBRIC.md, "Labelling", step 3).

A citation passes when the cited line exists, sits in the file that declares the
using end's top-level type, and names the used end: its simple name, or at the top level
also the name of a type nested in it (`Request` for `Connection`). The using end is the
source; an undirected edge may cite either end. Labels flagged unnamed are not checked
(they always go to review), nor are ends outside the checkout.

    python3 bench/check_citations.py --repos <dir with the checkouts>

writes labels/citations.csv (edge, level, status, reason) and prints the failures.
"""

import argparse
import csv
import re
from functools import cache
from pathlib import Path

BENCH = Path(__file__).resolve().parent


def top(fqn: str) -> str:
    parts = fqn.split('.')
    for i, p in enumerate(parts):
        if p[:1].isupper():
            return '.'.join(parts[:i + 1])
    return fqn


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.java = [p for p in root.rglob('*.java')]

    @cache
    def file_of(self, top_fqn: str) -> Path | None:
        """The file declaring a top-level type: by file name, else by declaration."""
        package, _, name = top_fqn.rpartition('.')
        tail = Path(*package.split('.'), f'{name}.java')
        for p in self.java:
            if p.as_posix().endswith(tail.as_posix()):
                return p
        decl = re.compile(rf'\b(class|interface|enum|record|@interface)\s+{re.escape(name)}\b')
        for p in self.java:
            if p.parent.as_posix().endswith(Path(*package.split('.')).as_posix()) and \
                    decl.search(p.read_text(errors='replace')):
                return p
        return None

    @cache
    def nested_names(self, top_fqn: str) -> frozenset[str]:
        f = self.file_of(top_fqn)
        if not f:
            return frozenset()
        return frozenset(re.findall(r'\b(?:class|interface|enum|record)\s+([A-Z]\w*)', f.read_text(errors='replace')))


def check(repo: Repo, using: str, used: str, cited: str, level: str) -> str | None:
    """None if the citation passes, else the reason."""
    path, _, line_no = cited.rpartition(':')
    if not path or not line_no.isdigit():
        return 'no file:line'
    f = repo.root / path
    if not f.is_file():
        return 'no such file'
    lines = f.read_text(errors='replace').splitlines()
    n = int(line_no)
    if not 1 <= n <= len(lines):
        return 'no such line'
    home = repo.file_of(top(using))
    if home is None:
        return 'using end not in checkout'
    if home.resolve() != f.resolve():
        return f'cited file is not {top(using).rsplit(".", 1)[-1]}\'s'
    names = {used.rsplit('.', 1)[-1]}
    if level == 'top':
        names |= {top(used).rsplit('.', 1)[-1]} | set(repo.nested_names(top(used)))
    if not any(re.search(rf'\b{re.escape(x)}\b', lines[n - 1]) for x in names):
        return 'line does not name the used end'
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repos', type=Path, required=True)
    args = ap.parse_args()
    rows = list(csv.DictReader(open(BENCH / 'labels' / 'blind_edges.csv', newline='')))
    repos: dict[str, Repo] = {}
    out = []
    for r in rows:
        repo = repos.setdefault(r['repo'], Repo(args.repos / r['repo']))
        for level in ('drawn', 'top'):
            label, cited = r[f'label_{level}'], r[f'file_line_{level}']
            if label not in ('declared', 'body_only'):
                continue
            if r['unnamed'] == 'true':
                out.append((r['edge_id'], level, 'review', 'unnamed'))
                continue
            src, tgt = r['source_fqn'], r['target_fqn']
            if repo.file_of(top(src)) is None and repo.file_of(top(tgt)) is None:
                out.append((r['edge_id'], level, 'skipped', 'both ends outside the checkout'))
                continue
            reason = check(repo, src, tgt, cited, level)
            if reason and r['directed'] == 'false':
                reason = check(repo, tgt, src, cited, level) and reason
            out.append((r['edge_id'], level, 'fail' if reason else 'pass', reason or ''))
    with open(BENCH / 'labels' / 'citations.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['edge_id', 'level', 'status', 'reason'])
        w.writerows(out)
    counts = {}
    for _, _, s, _ in out:
        counts[s] = counts.get(s, 0) + 1
    print(counts)
    for e, level, s, why in out:
        if s != 'pass':
            print(f'  {e} {level:5s} {s:7s} {why}')


if __name__ == '__main__':
    main()
