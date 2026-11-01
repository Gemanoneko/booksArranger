"""Retry classification for existing cleanup authority; never authorizes removal."""
import errno
import re

RETRY_SECONDS = 60.0
# Access/sharing/offline/timeouts may change without any catalog write.
_WINDOWS = {2, 3, 5, 21, 32, 33, 53, 64, 67, 121, 1231}
_ERRNO = {errno.ENOENT, errno.EACCES, errno.EPERM, errno.EBUSY, errno.EIO, errno.ETIMEDOUT}

def transient(error):
    if isinstance(error, InterruptedError):
        return False
    if isinstance(error, OSError) and (getattr(error, 'winerror', None) in _WINDOWS or error.errno in _ERRNO):
        return True
    reason = str(error or '')
    # Native boundaries preserve their actual OS error in this exact wrapper.
    codes = re.findall(r'\[WinError (\d+)\]', reason)
    if codes and all(int(code) in _WINDOWS for code in codes):
        return True
    return ('database is locked' in reason or 'database is busy' in reason or
            reason.startswith('Folder cleanup tries again later: '))
