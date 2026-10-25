"""0.22.1, backlog item 9 (Sergei, 2026-10-25): a clean file-name sequence decides a book's playback order.

`Z:\\Audiobooks\\James Rollins\\Sigma Force\\2. Map of Bones` holds 240 files named "Роллинс Джеймс - Кости волхвов - 01 -
Kosti_001.m4a" .. "- 240 - Kosti_240.m4a", in perfect sequence. Most of their track tags read "N/-1", which is no plain
number, so those files had no position; the 20 files re-tagged on 2020-03-07 carry a plain "N" and were sorted first.
The book was held as "Order unclear" with a proposed order starting 07, 09, 18, 21, 27: approving it would have built a
scrambled book. When the names number the files 1..N (or 0..N-1) without a gap or a repeat, that numbering is the order,
whatever a few odd tags say, and it is not "unclear". Pure: names in, positions out.
"""
import re
from pathlib import Path

VERSION = 'file-order-v1'
_RUNS = re.compile(r'\d+')


def _clean(values):
    """values (numbers, one per file) form start..start+n-1 with start 0 or 1, each once."""
    ordered = sorted(values)
    return len(values) >= 2 and ordered[0] in (0, 1) and ordered == list(range(ordered[0], ordered[0] + len(values)))


def filename_sequence(names):
    """[position per file] from the one clean continuous numbering the file names carry, else None.

    Every name's numbers are read at the same place, counted from the start ("Kosti_001" in "... - 01 - Kosti_001")
    and from the end; a place where the files run 1..N (or 0..N-1), each once, numbers them. Several such places must
    agree on the order ("01" and "Kosti_001" do); otherwise, or with fewer than two files, there is no sequence."""
    if not names or len(names) < 2:
        return None
    runs = [[int(value) for value in _RUNS.findall(Path(str(name)).stem)] for name in names]
    shortest = min(len(r) for r in runs)
    if not shortest:
        return None
    found = []
    for index in list(range(shortest)) + [-i for i in range(1, shortest + 1)]:
        values = [r[index] for r in runs]
        if _clean(values):
            found.append(values)
    if not found:
        return None
    order = [sorted(range(len(names)), key=lambda i: values[i]) for values in found]
    if any(o != order[0] for o in order[1:]):
        return None  # two numberings that disagree: the names do not settle the order
    return found[0]


def member_names(members):
    return [m.get('filename') or Path(m['path']).name for m in members]
