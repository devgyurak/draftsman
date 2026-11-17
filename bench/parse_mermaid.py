"""Read the Mermaid classDiagram a run answered with, as nodes and normalised edges.

An edge is (source, kind, target, directed): kind is inheritance, association or
dependency (RUBRIC.md, "Normalising a diagram"), or nesting for the `+--` some diagrams
draw from an outer type to its nested type (it collapses onto one top-level type); the source is the type that uses,
extends or contains the target. Names are kept as drawn, minus generics, backticks and
labels; resolving them to source types is the labeller's job. `inferred` records an edge
labelled «inferred»/<<inferred>>, which is stripped before labelling.

    python3 bench/parse_mermaid.py <transcript.jsonl>     # print what one run drew
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_BLOCK = re.compile(r'```mermaid\s*\n(.*?)```', re.S)
_NAME = r'(`[^`]+`|[\w.$]+(?:~[^~]*~)?)'
_CARD = r'(?:\s*"[^"]*")?'
# arrow -> (kind, which end is the source: 'L' left, 'R' right, None unordered)
_ARROWS = {
    '<|--': ('inheritance', 'R'), '--|>': ('inheritance', 'L'),
    '<|..': ('inheritance', 'R'), '..|>': ('inheritance', 'L'),
    '*-->': ('association', 'L'), 'o-->': ('association', 'L'),
    '*--': ('association', 'L'), '--*': ('association', 'R'),
    'o--': ('association', 'L'), '--o': ('association', 'R'),
    '-->': ('association', 'L'), '<--': ('association', 'R'), '--': ('association', None),
    '..>': ('dependency', 'L'), '<..': ('dependency', 'R'), '..': ('dependency', None),
    '+--': ('nesting', 'L'), '--+': ('nesting', 'R'),
}
_ARROW_ALT = '|'.join(re.escape(a) for a in sorted(_ARROWS, key=len, reverse=True))
_EDGE = re.compile(rf'^\s*{_NAME}{_CARD}\s*({_ARROW_ALT})\s*{_CARD.strip()}\s*{_NAME}\s*(?::\s*(.*))?$')
_CLASS = re.compile(rf'^\s*class\s+{_NAME}')
_ANNOTATION = re.compile(rf'^\s*<<[^>]+>>\s+{_NAME}')
_IGNORED = re.compile(r'^\s*($|%%|classDiagram|direction\b|note\b|style\b|classDef\b|cssClass\b|'
                      r'click\b|callback\b|link\b|linkStyle\b|title\b|accTitle\b|accDescr\b|---|\}|namespace\b|'
                      r'[+\-#~]|<<)')


def clean(name: str) -> str:
    """`a.b.C` -> a.b.C, Name~T~ -> Name."""
    name = name.strip('`')
    return re.sub(r'~.*~$', '', name)


@dataclass
class Diagram:
    nodes: set[str] = field(default_factory=set)
    edges: list[dict] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)


def parse(block: str) -> Diagram:
    d = Diagram()
    in_body = 0
    for line in block.splitlines():
        if in_body:                      # members inside `class X { ... }`
            in_body += line.count('{') - line.count('}')
            continue
        if m := _EDGE.match(line):
            left, arrow, right, label = clean(m.group(1)), m.group(2), clean(m.group(3)), m.group(4) or ''
            kind, side = _ARROWS[arrow]
            src, tgt = (left, right) if side != 'R' else (right, left)
            d.nodes.update((left, right))
            d.edges.append({'source': src, 'kind': kind, 'target': tgt, 'directed': side is not None,
                            'inferred': 'inferred' in label.lower()})
        elif m := _CLASS.match(line):
            d.nodes.add(clean(m.group(1)))
            if '{' in line:
                in_body = line.count('{') - line.count('}')
        elif m := _ANNOTATION.match(line):
            d.nodes.add(clean(m.group(1)))
        elif not _IGNORED.match(line):
            d.unparsed.append(line.strip())
    return d


def answer(transcript: Path) -> str:
    """The final result text of a run's stream-json transcript."""
    result = ''
    for line in open(transcript):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'result':
            result = event.get('result') or ''
    return result


def diagram(transcript: Path) -> Diagram | None:
    blocks = _BLOCK.findall(answer(transcript))
    return parse(blocks[0]) if blocks else None


if __name__ == '__main__':
    d = diagram(Path(sys.argv[1]))
    print(json.dumps({'nodes': sorted(d.nodes), 'edges': d.edges, 'unparsed': d.unparsed}, indent=2))
