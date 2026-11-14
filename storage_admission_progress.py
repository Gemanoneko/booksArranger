"""Bounded desktop admission telemetry; no storage or process mutations."""
from contextvars import ContextVar
import time

LIMIT_SECONDS = 597
_active = ContextVar('books_storage_admission_progress', default=None)


class Admission:
    def __init__(self, emit, *, clock=time.monotonic, cancelled=lambda:False):
        self.emit, self.clock = emit, clock
        self.cancelled=cancelled
        self.started = clock()
        self.phase, self.done, self.total, self.bytes = 'records', 0, None, 0
        self.progress = self.started
        self.sent = float('-inf')
        self.active = True

    def __enter__(self):
        self.token = _active.set(self)
        try:self.update(force=True)
        except BaseException:
            _active.reset(self.token)
            raise
        return self

    def update(self, phase=None, done=None, total=None, *, byte_count=0, force=False):
        if not self.active:return
        self.check_cancelled()
        now=self.clock()
        if now-self.started >= LIMIT_SECONDS:
            raise TimeoutError('The data folder check exceeded its time budget.')
        changed=phase is not None and phase!=self.phase
        if changed:self.phase,self.done,self.total,self.bytes=phase,0,total,0
        if done is not None and done>self.done:changed=True
        if byte_count:changed=True;self.bytes+=byte_count
        if done is not None:self.done=done
        if total is not None:self.total=total
        if changed:self.progress=now
        if force or changed and now-self.sent>=.25 or now-self.sent>=1:
            self.sent=now
            self.emit(dict(state='active',phase=self.phase,done=self.done,total=self.total,
                           bytes=self.bytes,elapsed_ms=int((now-self.started)*1000),
                           progress_age_ms=int((now-self.progress)*1000),limit_ms=LIMIT_SECONDS*1000))

    def complete(self):
        self.update(force=True)
        self.emit(dict(state='complete',elapsed_ms=int((self.clock()-self.started)*1000),limit_ms=LIMIT_SECONDS*1000))
        self.check_cancelled()
        if self.clock()-self.started >= LIMIT_SECONDS:
            raise TimeoutError('The data folder check exceeded its time budget.')
        self.active=False

    def check_cancelled(self):
        if self.cancelled():raise RuntimeError('The data folder check stopped because the app closed.')

    def __exit__(self, kind, error, tb):
        try:
            if kind is not None and self.active:
                self.emit(dict(state='failed',error=str(error),verification_required=type(error).__name__=='VerificationRequired',
                               elapsed_ms=int((self.clock()-self.started)*1000),limit_ms=LIMIT_SECONDS*1000))
        finally:_active.reset(self.token)


def report(phase=None,done=None,total=None,*,byte_count=0):
    active=_active.get()
    if active:active.update(phase,done,total,byte_count=byte_count)
