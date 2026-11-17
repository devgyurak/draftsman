"""Choose the T2 focus classes from grep counts, without Draftsman.

For every top-level public class, interface or record of a repository's production
sources (file name = type name, simple name declared once):

  uses     distinct other project type names that appear in its file
  used_by  other production files that mention its simple name

Comments and string literals are blanked first. The metric is uses + used_by. Classes
outside [min, max] are dropped; the rest are ranked and cut into equal strata, and one
class per stratum is drawn with the fixed seed. Pilot classes are drawn from the same
pool with the pilot seed, never a measured class.

    python3 bench/select_focus.py --repos <dir with the checkouts>

writes bench/focus.yaml and bench/results/candidates/<repo>.csv.
"""

import argparse
import csv
import fnmatch
import random
import re
from collections import Counter
from pathlib import Path

import yaml

BENCH = Path(__file__).resolve().parent

# comments and literals, longest first so that "//" inside a string stays in the string
_NOISE = re.compile(r'/\*.*?\*/|//[^\n]*|"""(?:.|\n)*?"""|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'',
                    re.S)
_DECL = re.compile(r'\b(?:class|interface|enum|record|@interface)\s+([A-Z]\w*)')
_MODIFIERS = r'(?:(?:abstract|final|sealed|non-sealed|static|strictfp)\s+)*'
_IDENT = re.compile(r'\b[A-Z]\w*\b')


def blank(text: str) -> str:
    return _NOISE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group()), text)


def excluded(rel: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or (pat.startswith('**/') and fnmatch.fnmatch(rel, pat[3:])):
            return True
    return False


def production_files(checkout: Path, roots: list[str], exclude: list[str]) -> dict[str, str]:
    files = {}
    for root in roots:
        for path in sorted((checkout / root).rglob('*.java')):
            rel = path.relative_to(checkout).as_posix()
            if path.name in ('package-info.java', 'module-info.java') or excluded(rel, exclude):
                continue
            files[rel] = blank(path.read_text(encoding='utf-8', errors='replace'))
    return files


def candidates(files: dict[str, str], kinds: list[str], unique: bool) -> list[dict]:
    declared = Counter(name for text in files.values() for name in _DECL.findall(text))
    project = set(declared)
    words = {rel: set(_IDENT.findall(text)) for rel, text in files.items()}
    kind_alt = '|'.join(kinds)
    rows = []
    for rel, text in files.items():
        name = Path(rel).stem
        top = re.search(rf'^public\s+{_MODIFIERS}({kind_alt})\s+{name}\b', text, re.M)
        if not top or (unique and declared[name] != 1):
            continue
        package = re.search(r'^\s*package\s+([\w.]+)\s*;', text, re.M)
        uses = len((words[rel] & project) - {name})
        used_by = sum(1 for other, ws in words.items() if other != rel and name in ws)
        rows.append({'name': name, 'fqn': f'{package.group(1)}.{name}' if package else name,
                     'kind': top.group(1), 'file': rel, 'uses': uses, 'used_by': used_by,
                     'metric': uses + used_by})
    return sorted(rows, key=lambda r: (r['metric'], r['fqn']))


def draw(pool: list[dict], strata: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    size = len(pool) / strata
    chosen = []
    for i in range(strata):
        stratum = pool[round(i * size):round((i + 1) * size)]
        pick = dict(rng.choice(stratum))
        pick['stratum'] = ['low', 'middle', 'high'][i] if strata == 3 else i
        chosen.append(pick)
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repos', type=Path, required=True, help='directory holding the checkouts')
    args = ap.parse_args()

    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    sel = tasks['selection']
    out = {'rule': {k: sel[k] for k in ('kinds', 'unique_simple_name', 'metric', 'min', 'max',
                                         'strata', 'seed', 'pilot_seed')},
           'measured': {}, 'pilot': {}}
    (BENCH / 'results' / 'candidates').mkdir(parents=True, exist_ok=True)

    for repo in tasks['tasks']['T2']['repos']:
        spec = tasks['repos'][repo]
        files = production_files(args.repos / repo, spec['roots'], spec['exclude'])
        rows = candidates(files, sel['kinds'], sel['unique_simple_name'])
        with open(BENCH / 'results' / 'candidates' / f'{repo}.csv', 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        pool = [r for r in rows if sel['min'] <= r['metric'] <= sel['max']]
        measured = draw(pool, sel['strata'], sel['seed'])
        out['measured'][repo] = measured
        if repo in sel['pilot_repos']:
            rest = [r for r in pool if r['fqn'] not in {m['fqn'] for m in measured}]
            out['pilot'][repo] = [dict(random.Random(sel['pilot_seed']).choice(rest))]
        print(f'{repo}: {len(files)} files, {len(rows)} candidates, {len(pool)} in '
              f'[{sel["min"]}, {sel["max"]}] -> ' + ', '.join(
                  f'{m["name"]} ({m["stratum"]}, {m["metric"]})' for m in measured)
              + (f' | pilot {out["pilot"][repo][0]["name"]}' if repo in out['pilot'] else ''))

    (BENCH / 'focus.yaml').write_text(
        '# Written by select_focus.py; committed before any measured run.\n'
        + yaml.safe_dump(out, sort_keys=False, allow_unicode=True))


if __name__ == '__main__':
    main()
