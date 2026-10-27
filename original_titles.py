"""Ruling 38 (Sergei 2026-10-27; it replaces the waiting part of ruling 29): translated books don't wait.

- Research tries to find the English original title (the research cache's catalog answers). If it is found, the book is
  filed under it; if not, the book converts right away under the title it has.
- The author folder is still the English spelling for a non-Russian author (the folder language rule of ruling 3).
- There is no "Waiting for the original title" state. The English title can be applied later through the rename pass
  (ruling 21); the background pass still asks the sources for it once the book is converted (gap_fill, the
  'original_title' gap of every Cyrillic title).

Locally the app knows a book is a translation when the library writes its author in Latin letters (Russian authors in
Cyrillic, everyone else in English), or in Cyrillic with a foreign first name («Скотт Вестерфельд», «Голиаф»), and the
title it read is Cyrillic. Research records the outcome for the details panel's "Original title" fact
(metadata_facts.original_title_lookup: 'found' with the English title, or 'none').

The 'original_titles' table of the 0.22.2 candidates (ruling 29's lookups) is no longer read or written; a catalog that
has it keeps it, unused.
"""


def translation(title, author):
    """True when a book is a translation with only its Russian title: the title read is Cyrillic and the author writes in
    another language: written in Latin letters (the library's folder language rule), or in Cyrillic with a foreign first
    name («Скотт Вестерфельд», «Голиаф», Sergei 2026-10-26)."""
    import local_identity
    return local_identity.script(title) == 'cyrillic' and (local_identity.script(author) == 'latin' or local_identity.foreign_given(author))
