"""A test's own scratch folder is removed when the test ends (2026-11-16).

Run directly, a test that made <repo>/scratch/<prefix><uuid4 hex> used to leave it there, one folder per test. When the
desktop check redirects fixtures (BOOKS_QA_FIXTURE_ROOT), nothing changes: that root belongs to the check, which removes
it itself, so no cleanup is registered.
"""
import os
from pathlib import Path
import re
import shutil
import stat

DEFAULT_SCRATCH = Path(__file__).resolve().parents[1] / 'scratch'


def remove_own_area(test, area, prefix):
    """Register the removal of exactly `area`, a folder this test made directly in the default scratch."""
    if 'BOOKS_QA_FIXTURE_ROOT' in os.environ:return
    area = Path(area)
    if area.parent.resolve() != DEFAULT_SCRATCH or not re.fullmatch(re.escape(prefix) + '[0-9a-f]{32}', area.name):
        raise ValueError('Not a test-owned scratch folder: ' + str(area))
    test.addCleanup(_remove, area)


def _remove(area):
    if not os.path.lexists(area):return
    # Never follow a link or junction out of the folder; rmtree removes inner links without entering them.
    if area.is_symlink() or area.is_junction() or not area.is_dir():
        raise RuntimeError('Test scratch folder was replaced by a link or file: ' + str(area))
    shutil.rmtree(area, onexc=_clear_read_only)


def _clear_read_only(function, path, error):
    """Fixtures make read-only payloads (test_application_publication). Clear that attribute and retry once, only on a
    plain file or folder; anything else, a deny ACL included, still fails the test."""
    if not isinstance(error, PermissionError) or os.path.islink(path) or os.path.isjunction(path):raise error
    os.chmod(path, stat.S_IWRITE)
    function(path)
