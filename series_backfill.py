"""v0.16.12 series backfill (Sergei, 2026-10-18): published audiobooks that were made without a series get one.

One background pass at a time, resumable across restarts (series_backfill table). For each finished book
without a series it asks the series sources (Goodreads first, FantLab fallback: public_research, with
their pacing and cache). When one is found and the book can be changed safely:

  1. writes the new metadata next to the published file (quicktime_chapters.retag): only the album, grouping,
     sort-album and track items change; every other atom, the media included, is copied byte for byte;
  2. proves nothing else changed: media and sample tables byte-identical (quicktime_chapters.media_unchanged),
     the compressed audio and its decoder configuration the same (the preservation proofs), chapters and
     cover the same, and the new tags as a newly converted book with that series would carry;
  3. renames it to the name the app gives a book with that series (metadata.propose), on the same volume,
     never over an existing file;
  4. records the new file in the catalog in one transaction (job output and manifest, verified identity,
     owned output, the book's review), so it reads as verified at once and nothing re-checks or purges it;
  5. removes the old file. No copy is kept (Sergei's rule); the old file goes only after the new one is
     proven, renamed and recorded.

Any doubt leaves the published file as it is and records why. File changes wait while a book converts.
"""
import copy
from contextlib import contextmanager
from datetime import datetime
import hashlib
import sqlite3
import json
import os
import threading
import time
from pathlib import Path

from native_io import BoundaryError, DirectoryBoundary, VerifiedFile, ordinary, publish_no_replace
from scanner import connect

TABLE = ('CREATE TABLE IF NOT EXISTS series_backfill(job_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,'
         'record TEXT NOT NULL,updated TEXT NOT NULL)')
FINAL = ('none', 'done', 'skipped', 'held')
ACTIVE = ('writing', 'written', 'renamed', 'cataloged')
ALBUM, GROUPING, SORT_ALBUM, TRACK = b'\xa9alb', b'\xa9grp', b'soal', b'trkn'
PASS_WAIT = 600
START_DELAY = 120  # after startup: the published check and the queue come first
TEMP_PREFIX = '.books-arranger-series-'


class Held(ValueError):
    """The book is left as it is, with this reason."""


class Later(Exception):
    """Not now (a conversion, a scan, a source pause or an unfinished cleanup); the next pass tries again."""
    def __init__(self, reason, retry_at=None, waits=None):
        super().__init__(reason)
        self.retry_at = retry_at
        self.waits = waits or []


def _stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def encoded(manifest):
    """The stored manifest text and its hash, exactly as AudioJobs.enqueue freezes them."""
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return text, hashlib.sha256(text.encode('utf-8')).hexdigest()


def album(review):
    return ' - '.join([review['series'], review.get('number', ''), review['title']])


def series_tags(review):
    """The Apple metadata items a book converted with this series carries (audio_pipeline._encode_inputs)."""
    from quicktime_chapters import text_tag, track_tag
    value = album(review)
    tags = {ALBUM: text_tag(ALBUM, value), GROUPING: text_tag(GROUPING, review['series']), SORT_ALBUM: text_tag(SORT_ALBUM, value)}
    if str(review.get('number', '')).isdigit() and 0 < int(review['number']) < 65536:
        tags[TRACK] = track_tag(int(review['number']))
    return tags


def sha256(path, stop):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            if stop.is_set():
                raise InterruptedError('Series update stopped; the published audiobook is unchanged')
            value.update(block)
    return value.hexdigest()


