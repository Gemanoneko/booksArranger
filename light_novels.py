"""0.29.0 item 4: Light Novels as an audiobook type.

Sergei (2026-11-17): everything in a source "Light Novels" folder goes to Audiobooks Sorted\\Light Novels, keeping the usual
hierarchy inside it (author, series, ...). A source folder named "Ранобэ" is the same (his answer 3). A book is a light novel
or a short-story collection, never both (answer 2). The box sits wherever Short Stories does (answer 1): the Manual
Conversion window, a row's Edit names editor and the details panel's Metadata form.

The folder is a pre-tick, never the last word: the exact folder segment (any case), never a substring, between the library
root and the book's files. Sergei's saved value (Edit names, entered_names field light_novel) wins over it.
"""
import os

FOLDER = 'Light Novels'  # the top folder in Audiobooks Sorted
FOLDER_NAMES = frozenset({'light novels', 'ранобэ'})
BOTH = 'A book is a light novel or a short-story collection, not both. Untick one of them.'


def _segments(path, root):
    path, root = os.path.normpath(str(path)), os.path.normpath(str(root)) if root else ''
    if root and os.path.normcase(path).startswith(os.path.normcase(root.rstrip('\\/')) + os.sep):
        path = path[len(root.rstrip('\\/')) + 1:]
    else:
        path = os.path.splitdrive(path)[1]
    return [part for part in os.path.dirname(path).replace('/', '\\').split('\\') if part]


def from_path(path, root=None):
    """True when a folder between the library root and this file is named Light Novels or Ранобэ (any case)."""
    return any(part.casefold() in FOLDER_NAMES for part in _segments(path, root))


def from_row(row, root=None):
    """The folder pre-tick of a scanned book: every file of it lies in such a folder."""
    paths = [str(m.get('path')) for m in (row or {}).get('members') or [] if isinstance(m, dict) and m.get('path')]
    return bool(paths) and all(from_path(p, root or (row or {}).get('source_root') or (row or {}).get('root')) for p in paths)


def check(light_novel, collection):
    if type(light_novel) is not bool:
        raise ValueError('Light novel must be an explicit boolean')
    if light_novel and collection is True:
        raise ValueError(BOTH)
