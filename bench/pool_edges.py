"""Pool the measured runs' edges into one blind list for labelling (RUBRIC.md, "Labelling").

    python3 bench/pool_edges.py [--round v2]

writes, under the round's labels directory (rounds.py),
  labels/blind_edges.csv   one row per distinct edge in its context (repository and
                           focus), shuffled with the fixed seed, with empty columns for
                           the labeller. No arm, run or «inferred» mark.
  labels/occurrences.csv   which runs drew each edge, with arm and «inferred» mark. Not
                           for the labeller: it unblinds.
  labels/nodes.csv         every node each run drew, for the existence check.

An undirected edge (`--`, `..`) keeps its two names in sorted order.

A later round carries over the final labels of every edge an earlier round already
labelled (same repository, focus, names, kind and direction: what a label depends on);
`carried_from` names that edge as the round that labelled it first named it, and the
labeller fills only the rows left empty.
"""

import argparse
import csv
import random
import re
from pathlib import Path

import yaml

import rounds
from parse_mermaid import diagram

BENCH = Path(__file__).resolve().parent
# as drawn and on top-level types (RUBRIC.md, "Two levels, and nesting edges")
LABEL_COLUMNS = ['source_fqn', 'target_fqn', 'label_drawn', 'file_line_drawn',
                 'label_top', 'file_line_top', 'unnamed', 'note']
# what an edge is judged to be, which rounds must agree on
VERDICT_COLUMNS = ['source_fqn', 'target_fqn', 'label_drawn', 'label_top', 'unnamed']


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--round', default='v1')
    args = ap.parse_args()
    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    pooled: dict[tuple, list[dict]] = {}
    nodes = []
    for meta_file in sorted(rounds.raw(args.round).glob('*.meta.json')):
        meta = yaml.safe_load(meta_file.read_text())
        d = diagram(meta_file.with_name(meta_file.name.replace('.meta.json', '.jsonl')))
        focus = meta['focus'] or '-'
        if d is None:                    # a failed run draws nothing (score.py counts it)
            continue
        nodes += [{'run': meta['id'], 'repo': meta['repo'], 'focus': focus, 'node': n} for n in sorted(d.nodes)]
        for e in d.edges:
            src, tgt = e['source'], e['target']
            if not e['directed']:
                src, tgt = sorted((src, tgt))
            key = (meta['repo'], focus, src, e['kind'], tgt, e['directed'])
            pooled.setdefault(key, []).append({'run': meta['id'], 'arm': meta['arm'], 'inferred': e['inferred']})

    keys = sorted(pooled)
    random.Random(tasks['selection']['seed']).shuffle(keys)
    # a series keeps what changed out of its ids, which the labeller reads (V3S-0001)
    prefix = 'E' if args.round == 'v1' else re.sub(r'-.*', 'S', args.round).upper() + '-'
    carried = {}
    # v1, v2, ... before this round; the earliest keeps an edge, which later ones carried. A
    # series of its own on round N's configuration with something changed (v3-haiku: another
    # model) carries over rounds 1 to N: a label depends on the edge and the source only
    n, series = re.fullmatch(r'v(\d+)(-.+)?', args.round).groups()
    for earlier in (f'v{i}' for i in range(1, int(n) + (1 if series else 0))):
        for r in csv.DictReader(open(rounds.labels(earlier) / 'final_edges.csv', newline='')):
            key = (r['repo'], r['focus'], r['source_name'], r['kind'], r['target_name'], r['directed'])
            first = carried.setdefault(key, r)
            # a later round that corrected an earlier one's label would be undone silently
            if any(first[c] != r[c] for c in VERDICT_COLUMNS):
                raise SystemExit(f'{r["edge_id"]} ({earlier}) and {first["edge_id"]} label the same '
                                 'edge differently; settle which holds before pooling')
    labels = rounds.labels(args.round)
    labels.mkdir(parents=True, exist_ok=True)
    if (labels / 'blind_edges.csv').exists() and any(
            r['label_top'] for r in csv.DictReader(open(labels / 'blind_edges.csv', newline=''))):
        raise SystemExit(f'{labels / "blind_edges.csv"} already holds labels; not overwritten')
    with open(labels / 'blind_edges.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['edge_id', 'repo', 'focus', 'source_name', 'kind', 'target_name', 'directed', *LABEL_COLUMNS]
                   + (['carried_from'] if carried else []))
        for i, (repo, focus, src, kind, tgt, directed) in enumerate(keys, 1):
            old = carried.get((repo, focus, src, kind, tgt, str(directed).lower()))
            w.writerow([f'{prefix}{i:04d}', repo, focus, src, kind, tgt, str(directed).lower(),
                        *[old[c] if old else '' for c in LABEL_COLUMNS]]
                       + ([old['edge_id'] if old else ''] if carried else []))
    with open(labels / 'occurrences.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['edge_id', 'run', 'arm', 'inferred'])
        for i, key in enumerate(keys, 1):
            for o in pooled[key]:
                w.writerow([f'{prefix}{i:04d}', o['run'], o['arm'], str(o['inferred']).lower()])
    with open(labels / 'nodes.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['run', 'repo', 'focus', 'node'])
        w.writeheader()
        w.writerows(nodes)
    n_carried = sum((repo, focus, src, kind, tgt, str(d).lower()) in carried for repo, focus, src, kind, tgt, d in keys)
    print(f'{sum(len(v) for v in pooled.values())} edges drawn, {len(keys)} distinct in context '
          f'({n_carried} labelled in earlier rounds, {len(keys) - n_carried} to label), {len(nodes)} nodes')


if __name__ == '__main__':
    main()
