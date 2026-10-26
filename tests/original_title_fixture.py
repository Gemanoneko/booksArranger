"""Ruling 29 (0.22.2): a translation with only its Russian title waits for its English original title (original_titles).

The identity, structure and admission suites written before it use Latin-named authors with Russian titles to test other
rules; in those modules no book waits for its original title. The ruling itself is tested in
test_identity_0222.OriginalTitleWaitTests, which does not use this."""
from unittest.mock import patch


def no_wait():
    """Started patch: no book is a translation that waits. Stop it in tearDownModule."""
    started = patch('original_titles.translation', return_value=False)
    started.start()
    return started
