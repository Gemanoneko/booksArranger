"""Bounded retries for explicitly replay-safe SQLite transactions only."""
import sqlite3
import time
from scanner import connect

BUSY_SECONDS = 30
BUSY_ATTEMPTS = 60

def transaction(database, operation, stop=None):
    # Callers must supply only database operations: no requests, approval,
    # publication, source cleanup, or mutable request-budget accounting.
    deadline=time.monotonic()+BUSY_SECONDS
    for attempt in range(BUSY_ATTEMPTS):
        if stop is not None and stop.is_set():raise InterruptedError()
        try:
            with connect(database,timeout=min(.25,max(0,deadline-time.monotonic()))) as db:
                db.execute('BEGIN IMMEDIATE')
                result=operation(db)
            return result
        except sqlite3.OperationalError as error:
            code=getattr(error,'sqlite_errorcode',None)
            if type(code) is not int or code&255!=sqlite3.SQLITE_BUSY:raise
            remaining=deadline-time.monotonic()
            if remaining<=0 or attempt+1==BUSY_ATTEMPTS:raise
            delay=min(1,.1*2**min(attempt,4),remaining)
            if stop is not None:
                if stop.wait(delay):raise InterruptedError()
            else:time.sleep(delay)