class SeriesBackfill:
    def __init__(self, merge, research=None, stage=None, clock=time.time):
        self.merge = merge
        self.database = merge.inventory.database
        self.research = research
        self.clock = clock
        self.stage = Path(stage) if stage else Path(merge.stage_root).parent / 'series-backfill'
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.thread = None
        self.progress = None
        with connect(self.database) as db:
            db.execute(TABLE)

    # ------------------------------------------------------------------ thread
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop.clear()
        self.thread = threading.Thread(target=self._run, name='books-series-backfill', daemon=True)  # close() stops it; a hard exit is what the resumable states are for
        self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(30)

    def _run(self):
        if self.wake.wait(START_DELAY):
            self.wake.clear()
        while not self.stop.is_set():
            try:
                self.run_pass()
            except InterruptedError:
                pass
            except Exception:
                pass  # display only; every book records its own reason
            finally:
                self.progress = None
            self.wake.wait(self._next_wait())
            self.wake.clear()

    def _next_wait(self):
        """Due deferrals get another pass without a hot loop or renewed provider allowance."""
        due = [json.loads(row['record']).get('next_attempt') for row in
               self._rows("SELECT record FROM series_backfill WHERE state NOT IN (%s)" % ','.join('?' * len(FINAL)), FINAL)]
        due = [value for value in due if isinstance(value, (int, float))]
        return max(30, min(PASS_WAIT, min(due) - self.clock())) if due else PASS_WAIT

    def status(self):
        """The progress row: {'title', 'done', 'total', 'step'} while a pass works on a book, else None."""
        value = self.progress
        return dict(value) if value else None

    # ------------------------------------------------------------------ ledger
    def _rows(self, sql, params=()):
        with connect(self.database) as db:
            return [dict(r) for r in db.execute(sql, params)]

    def entry(self, job_id):
        rows = self._rows('SELECT * FROM series_backfill WHERE job_id=?', (job_id,))
        if not rows:
            return None
        row = rows[0]
        row['record'] = json.loads(row['record'])
        return row

    def _set(self, job_id, state, reason='', record=None):
        with connect(self.database) as db:
            prior = db.execute('SELECT record FROM series_backfill WHERE job_id=?', (job_id,)).fetchone()
            value = record if record is not None else (json.loads(prior[0]) if prior else {})
            db.execute('INSERT OR REPLACE INTO series_backfill VALUES(?,?,?,?,?)',
                       (job_id, state, reason, json.dumps(value, ensure_ascii=False), _stamp()))

    # ------------------------------------------------------------------ pass
    def candidates(self):
        """Finished books (the newest job of each book) without a series and without a final record."""
        entries = {r['job_id']: r for r in self._rows('SELECT job_id,state,record FROM series_backfill')}
        newest = {}
        for row in self._rows("SELECT job_id,json_extract(manifest,'$.candidate_id') AS candidate FROM audio_jobs ORDER BY created,job_id"):
            newest[row['candidate']] = row['job_id']
        result = []
        for row in self._rows("SELECT * FROM audio_jobs WHERE state='completed' AND output IS NOT NULL ORDER BY updated,job_id"):
            manifest = json.loads(row['manifest'])
            review = manifest.get('metadata') or {}
            entry = entries.get(row['job_id'])
            record = json.loads(entry['record']) if entry else {}
            if entry and (entry['state'] in FINAL + ACTIVE or record.get('next_attempt', 0) > self.clock()) \
                    or newest.get(manifest.get('candidate_id')) != row['job_id']:
                continue
            if review.get('series') or not review.get('title') or not review.get('canonical_author'):
                continue
            result.append(row)
        # Unvisited books go first; one slow oldest candidate cannot monopolize a pass.
        return sorted(result, key=lambda row: json.loads(entries[row['job_id']]['record']).get('last_attempt', 0)
                      if row['job_id'] in entries else 0)

    def _defer(self, job_id, wait, found=None, state='deferred', manifest=None):
        entry = self.entry(job_id)
        record = dict(entry['record']) if entry else {}
        if state == 'deferred' and entry and entry['state'] in ACTIVE:
            state = entry['state']  # Never replace a crash-recovery checkpoint with a lookup state.
        now = self.clock()
        record.update(last_attempt=now, next_attempt=max(now + 60, wait.retry_at or now + PASS_WAIT),
                      waits=wait.waits, deferrals=record.get('deferrals', 0) + 1)
        if found:
            binding = encoded(manifest)[1] if manifest is not None else None
            found_at = self._finding_time(found, now)
            if record.get('found') == found and record.get('found_binding') == binding:
                found_at = min(record.get('found_at', 0), found_at)
            record['found'] = found
            record['found_binding'] = binding
            record['found_at'] = found_at  # Waiting for idle does not renew source-evidence age.
        self._set(job_id, state, str(wait), record)

    @staticmethod
    def _finding_time(found, now):
        """The oldest actual receipt, not the time an old cache entry was observed."""
        times = []
        for receipt in found.get('receipts') or []:
            try:
                digest = receipt['sha256']
                if not isinstance(digest, str) or len(digest) != 64 or set(digest) - set('0123456789abcdef'):
                    return 0
                parsed = datetime.fromisoformat(receipt['retrieved_utc'].replace('Z', '+00:00'))
                if parsed.tzinfo is None or parsed.timestamp() > now + 60:
                    return 0
                times.append(parsed.timestamp())
            except (KeyError, TypeError, ValueError, AttributeError):
                return 0
        return min([now, *times]) if times else 0

    def run_pass(self):
        try:
            self._pass()
        finally:
            self.progress = None

    def _pass(self):
        if self.research is None:
            return
        for row in self._rows('SELECT job_id FROM series_backfill WHERE state IN (%s)' % ','.join('?' * len(ACTIVE)), ACTIVE):
            entry = self.entry(row['job_id'])
            if entry['record'].get('next_attempt', 0) > self.clock():
                continue
            try:
                self._idle()
                self.resume(row['job_id'])
            except Later as wait:
                self._defer(row['job_id'], wait, state=entry['state'])
        books = self.candidates()
        jobs = self.merge.jobs.status()['jobs'] if books and getattr(self.merge, 'publications', None) is not None else None
        for index, row in enumerate(books):
            if self.stop.is_set():
                return
            manifest = json.loads(row['manifest'])
            title = manifest['metadata']['title']
            self.progress = {'title': title, 'done': index, 'total': len(books), 'step': 'looking up'}
            found = None
            try:
                reason = self.unsafe(row, jobs)
                if reason:
                    self._set(row['job_id'], 'skipped', reason)
                    continue
                entry = self.entry(row['job_id'])
                prior = entry['record'] if entry else {}
                found = prior.get('found') if prior.get('found_binding') == encoded(manifest)[1] and prior.get('found_at', 0) > 0 \
                    and 0 <= self.clock() - prior.get('found_at', 0) <= 7 * 86400 else None
                found = found or self.lookup(manifest)
                preferred = prior.get('found') or {}
                if found and prior.get('found_binding') == encoded(manifest)[1] and preferred.get('provider') == 'goodreads' \
                        and (found['name'], found['number']) != (preferred.get('name'), preferred.get('number')):
                    raise Held('The new series answer conflicts with the retained Goodreads sequence; copies kept')
                if not found:
                    self._set(row['job_id'], 'none', 'No series found on Goodreads or FantLab')
                    continue
                self.progress = {'title': title, 'done': index, 'total': len(books), 'step': 'updating'}
                self.apply(row['job_id'], found)
            except Later as wait:
                self._defer(row['job_id'], wait, found, manifest=manifest)
                continue
            except InterruptedError:
                return
            except Held as held:
                entry = self.entry(row['job_id'])
                evidence = dict(entry['record']) if entry else {}
                evidence['last_attempt'] = self.clock()
                self._set(row['job_id'], 'held', str(held), evidence)
            except Exception as error:
                self._defer(row['job_id'], Later('Series lookup could not finish: ' + (str(error) or type(error).__name__)), found, manifest=manifest)

    # ------------------------------------------------------------------ checks
    def unsafe(self, row, jobs=None):
        """A permanent reason this book is not changed (recorded as skipped), or ''. Raises Later when it is only not yet."""
        merge = self.merge
        job_id = row['job_id']
        manifest = json.loads(row['manifest'])
        output = json.loads(row['output'])
        if manifest.get('replacement_id') or manifest.get('replacement_parent_job_id'):
            return 'Part of a replacement; left as it is'
        with connect(self.database) as db:
            def table(name):
                return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
            if table('audiobook_replacements') and db.execute(
                    'SELECT 1 FROM audiobook_replacements WHERE parent_job_id=? OR replacement_job_id=?', (job_id, job_id)).fetchone():
                return 'Part of a replacement; left as it is'
            if table('kept_files') and db.execute('SELECT 1 FROM kept_files WHERE job_id=?', (job_id,)).fetchone():
                return 'Files kept at your choice; left as they are'
            cleanup = db.execute('SELECT state FROM source_cleanup WHERE job_id=?', (job_id,)).fetchone() if table('source_cleanup') else None
            recovery = db.execute('SELECT state FROM recovery_retention WHERE job_id=?', (job_id,)).fetchone() if table('recovery_retention') else None
            storage = db.execute('SELECT state FROM storage_cleanup_jobs WHERE job_id=?', (job_id,)).fetchone() if table('storage_cleanup_jobs') else None
            folders = db.execute('SELECT state FROM source_folder_cleanup_jobs WHERE job_id=?', (job_id,)).fetchone() if table('source_folder_cleanup_jobs') else None
        if cleanup and cleanup[0] != 'completed' or recovery and recovery[0] != 'deleted' or not storage or storage[0] != 'completed' \
                or folders and folders[0] not in ('completed', 'unsupported') or job_id in merge.__dict__.get('_post_jobs', set()):
            raise Later('Its cleanup is not finished yet')
        from encoding_policy import AUTOMATIC_PROFILE, LEGACY_PROFILE, PROFILE
        if output.get('validation', {}).get('profile') not in {PROFILE, LEGACY_PROFILE, AUTOMATIC_PROFILE}:
            return 'Made by an earlier profile; left as it is'
        publications = getattr(merge, 'publications', None)
        if publications is not None:
            current = publications.publication(jobs if jobs is not None else merge.jobs.status()['jobs'], manifest['candidate_id'])
            if not current or current.get('kind') != 'original' or current.get('id') != job_id:
                return 'Has a chapter update or a newer version; left as it is'
        return ''

    def lookup(self, manifest):
        from public_research import ResearchWait
        from public_work_identity import EvidenceConflict
        review = manifest['metadata']
        result = {'sources': []}
        budget = {'remaining': 6}
        waits = []
        for provider, args in (('_series_goodreads', (review['title'], review['canonical_author'], self.stop, budget, result)),
                               ('_series_fantlab', (review['title'], review['canonical_author'], False, self.stop, budget, result))):
            try:
                found = getattr(self.research, provider)(*args)
                if found:
                    return dict(found, receipts=result['sources'], deferred_sources=waits)
            except ResearchWait as wait:
                waits.append({'source': wait.source, 'reason': wait.reason, 'retry_at': wait.retry_at,
                              'kind': wait.kind, 'scope': wait.scope})
            except EvidenceConflict as error:
                raise Held('Series sources need review: ' + str(error)) from None
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                waits.append({'source': provider.removeprefix('_series_'), 'reason': str(error) or type(error).__name__,
                              'retry_at': self.clock() + PASS_WAIT, 'kind': 'unverified_response', 'scope': 'candidate'})
        if waits:
            raise Later('; '.join(item['source'] + ': ' + item['reason'] for item in waits),
                        min(item['retry_at'] for item in waits), waits)
        return None

    def _idle(self):
        """File changes wait for the book queue, a cleanup and a scan; series lookups do not."""
        merge = self.merge
        jobs = merge.jobs
        if jobs._thread and jobs._thread.is_alive() or merge.cleanup.thread and merge.cleanup.thread.is_alive() or merge.cleanup.current:
            raise Later('A book is being converted or cleaned up', self.clock() + 60)
        if merge.inventory.worker and merge.inventory.worker.is_alive():
            raise Later('A library scan is running', self.clock() + 60)

    # ------------------------------------------------------------------ the update
    def apply(self, job_id, found):
        """Steps 1-5 for one book; any doubt leaves the published file and records why."""
        from metadata import propose
        self._idle()
        rows = self._rows('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,))
        manifest = json.loads(rows[0]['manifest'])
        output = json.loads(rows[0]['output'])
        review = dict(manifest['metadata'], series=found['name'], number=found['number'])
        facts = copy.deepcopy(manifest.get('metadata_facts'))
        old = ordinary(output['final_path'])
        root = ordinary(manifest['root'])
        current = propose('', str(root), 'audiobook', {}, manifest['metadata'], automatic_facts=facts)
        record = {'series': found['name'], 'number': found['number'], 'provider': found['provider'], 'source_url': found['source_url'],
                  'old_path': str(old), 'old_sha256': output['sha256'], 'old_size': output['size'],
                  'research_receipts': found.get('receipts', []), 'deferred_sources': found.get('deferred_sources', [])}
        try:
            if not current.get('path') or os.path.normcase(current['path']) != os.path.normcase(str(old)):
                raise Held("The audiobook's name does not follow the app's naming; left as it is")
            if facts:
                facts['series_state'] = 'verified'
            target = propose('', str(root), 'audiobook', {}, review, automatic_facts=facts)
            if not target.get('path'):
                raise Held('No name for the series: ' + (target.get('reason') or 'unknown'))
            new = ordinary(target['path'])
            if not new.is_relative_to(root) or new.suffix.lower() != '.m4b' or new == old:
                raise Held('The series name is not a valid audiobook name')
            temp = old.parent / (TEMP_PREFIX + job_id + '.m4b')
            record.update(new_path=str(new), temp=str(temp), review=review)
            record.update(root=str(root), parent_identity=output['parent_identity'])
            with self._boundary(record), VerifiedFile(old) as original:
                if original.facts()['size'] != output['size'] or original.sha256() != output['sha256']:
                    raise Held('The published audiobook changed since it was verified; left as it is')
                record['old_identity'] = original.facts()['identity']
                self._set(job_id, 'writing', '', record)
                self._own_temporary(job_id, temp)
                self._write(job_id, manifest, output, old, temp, review, record)
        except Held as held:
            self._discard_temp(job_id, record)
            self._set(job_id, 'held', str(held), record)
            return
        except (Later, InterruptedError):
            self._discard_temp(job_id, record)
            self._set(job_id, 'pending', '', record)
            raise
        except Exception as error:
            self._discard_temp(job_id, record)
            self._set(job_id, 'held', 'Series update failed; the audiobook is unchanged: ' + (str(error) or type(error).__name__), record)
            return
        finally:
            self._clear_stage(job_id)
        self.resume(job_id)

    def _write(self, job_id, manifest, output, old, temp, review, record):
        """Steps 1-2: the new metadata in a new file next to the old one, then the proofs."""
        from quicktime_chapters import retag, media_unchanged, ChapterFormatError
        from audio_pipeline import audio_packet_hash, copied_audio_evidence, probe
        try:
            receipt = retag(old, temp, self.stop, series_tags(review))
            if receipt['input_sha256'] != output['sha256'] or receipt['input_size'] != output['size']:
                raise Held('The published audiobook changed since it was verified; left as it is')
            media_unchanged(old, temp, self.stop)
        except ChapterFormatError as error:
            raise Held('The audiobook cannot be retagged safely: ' + str(error)) from None
        stage = self.stage / job_id
        stage.mkdir(parents=True, exist_ok=True)
        duration = float(output.get('validation', {}).get('duration') or 0) or 3600.0
        if audio_packet_hash(old, stage, self.stop, duration) != audio_packet_hash(temp, stage, self.stop, duration):
            raise Held('The audio changed while retagging; left as it is')
        if copied_audio_evidence(old, stage, self.stop, duration, source_relative=True) != copied_audio_evidence(temp, stage, self.stop, duration, source_relative=True):
            raise Held('The audio decoder configuration or timing changed while retagging; left as it is')
        before = probe(old, stage, self.stop)
        after = probe(temp, stage, self.stop)
        self.check_tags(before, after, review)
        stat = temp.stat()
        record.update(new_sha256=sha256(temp, self.stop), new_size=stat.st_size, new_mtime=stat.st_mtime_ns)
        with VerifiedFile(temp) as written:
            if written.facts()['size'] != record['new_size'] or written.sha256() != record['new_sha256']:
                raise Held('The new file changed during verification; the audiobook is unchanged')
            record['new_identity'] = written.facts()['identity']
        self._set(job_id, 'written', '', record)

    @staticmethod
    def check_tags(before, after, review):
        """The new file carries the series as a converted book would; everything else read back is unchanged."""
        def tags(raw):
            return {k.lower(): str(v) for k, v in raw.get('format', {}).get('tags', {}).items()}
        old, new = tags(before), tags(after)
        wanted = {'album': album(review), 'grouping': review['series'], 'sort_album': album(review)}
        if str(review.get('number', '')).isdigit() and 0 < int(review['number']) < 65536:
            wanted['track'] = str(int(review['number']))
        for key, value in wanted.items():
            if new.get(key) != value:
                raise Held('Series tags did not read back: ' + key)
        if {k: v for k, v in old.items() if k not in wanted} != {k: v for k, v in new.items() if k not in wanted}:
            raise Held('Other metadata changed while retagging; left as it is')
        if before.get('chapters') != after.get('chapters'):
            raise Held('Chapters changed while retagging; left as it is')
        streams = lambda raw: [{k: s.get(k) for k in ('codec_type', 'codec_name', 'disposition', 'duration_ts')} for s in raw.get('streams', [])]
        if streams(before) != streams(after):
            raise Held('Streams changed while retagging; left as it is')

    def resume(self, job_id):
        """Steps 3-5 from the recorded state; safe to repeat after a restart at any point."""
        entry = self.entry(job_id)
        record = entry['record']
        state = entry['state']
        temp, new, old = Path(record['temp']), Path(record['new_path']), Path(record['old_path'])
        if state == 'writing':
            # Stopped while writing: the new file is not proven, so it goes; the published file never changed.
            self._discard_temp(job_id, record)
            self._set(job_id, 'pending', '', record)
            return
        try:
            with self._boundary(record) as boundary:
                self._resume_protected(job_id, record, state, temp, new, old, boundary)
        except (BoundaryError, OSError, Held, KeyError) as error:
            self._set(job_id, 'held', 'Series recovery could not verify the files; remaining copies kept: ' + str(error), record)

    @contextmanager
    def _boundary(self, record):
        """Rebind persisted ordinary ancestry; legacy unbound recovery records fail closed."""
        root = ordinary(record['root'])
        old, new, temp = (ordinary(record[key]) for key in ('old_path', 'new_path', 'temp'))
        if old == new or old.parent != new.parent or old.parent != temp.parent or temp in (old, new):
            raise Held('The recorded series paths do not share their original parent')
        with DirectoryBoundary(root, old.parent) as boundary:
            if [list(item) for item in boundary.identities] != record['parent_identity']:
                raise Held('The audiobook parent identity changed')
            yield boundary

    @contextmanager
    def _protected(self, path, record, kind, delete=False):
        """Hash the exact held file object, never accepting time/size as a byte proof."""
        with VerifiedFile(path, delete=delete) as handle:
            facts = handle.facts()
            if facts['identity'] != record[kind + '_identity'] or facts['size'] != record[kind + '_size'] \
                    or handle.sha256() != record[kind + '_sha256']:
                raise Held('The ' + kind + ' file no longer matches its verified identity and bytes')
            if delete and facts['links'] != 1:
                raise Held('The former file has another filesystem alias; kept')
            yield handle

    def _resume_protected(self, job_id, record, state, temp, new, old, boundary):
        if state == 'written':
            if temp.exists() and not new.exists():
                if not self._proven(temp, record):
                    self._discard_temp(job_id, record)
                    self._set(job_id, 'held', 'The new file changed before it was renamed; the audiobook is unchanged', record)
                    return
                try:
                    def same_identity(facts):
                        if facts['identity'] != record['new_identity']:
                            raise Held('The verified temporary identity changed')
                    publish_no_replace(temp, new, boundary, record['new_sha256'], record['new_size'], same_identity)
                except FileExistsError:
                    self._discard_temp(job_id, record)
                    self._set(job_id, 'held', 'A file with the series name already exists: ' + new.name, record)
                    return
                except OSError as error:
                    self._discard_temp(job_id, record)
                    self._set(job_id, 'held', 'The audiobook could not be renamed; it is unchanged: ' + str(error), record)
                    return
            elif temp.exists() and new.exists():
                self._discard_temp(job_id, record)
                self._set(job_id, 'held', 'A file with the series name already exists: ' + new.name, record)
                return
            elif not new.exists():
                self._set(job_id, 'held', 'The new file is gone; the audiobook is unchanged', record)
                return
            if not self._proven(new, record):
                self._set(job_id, 'held', 'The renamed file is not the proven one; check ' + new.name, record)
                return
            self._set(job_id, 'renamed', '', record)
            state = 'renamed'
        if state not in ('renamed', 'cataloged'):
            return
        # Every recovery entry point proves and protects the replacement through
        # catalog commit and exact-handle old-file disposal. No pathname unlink.
        with self._protected(new, record, 'new'):
            if state == 'renamed':
                try:
                    self.catalog(job_id, record)
                except sqlite3.Error as error:
                    raise Later('The catalog is busy: ' + str(error)) from None
                except Exception as error:
                    # Preserve both copies on a catalog refusal: no rollback may
                    # remove the only playable copy if the original changed.
                    self._set(job_id, 'held', 'The catalog could not record the series; copies kept: ' + (str(error) or type(error).__name__), record)
                    return
            if old.exists():
                with self._protected(old, record, 'old', delete=True) as former:
                    if record['old_identity'] == record['new_identity']:
                        raise Held('The old and new names identify the same file')
                    boundary.revalidate()
                    record['removal_intended'] = True
                    self._set(job_id, 'cataloged', '', record)
                    former.dispose()
                if old.exists():
                    raise Held('Former-file disposition has not completed; copies kept')
            elif not record.get('removal_intended'):
                raise Held('The former file is missing without a removal receipt')
            self._forget_temporary(job_id, temp)
            self._set(job_id, 'done', '', record)

    def _proven(self, path, record):
        """The proven new file: its exact native identity and complete held hash."""
        try:
            with self._protected(path, record, 'new'):
                return True
        except (BoundaryError, OSError, Held, KeyError):
            return False

    def catalog(self, job_id, record):
        """Step 4, one transaction: the book reads as verified at once, at its new path."""
        merge = self.merge
        new = ordinary(record['new_path'])
        with connect(self.database) as db:
            row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()
            manifest = json.loads(row['manifest'])
            output = json.loads(row['output'])
            if output['final_path'] == str(new) and output['sha256'] == record['new_sha256']:
                db.execute("UPDATE series_backfill SET state='cataloged',updated=? WHERE job_id=?", (_stamp(), job_id))
                return  # recorded before a restart
            if output['final_path'] != record['old_path'] or output['sha256'] != record['old_sha256']:
                raise Held('The book changed meanwhile')
            root = ordinary(manifest['root'])
            with DirectoryBoundary(root, new.parent) as boundary:
                ancestry = [list(item) for item in boundary.identities]
            review = record['review']
            manifest['metadata'] = dict(manifest['metadata'], series=review['series'], number=review['number'])
            manifest['destination'] = str(new)
            source = {'provider': record['provider'], 'url': record['source_url'], 'backfilled': _stamp(),
                      'evidence': record.get('research_receipts', []), 'deferred_sources': record.get('deferred_sources', [])}
            if isinstance(manifest.get('metadata_facts'), dict):
                manifest['metadata_facts'] = dict(manifest['metadata_facts'], series_state='verified', series_source=source)
            text, digest = encoded(manifest)
            validation = dict(output['validation'], sha256=record['new_sha256'], size=record['new_size'])
            validation['tags'] = dict(validation.get('tags') or {}, album=album(review), grouping=review['series'])
            updated = dict(output, final_path=str(new), sha256=record['new_sha256'], size=record['new_size'], parent_identity=ancestry, validation=validation)
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=?,output=?,updated=? WHERE job_id=? AND output=?',
                                 (text, digest, json.dumps(updated), _stamp(), job_id, row['output'])).rowcount
            if changed != 1:
                raise Held('The book changed meanwhile')
            identity = merge._identity_key(new, record['new_sha256'])
            stat = os.stat(new)
            db.execute('DELETE FROM verified_outputs WHERE job_id=?', (job_id,))
            db.execute('INSERT OR REPLACE INTO verified_outputs VALUES(?,?,?,?,?)',
                       (*identity, job_id, json.dumps([stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]), _stamp()))
            db.execute("UPDATE owned_artifacts SET path=?,sha256=?,size=? WHERE job_id=? AND kind='output'",
                       (str(new), record['new_sha256'], record['new_size'], job_id))
            group = db.execute('SELECT review FROM book_groups WHERE id=?', (manifest['candidate_id'],)).fetchone()
            if group and group[0]:
                stored = dict(json.loads(group[0]), series=review['series'], number=review['number'])
                db.execute('UPDATE book_groups SET review=? WHERE id=?', (json.dumps(stored, ensure_ascii=False), manifest['candidate_id']))
            context = db.execute('SELECT revision,data FROM candidate_context WHERE id=?', (manifest['candidate_id'],)).fetchone()
            if context and context[0] == manifest['candidate_revision']:
                data = json.loads(context[1])
                if isinstance(data.get('metadata_facts'), dict):
                    data['metadata_facts'] = dict(data['metadata_facts'], series_state='verified', series_source=source)
                why = 'Series and position added after publication from %s (Sergei 2026-10-18 series backfill).' % record['provider']
                for field, value in (('series', review['series']), ('number', review['number'])):
                    data.setdefault('metadata_evidence', []).append({'field': field, 'cited_value': value, 'source_url': record['source_url'],
                                                                    'retrieved_utc': _stamp(), 'reviewer_actor': 'assistant',
                                                                    'reviewer_identity': 'Books Arranger series backfill', 'basis': why})
                db.execute('UPDATE candidate_context SET data=? WHERE id=? AND revision=?',
                           (json.dumps(data, ensure_ascii=False), manifest['candidate_id'], context[0]))
            db.execute("UPDATE series_backfill SET state='cataloged',updated=? WHERE job_id=?", (_stamp(), job_id))
        merge.__dict__.get('_validated_outputs', {}).pop(job_id, None)
        if hasattr(merge, 'invalidate_status'):
            merge.invalidate_status()

    def _clear_stage(self, job_id):
        """The proof tools' own output files for this book (never anything else)."""
        folder = self.stage / job_id
        try:
            if folder.is_dir():
                for item in folder.iterdir():
                    if item.is_file() and item.suffix in ('.stdout', '.stderr'):
                        item.unlink()
                folder.rmdir()
        except OSError:
            pass

    # ------------------------------------------------------------------ owned temporary file
    def _own_temporary(self, job_id, temp):
        """The new file is app-owned while it exists, so a library scan never catalogs it."""
        with connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO owned_artifacts VALUES(?,?,?,?,?)', (str(temp), job_id, 'temporary', '', 0))
        if temp.exists():
            os.unlink(temp)  # our own unproven file from an interrupted pass

    def _discard_temp(self, job_id, record):
        temp = record.get('temp')
        if not temp:
            return
        try:
            if Path(temp).exists():
                os.unlink(temp)
            self._forget_temporary(job_id, Path(temp))
        except OSError:
            pass

    def _forget_temporary(self, job_id, temp):
        with connect(self.database) as db:
            db.execute("DELETE FROM owned_artifacts WHERE path=? AND job_id=? AND kind='temporary'", (str(temp), job_id))
