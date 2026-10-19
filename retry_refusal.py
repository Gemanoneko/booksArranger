"""Typed records for a refused M4B Retry or Repair (Judy's RefusedRetry spec, 2026-10-19).

The worker stores each refusal with a cause (what stopped it), a fix (who can clear it: 'update' an app
update, 'wait' the app's own cleanup, 'review' a new review, 'user' Sergei) and the key of the code that
decided it. The UI takes its words from the cause and its behaviour from the fix; nothing reads the
English reason, which is kept only for the Technical detail line.

A record whose fix is 'update' goes stale when the deciding code changes: the M4B preservation module
for 'unsupported_file', the app version for every other cause. A stale record no longer blocks Retry;
the next refusal under the new code stores a new record (one attempt per book per build).
"""
import functools
import json

FIXES = {'unsupported_file': 'update', 'working_files': 'wait', 'source_changed': 'review', 'file_problem': 'user', 'unknown': 'update'}

# v0.18.0 stored plain text. Those records are converted once (legacy()), keyed to the v0.18.0 code, so they
# go stale exactly when a build whose deciding code changed first runs. Hash of the installed v0.18.0
# m4b_preservation.py (equal to its git blob at v0.18.0).
LEGACY_VERSION = '0.18.0'
LEGACY_PRESERVATION_SHA256 = 'bc16d6094c1706e086a7d9b3798500af9f1fbfecb191799d0a3b7146b09e37b8'
# Conversion only: v0.18.0 refusal texts. The causes of every newer record are typed where they are raised.
LEGACY_WORKING_FILES = 'Prior audio working files need verified disposal before another source copy'
LEGACY_OWNERSHIP = 'Prior working-file ownership requires attention: '
LEGACY_SOURCE_CHANGED = frozenset({'Frozen review/source/cover/policy changed; failed job preserved', 'Reviewed candidate unavailable',
                                   'Reviewed candidate changed during source proof', 'Approved title unavailable'})
LEGACY_FILE_PROBLEM = frozenset({'Source alias is not eligible for repaired admission'})
# Every fixed refusal text v0.18.0's m4b_preservation can raise (its need()/Refused literals), plus the
# 'Missing/duplicate ' prefix it builds for a box kind.
LEGACY_PRESERVATION = frozenset('''32-bit box overflow|AAC roll mapping count/reference|Ambiguous chunk offset table|Artwork bound|Artwork format|Audiobook media type
|Box count/header bound|Box extent invalid|Bytes after the audio container are not exactly the final audio frames|Candidate changed retained source bytes
|Candidate extent changed|Candidate metadata differs from approved plan|Candidate silent frames differ from approved plan|Candidate tail padding is not exactly zero bytes
|Chapter reference repair changed track media|Chapter reference repair profile|Chapter reference size|Chapter samples lie past the audio container|Chunk map profile
|Chunk outside retained mdat|Chunk/sample overflow|Clock header|Composition sample count|Container byte bound|Data reference profile|Decode count/media clock mismatch
|Decoder description truncated|Dependency sample count|Duplicate approved metadata item|Duplicate track identity|EOF-sized box unsupported|EOF-sized boxes unsupported
|Exactly one audio track required|External/reference data refused|File type location/bound|File type payload|Full-box version/flags|Handler header|Invalid decode run
|Metadata handler profile|Metadata item bound|Metadata item format|Metadata read bound|Missing decoder description|Multiple/oversized movie|New metadata box size bound
|No approved metadata changes|No chunk map|No chunks|Only the final audio frames can be silenced|Overlapping sample payload|Required top-level boxes/wide successor
|Sample data reference|Sample size table|Short immutable stream read|Short protected read|Short verification read|Silence repair changed a timing or description table
|Silence repair changed an intact sample size|Silence repair changed the track|Silence repair moved an intact sample|Silence repair needs 64-bit chunk offsets
|Silence repair needs AAC-LC mono/stereo with 1024-sample frames|Silence repair needs MPEG-4 audio|Silence repair needs a plain AAC-LC configuration
|Silence repair needs an AAC-LC decoder description|Silence repair needs mono or stereo|Silence repair would replace more than one second of audio
|Single sample description required|Size repair needs a 32-bit audio container header|Source size|Sync sample bounds|Table count/extent|Text tag bound|Text tag type
|Top-level box count|Top-level extent invalid|Track bytes changed|Track count|Track header version|Track identity|Track number bound
|Truncated chapter samples cannot be repaired|Truncated extended box|Truncated fixed-size samples cannot be repaired|Truncated integer|Unknown approved tag
|Unknown chapter image field extension|Unknown repair|Unmapped samples|Unreferenced chapter/video track|Unresolved chapter reference|Unsupported AAC roll description
|Unsupported audio sample entry|Unsupported chapter image sample entry|Unsupported chapter text entry|Unsupported edit list rate/value|Unsupported sample group pair
|Unsupported structural box|Unsupported top-level reference/fragment box|Unsupported track handler|Unsupported track-local user data|Unsupported wide placeholder extent
|Unsupported/ambiguous brand|Wide placeholder must precede retained mdat|Zero clock/duration|Zero sample'''.replace('\n', '').split('|'))


