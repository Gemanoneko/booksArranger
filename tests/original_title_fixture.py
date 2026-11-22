"""Since ruling 38 (Sergei 2026-10-27) no book waits for its English original title; research only records whether a
translation's English title was found (metadata_facts.original_title_lookup, the details panel's "Original title").

The identity, structure and admission suites written before ruling 29 use Latin-named authors with Russian titles to test
other rules; this patch keeps that fact out of their results, as before. The ruling itself is tested in
test_identity_0222.TranslationNoWaitTests and test_original_title_wait, which do not use this."""
from unittest.mock import patch


class _Patches:
    """Several patches started and stopped as one (the suites call start() and stop() on what no_wait() returns)."""
    def __init__(self, *patches):
        self.patches = patches

    def start(self):
        for item in self.patches:
            item.start()
        return self

    def stop(self):
        for item in reversed(self.patches):
            item.stop()


def no_wait():
    """Started patch: no book is a translation, and (0.31.0 step 2) no book is looked up online before review. These
    suites predate both and test other rules with sources that are closed; the look-up before review has its own
    tests (test_lookup_before_review_031). Stop it in tearDownModule."""
    return _Patches(patch('original_titles.translation', return_value=False),
                    patch('public_research.PublicResearch.lookup_before_review', False)).start()


def no_lookup():
    """Started patch: no book is looked up online before review (0.31.0 step 2), and nothing else. For the suites
    that predate the look-up and run with sources that are closed or cannot be reached: under R2 such a book now
    waits for its sources (a few tries), which is not what those suites test. Stop it in tearDownModule."""
    return _Patches(patch('public_research.PublicResearch.lookup_before_review', False)).start()
