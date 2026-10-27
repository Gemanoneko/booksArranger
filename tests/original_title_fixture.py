"""Since ruling 38 (Sergei 2026-10-27) no book waits for its English original title; research only records whether a
translation's English title was found (metadata_facts.original_title_lookup, the details panel's "Original title").

The identity, structure and admission suites written before ruling 29 use Latin-named authors with Russian titles to test
other rules; this patch keeps that fact out of their results, as before. The ruling itself is tested in
test_identity_0222.TranslationNoWaitTests and test_original_title_wait, which do not use this."""
from unittest.mock import patch


def no_wait():
    """Started patch: no book is a translation. Stop it in tearDownModule."""
    started = patch('original_titles.translation', return_value=False)
    started.start()
    return started
