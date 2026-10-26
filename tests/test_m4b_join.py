"""Ruling 19a (Sergei 2026-10-24, method A): M4B parts that each carry an explicit part marker ("Часть 2", "Part 2", "CD 2")
are joined into one book, decoded and encoded once to AAC at the parts' bitrate through the normal conversion and its
verification, keeping every part's chapters at their offsets with their titles; a part without chapters becomes one
chapter named after the part, and repeated titles stay separate chapters. Bare-numbered parts ("Чужак 2") stay separate
books (rulings 13 and 15). The originals are removed only after the joined book is verified in Sorted. Real private
audio fixtures, the production output policy with a separate Sorted folder; no network."""
import json, shutil, subprocess, threading, unittest
from pathlib import Path

import groups
import split_books
import test_approve_as_is
from test_split_books import make_part, row as catalog_row


def part(path, title, track, chapters=None, album='Оно', artist='Стивен Кинг', total=3, seconds=1):
    """A private .m4b part: `chapters` is [(start ms, end ms, title)] or None for a part without chapters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    args = [shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'sine=frequency=%d:duration=%d' % (300 + 100 * track, seconds)]
    if chapters:
        meta = path.with_suffix('.txt')
        meta.write_text(';FFMETADATA1\n' + ''.join('[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n' % c for c in chapters), encoding='utf-8')
        args += ['-f', 'ffmetadata', '-i', str(meta), '-map', '0:a', '-map_chapters', '1']
    args += ['-c:a', 'aac', '-b:a', '64k', '-ar', '44100', '-ac', '1', '-metadata', 'album=' + album, '-metadata', 'artist=' + artist,
             '-metadata', 'title=' + title, '-metadata', 'track=%d/%d' % (track, total), str(path)]
    subprocess.run(args, check=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if chapters:
        path.with_suffix('.txt').unlink()
    return path


class GroupingTests(unittest.TestCase):
    def test_explicitly_marked_parts_with_their_own_chapters_are_one_book(self):
        files = [catalog_row('Stephen King/Оно/Оно. Часть %d.m4b' % n, {'album': 'Оно', 'artist': 'Стивен Кинг', 'title': 'Оно. Часть %d' % n, 'track': '%d/3' % n})
                 for n in (1, 2, 3)]
        chaptered = frozenset(f['path'] for f in files)
        built = groups.build(files, chaptered=chaptered)
        self.assertEqual([len(g['members']) for g in built.values()], [3], 'one book (before ruling 19a: three separate parts)')
        self.assertTrue(next(iter(built.values()))['split_book'])
        self.assertTrue(split_books.joinable_parts([groups.member(f) for f in files]))

    def test_bare_numbered_parts_are_one_set_their_chapters_decide(self):
        files = [catalog_row('Stephen King/Чужак %d.m4b' % n, {'album': 'Чужак', 'artist': 'Стивен Кинг', 'title': 'Чужак %d' % n, 'track': '%d/2' % n}) for n in (1, 2)]
        # Not explicitly marked: not joined by ruling 19a; one candidate whose chapters decide in research (test_part_sets).
        self.assertFalse(split_books.joinable_parts([groups.member(f) for f in files]))
        built = groups.build(files, chaptered=frozenset(f['path'] for f in files))
        self.assertEqual([len(g['members']) for g in built.values()], [2])

    def test_explicit_markers_counted(self):
        marked = lambda name, title='': split_books.explicit_part(groups.member(catalog_row('A/' + name, {'title': title})))
        for name in ('Оно. Часть 2.m4b', 'Book Part 2.m4b', 'Книга CD2.m4b', 'Диск 3.m4b', 'Глава 4.m4b', 'x.m4b'):
            with self.subTest(name=name):
                self.assertEqual(marked(name, 'Chapter 2' if name == 'x.m4b' else ''), True)
        for name in ('Чужак 2.m4b', 'Том 2.m4b', 'Книга 2.m4b', 'Трек 2.m4b'):
            with self.subTest(name=name):
                self.assertFalse(marked(name))


class JoinTests(test_approve_as_is.ApproveFixture):
    def three_parts(self):
        folder = self.audio / 'Stephen King' / 'Оно'
        return [part(folder / 'Оно. Часть 1.m4b', 'Оно. Часть 1', 1, [(0, 400, 'Пролог'), (400, 1000, 'Глава 1')]),
                part(folder / 'Оно. Часть 2.m4b', 'Оно. Часть 2', 2, [(0, 600, 'Глава 1'), (600, 1000, 'Интерлюдия')]),
                part(folder / 'Оно. Часть 3.m4b', 'Оно. Часть 3', 3)]

    def test_marked_parts_are_joined_keeping_every_chapter_and_removed_only_after_verification(self):
        sources = self.three_parts()
        rows = self.start()
        self.assertEqual([len(r['members']) for r in rows], [3], [r['scope'] for r in rows])
        row = rows[0]
        result = self.research(row)
        self.assertEqual(result['reasons'], [], result.get('reasons'))
        self.service.approve_automatic(row, result, threading.Event(), self.service.automatic.research.client)
        self.wait()
        job = self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['state'], 'completed', job)
        validation = job['output']['validation']
        self.assertEqual(validation['encoding']['mode'], 'normalize', 'decoded and encoded once')
        self.assertEqual(validation['encoding']['bitrate'], max(validation['encoding']['source_bitrates']), "at the parts' bitrate")
        self.assertEqual([c['title'] for c in validation['chapters']], ['Пролог', 'Глава 1', 'Глава 1', 'Интерлюдия', 'Оно. Часть 3'],
                         'every chapter kept, a repeated title stays separate, a part without chapters is one chapter named after it')
        offsets = [round(c['start'] / 1000, 1) for c in validation['chapters']]
        self.assertEqual(offsets, [0.0, 0.4, 1.0, 1.6, 2.0], 'each part starts where the one before it ends')
        self.assertAlmostEqual(validation['decoded_duration'], sum(validation['source_durations']), delta=validation['duration_tolerance'])
        self.assertEqual([p['name'] for p in job['manifest']['part_chapters']], ['Оно. Часть 1', 'Оно. Часть 2', 'Оно. Часть 3'])
        final = Path(job['output']['final_path'])
        self.assertTrue(final.is_file()); self.assertEqual(final.parent.parent, self.sorted)
        cleanup = self.service.cleanup.status(job['job_id'])
        self.assertEqual(cleanup['state'], 'completed', cleanup)
        self.assertTrue(all(not p.exists() for p in sources), 'removed only once the joined book was verified in Sorted')

    def test_a_part_whose_chapters_changed_after_the_plan_is_refused_and_nothing_is_removed(self):
        from unittest import mock
        import audio_pipeline
        sources = self.three_parts()
        row = self.start()[0]
        result = self.research(row)
        real = audio_pipeline.source_chapters
        def changed(path, stage, stop, duration):
            found = real(path, stage, stop, duration)
            return [dict(c, title=c['title'] + ' (changed)') for c in found] if str(path).endswith('source00001.m4b') else found
        with mock.patch.object(audio_pipeline, 'source_chapters', changed):
            self.service.approve_automatic(row, result, threading.Event(), self.service.automatic.research.client)
            self.wait()
        job = self.service.jobs.status()['jobs'][0]
        self.assertNotEqual(job['state'], 'completed', job)
        self.assertTrue(all(p.exists() for p in sources), 'originals kept')


if __name__ == '__main__':
    unittest.main()


def setUpModule():
    # Ruling 29 (0.22.2) has its own tests; these fixtures predate it (tests/original_title_fixture.py): Russian titles by
    # authors credited in Cyrillic with a foreign first name, used to test other rules.
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()
