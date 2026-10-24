"""PublicResearch.local_agreement pinned for one test, restored by tearDown() or by the cleanups, whichever runs first.

Several modules borrow another class's setUp()/tearDown() without running its cleanups (test_working_lifecycle,
test_standing_admission, test_manual_research). A class-wide patch started in setUp() and stopped only by a
cleanup then leaked into every later module of the same gate worker (0.22.0, batch 0). Not a production path."""
from public_research import PublicResearch

_MISSING = object()


class Pin:
    def __init__(self, value):
        self.saved = PublicResearch.__dict__.get('local_agreement', _MISSING)
        PublicResearch.local_agreement = value
        self.active = True

    def restore(self):
        if not self.active:
            return
        self.active = False
        if self.saved is _MISSING:
            del PublicResearch.local_agreement
        else:
            PublicResearch.local_agreement = self.saved


def pin(test, value):
    """Pin the switch for test; restored by test.tearDown (call restore_pin there) or test's cleanups."""
    test._research_pin = Pin(value)
    test.addCleanup(test._research_pin.restore)


def restore_pin(test):
    holder = getattr(test, '_research_pin', None)
    if holder is not None:
        holder.restore()