@functools.lru_cache(maxsize=1)
def app_version():
    """The running app's version (package.json, or a packaged VERSION); constant for the run."""
    try:
        from web_server import version
        return version()
    except Exception:
        return 'unknown'


@functools.lru_cache(maxsize=1)
def preservation_sha256():
    """sha256 of the loaded m4b_preservation module: the key the repair check also uses."""
    try:
        import m4b_repair
        return m4b_repair._MODULE_SHA256
    except Exception:
        return None


def current_key(cause):
    """The key of the code that decides this cause in the running build."""
    if cause == 'unsupported_file' and preservation_sha256():
        return 'm4b_preservation:' + preservation_sha256()
    return 'app:' + app_version()


def record(reason, cause, at):
    """The stored refusal: raw reason, typed cause and fix, the app version and the deciding-code key."""
    cause = cause if cause in FIXES else 'unknown'
    return {'reason': str(reason or 'Admission refused'), 'cause': cause, 'fix': FIXES[cause], 'app_version': app_version(),
            'key': current_key(cause), 'at': at}


def _typed(value):
    return isinstance(value, dict) and value.get('cause') in FIXES and value.get('fix') == FIXES[value['cause']] and isinstance(value.get('key'), str)


def legacy_cause(text):
    """Conversion of v0.18.0 records only: the cause from the stored text."""
    if text == LEGACY_WORKING_FILES:
        return 'working_files'
    if text.startswith(LEGACY_OWNERSHIP):
        return 'file_problem'
    for prefix in ('Failed M4B retained: ', 'Repair refused: ', 'No provable repair: '):
        if text.startswith(prefix):
            rest = text[len(prefix):]
            if rest in LEGACY_SOURCE_CHANGED:
                return 'source_changed'
            if rest in LEGACY_FILE_PROBLEM or rest.startswith(('[Errno', '[WinError')):
                return 'file_problem'
            if rest in LEGACY_PRESERVATION or rest.startswith('Missing/duplicate '):
                return 'unsupported_file'
            return 'unknown'
    return 'unknown'


def legacy(text, at=''):
    """A v0.18.0 plain-text refusal as a typed record keyed to the v0.18.0 code; the text is kept."""
    text = str(text or '')
    cause = legacy_cause(text)
    key = 'm4b_preservation:' + LEGACY_PRESERVATION_SHA256 if cause == 'unsupported_file' else 'app:' + LEGACY_VERSION
    return {'reason': text, 'cause': cause, 'fix': FIXES[cause], 'app_version': LEGACY_VERSION, 'key': key, 'at': str(at or ''), 'converted': True}


def parse(detail, at=''):
    """The typed record stored in m4b_readmissions.detail; a v0.18.0 text reads as legacy() would convert it."""
    try:
        value = json.loads(detail)
    except (TypeError, ValueError):
        value = None
    return dict(value) if _typed(value) else legacy(detail, at)


def stale(value):
    """True when the deciding code changed since the refusal; only an 'update' fix goes stale."""
    return value.get('fix') == 'update' and value.get('key') != current_key(value.get('cause'))


def convert_legacy(db):
    """Once, at startup: every refused record without a typed cause gets one; state, order and text are kept.

    A compare-and-set on the detail column only, so a record that changes meanwhile is left as it is (it is
    read through parse() the same way). Returns the number converted.
    """
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='m4b_readmissions'").fetchone() is None:
        return 0
    converted = 0
    for parent, detail, updated in db.execute("SELECT parent_job_id,detail,updated FROM m4b_readmissions WHERE state='refused'").fetchall():
        try:
            if _typed(json.loads(detail)):
                continue
        except (TypeError, ValueError):
            pass
        converted += db.execute("UPDATE m4b_readmissions SET detail=? WHERE parent_job_id=? AND state='refused' AND detail=?",
                                (json.dumps(legacy(detail, updated), ensure_ascii=False), parent, detail)).rowcount
    return converted


def group(value):
    """The attention group of a book whose refusal is current."""
    return 'unsupported' if value.get('cause') == 'unsupported_file' else 'other'
