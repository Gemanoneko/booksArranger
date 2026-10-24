"""Fixtures written before the 0.21.3 deletion rule publish their books inside their own library.

Sergei's rulings 2 and 1a (2026-10-24, source_config.require_sorted): a source is removed only when its verified
result is in the configured output folder, outside every source. That rule is tested where it is enforced:
test_source_cleanup (enrolment, run start, each removal), test_automatic_processing (Start) and test_inplace_m4b
(the in-place rename). The fixtures below test other things (retries, folders, recovery copies, status), so they
declare their own library as the output folder instead of moving every output. Not a production path.
"""
from unittest.mock import patch


def library_is_sorted(root):
    """An output_policy for CleanupJobs: this fixture's library is its output folder."""
    return lambda: (str(root), ())


def fixture_library(service):
    """MergeService.output_policy for a fixture: the configured output folder, else its own audiobook library."""
    inventory = service.inventory
    return (getattr(inventory, 'output_root', None) or inventory.roots['Audiobooks'], ())


def patch_merge_service(test_case=None):
    """Patch MergeService.output_policy with fixture_library for one test (test_case) or a whole module (returned)."""
    from merge_service import MergeService
    patcher = patch.object(MergeService, 'output_policy', fixture_library)
    patcher.start()
    if test_case is not None:
        test_case.addCleanup(patcher.stop)
    return patcher
