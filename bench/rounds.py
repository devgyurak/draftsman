"""Where each round of the measured set keeps its runs, labels and scores.

v1 is the first round, kept where it was written; a later round (v2, ...) reruns the same
configuration on an image whose Draftsman changed and keeps its files apart. The recall
denominators are shared by every round.
"""

from pathlib import Path

BENCH = Path(__file__).resolve().parent
DENOMINATORS = BENCH / 'labels' / 'denominators'


def raw(round_: str) -> Path:
    return BENCH / 'results' / 'raw' / ('measured' if round_ == 'v1' else f'measured-{round_}')


def labels(round_: str) -> Path:
    return BENCH / 'labels' if round_ == 'v1' else BENCH / 'labels' / round_


def scores(round_: str) -> Path:
    return BENCH / 'results' / 'scores' if round_ == 'v1' else BENCH / 'results' / 'scores' / round_
