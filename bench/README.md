# Benchmark

How Draftsman's class diagrams compare with Claude Code on its own and with another
class-diagram skill: relations without a basis in the source, relations missed, cost and
time. **Status: preparation.** No measured run yet; this page will hold the results.

## Method

| | |
|---|---|
| Model | `claude-opus-5-5`, effort `high`, Claude Code 2.1.326 |
| Arms | A: Claude Code with no plugin · B: Draftsman · C: night-market `class-diagram` |
| Repositories | Java, by size: spring-petclinic (30 files), jsoup (105), Netty (2,076); commits in [`tasks.yaml`](tasks.yaml) |
| T1 | the whole of spring-petclinic, 3 runs per arm |
| T2 | 3 focus classes per repository, 1 hop in either direction, 2 runs per arm |
| Runs | 9 (T1) + 54 (T2) = 63, in shuffled order, each in a fresh container checkout |

Every arm gets the same natural-language prompt ([`tasks.yaml`](tasks.yaml)); none uses a
slash command. Each run is isolated: no MCP servers, no user, project or local settings,
only the arm's own plugin.

**Focus classes** are drawn by [`select_focus.py`](select_focus.py) from grep counts, not
from Draftsman's output: how many project types a class's file names, plus how many other
files name it. Classes counted below 3 or above 40 are dropped; the rest are cut into three
strata by rank and one class per stratum is drawn with a fixed seed. The result is in
[`focus.yaml`](focus.yaml); the counts for every candidate are in
[`results/candidates/`](results/candidates/).

**Scoring** follows [`RUBRIC.md`](RUBRIC.md): edges from all runs are pooled and labelled
blind, citations are checked by script, and every edge labelled *unsupported* or *wrong
kind or direction* is checked by a person. The headline is the share of edges at the focus
class that have no basis in the source.

## Limits

- **Hub classes are not measured.** The upper bound of 40 leaves out classes such as
  Netty's `Channel` or `ByteBuf`, whose direct neighbourhood runs into the hundreds; no arm
  could draw it within 40 classes, and the recall denominator could not be written by hand.
- One language (Java), one model, two runs per focus class.
- The grep count that picks the focus classes is a proxy: it counts names, so a simple
  name shared with an unrelated type adds to it.
- Draftsman reads declarations, not method bodies; relations found only in bodies are
  reported as recall it is expected to lose.

## Change log

Changes to the prompt, the arms or the rubric after the pilot are listed here.

- 2026-11-17 — configuration, rubric and focus classes committed; pilot not yet run.
