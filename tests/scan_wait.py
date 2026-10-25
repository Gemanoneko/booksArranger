"""Waiting for a fixture catalog scan, or any test thread, until it has ended (2026-10-25).

A test that scans its fixture library must wait until that scan has finished, not for a fixed number of seconds:
`inventory.worker.join(10)` returns silently when the time runs out. Under the full gate's concurrent load the 0.22.0
entry check read test_catalog_paging's catalog while its scan was still running (119 of 127 books catalogued), failed
on the count, and then could not delete the catalog file the running scan still held open (WinError 32).
"""

# Seconds. A fixture scan takes well under a second alone and passed 10 s under the full gate; this bound only exists
# so a thread that never ends fails its test clearly instead of hanging the gate.
DEADLINE = 120.0


def finish_thread(thread, what, deadline=DEADLINE):
    """Wait until `thread` has ended; fail clearly, naming `what`, if it is still running after `deadline` s."""
    thread.join(deadline)
    if thread.is_alive():
        raise AssertionError('%s did not finish within %g s' % (what, deadline))


def finish_scan(inventory, deadline=DEADLINE):
    """Wait until the inventory's scan thread has ended."""
    if inventory.worker is None:
        raise AssertionError('No scan was started')
    finish_thread(inventory.worker, 'The fixture scan', deadline)


def close_scan(inventory, deadline=DEADLINE):
    """Stop the inventory's scan if one is running and wait for it to end, so no scan connection holds the catalog
    open when the test deletes it. Register it after the folder's own cleanup: cleanups run last-in, first-out."""
    inventory.stop()
    if inventory.worker is not None:
        finish_thread(inventory.worker, 'The stopped fixture scan', deadline)
