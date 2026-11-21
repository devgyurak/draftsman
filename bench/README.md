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
kind or direction* is checked by a person. Edges are compared on top-level types, so a
diagram scores the same whether or not it draws nested types. The headline is the share of
edges at the focus class that have no basis in the source.

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
- **Arm C runs as its author built it, in our isolation, outside its stated range.**
  - Its explorer subagent is written for Python, JS/TS and Rust sources (its globs and
    example); these repositories are Java.
  - Its skill asks for at most 15 classes and for an explorer subagent (Sonnet, effort
    medium, at most 25 file reads). In the pilot it did neither: it read the files itself
    and drew up to 48 classes, following the prompt's limit of 80. Its recall is measured
    as it behaved, not as its skill describes.
  - It renders through a Mermaid Chart MCP server that no isolated run has, so it cannot
    meet its own exit criteria; retries this causes add to its cost and time. Its cost and
    time are listed in the tables with this note and left out of the cost and time figure.
  - It runs without its declared dependencies. Its manifest names gauntlet (which brings
    leyline and oracle); with them missing, Claude Code skips the plugin entirely, as the
    pilot showed. The class-diagram skill uses none of them, and they add session hooks
    that star a GitHub repository, fetch discussions and start a daemon, so we removed the
    one `dependencies` line instead of installing them.
  - The Mermaid text it writes is what is scored.
- **Uses that never name a type are not in the recall denominators** (a call on a field of
  that type, a nested class using its outer class's field). Counting them would take type
  inference. This lowers the body-only recall every arm is measured against, the measure
  Draftsman is expected to lose, so it slightly favours Draftsman.
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
- 2026-11-17, before the pilot, after review:
  - Main scoring on top-level types, both ends collapsed; nested types as drawn are
    secondary. Five denominator rows added for it (Connection: four incoming through its
    nested types, one outgoing from `Connection.Response`).
  - The image holds only the plugin's own files: the answer key (`bench/`, `docs/`) had
    been about to go into every arm's container with the next build.
  - run.py: an interrupted run is redone instead of skipped; the credential is masked in
    transcripts; each run records the image ID and the session's init event; the other
    arms' plugins are removed before a session starts; stdin is closed.
  - Limits: arm C's stated language range and file budget, unnamed uses.
- 2026-11-17, pilot (6 runs, subscription token): isolation, metering and arm B worked.
  Arm C's plugin never loaded: its manifest declares gauntlet as a dependency and Claude
  Code skips a plugin whose dependency is missing. Its `dependencies` line is now removed
  at build time (see Limits); the two arm C pilot runs were discarded and run again.
- 2026-11-17, second pilot round: with the plugin loaded, arm C's skill still did not fire
  (2 of 2 runs drew the diagram without it), while Draftsman's did (2 of 2). Every arm's
  prompt now adds the same sentence, "If a skill for drawing class diagrams is available,
  use it." Arm A has no such skill. All six pilot runs were discarded and the pilot was
  run again with this prompt. (T1's class limit reads 80 like T2's since the bounds were
  raised; spring-petclinic has 25 types, so it does not bind.)
- 2026-11-17, pilot with the new prompt: the skill fired in every arm B and arm C run;
  six runs, $1.19 in Claude Code's cost estimates, at most $0.37 a run. Measured runs
  capped at $3 each, on the subscription token, with the pilot's image.
- 2026-11-17, after the measured runs, before labelling: the parser also reads `+--`
  (outer type to nested type, kind *nesting*), which 42 drawn edges use and the rubric's
  arrow table did not list; on top-level types it collapses onto one type and drops out of
  the main scoring. `o-->` and `*-->` read as association.
- 2026-11-17, before labelling (no edge yet labelled or read by arm): each edge gets a
  label on top-level types, which the headline uses, and one as drawn. With one label, an
  edge drawn to an outer type whose only evidence sits in its nested type would have
  counted as unsupported in the main scoring. Nesting edges are *self* at the top level
  and *declared* as drawn when the nesting is real.
- 2026-11-17, before labelling: three gaps of collapsing to top-level types closed.
  Inheritance drawn between nested types (`A.X --|> B`) is not wrong kind once collapsed;
  the top-level citation check accepts the name of a type nested in the other end; recall
  finds a pair from an edge of any kind, in its direction or undirected.
- 2026-11-20, after the first labels, before review and before any edge was read by arm:
  three cases the labeller reported as undecided are settled (RUBRIC.md, "Decided at
  review"). Four edges drawn from an anonymous class as a named node, labelled *wrong kind
  or direction*, become *declared* at both levels: the anonymous class does implement the
  target, and its enclosing type declares the target elsewhere. The seven *undecidable*
  same-name edges and the four outer-to-nested uses keep their labels.
- 2026-11-20, human review: the reviewer read the 123 rows by eye and changed none beyond
  the four above; the sheet records each row as agreed. `score.py` applies the review,
  unblinds the labels and scores the runs. No label disagrees with another after
  collapsing to top-level types, and no relation labelled real is missing from the recall
  denominators (three nesting edges, declarations rather than uses, are not counted as
  missing).
- 2026-11-20, second round (v2), after Draftsman 0.3.0 (`c68baa0`: nested types folded
  in focus diagrams, annotations create relations, one command draws a diagram). Same
  configuration, prompts, focus classes and rubric; all three arms run again, 63 runs, no
  failures, $9.46. The image is the first round's with only Draftsman's files replaced
  (`update_draftsman.sh`), so Claude Code, the Python packages, the repositories and
  night-market are byte for byte the same. Results are in `results/raw/measured-v2/`,
  `labels/v2/` and `results/scores/v2/`; the first round's stay where they were.
  - Labels: 382 of the 514 distinct edges were drawn in the first round as well and keep
    its final labels (a label depends only on the edge and the source). The other 132
    were labelled blind by a separate session started outside this repository, so that
    neither the commit history nor this page reached it, and allowed to open only the
    rubric, `tasks.yaml`, the edge list and the sources (`labels/v2/BRIEF.md`).
  - The cases that session found undecided were all settled by rules already written
    (qualified nested names as drawn, the focus file deciding a shared name, edges to an
    anonymous class, outer-to-nested uses); no rule changed.
  - Human review: 52 rows (32 in full, 20 sampled), all agreed by eye. This review was not
    blind: the reviewer knew what 0.3.0 changed. The sheet gives the cited lines and the
    files naming both types, so each verdict rests on the source.
  - `score.py` counted a diagram with no edges as a failed run, which the rubric does not;
    no run of either round had none, so no figure changed.
