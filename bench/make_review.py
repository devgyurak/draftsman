"""Build the human-review sheet (RUBRIC.md, "Labelling", step 4).

Every edge labelled unsupported, indirect, wrong kind or direction, or undecidable at
either level; every unnamed label and failed citation; the rows the labeller flagged; and
a 20% sample of the rest (fixed seed). Each row carries the cited lines and the
production files in which both simple names appear, so an empty list confirms
*unsupported* at once. No arm or run: the sheet stays blind.

    python3 bench/make_review.py --repos <dir with the checkouts>
"""

import argparse
import csv
import random
import re
from pathlib import Path

import yaml

from select_focus import excluded

BENCH = Path(__file__).resolve().parent
ALWAYS = {'unsupported', 'indirect', 'wrong_kind_or_direction', 'undecidable'}
# rows the labelling session listed as uncertain (its report)
FLAGGED = {'E0032', 'E0259', 'E0071', 'E0149', 'E0132', 'E0461', 'E0256', 'E0243',
           'E0278', 'E0227', 'E0206', 'E0275'}
_PD = 'common/src/main/java/io/netty/util/internal/PlatformDependent.java:622'
_SSL = 'microbench/src/main/java/io/netty/microbench/handler/ssl/AbstractSslEngineBenchmark.java:128'
_ANON = 'RUBRIC "Decided at review": anonymous class as a node, strongest evidence of the pair'
_UNDECIDABLE = 'RUBRIC "Decided at review": the focus file decides the name'
_NESTED = 'RUBRIC "Decided at review": outer-to-nested use, self at the top level'
# edge -> (verdict, label_drawn, file_line_drawn, label_top, file_line_top, note), prefilled
DECIDED = {
    **{e: ('change', 'declared', _PD, 'declared', _PD, _ANON) for e in ('E0027', 'E0091', 'E0297')},
    'E0028': ('change', 'declared', _SSL, 'declared', _SSL, _ANON),
    **{e: ('agree', '', '', '', '', _UNDECIDABLE)
       for e in ('E0003', 'E0086', 'E0242', 'E0415', 'E0258', 'E0085', 'E0270')},
    **{e: ('agree', '', '', '', '', _NESTED) for e in ('E0004', 'E0094', 'E0369', 'E0408')},
}


def top(fqn: str) -> str:
    parts = fqn.split('.')
    for i, p in enumerate(parts):
        if p[:1].isupper():
            return '.'.join(parts[:i + 1])
    return fqn


def simple(fqn: str, drawn: str) -> str:
    if fqn in ('', '?') or '|' in fqn:
        return re.sub(r'.*[._]', '', drawn)
    return fqn.rsplit('.', 1)[-1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repos', type=Path, required=True)
    args = ap.parse_args()
    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    rows = list(csv.DictReader(open(BENCH / 'labels' / 'blind_edges.csv', newline='')))
    failed = {r['edge_id'] for r in csv.DictReader(open(BENCH / 'labels' / 'citations.csv'))
              if r['status'] == 'fail'}

    texts: dict[str, dict[str, str]] = {}
    for repo, spec in tasks['repos'].items():
        root = args.repos / repo
        texts[repo] = {p.relative_to(root).as_posix(): p.read_text(errors='replace')
                       for r in spec['roots'] for p in (root / r).rglob('*.java')
                       if not excluded(p.relative_to(root).as_posix(), spec['exclude'])}

    def why(r: dict) -> str:
        reasons = sorted({r['label_drawn'], r['label_top']} & ALWAYS)
        if r['unnamed'] == 'true':
            reasons.append('unnamed')
        if r['edge_id'] in failed:
            reasons.append('citation')
        if r['edge_id'] in FLAGGED:
            reasons.append('labeller flagged')
        return ', '.join(reasons)

    must = [r for r in rows if why(r)]
    rest = [r for r in rows if not why(r)]
    sample = random.Random(tasks['selection']['seed']).sample(rest, round(len(rest) * 0.2))

    def cited(repo: str, ref: str) -> str:
        path, _, n = ref.rpartition(':')
        text = texts[repo].get(path) or ((args.repos / repo / path).read_text(errors='replace')
                                         if path and (args.repos / repo / path).is_file() else '')
        lines = text.splitlines()
        return lines[int(n) - 1].strip() if n.isdigit() and 0 < int(n) <= len(lines) else ''

    out = []
    for r in sorted(must, key=lambda r: r['edge_id']) + sorted(sample, key=lambda r: r['edge_id']):
        a, b = simple(r['source_fqn'], r['source_name']), simple(r['target_fqn'], r['target_name'])
        both = sorted(p for p, t in texts[r['repo']].items()
                      if re.search(rf'\b{re.escape(a)}\b', t) and re.search(rf'\b{re.escape(b)}\b', t))
        focus = r['focus']
        incident = focus != '-' and top(focus) in (top(r['source_fqn']), top(r['target_fqn']))
        verdict, drawn, line_drawn, top_, line_top, note = DECIDED.get(r['edge_id'], ('',) * 6)
        out.append({**r, 'review_because': why(r) or 'sample',
                    'focus_incident': str(incident).lower(),
                    'cited_drawn': cited(r['repo'], r['file_line_drawn']),
                    'cited_top': cited(r['repo'], r['file_line_top']),
                    'files_naming_both': ' '.join(both[:12]) + (f' (+{len(both) - 12})' if len(both) > 12 else ''),
                    'verdict': verdict, 'new_label_drawn': drawn, 'new_file_line_drawn': line_drawn,
                    'new_label_top': top_, 'new_file_line_top': line_top, 'reviewer_note': note})
    with open(BENCH / 'labels' / 'review.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f'{len(must)} to review in full, {len(sample)} sampled of {len(rest)}; '
          f'{sum(o["focus_incident"] == "true" for o in out)} incident to the focus')


if __name__ == '__main__':
    main()
