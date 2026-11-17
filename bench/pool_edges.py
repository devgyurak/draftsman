"""Pool the measured runs' edges into one blind list for labelling (RUBRIC.md, "Labelling").

    python3 bench/pool_edges.py

writes
  labels/blind_edges.csv   one row per distinct edge in its context (repository and
                           focus), shuffled with the fixed seed, with empty columns for
                           the labeller. No arm, run or «inferred» mark.
  labels/occurrences.csv   which runs drew each edge, with arm and «inferred» mark. Not
                           for the labeller: it unblinds.
  labels/nodes.csv         every node each run drew, for the existence check.

An undirected edge (`--`, `..`) keeps its two names in sorted order.
"""

import csv
import random
from pathlib import Path

import yaml

from parse_mermaid import diagram

BENCH = Path(__file__).resolve().parent
LABEL_COLUMNS = ['source_fqn', 'target_fqn', 'label', 'unnamed', 'file_line', 'note']


def main() -> None:
    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    pooled: dict[tuple, list[dict]] = {}
    nodes = []
    for meta_file in sorted((BENCH / 'results' / 'raw' / 'measured').glob('*.meta.json')):
        meta = yaml.safe_load(meta_file.read_text())
        d = diagram(meta_file.with_name(meta_file.name.replace('.meta.json', '.jsonl')))
        focus = meta['focus'] or '-'
        nodes += [{'run': meta['id'], 'repo': meta['repo'], 'focus': focus, 'node': n} for n in sorted(d.nodes)]
        for e in d.edges:
            src, tgt = e['source'], e['target']
            if not e['directed']:
                src, tgt = sorted((src, tgt))
            key = (meta['repo'], focus, src, e['kind'], tgt, e['directed'])
            pooled.setdefault(key, []).append({'run': meta['id'], 'arm': meta['arm'], 'inferred': e['inferred']})

    keys = sorted(pooled)
    random.Random(tasks['selection']['seed']).shuffle(keys)
    labels = BENCH / 'labels'
    with open(labels / 'blind_edges.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['edge_id', 'repo', 'focus', 'source_name', 'kind', 'target_name', 'directed', *LABEL_COLUMNS])
        for i, (repo, focus, src, kind, tgt, directed) in enumerate(keys, 1):
            w.writerow([f'E{i:04d}', repo, focus, src, kind, tgt, str(directed).lower(), *[''] * len(LABEL_COLUMNS)])
    with open(labels / 'occurrences.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['edge_id', 'run', 'arm', 'inferred'])
        for i, key in enumerate(keys, 1):
            for o in pooled[key]:
                w.writerow([f'E{i:04d}', o['run'], o['arm'], str(o['inferred']).lower()])
    with open(labels / 'nodes.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['run', 'repo', 'focus', 'node'])
        w.writeheader()
        w.writerows(nodes)
    print(f'{sum(len(v) for v in pooled.values())} edges drawn, {len(keys)} distinct in context, '
          f'{len(nodes)} nodes')


if __name__ == '__main__':
    main()
