"""Score the measured runs (RUBRIC.md, "Measures").

    uv run python bench/score.py --repos <dir with the checkouts> [--round v2]

Applies the human review (review.csv) to the first labels, unblinds them with
occurrences.csv and writes, in the round's directories (rounds.py),
  final_edges.csv   the labels scored: the first labels with the review applied
  runs.csv          one row per run
  summary.csv       per task, repository and arm; T2 also over jsoup and Netty
                                together, and over all three repositories
and prints the relations labelled as real that the recall denominators lack, which
RUBRIC.md ("Recall denominators") says to add by hand.

Edge measures are on the edges each run drew, counted once per run: at the top level an
edge is its pair of top-level types with its kind and direction, so two nested edges that
collapse onto one pair count once. Shares are pooled over the runs of a group (sum of
counts over sum of edges scored); recall is the mean over runs, n/a left out.
"""

import argparse
import csv
import json
import re
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

import yaml

import rounds
from check_citations import Repo
from parse_mermaid import diagram
from select_focus import excluded

BENCH = Path(__file__).resolve().parent
# worst first: an edge whose drawings disagree at the top level takes the worst label
ORDER = ['unsupported', 'indirect', 'wrong_kind_or_direction', 'body_only', 'declared', 'undecidable', 'self']
STRENGTH = {'declared': 2, 'body_only': 1}


def top(fqn: str) -> str:
    parts = fqn.split('.')
    for i, p in enumerate(parts):
        if p[:1].isupper():
            return '.'.join(parts[:i + 1])
    return fqn


def tops(fqn: str) -> set[str]:
    """Top-level types of an end; an undecidable end lists several."""
    return {top(f) for f in fqn.split('|')}


