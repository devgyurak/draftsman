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
files name it. A class whose simple name the sources also import from elsewhere is
skipped, since the count would include its look-alike. Classes outside [8, 80] are
dropped ([3, 40] for spring-petclinic, whose largest class counts 7); the rest are cut
into three strata by rank and one class per stratum is drawn with a fixed seed. The result is in
[`focus.yaml`](focus.yaml); the counts for every candidate are in
[`results/candidates/`](results/candidates/).

**Scoring** follows [`RUBRIC.md`](RUBRIC.md): edges from all runs are pooled and labelled
blind, citations are checked by script, and every edge labelled *unsupported*, *indirect* or *wrong
kind or direction* is checked by a person. The headline is the share of edges at the focus
class that have no basis in the source.

## Limits

- **Hub classes are not measured.** The upper bound of 80 leaves out classes such as
  Netty's `Channel` or `ByteBuf`, whose direct neighbourhood runs into the hundreds; no arm
  could draw it within the prompt's 80 classes, and the recall denominator could not be
  written by hand.
- **Small classes are not measured in jsoup and Netty.** Their lower bound of 8 leaves out
  classes with fewer relations, where we expect every arm to do well; spring-petclinic,
  bounded at [3, 40], is the only place small classes are measured.
- **Only jsoup and Netty compare repository sizes.** spring-petclinic's classes are small
  as well as its repository (counts 4–7, against 13–21 in jsoup and 8–24 in Netty), so the
  figures show it apart, as the small-class case, not as the first step of a size scale.
- One language (Java), one model, two runs per focus class.
- The grep count that picks the focus classes is a proxy: it counts names, so a simple
  name shared with an unrelated type adds to it.
- **Arm C runs as its author built it, in our isolation.** Its skill limits a diagram to
  15 classes, so its recall is bounded by its own rule against the prompt's 80; it
  explores through a subagent on Sonnet; and it renders through a Mermaid Chart MCP server
  that no isolated run has. The Mermaid text it writes is what is scored.
- Draftsman reads declarations, not method bodies; relations found only in bodies are
  reported as recall it is expected to lose.

## Change log

Changes to the prompt, the arms or the rubric after the pilot are listed here.

- 2026-11-17 — configuration, rubric and focus classes committed; pilot not yet run.
- 2026-11-17, before the pilot — focus classes drawn again with the same seed:
  - Netty's `io.netty.util.BooleanSupplier` had been drawn on a count of 3 files, two of
    which import `java.util.function.BooleanSupplier`; its real count is 1. Names the
    sources also import from elsewhere are now skipped (16 of Netty's 1,456 candidates).
  - jsoup's `org.jsoup.examples` is excluded, as Netty's `example/` already was.
  - Bounds raised from [3, 40] to [8, 80] for jsoup and Netty, and the prompt's limit from
    40 to 80 classes. With [3, 40] every drawn class had at most about 20 relations, small
    enough, we expected, for any arm to find by reading one file, which would leave the
    arms indistinguishable.
    Raising only the upper bound moved Netty's strata from 3–7 / 7–12 / 12–40 to
    3–7 / 7–13 / 13–80; the lower bound is what changes them.
  - Labels: *indirect* added (indirect inheritance and uses through an inherited member,
    outside the headline); empty recall denominators are *n/a*.
- 2026-11-17, before the pilot — recall denominators drafted from the source (no Draftsman
  output) for the nine focus classes and spring-petclinic, awaiting human review; the
  rubric records eight cases the draft showed to be undecided (qualified nested names,
  uses that never name the type, and others).