def final_labels(labels: Path) -> dict[str, dict]:
    rows = {r['edge_id']: r for r in csv.DictReader(open(labels / 'blind_edges.csv', newline=''))}
    for r in csv.DictReader(open(labels / 'review.csv', newline='')):
        e = rows[r['edge_id']]
        e['reviewed'] = r['verdict']
        if r['verdict'] != 'change':
            continue
        for level in ('drawn', 'top'):
            if r[f'new_label_{level}']:
                e[f'label_{level}'] = r[f'new_label_{level}']
                e[f'file_line_{level}'] = r[f'new_file_line_{level}']
        e['note'] = (e['note'] + '; ' if e['note'] else '') + 'review: ' + r['reviewer_note']
    for e in rows.values():
        e.setdefault('reviewed', '')
    with open(labels / 'final_edges.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(next(iter(rows.values()))))
        w.writeheader()
        w.writerows(rows.values())
    return rows


def denominators(repo: str, focus: str) -> list[dict]:
    name = '_T1_all' if focus == '-' else focus.rsplit('.', 1)[-1]
    return list(csv.DictReader(open(rounds.DENOMINATORS / repo / f'{name}.csv', newline='')))


def recall_pairs(rows: list[dict], level: str) -> dict[tuple, dict[str, str]]:
    """{(direction, user, used): evidence}, collapsed at the top level (strongest evidence)."""
    pairs: dict[tuple, str] = {}
    for r in rows:
        src, tgt = r['source_type'], r['target_type']
        if level == 'top':
            src, tgt = top(src), top(tgt)
            if src == tgt:
                continue
        elif 'counts when collapsed' in r['note']:
            continue
        key = (r['direction'], src, tgt)
        if STRENGTH[r['evidence']] > STRENGTH.get(pairs.get(key, ''), 0):
            pairs[key] = r['evidence']
    return pairs


def transcript_facts(path: Path) -> dict:
    result, skills, agents = {}, [], 0
    for line in open(path):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'result':
            result = event
        for block in (event.get('message') or {}).get('content') or []:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                if block.get('name') == 'Skill':
                    skills.append(block.get('input', {}).get('skill', ''))
                elif block.get('name') in ('Task', 'Agent'):
                    agents += 1
    usage = result.get('modelUsage') or {}
    return {
        'cost_usd': result.get('total_cost_usd'),
        'seconds': (result.get('duration_ms') or 0) / 1000,
        'turns': result.get('num_turns'),
        'tokens': sum(u.get('inputTokens', 0) + u.get('outputTokens', 0) + u.get('cacheReadInputTokens', 0)
                      + u.get('cacheCreationInputTokens', 0) for u in usage.values()),
        'output_tokens': sum(u.get('outputTokens', 0) for u in usage.values()),
        'is_error': result.get('is_error', True) or result.get('subtype') != 'success',
        'skills': skills,
        'subagents': agents,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repos', type=Path, required=True)
    ap.add_argument('--round', default='v1')
    args = ap.parse_args()
    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    labels = rounds.labels(args.round)
    edges = final_labels(labels)
    drawn_in: dict[str, dict[str, bool]] = defaultdict(dict)   # run -> edge -> every drawing inferred
    for o in csv.DictReader(open(labels / 'occurrences.csv', newline='')):
        seen = drawn_in[o['run']]
        seen[o['edge_id']] = seen.get(o['edge_id'], True) and o['inferred'] == 'true'
    nodes = defaultdict(list)
    for n in csv.DictReader(open(labels / 'nodes.csv', newline='')):
        nodes[n['run']].append(n['node'])

    repos = {name: Repo(args.repos / name) for name in tasks['repos']}
    words = {name: set(subprocess.run(['git', '-C', str(args.repos / name), 'grep', '-hoIwE', '[A-Za-z_][A-Za-z0-9_]*'],
                                      capture_output=True, text=True, check=True).stdout.split())
             for name in tasks['repos']}

    def production(repo: str, fqn: str) -> bool:
        f = repos[repo].file_of(top(fqn)) if '|' not in fqn else None
        if f is None:
            return False
        rel = f.relative_to(repos[repo].root).as_posix()
        spec = tasks['repos'][repo]
        return any(rel.startswith(r.rstrip('/') + '/') or r == '.' for r in spec['roots']) and \
            not excluded(rel, spec['exclude'])

    def node_kind(repo: str, focus: str, node: str) -> str:
        """exists, nested_spelling (Outer_Inner), renamed (a real type by another name) or invented."""
        if node.rsplit('.', 1)[-1] in words[repo]:
            return 'exists'
        resolved = {r[f'{end}_fqn'] for r in edges.values() for end in ('source', 'target')
                    if r['repo'] == repo and r['focus'] == focus and r[f'{end}_name'] == node}
        resolved = {f for f in resolved if '|' not in f and repos[repo].file_of(top(f))}
        for f in resolved:
            nested = [p for p in f.split('.') if p[:1].isupper()]
            if node.replace('_', '') == ''.join(nested):
                return 'nested_spelling'
        return 'renamed' if resolved else 'invented'

    additions = set()
    conflicts = []
    runs = []
    for meta_file in sorted(rounds.raw(args.round).glob('*.meta.json')):
        meta = json.loads(meta_file.read_text())
        rid, repo, focus = meta['id'], meta['repo'], meta['focus'] or '-'
        transcript = meta_file.with_name(meta_file.name.replace('.meta.json', '.jsonl'))
        facts = transcript_facts(transcript)
        d = diagram(transcript)
        failed = d is None or bool(d.unparsed) or facts['is_error'] or meta['timed_out']
        plugin = {'A': None, 'B': 'draftsman', 'C': 'class-diagram'}[meta['arm']]
        row = {'run': rid, 'task': meta['task'], 'repo': repo, 'focus': focus, 'arm': meta['arm'],
               'failed': failed,
               'skill_fired': '' if plugin is None else any(plugin in s for s in facts['skills']),
               'subagents': facts['subagents'], 'cost_usd': facts['cost_usd'], 'seconds': facts['seconds'],
               'turns': facts['turns'], 'tokens': facts['tokens'], 'output_tokens': facts['output_tokens']}
        drawn = drawn_in[rid]
        focus_top = top(focus)

        # top level: one edge per (pair of top-level types, kind, direction)
        collapsed: dict[tuple, dict] = {}
        for eid, inferred in drawn.items():
            e = edges[eid]
            src, tgt = e['source_fqn'], e['target_fqn']
            a, b = ('|'.join(sorted(tops(src))), '|'.join(sorted(tops(tgt))))
            if e['directed'] == 'false':
                a, b = sorted((a, b))
            key = (a, e['kind'], b, e['directed'])
            label = e['label_top']
            prev = collapsed.setdefault(key, {'label': label, 'inferred': inferred})
            if label != prev['label']:
                conflicts.append((rid, key, prev['label'], label))
                prev['label'] = min(label, prev['label'], key=ORDER.index)
            prev['inferred'] = prev['inferred'] and inferred

        def incident_top(key):
            return focus == '-' or focus_top in set(key[0].split('|')) | set(key[2].split('|'))

        def counts(items, prefix):
            scored = [x for x in items if x not in ('self', 'undecidable')]
            row[f'{prefix}_scored'] = len(scored)
            row[f'{prefix}_undecidable'] = sum(x == 'undecidable' for x in items)
            for lab in ('unsupported', 'indirect', 'wrong_kind_or_direction', 'body_only', 'declared'):
                row[f'{prefix}_{lab}'] = sum(x == lab for x in scored)

        counts([v['label'] for k, v in collapsed.items() if incident_top(k)], 'top')
        counts([v['label'] for k, v in collapsed.items() if incident_top(k) and not v['inferred']], 'top_noinf')
        counts([v['label'] for v in collapsed.values()], 'top_all')
        counts([edges[e]['label_drawn'] for e in drawn
                if focus == '-' or focus in edges[e]['source_fqn'].split('|') + edges[e]['target_fqn'].split('|')],
               'drawn')
        row['inferred_edges'] = sum(drawn.values())
        row['unnamed'] = sum(edges[e]['unnamed'] == 'true' for e in drawn)

        kinds = [node_kind(repo, focus, n) for n in nodes[rid]]
        row['nodes'] = len(kinds)
        for k in ('nested_spelling', 'renamed', 'invented'):
            row[f'nodes_{k}'] = kinds.count(k)

        # recall
        den_rows = denominators(repo, focus)
        for level in ('top', 'drawn'):
            pairs = recall_pairs(den_rows, level)
            have = set()
            for eid in drawn:
                e = edges[eid]
                src, tgt = e['source_fqn'], e['target_fqn']
                if '|' in src + tgt:
                    continue
                if level == 'top':
                    src, tgt = top(src), top(tgt)
                have.add((src, tgt))
                if e['directed'] == 'false':
                    have.add((tgt, src))
            directions = ['-'] if focus == '-' else ['out', 'in']
            for direction in directions:
                for scope, allowed in (('declared', {'declared'}), ('all', {'declared', 'body_only'})):
                    want = [(s, t) for (dr, s, t), ev in pairs.items() if dr == direction and ev in allowed]
                    col = f'recall_{level}_{"all" if direction == "-" else direction}_{scope}'
                    row[col] = 'n/a' if not want else (0.0 if failed else sum(p in have for p in want) / len(want))
                    row[col.replace('recall', 'den')] = len(want)

            # relations labelled real that the denominator lacks
            known = {(s, t) for (_, s, t) in pairs}
            for eid in drawn:
                e = edges[eid]
                # a nesting edge is a declaration inside, not a use
                if e[f'label_{level}'] not in ('declared', 'body_only') or e['unnamed'] == 'true' \
                        or e['kind'] == 'nesting':
                    continue
                src, tgt = e['source_fqn'], e['target_fqn']
                if not (production(repo, src) and production(repo, tgt)):
                    continue
                if level == 'top':
                    src, tgt = top(src), top(tgt)
                if src == tgt or (focus != '-' and focus_top not in (top(src), top(tgt))):
                    continue
                if level == 'drawn' and focus != '-' and focus not in (src, tgt):
                    continue
                if (src, tgt) in known or (e['directed'] == 'false' and (tgt, src) in known):
                    continue
                additions.add((level, repo, focus, src, tgt, e['edge_id'], e[f'label_{level}'], e[f'file_line_{level}']))
        runs.append(row)

    out = rounds.scores(args.round)
    out.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in runs for k in r))
    with open(out / 'runs.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(runs)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in runs:
        groups[(r['task'], r['repo'], r['arm'])].append(r)
        if r['task'] == 'T2':
            groups[('T2', 'all', r['arm'])].append(r)
            if r['repo'] != 'spring-petclinic':
                groups[('T2', 'jsoup+netty', r['arm'])].append(r)
    summary = []
    for (task, repo, arm), rs in sorted(groups.items()):
        s = {'task': task, 'repo': repo, 'arm': arm, 'runs': len(rs), 'failed': sum(r['failed'] for r in rs),
             'skill_fired': '' if arm == 'A' else sum(r['skill_fired'] is True for r in rs)}
        for prefix in ('top', 'top_noinf', 'top_all', 'drawn'):
            n = sum(r[f'{prefix}_scored'] for r in rs)
            s[f'{prefix}_scored'] = n
            s[f'{prefix}_undecidable'] = sum(r[f'{prefix}_undecidable'] for r in rs)
            for lab in ('unsupported', 'indirect', 'wrong_kind_or_direction'):
                k = sum(r[f'{prefix}_{lab}'] for r in rs)
                s[f'{prefix}_{lab}'] = k
                s[f'{prefix}_{lab}_share'] = round(k / n, 4) if n else 'n/a'
        for k in ('nodes', 'nodes_nested_spelling', 'nodes_renamed', 'nodes_invented', 'inferred_edges', 'unnamed'):
            s[k] = sum(r[k] for r in rs)
        for col in [c for c in fields if c.startswith('recall_')]:
            vals = [r[col] for r in rs if col in r and r[col] != 'n/a']
            s[col] = round(statistics.mean(vals), 4) if vals else 'n/a'
            s[col + '_na'] = sum(1 for r in rs if r.get(col) == 'n/a')
        for k in ('cost_usd', 'seconds', 'tokens', 'output_tokens', 'turns'):
            vals = [r[k] for r in rs]
            s[f'{k}_median'] = round(statistics.median(vals), 4)
            s[f'{k}_min'] = round(min(vals), 4)
            s[f'{k}_max'] = round(max(vals), 4)
        summary.append(s)
    with open(out / 'summary.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for s in summary for k in s)))
        w.writeheader()
        w.writerows(summary)

    print(f'{len(runs)} runs, {sum(r["failed"] for r in runs)} failed; '
          f'{sum(1 for e in edges.values() if e["reviewed"] == "change")} labels changed in review')
    for rid, key, a, b in conflicts:
        print(f'  labels disagree after collapsing: {rid} {key}: {a} / {b}')
    for level, repo, focus, src, tgt, eid, label, line in sorted(additions):
        print(f'  missing from the denominator ({level}): {repo} {focus.rsplit(".", 1)[-1]}: '
              f'{src} -> {tgt} [{label} {line}] {eid}')


if __name__ == '__main__':
    main()
