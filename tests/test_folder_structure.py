"""0.22.1, backlog items 9 and 10 (Sergei, 2026-10-25): real rows from his library, read the way he files his books.

Item 9: a clean file-name sequence decides the order (Map of Bones: 240 files, most track tags "N/-1", 20 re-tagged
"N" were sorted first); the folder structure Author\\Series\\N. Title names the author, the series, the book's number
and the title (ruling 6: a local source is enough; the folder's Latin title is the original, ruling 16); scrambled tags
give way to it (Black Order); a single file has nothing to order (Anita Blake 0); a disc tag that repeats the book's
number in its series is no missing disc (VanderMeer "Книга 1", disc 1/3). Item 10: a single file titled "1986" is a
whole book; an author named before the title in a tag ("Джастин Кронин. Перерождение 2") is set aside; the row shows
the author the app resolved; Sergei's reader rules (Сланевский, Смелова, Пухов) never make a reader the author.
Catalog rows only (groups.build on inventory-shaped rows, as the scanner stores them); no file, no network."""
import contextlib, json, sqlite3, tempfile, threading, unittest
from pathlib import Path

import author_rules
import groups
import local_identity
from metadata import propose
from public_research import PublicClient, PublicResearch, ResearchWait
from source_identity import source_gate

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'folder-structure-tests'; AREA.mkdir(parents=True, exist_ok=True)
ROOT = 'Z:\\Audiobooks'
SORTED = 'Z:\\Audiobooks Sorted'
SIGMA = 'James Rollins\\Sigm\u0430 Force'  # the live folder name carries a Cyrillic "а"


def file_row(relative, **tags):
    path = ROOT + '\\' + relative
    metadata = {'title': tags.get('title', ''), 'artist': tags.get('artist', ''), 'tags': tags,
                'probe': {'format': {'duration': '60'}, 'streams': [{'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '44100', 'channels': 1}]}}
    return {'root': ROOT, 'path': path, 'kind': 'audiobook', 'size': 1000, 'modified': 1000, 'metadata': json.dumps(metadata, ensure_ascii=False),
            'error': '', 'missing': 0, 'seen': 1, 'arrival': 0, 'review': ''}


def built(rows):
    """{book folder or file: row} as the catalog groups them."""
    found = {}
    for n, (scope, group) in enumerate(groups.build(rows).items()):
        row = dict(group, id='book-%d' % n, revision=1, fingerprint='fp-%d' % n, source_root=ROOT)
        key = str(Path(group['members'][0]['path']).parent) if len(group['members']) > 1 else group['members'][0]['path']
        found[key] = row
    return found


class Offline:
    """Every public source is closed: identity must not need one."""
    def __init__(self, database):
        self.database = database; self.calls = []

    def _closed(self, url, *_, **__):
        self.calls.append(url); raise ResearchWait('offline', 'private fixture', 0)
    json = read = _closed

    def discover(self, query, *_):
        self.calls.append(query); raise ResearchWait('offline', 'private fixture', 0)
    wikipedia = discover

    def receipt(self, url):
        return {'url': url}


class Base(unittest.TestCase):
    def catalog(self, rows):
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        database = Path(temp.name) / 'catalog.sqlite3'
        with contextlib.closing(sqlite3.connect(database)) as db:
            db.execute("CREATE TABLE files(root TEXT,path TEXT,kind TEXT,metadata TEXT,missing INTEGER DEFAULT 0,PRIMARY KEY(root,path))")
            for row in rows:
                db.execute("INSERT INTO files VALUES(?,?,'audiobook',?,0)", (ROOT, row['path'], row['metadata']))
            author_rules.seed(db)  # Sergei's 2026-10-24 answers: Сланевский, Смелова and Пухов are readers
            db.commit()
        self.research = PublicResearch(Offline(str(database)), leads=[])
        self.books = built(rows)
        return self.books

    def lookup(self, row):
        return self.research.lookup(dict(row, _manual_metadata_sources=[]), ROOT, threading.Event())

    def goes_to(self, row, result):
        review = dict(result['review'], organization_policy='books-hierarchy-v2')
        return propose(row['members'][0]['path'], SORTED, 'audiobook', row['metadata'], review, automatic_facts=result.get('metadata_facts'))['path']

    def approved(self, row):
        """What Approve and the row show (rulings 6b and 11a)."""
        return self.research.approved(row, ROOT)['approval']

    def approved_to(self, row):
        """Where Sergei's Approve files the book, with what the row shows."""
        return self.goes_to(row, self.research.approved(row, ROOT))

    def in_sorted(self, series, author):
        """Ruling 52: a book of this series already converted into Sorted under this author folder (a completed job)."""
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS audio_jobs(job_id TEXT PRIMARY KEY,state TEXT,manifest TEXT,updated TEXT)')
            count = db.execute('SELECT count(*) FROM audio_jobs').fetchone()[0]
            manifest = {'metadata': {'title': 'Другая книга', 'author': author, 'canonical_author': author, 'series': series, 'number': '9'}}
            db.execute("INSERT INTO audio_jobs VALUES(?,'completed',?,?)", ('job-%d' % count, json.dumps(manifest, ensure_ascii=False), '2026-10-27T00:00:%02d' % count))
            db.commit()

    def split_asked(self, row, series, number, title):
        """Ruling 52: asked (title_series) with the split filled in; returns the lookup."""
        result = self.lookup(row)
        ask = result.get('ask') or {}
        self.assertEqual((ask.get('kind'), ask.get('why')), ('title_author', 'title_series'), (result['reasons'], ask))
        self.assertEqual(ask.get('split'), {'series': series, 'number': number, 'title': title})
        self.assertEqual(ask['fields']['title']['proposal'], title, 'the Title field shows the split title')
        self.assertEqual((ask['fields']['series']['proposal'], ask['fields']['number']['proposal']), (series, number))
        return result


def map_of_bones():
    # 240 files in perfect sequence; most track tags "N/-1"; the 20 files re-tagged on 2020-03-07 carry a plain "N".
    odd = {7, 9, 18, 21, 27, 29, 32, 35, 41, 44, 52, 60, 77, 100, 104, 106, 108, 113, 117, 150}
    return [file_row(SIGMA + '\\2. Map of Bones\\Роллинс Джеймс - Кости волхвов - %02d - Kosti_%03d.m4a' % (n, n),
                     track=('%d' % n) if n in odd else '%d/-1' % n, album='Кости волхвов', artist='Роллинс Джеймс', title='Kosti_%03d' % n, genre='Speech')
            for n in range(1, 241)]


class OrderTests(Base):
    def test_a_clean_file_name_sequence_decides_the_order_whatever_a_few_odd_tags_say(self):
        row = self.catalog(map_of_bones())[ROOT + '\\' + SIGMA + '\\2. Map of Bones']
        names = [m['filename'] for m in sorted(row['members'], key=lambda m: m['order'])]
        self.assertEqual(names[:3], ['Роллинс Джеймс - Кости волхвов - 01 - Kosti_001.m4a', 'Роллинс Джеймс - Кости волхвов - 02 - Kosti_002.m4a',
                                     'Роллинс Джеймс - Кости волхвов - 03 - Kosti_003.m4a'], 'never 07, 09, 18, 21, 27 first')
        self.assertEqual([int(n.split(' - ')[2]) for n in names], list(range(1, 241)))
        self.assertFalse(any(m['order_conflict'] for m in row['members']))
        result = self.lookup(row)
        self.assertNotIn('Playback order uncertain', result['reasons'])

    def test_no_sequence_when_the_names_do_not_settle_it(self):
        import track_order
        self.assertIsNone(track_order.filename_sequence(['CD1 - 01.mp3', 'CD1 - 02.mp3', 'CD2 - 01.mp3', 'CD2 - 02.mp3']))
        self.assertIsNone(track_order.filename_sequence(['01.mp3', '02.mp3', '04.mp3']), 'a gap')
        self.assertIsNone(track_order.filename_sequence(['Глава.mp3', 'Пролог.mp3']))
        self.assertEqual(track_order.filename_sequence(['00_00_Prolog.mp3', '00_01_Blagodarnosti.mp3', '01_02_Nyneshniy den.mp3']), [0, 1, 2])
        self.assertEqual(track_order.filename_sequence(['Orakul_002.mp3', 'Orakul_001.mp3']), [2, 1])

    def test_tags_that_number_the_files_in_the_order_their_names_sort_are_no_conflict(self):
        # "9. Bloodline": names number part and chapter (00_00 .. 04_45, the chapter count restarting is no sequence),
        # the tags number the files 01/51 .. 51/51 in that same order.
        names = ['00_00_Rollins_D_Liniya_krovi', '00_01_Blagodarnosti', '00_02_Vyskazyvaniya', '01_01_Nyneshniy den', '01_02_Nyneshniy den', '02_03_Ray i ad']
        rows = [file_row(SIGMA + '\\9. Bloodline\\%s.mp3' % name, track='%02d/%02d' % (n, len(names)), album='Линия крови. Отряд сигма_08', artist='Роллинс Джеймс')
                for n, name in enumerate(names, 1)]
        row = self.catalog(rows)[ROOT + '\\' + SIGMA + '\\9. Bloodline']
        self.assertFalse(any(m['order_conflict'] for m in row['members']))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], result['reasons'])
        self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), ('Bloodline', 'Sigma Force', '9'))

    def test_a_single_file_is_never_order_unclear(self):
        row = self.catalog([file_row('Laurell K. Hamilton\\Anita Blake\\0 Those Who Seek Forgiveness.m4b', track='1', album='Anita Blake 0 - Those Who Seek Forgiveness',
                                     title='Anita Blake 0 - Those Who Seek Forgiveness', artist='Laurell K. Hamilton', album_artist='Laurell K. Hamilton')])
        row = next(iter(row.values()))
        self.assertFalse(row['members'][0]['order_conflict'], 'its name says 0, its tag 1: one file has nothing to order')
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        review = result['review']
        self.assertEqual((review['title'], review['series'], review['number'], review['canonical_author']),
                         ('Those Who Seek Forgiveness', 'Anita Blake', '0', 'Hamilton Laurell K.'), 'a prequel is position 0')
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Hamilton Laurell K\\Anita Blake\\Anita Blake - 0 - Those Who Seek Forgiveness - Hamilton Laurell K.m4b')


class StructureTests(Base):
    def test_map_of_bones_is_james_rollins_sigma_force_2_with_its_original_title(self):
        row = self.catalog(map_of_bones())[ROOT + '\\' + SIGMA + '\\2. Map of Bones']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        review = result['review']
        self.assertEqual((review['title'], review['canonical_author'], review['series'], review['number']), ('Map of Bones', 'Rollins James', 'Sigma Force', '2'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Rollins James\\Sigma Force\\Sigma Force - 2 - Map of Bones - Rollins James.m4b',
                         'was Rollins James\\Кости волхвов - Rollins James.m4b')
        self.assertNotIn('original_title', result['metadata_facts']['gap_search']['gaps'], 'the folder names the original title')

    def test_black_order_scrambled_tags_give_way_to_the_folders_and_the_file_names(self):
        rows = [file_row(SIGMA + '\\3. Black Order\\Чёрный орден - чит. Кирсанов С. - %02d - Роллинс Джеймс.m4a' % n,
                         track='%d/-1' % n, album='чит. Кирсанов С.', artist='Чёрный орден', title='Роллинс Джеймс') for n in range(1, 97)]
        row = self.catalog(rows)[ROOT + '\\' + SIGMA + '\\3. Black Order']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        review = result['review']
        self.assertEqual((review['title'], review['canonical_author'], review['series'], review['number']), ('Black Order', 'Rollins James', 'Sigma Force', '3'))
        self.assertEqual([m['filename'].split(' - ')[2] for m in sorted(row['members'], key=lambda m: m['order'])][:3], ['01', '02', '03'])
        shown = self.approved(row)
        self.assertNotIn('Кирсанов', shown['title'] + shown['author'], 'a reader ("чит.") is never the title or the author')

    def test_the_last_oracle_series_in_the_album_artist_is_not_the_author_and_the_disc_tag_does_not_order(self):
        rows = [file_row(SIGMA + '\\5. The Last Oracle\\Orakul_%03d.mp3' % n, track='%03d/216' % n, disc='06', album='Последний оракул',
                         artist='Роллинс Джеймс', album_artist='Отряд "Сигма"', title='Orakul_%03d' % n) for n in range(1, 217)]
        row = self.catalog(rows)[ROOT + '\\' + SIGMA + '\\5. The Last Oracle']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'not "Track numbers skip or don\'t start at 1"')
        review = result['review']
        self.assertEqual((review['title'], review['canonical_author'], review['series'], review['number']), ('The Last Oracle', 'Rollins James', 'Sigma Force', '5'))

    def vandermeer(self):
        folder = 'Jeff VanderMeer\\Annihilation\\'
        return self.catalog([
            file_row(folder + '477. Книга 1. Аннигиляция (Сергей Пухов)\\11. Аннигиляция.m4b', track='1/1', disc='1/3', album='Аннигиляция',
                     artist='Джефф Вандермеер', album_artist='Джефф Вандермеер', title='Аннигиляция'),
            file_row(folder + '478. Книга 2. Консолидация (Сергей Пухов)\\21. Ворожба.m4b', track='1/3', disc='2/3', album='Консолидация', artist='Джефф Вандермеер', album_artist='Джефф Вандермеер', title='Ворожба'),
            file_row(folder + '478. Книга 2. Консолидация (Сергей Пухов)\\22. Губка.m4b', track='2/3', disc='2/3', album='Консолидация', artist='Джефф Вандермеер', album_artist='Джефф Вандермеер', title='Губка'),
            file_row(folder + '478. Книга 2. Консолидация (Сергей Пухов)\\23. Ворота.m4b', track='3/3', disc='2/3', album='Консолидация', artist='Джефф Вандермеер', album_artist='Джефф Вандермеер', title='Ворота'),
            file_row(folder + '1340. Книга 3. Ассимиляция (Сергей Пухов)\\31. Ассимиляция.m4b', track='1/2', disc='3/3', album='Ассимиляция', artist='Джефф Вандермеер', title='Ассимиляция 1'),
            file_row(folder + '1340. Книга 3. Ассимиляция (Сергей Пухов)\\32. Ассимиляция.m4b', track='2/2', disc='3/3', album='Ассимиляция', artist='Джефф Вандермеер', title='Ассимиляция 2')])

    def test_vandermeer_book_1_is_annihilation_1_not_three_missing_discs(self):
        books = self.vandermeer()
        self.assertEqual(len(books), 3, 'each "Книга N" folder is its own book, never three parts of one')
        row = books[ROOT + '\\Jeff VanderMeer\\Annihilation\\477. Книга 1. Аннигиляция (Сергей Пухов)\\11. Аннигиляция.m4b']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'not "Files unclear: the tags say 3 discs, but 1 is here"')
        review = result['review']
        self.assertEqual((review['title'], review['canonical_author'], review['series'], review['number']), ('Аннигиляция', 'VanderMeer Jeff', 'Annihilation', '1'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\VanderMeer Jeff\\Annihilation\\Annihilation - 1 - Аннигиляция - VanderMeer Jeff.m4b')
        self.assertIn('original_title', result['metadata_facts']['gap_search']['background'], 'the English title comes from a source, later')
        self.assertNotIn('Пухов', self.approved(row)['author'], 'the reader in brackets is no author (and the uploader number 477 no position)')

    def test_vandermeer_books_2_and_3_are_one_book_each_with_their_parts_in_order(self):
        books = self.vandermeer()
        for folder, number, title, parts in (('478. Книга 2. Консолидация (Сергей Пухов)', '2', 'Консолидация', 3), ('1340. Книга 3. Ассимиляция (Сергей Пухов)', '3', 'Ассимиляция', 2)):
            row = books[ROOT + '\\Jeff VanderMeer\\Annihilation\\' + folder]
            self.assertEqual(len(row['members']), parts)
            result = self.lookup(row)
            self.assertEqual(result['reasons'], [], folder)
            self.assertEqual(result.get('part_set', {}).get('decision', 'join'), 'join', 'never separate books of a series')
            self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), (title, 'Annihilation', number))


class NumberTitleTests(Base):
    def jesper(self):
        return self.catalog([
            file_row('JESPER ERSGARD\\JESPER ERSGARD - 1986.m4b', album='1986', title='1986', artist='Илья Сланевский', genre='Other'),
            file_row('JESPER ERSGARD\\JESPER ERSGARD - 1986 Season 2.m4b', album='1986 Сезон 2', title='1986 Сезон 2', artist='Илья Сланевский', album_artist='Илья Сланевский'),
            file_row('JESPER ERSGARD\\Jesper Ersgard - 1986 Book 3 At the End of Time.m4b', album='1986 Book 3 At the End of Time', title='1986 Book 3 At the End of Time', artist='Jesper Ersgard')])

    def test_a_single_file_titled_1986_is_a_whole_book_by_the_author_its_name_and_folder_give(self):
        row = self.jesper()[ROOT + '\\JESPER ERSGARD\\JESPER ERSGARD - 1986.m4b']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], 'not "Part of a bigger book: This file is named as one chapter."')
        self.assertEqual((result['review']['title'], result['review']['canonical_author']), ('1986', 'Ersgard Jesper'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Ersgard Jesper\\1986 - Ersgard Jesper.m4b', 'was Без автора\\1986.m4b')
        shown = self.approved(row)
        self.assertNotIn(shown['author'], ('', 'Без автора', 'Илья Сланевский'), 'the row shows the author the app resolved, never the reader')

    def test_a_lone_number_beside_numbered_files_stays_a_chapter(self):
        rows = [file_row('Кто-то Иванов - Книга\\%02d.m4b' % n, album='%02d' % n, title='%02d' % n, artist='Кто-то Иванов') for n in (4, 5)]
        books = self.catalog(rows)
        result = self.lookup(books[ROOT + '\\Кто-то Иванов - Книга\\05.m4b'])
        self.assertIn(local_identity.PIECE_REASON, result['reasons'], 'positive control: chapter files are pieces')

    def test_a_held_piece_shows_the_author_it_resolved(self):
        record = {'accepted': False, 'ask': None, 'route': None, 'held': 'one chapter',
                  'fields': {'title': {'value': '1986', 'basis': 'tag'}, 'author': {'value': 'JESPER ERSGARD', 'basis': 'file_name'}}}
        self.assertEqual(local_identity.shown(record)['author'], 'JESPER ERSGARD')


class CroninTests(Base):
    def test_perezhdenie_2_is_the_passage_2_twelve_by_justin_cronin(self):
        folder = 'Justin Cronin\\The Passage Trilogy\\'
        books = self.catalog([
            file_row(folder + 'Перерождение 1. Перерождение.m4b', track='1', album='Перерождение', artist='Джастин Кронин', album_artist='Светлана Смелова', title='Джастин Кронин. Перерождение'),
            file_row(folder + 'Перерождение 2. Двенадцать.m4b', track='2', album='Джастин Кронин. Перерождение 2', artist='Светлана Смелова', title='Двенадцать'),
            file_row(folder + 'Перерождение 3. Город зеркал.m4b', album='Перерождение 3. Город зеркал', artist='Светлана Смелова', title='Перерождение 3. Город зеркал')])
        row = books[ROOT + '\\' + folder + 'Перерождение 2. Двенадцать.m4b']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [], '"<Series> N. <Title>" is no chapter label')
        review = result['review']
        self.assertEqual((review['title'], review['canonical_author'], review['series'], review['number']), ('Двенадцать', 'Cronin Justin', 'The Passage', '2'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Cronin Justin\\The Passage\\The Passage - 2 - Двенадцать - Cronin Justin.m4b',
                         'was Без автора\\Джастин Кронин. Перерождение 2.m4b')
        self.assertNotIn('Смелова', self.approved(row)['author'], 'the reader rule')
        third = self.lookup(books[ROOT + '\\' + folder + 'Перерождение 3. Город зеркал.m4b'])
        self.assertEqual((third['review']['title'], third['review']['number']), ('Город зеркал', '3'))

    def test_an_author_named_before_the_title_in_a_tag_is_set_aside(self):
        books = self.catalog([file_row('Unsorted\\Кронин\\Перерождение.m4b', album='Джастин Кронин. Перерождение', title='Джастин Кронин. Перерождение', artist='Светлана Смелова')])
        result = self.lookup(next(iter(books.values())))
        self.assertEqual(result['reasons'], [], result)
        self.assertEqual((result['review']['title'], result['review']['canonical_author']), ('Перерождение', 'Кронин Джастин'))


class StructureGuardTests(Base):
    def row(self, *relative):
        return {'members': [{'path': ROOT + '\\' + r, 'filename': Path(r).name} for r in relative]}

    def test_only_author_series_book_with_a_number(self):
        read = lambda *r: local_identity.folder_structure(self.row(*r), ROOT)
        self.assertIsNone(read('Unsorted\\Книги\\01. Title.mp3'), 'a container is no author')
        self.assertIsNone(read('Jeff VanderMeer\\Born\\Борн 1.m4b', 'Jeff VanderMeer\\Born\\Борн 2.m4b'), 'a book folder of parts, no series')
        self.assertIsNone(read('Stephen King\\Оно\\1 часть\\01.mp3'), 'a part folder is a piece of a book')
        self.assertIsNone(read('Stephen King\\Оно\\01. Глава 1.mp3'), 'a chapter file')
        found = read('Jeff VanderMeer\\Annihilation\\477. Книга 1. Аннигиляция (Сергей Пухов)\\11. Аннигиляция.m4b')
        self.assertEqual((found['series'], found['position'], found['title'], found['reader']), ('Annihilation', '1', 'Аннигиляция', 'Сергей Пухов'))
        found = read(SIGMA + '\\2. Map of Bones\\01.m4a', SIGMA + '\\2. Map of Bones\\02.m4a')
        self.assertEqual((found['author'], found['series'], found['position'], found['title']), ('James Rollins', 'Sigma Force', '2', 'Map of Bones'))

    # The measurement on the live copy (0.22.1): series folders written with their author, a count of books and a reader
    # became series names ("Lee Patrick\Ли Патрик – Трэвис Чейз 1-3 [Пухов Сергей]\Ли Патрик – Трэвис Чейз 1-3 [Пухов
    # Сергей] - 1 - Брешь"), and a book folder "Author (year) - Title" lost its title to a series album tag.
    def test_a_series_folder_with_its_author_a_count_and_a_reader_names_the_series_only(self):
        rows = [file_row('Patrick Lee\\Ли Патрик – Трэвис Чейз 1-3 [Пухов Сергей]\\1. Брешь\\Патрик Ли - Патрик Ли - Брешь - %02d - Брешь.m4a' % n,
                         title='Брешь', artist='Патрик Ли', album='Патрик Ли - Брешь', track='%d/-1' % n, disc='1/1') for n in (1, 2, 3)]
        row = self.catalog(rows)[ROOT + '\\Patrick Lee\\Ли Патрик – Трэвис Чейз 1-3 [Пухов Сергей]\\1. Брешь']
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), ('Брешь', 'Трэвис Чейз', '1'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Lee Patrick\\Трэвис Чейз\\Трэвис Чейз - 1 - Брешь - Lee Patrick.m4b')
        rows = [file_row('Robin Hobb\\Робин Хобб - Сага о Видящих\\1. Ученик убийцы\\Ученик убийцы, часть %d.m4b' % n, title='Ученик убийцы', album='Ученик убийцы',
                         artist='Хобб Робин', track='%d/2' % n, disc='1/3') for n in (1, 2)]
        row = self.catalog(rows)[ROOT + '\\Robin Hobb\\Робин Хобб - Сага о Видящих\\1. Ученик убийцы']
        review = self.lookup(row)['review']
        self.assertEqual((review['title'], review['series'], review['number']), ('Ученик убийцы', 'Сага о Видящих', '1'))
        read = lambda *r: local_identity.folder_structure(self.row(*r), ROOT)
        found = read('Clive Barker\\Книга Крови - Том 4\\2 - Нечеловеческое состояние\\01.mp3')
        self.assertEqual(found['series'], 'Книга Крови - Том 4', 'control: a dash that is no author keeps the series name whole')

    def test_a_book_folder_named_author_year_title_names_the_book_over_a_series_album_tag(self):
        rows = [file_row('Anne McCaffrey\\Dragonriders of Pern\\08. Энн Маккефри (2012) - Белый дракон\\Энн Маккефри (2012) - Белый дракон (Часть %d).m4b' % n,
                         title='Белый дракон (Часть %d)' % n, album='Пернский цикл', artist='Энн Маккефри', track='%d/2' % n, disc='4') for n in (1, 2)]
        row = self.catalog(rows)[ROOT + '\\Anne McCaffrey\\Dragonriders of Pern\\08. Энн Маккефри (2012) - Белый дракон']
        review = self.lookup(row)['review']
        self.assertEqual((review['title'], review['series'], review['number']), ('Белый дракон', 'Dragonriders of Pern', '8'), 'was "Пернский цикл", the album')
        # Control: a tag title that adds to the folder's ("Единая теория всего. Том 1" in "4. Единая Теория Всего") stays.
        rows = [file_row('Константин Образцов\\Красные цепи\\4. Единая Теория Всего\\Том 1 - Единая теория всего. - Горизонт Событий.m4b',
                         title='Единая теория всего. Том 1', album='Единая теория всего. Том 1', artist='Константин Образцов')]
        row = next(iter(self.catalog(rows).values()))
        self.assertEqual(self.lookup(row)['review']['title'], 'Единая теория всего. Том 1')


class SeriesFolderFileTests(Base):
    """Senua's 0.22.1 review, W1 and W2, on the live rows (names and tags as the catalog holds them, 2026-10-26). A single
    file in an Author\\Series folder took its file name as the title over a clean tag title: another author's name
    («Сергей Недоруб - Севастопольский дозор»), a dangling bracket («Марина Ясинская - Чужой Дозор )») and the file's part
    number («Игры Немезиды 1»). A book folder under its author («5. Игры Немезиды») was read as the series."""
    DOZORY = 'Сергей Лукьяненко\\Вселенная Дозоров - Межавторский цикл\\'
    LIVE = (('16 - Сергей Недоруб - Севастопольский дозор (08_00-20_00 16 мая 2016).m4b',
             dict(title='Севастопольский дозор', artist='Сергей Недоруб', album='Севастопольский дозор', genre='Фантастика', date='2016', album_artist='Воронецкий Станислав')),
            ('19 - Виталий Каплан - Масть (март 1788 - май 1789).m4b',
             dict(title='Масть', artist='Виталий Каплан', album='Масть', genre='Боевое фэнтези, Городское фэнтези', date='2016', album_artist='Станислав Воронецкий')),
            ('25 - Марина Ясинская - Чужой Дозор (2017 (с 1932)).m4b',
             dict(title='Чужой Дозор', artist='Мария Ясинская', album='Чужой Дозор', genre='Фантастика', date='2017', album_artist='Евгения Меркулова')),
            ('27 - Валерий Пылаев - Запах Сумрака (август-сентябрь 2010).m4b',
             dict(title='Дозоры. Запах Сумрака', artist='Валерий Пылаев', album='Дозоры. Запах Сумрака', genre='Фантастика', date='2018', album_artist='Алексей Данков')),
            ('05 - С. Лукьяненко, И. Кузнецов - Печать сумрака (август 2003 - апрель 2004).m4b',
             dict(title='Печать сумрака', artist='С. Лукьяненко, И. Кузнецов', album='Печать сумрака', genre='аудиокнига', date='2014')))

    def test_a_clean_tag_title_beats_the_file_name_of_a_single_file_in_a_series_folder(self):
        books = self.catalog([file_row(self.DOZORY + name, **tags) for name, tags in self.LIVE])
        self.assertEqual(len(books), len(self.LIVE))
        for name, tags in self.LIVE:
            row = books[ROOT + '\\' + self.DOZORY + name]
            result = self.lookup(row)
            review = result.get('review') or {}
            shown = self.approved(row)
            self.assertEqual(shown['title'], tags['title'], name)
            if review:
                self.assertEqual(review['title'], tags['title'], name)
                self.assertNotIn(name.split(' - ')[1] + ' - ', self.goes_to(row, result), 'no author before the title in the file name')
            for wrong in ('Недоруб - ', 'Каплан - ', 'Ясинская - ', 'Пылаев - ', ')', '('):
                self.assertNotIn(wrong, shown['title'], name)

    def test_the_title_read_from_a_name_drops_the_people_before_it_and_unbalanced_brackets(self):
        read = lambda relative: local_identity.folder_structure({'members': [{'path': ROOT + '\\' + relative, 'filename': Path(relative).name}]}, ROOT)
        expected = {'16': 'Севастопольский дозор', '19': 'Масть', '25': 'Чужой Дозор', '27': 'Запах Сумрака', '05': 'Печать сумрака'}
        for name, _ in self.LIVE:
            found = read(self.DOZORY + name)
            # Rulings 30 and 37 (Sergei 2026-10-26): the universe «Вселенная Дозоров» and its one numbered series «Межавторский цикл».
            self.assertEqual((found['title'], found['position'], found['universe'], found['series']),
                             (expected[name[:2]], str(int(name[:2])), 'Вселенная Дозоров', 'Межавторский цикл'), name)
        # With no title tag the name is the only source: the clean title, never the author or a dangling bracket.
        row = next(iter(self.catalog([file_row(self.DOZORY + self.LIVE[2][0], artist='Мария Ясинская')]).values()))
        self.assertEqual(self.approved(row)['title'], 'Чужой Дозор')
        # Controls: a title that is no person keeps its dash ("Книга Крови - Том 4" kept its series name above); a title
        # that only starts with a word that is a first name stays whole.
        self.assertEqual(read('Clive Barker\\Books of Blood\\3. Сын целлулоида - Ревущий мясник.m4b')['title'], 'Сын целлулоида - Ревущий мясник')
        self.assertEqual(read('Clive Barker\\Books of Blood\\3. Мария - Ревущий мясник.m4b')['title'], 'Мария - Ревущий мясник', 'one word is no person here')

    def test_a_book_folder_under_its_author_is_no_series_and_the_file_part_number_is_no_title(self):
        # Live: "James S. A. Corey\5. Игры Немезиды\5. Игры Немезиды 1.m4b" (one 16 h file); c26bc58 read series «5. Игры
        # Немезиды» #5 and filed it under "Corey James S. A\5. Игры Немезиды\5. Игры Немезиды - 5 - …".
        live = 'James S. A. Corey\\5. Игры Немезиды\\5. Игры Немезиды 1.m4b'
        tags = dict(title='Игры Немезиды', artist='Джеймс Кори', album='Игры Немезиды', genre='Speech', date='2018', album_artist='Кирилл Головин')
        self.assertIsNone(local_identity.folder_structure({'members': [{'path': ROOT + '\\' + live, 'filename': Path(live).name}]}, ROOT))
        row = next(iter(self.catalog([file_row(live, **tags)]).values()))
        result = self.lookup(row)
        review = result.get('review') or {}
        self.assertFalse(review.get('series') or review.get('number'), 'no series from a book folder')
        if review:
            self.assertNotIn('\\5. Игры Немезиды\\', self.goes_to(row, result))
        # Backlog item 10(b) (a single file is a whole book unless real sibling parts exist), as Jane applied it on
        # 2026-10-26: alone in a folder that names the book without the number, it is the whole book, never "set name +
        # number" (0.22.0 and c26bc58 both said «Игры Немезиды 1»).
        self.assertEqual(self.approved(row)['title'], 'Игры Немезиды')
        self.assertEqual((result['reasons'], review.get('title')), ([], 'Игры Немезиды'))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Corey James S. A\\Игры Немезиды - Corey James S. A.m4b')
        # Without a tag the name is read the same way.
        row = next(iter(self.catalog([file_row(live, artist='Джеймс Кори')]).values()))
        self.assertEqual(self.approved(row)['title'], 'Игры Немезиды')
        # Controls, rulings 13 and 15 unchanged: a sibling part beside it, a folder that does not name the book, a volume.
        books = self.catalog([file_row('James S. A. Corey\\Разное\\Игры Немезиды 1.m4b', **tags)])
        self.assertEqual(self.approved(next(iter(books.values())))['title'], 'Игры Немезиды 1', 'the folder names no book')
        books = self.catalog([file_row('Takemiya Yuyuko\\Торадора!\\Торадора! Том 5.m4b', title='Торадора!', album='Торадора!', artist='Такэмия Ююко')])
        self.assertEqual(self.approved(next(iter(books.values())))['title'], 'Торадора! 5', 'a volume keeps its number (ruling 13)')
        # Files beside it (two parts in one folder group as one book, held to be joined; ruling 19), or siblings not read:
        # never a whole book by this rule.
        lone = {'members': [{'path': ROOT + '\\' + live, 'filename': Path(live).name}]}
        self.assertEqual(local_identity.whole_in_book_folder(lone, []), 'Игры Немезиды')
        self.assertEqual(local_identity.whole_in_book_folder(lone, [{'filename': '5. Игры Немезиды 2.m4b', 'tags': {}}]), '')
        self.assertEqual(local_identity.whole_in_book_folder(lone, None), '')
        # The Expanse #5 (Sergei and Jane, 2026-10-26): the series comes from the series lookup after conversion, never from
        # the folder, which gives only the position. The converted book has no series, so series backfill takes it up
        # (candidates: no series, a title and an author), and its Goodreads lookup, with the answers Goodreads gave on
        # 2026-10-26 (search: the Russian edition «Игры Немезиды (Пространство, #5)», a translator among the credits; its
        # book page: series The Expanse, #5), supplies The Expanse #5. The rename then files it as below; the English
        # title «Nemesis Games» is the later rename pass's (rulings 16 and 21).
        from metadata import propose
        from test_series_research import Sources, book_page, search_page
        row = next(iter(self.catalog([file_row(live, **tags)]).values()))
        result = self.lookup(row)
        review = dict(result['review'], organization_policy='books-hierarchy-v2')  # as the job's manifest carries it
        self.assertEqual((review['title'], review['canonical_author'], review.get('series', '')), ('Игры Немезиды', 'Corey James S. A.', ''), 'a series backfill candidate')
        self.assertEqual(propose('', SORTED, 'audiobook', {}, review, automatic_facts=result.get('metadata_facts'))['path'],
                         SORTED + '\\Corey James S. A\\Игры Немезиды - Corey James S. A.m4b', 'converted first under its own name')
        sources = Sources()
        sources.goodreads_search = search_page(('42482205', 'Игры Немезиды (Пространство, #5)', ['James S.A. Corey', 'Джеймс Кори', 'Галина Соловьева']))
        sources.goodreads_books['42482205'] = book_page('42482205', 'Игры Немезиды', ['James S.A. Corey', 'Джеймс Кори'], 'The Expanse', '5')
        hours = iter(range(10 ** 6, 10 ** 9, 3600))  # each request an hour after the last: no real pacing wait in a test
        research = PublicResearch(PublicClient(str(Path(self.research.client.database).parent / 'series.sqlite3'), fetch=sources.fetch, clock=lambda: next(hours)), leads=[])
        found = research._series_goodreads(review['title'], review['canonical_author'], threading.Event(), {'remaining': 6, 'lane': 'series'}, {'sources': []})
        self.assertEqual((found['name'], found['number']), ('The Expanse', '5'))
        facts = dict(result.get('metadata_facts') or {}, series_state='verified')  # series backfill's own step (SeriesBackfill.apply)
        renamed = propose('', SORTED, 'audiobook', {}, dict(review, series=found['name'], number=found['number']), automatic_facts=facts)
        self.assertEqual(renamed['path'], SORTED + '\\Corey James S. A\\The Expanse\\The Expanse - 5 - Игры Немезиды - Corey James S. A.m4b')
        # Positive control: under the old title «Игры Немезиды 1» Goodreads' edition is no match, so no series came.
        self.assertIsNone(research._series_goodreads('Игры Немезиды 1', review['canonical_author'], threading.Event(), {'remaining': 6, 'lane': 'series'}, {'sources': []}))
        # A bitrate is no part number: "Антитела 128" alone in "Антитела" is still asked (Q3), never cut to «Антитела».
        bitrate = {'members': [{'path': ROOT + '\\Unsorted\\Антитела\\Антитела 128.mp3', 'filename': 'Антитела 128.mp3'}]}
        self.assertEqual(local_identity.whole_in_book_folder(bitrate, []), '')
        # The same file in a real series folder is book 5 of the series, a whole book: series and number from the folders,
        # the title from the tag, never the file's part number.
        row = next(iter(self.catalog([file_row('James S. A. Corey\\The Expanse\\5. Игры Немезиды 1.m4b', **tags)]).values()))
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), ('Игры Немезиды', 'The Expanse', '5'))
        # Other book folders named the same way under their author on the live drive.
        for relative in ('Joe Hill\\930. Коробка в форме сердца (Михаил Прокопов)\\Коробка в форме сердца.m4b',
                         'Harry Potter\\62. Книга 1 - Гарри Поттер и философский камень (Александр Клюквин)\\Джоан Роулинг - Книга 1 - Гарри Поттер и философский камень.m4b'):
            self.assertIsNone(local_identity.folder_structure({'members': [{'path': ROOT + '\\' + relative, 'filename': Path(relative).name}]}, ROOT), relative)

    def test_a_lone_volume_in_its_set_folder_keeps_its_number(self):
        # Senua's 0.22.1 review, W14: "Торадора!\Торадора! 6.m4b" became the whole book «Торадора!» because the set's folder
        # is named like the file without its number. Only a folder that carries the book's position is the book's own folder.
        for tags in (dict(title='Торадора!', album='Торадора!', artist='Такэмия Ююко'), dict(title='Торадора! 6', album='Торадора! 6', artist='Такэмия Ююко')):
            row = next(iter(self.catalog([file_row('Takemiya Yuyuko\\Торадора!\\Торадора! 6.m4b', **tags)]).values()))
            result = self.lookup(row)
            self.assertEqual(self.approved(row)['title'], 'Торадора! 6', tags)
            self.assertEqual(self.goes_to(row, result), SORTED + '\\Takemiya Yuyuko\\Торадора! 6 - Takemiya Yuyuko.m4b', tags)
        row = next(iter(self.catalog([file_row('Анджей Сапковский\\Ведьмак\\Ведьмак 3.m4b')]).values()))
        self.assertEqual(self.approved(row)['title'], 'Ведьмак 3')
        lone = lambda relative: {'members': [{'path': ROOT + '\\' + relative, 'filename': Path(relative).name}]}
        self.assertEqual(local_identity.whole_in_book_folder(lone('Takemiya Yuyuko\\Торадора!\\Торадора! 6.m4b'), []), '')
        # Controls: the book's own folder by its position, or an uploader number with a reader.
        self.assertEqual(local_identity.whole_in_book_folder(lone('James S. A. Corey\\5. Игры Немезиды\\5. Игры Немезиды 1.m4b'), []), 'Игры Немезиды')
        self.assertEqual(local_identity.whole_in_book_folder(lone('Joe Hill\\930. Коробка в форме сердца (Михаил Прокопов)\\Коробка в форме сердца 1.m4b'), []), 'Коробка в форме сердца')

    def test_a_title_with_a_dash_keeps_what_is_no_credit_of_this_book(self):
        # Senua's 0.22.1 review, W15: with no title tag, «Сын целлулоида - Ревущий мясник» lost its first half (the file-name
        # reading takes "X - Y" for "Author - Title"). W8: a person who is not the book's author («Жозеф Фуше», the subject
        # of a biography tagged Стефан Цвейг) was stripped as a credit.
        for tags in ({}, dict(artist='Clive Barker')):
            row = next(iter(self.catalog([file_row('Clive Barker\\Books of Blood\\3. Сын целлулоида - Ревущий мясник.m4b', **tags)]).values()))
            result = self.lookup(row)
            self.assertEqual(self.approved(row)['title'], 'Сын целлулоида - Ревущий мясник', tags)
            self.assertEqual(self.goes_to(row, result), SORTED + '\\Barker Clive\\Books of Blood\\Books of Blood - 3 - Сын целлулоида - Ревущий мясник - Barker Clive.m4b', tags)
        row = next(iter(self.catalog([file_row('Стефан Цвейг\\Биографии\\03 - Жозеф Фуше - Портрет политического деятеля.m4b', artist='Стефан Цвейг')]).values()))
        self.assertEqual(self.approved(row)['title'], 'Жозеф Фуше - Портрет политического деятеля')
        # 0.24.0: «Стефан Цвейг» (a first name the app does not know) is asked its English spelling first (ruling 39); the
        # title the question proposes is the same.
        result = self.lookup(row)
        self.assertEqual((result.get('review') or {}).get('title') or result['ask']['fields']['title']['proposal'], 'Жозеф Фуше - Портрет политического деятеля')
        # The book's own author or a known reader before the title is still a credit (W1): the author tag, a slip in the
        # first name aside (live: "Марина Ясинская" tagged "Мария Ясинская"), the reader of this book, and with no author tag
        # the person the file name credits.
        read = lambda relative, **tags: local_identity.folder_structure({'members': [{'path': ROOT + '\\' + relative, 'filename': Path(relative).name,
                                                                                      'metadata': {'tags': tags}}]}, ROOT)['title']
        self.assertEqual(read(self.DOZORY + self.LIVE[2][0], artist='Мария Ясинская'), 'Чужой Дозор')
        self.assertEqual(read('Clive Barker\\Books of Blood\\3. Игорь Князев - Ревущий мясник.m4b', artist='Clive Barker', narrator='Игорь Князев'), 'Ревущий мясник')
        self.assertEqual(read('Clive Barker\\Books of Blood\\3. Игорь Князев - Ревущий мясник.m4b', artist='Clive Barker'), 'Игорь Князев - Ревущий мясник')
        self.assertEqual(read(self.DOZORY + self.LIVE[0][0]), 'Севастопольский дозор')


class OddNameTests(Base):
    """0.22.1 (Jane for Sergei, 2026-10-26): the live books that items 9 and 10 let through with odd names are asked, never
    filed by themselves. Each becomes a question on the to-do list with the existing rows (Title or author missing,
    Author unclear); nothing is renamed by the app, and Sergei's Approve still files what the row shows."""

    def book(self, folder, names, **tags):
        rows = [file_row(folder + '\\' + name, **{k: (v % n if isinstance(v, str) and '%' in v else v) for k, v in tags.items()}) for n, name in enumerate(names, 1)]
        return self.catalog(rows)[ROOT + '\\' + folder]

    def asked(self, row, kind, why):
        result = self.lookup(row)
        self.assertTrue(result['reasons'], 'held, never filed by itself')
        self.assertEqual((result['ask']['kind'], result['ask']['why']), (kind, why))
        self.assertIs(result['ask'].get('odd_name'), True, 'marked, so the page keeps it out of bulk Approve as is')
        return result

    def test_a_bitrate_in_the_title_is_asked(self):
        row = self.book('Кевин Андерсон - Антитела-128', ['Anderson_Antitela_%02d.mp3' % n for n in (1, 2, 3)],
                        title='Anderson_Antitela_%02d', artist='Кевин Андерсон', album='Антитела 128', track='%d')
        result = self.asked(row, 'title_author', 'title_bitrate')
        self.assertEqual(result['ask']['fields']['title']['proposal'], 'Антитела 128', 'nothing renamed: the row shows what the app read')
        self.assertEqual(result['reasons'], ['Title or author missing'])
        self.assertEqual(self.approved(row)['title'], 'Антитела 128', "Sergei's Approve still files what the row shows")

    def test_two_people_in_one_author_are_asked_with_each_as_a_choice(self):
        # Good Omens as it is on the drive: 177 files over CDs, each CD's files numbered from 1, the album naming the CD.
        rows = [file_row("Niel Gaiman\\Good Omens\\Neil Gaiman &Terry Pratchett   - ''GOOD OMENS'' CD%d - %02d - unknown title.m4a" % (cd, n),
                         artist='Neil Gaiman &Terry Pratchett  ', album='"GOOD OMENS" CD%d' % cd, track='%d' % n) for cd in (1, 2) for n in (1, 2)]
        row = self.catalog(rows)[ROOT + '\\Niel Gaiman\\Good Omens']
        result = self.asked(row, 'author_unclear', 'two_people')
        self.assertEqual([c['name'] for c in result['ask']['candidates']][:2], ['Neil Gaiman', 'Terry Pratchett'])
        row = self.book('William Gibson\\Gibson_i _Sterling_-_Mashina_razlichiy_-_Kirsanov Sergei', ['Гибсон Уильям, Стерлинг Брюс - Машина различий - %02d - unknown title.m4a' % n for n in (1, 2)],
                        artist=' Гибсон Уильям, Стерлинг Брюс', album='Машина различий', track='%d/-1')
        result = self.asked(row, 'author_unclear', 'two_people')
        self.assertEqual([c['name'] for c in result['ask']['candidates']][:2], ['Гибсон Уильям', 'Стерлинг Брюс'])
        row = self.book('Сергей Лукьяненко\\Лукьяненко Сергей, Громов Александр - Реверс (Владимир Маслаков)', ['01-0%d.mp3' % n for n in (1, 2)],
                        title='Глава 1-0%d', artist='С. Лукьяненко, А. Громов', album='Реверс', album_artist='Владимир Маслаков', track='%d/49')
        self.asked(row, 'author_unclear', 'two_people')

    def test_a_folder_name_with_underscores_is_never_the_author(self):
        # The live row: the tags credit «Ричард Форд». Futaba's 0.22.1 QA, M-2: the folder name won the one-spelling vote as
        # that credit's "local English spelling", so the row was asked and the book filed under "Richard_Ford_Labirint"
        # whatever the answer. A name with underscores is no spelling of a person: the clean credit files the book by
        # itself, as any clean tag credit does (ruling 6; Q3 asks only when the name the app would file is odd).
        row = self.book('Sbornik_Astronomikon\\Richard_Ford_Labirint\\Mp3', ['Ричард Форд - Лабиринт - %02d - unknown title.m4a' % n for n in (1, 2)],
                        title='Лабиринт', artist='Ричард Форд', album='Лабиринт', track='%d/-1')
        result = self.lookup(row)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Форд Ричард\\Лабиринт - Форд Ричард.m4b')
        # The folder name the only credit: asked, the name without underscores proposed, and Approve as is files what the
        # Author field shows (Judy 11.3), never the underscores.
        row = self.book('Unsorted\\Richard_Ford - Labirint', ['%02d.m4a' % n for n in (1, 2)], title='Лабиринт', album='Лабиринт', track='%d')
        result = self.asked(row, 'title_author', 'author_folder')
        # Ruling 33 (Sergei 2026-10-26): proposed surname first, as the library files it.
        self.assertEqual(result['ask']['fields']['author']['proposal'], 'Ford Richard', 'the credit is offered, Sergei confirms')
        self.assertEqual(self.approved(row)['author'], 'Richard Ford')
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT)), SORTED + '\\Ford Richard\\Лабиринт - Ford Richard.m4b')

    def test_the_author_sergei_confirms_on_the_underscore_row_decides_where_it_goes(self):
        # Futaba's 0.22.1 QA, M-2: on this row the Author field offered «Ричард Форд», yet with nothing typed, «Ричард Форд»
        # or «Форд Ричард» typed, the Goes to line and the converted book were "Richard_Ford_Labirint\Лабиринт -
        # Richard_Ford_Labirint.m4b": the one-spelling-per-person vote (ruling 3) took the junk folder name as the
        # person's local English spelling. His answer is final (rulings 6a, 6b, 12), Cyrillic included.
        row = self.book('Sbornik_Astronomikon\\Richard_Ford_Labirint\\Mp3', ['Ричард Форд - Лабиринт - %02d - unknown title.m4a' % n for n in (1, 2)],
                        title='Лабиринт', artist='Ричард Форд', album='Лабиринт', track='%d/-1')
        for typed, folder in ((None, 'Форд Ричард'), ('Ричард Форд', 'Форд Ричард'), ('Форд Ричард', 'Форд Ричард'), ('Richard Ford', 'Ford Richard')):
            result = self.research.approved(row, ROOT, author=typed)
            path = self.goes_to(row, result)
            self.assertEqual(path, SORTED + '\\%s\\Лабиринт - %s.m4b' % (folder, folder), typed)
            self.assertNotIn('_', path, typed)
        # Through Sergei's author rules like a tag (ruling 12, Senua's 0.22.0 m2): a same_as rule decides the folder.
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db, 'same_as', 'Ричард Форд', target='Ford Richard', source='test')
            db.commit()
        self.assertEqual(self.goes_to(row, self.research.approved(row, ROOT, author='Ричард Форд')), SORTED + '\\Ford Richard\\Лабиринт - Ford Richard.m4b')

    def test_a_series_and_number_in_the_name_are_split_asked_filled_in_and_filed_once_confirmed(self):
        # Ruling 41 (Sergei 2026-10-27, "2. Yes"): "Series N. Title" fills Series, Number and Title; the series never stays
        # in the title. Ruling 52 (Sergei 2026-10-27, "a") narrows it: the book files by itself only when something confirms
        # the series; until then the row asks with the split filled in, and Approve files it. The ":" Windows refuses in a
        # folder or file name is the path's "_" (metadata.safe_name), the tags keep it.
        cases = (('Unsorted\\Джеймс Герберт - Крысы 1. Крысы', ['%02d.mp3' % n for n in (1, 2)], dict(title='Глава %d', artist='Джеймс Герберт', album='Крысы 1. Крысы', track='%d'),
                  ('Крысы', 'Крысы', '1'), 'Герберт Джеймс\\Крысы\\Крысы - 1 - Крысы - Герберт Джеймс.m4b'),
                 ('Unsorted\\Дивов Олег\\Профессия_ инквизитор 1. Леди не движется', ['%02d.mp3' % n for n in (1, 2)], dict(title='Глава %d', artist='Олег Дивов', album='Профессия: инквизитор 1. Леди не движется', track='%d'),
                  ('Леди не движется', 'Профессия: инквизитор', '1'), 'Дивов Олег\\Профессия_ инквизитор\\Профессия_ инквизитор - 1 - Леди не движется - Дивов Олег.m4b'),
                 ('Max Fray\\Сновидения Эхо\\Frai_Maks_Vsya_pravda_o_nas (Ovuor)', ['Макс Фрай - Сновидения Ехо #3 - Вся правда о нас  - %02d - %02d - Maks Frai - Vsya pravda o nas - (Ovuor).m4a' % (n, n) for n in (1, 2)],
                  dict(title='%02d - Maks Frai - Vsya pravda o nas - (Ovuor)', artist='Макс Фрай', album='Сновидения Ехо #3 - Вся правда о нас ', track='%d'), ('Вся правда о нас', 'Сновидения Ехо', '3'), None),
                 ('Max Fray\\Сновидения Эхо\\Макс Фрай_Мертвый ноль_Гмыза Игорь', ['Макс Фрай - Мертвый ноль 7. Мертвый ноль - %02d - %02d.m4a' % (n, n) for n in (1, 2)],
                  dict(title='%02d', artist='Макс Фрай', album='Мертвый ноль 7. Мертвый ноль', track='%d/-1'), ('Мертвый ноль', 'Мертвый ноль', '7'), None),
                 ('Unsorted\\Дивов. Профессия инквизитор\\7\\Олег Дивов_ Война миров_Ирина Зубкова', ['%02d  Война миров.mp3' % n for n in (0, 1)],
                  dict(title='Глава %d', artist='Олег Дивов', album='Профессия: инквизитор 7. Война миров', album_artist='И. Зубкова', track='%d'), ('Война миров', 'Профессия: инквизитор', '7'), None),
                 ('Unsorted\\Шваб Виктория - Сотворение света (Иванов_С)', ['01_Razrushennyy mir.mp3', '02_Razrushennyy mir.mp3'],
                  dict(title='Глава %d', artist='Виктория Шваб', album='Оттенки магии 03. Сотворение света', track='%d'), ('Сотворение света', 'Оттенки магии', '3'), None))
        for folder, names, tags, (title, series, number), path in cases:
            with self.subTest(folder=folder):
                row = self.book(folder, names, **tags)
                self.split_asked(row, series, number, title)
                self.assertEqual(self.approved(row)['title'], title, 'the row and Approve show the split title')
                if path:
                    self.assertEqual(self.approved_to(row), SORTED + '\\' + path, 'Approve files the split')
                # Confirmed: a book of the series already in Sorted under this author files it by itself.
                self.in_sorted(series, self.research.approved(row, ROOT)['review']['author'])
                result = self.lookup(row)
                self.assertEqual((result['reasons'], result.get('ask')), ([], None))
                self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), (title, series, number))
                if path:
                    self.assertEqual(self.goes_to(row, result), SORTED + '\\' + path)
        # Controls: a word that only numbers a part is no series; a name without the pattern is untouched.
        self.assertIsNone(local_identity.series_title_parts('Книга 1. Начало'))
        self.assertIsNone(local_identity.series_title_parts('Warhammer 40000. Месть Гоббо'))
        self.assertIsNone(local_identity.series_title_parts('Комната ужасов 2'))
        self.assertEqual(local_identity.series_title_parts('Колесо времени - 01. Око мира'), {'series': 'Колесо времени', 'number': '1', 'title': 'Око мира'})
        self.assertEqual(local_identity.series_title_parts('Робин Хобб - Сага о Видящих 2. Королевский убийца', 'Робин Хобб'),
                         {'series': 'Сага о Видящих', 'number': '2', 'title': 'Королевский убийца'})

    def test_sibling_folders_decide_the_series_and_one_series_has_one_spelling(self):
        # Rulings 45 and 46 (Sergei 2026-10-27), the live folder Max Fray\Сновидения Эхо: «Мертвый ноль 7. Мертвый ноль» is
        # book 7 of «Сновидения Ехо», the series its sibling folders carry, not series «Мертвый ноль»; «Сновидения Эхо 2» and
        # «Сновидения Ехо #3» are one series, filed «Сновидения Ехо».
        parent = 'Max Fray\\Сновидения Эхо\\'
        books = [('Frai_Maks_Slishkom_mnogo_koshmarov (Ovuor)', 'Сновидения Эхо 2 - Слишком много кошмаров'), ('Frai_Maks_Vsya_pravda_o_nas (Ovuor)', 'Сновидения Ехо #3 - Вся правда о нас '),
                 ('Frai_Maks_Ya_idu_iskat (Ovuor)', 'Сновидения Ехо #4 - Я иду искать'), ('Макс Фрай_Сундук мертвеца_Валерий Смекалов', 'Сновидения Ехо 5. Сундук мертвеца'),
                 ('Макс Фрай_Мертвый ноль_Гмыза Игорь', 'Мертвый ноль 7. Мертвый ноль')]
        rows = [file_row(parent + folder + '\\%02d.m4a' % n, title='%02d' % n, artist='Макс Фрай', album=album, track='%d/-1' % n) for folder, album in books for n in (1, 2)]
        catalog = self.catalog(rows)
        zero = catalog[ROOT + '\\' + parent + 'Макс Фрай_Мертвый ноль_Гмыза Игорь']
        # Senua's 0.22.3 review, m22: the siblings' «Сновидения Ехо» is itself unconfirmed (their set asks, ruling 53), so
        # «Мертвый ноль» asks with it filled in; once Sorted holds «Сновидения Ехо» (his Approve of the set), it files.
        self.split_asked(zero, 'Сновидения Ехо', '7', 'Мертвый ноль')
        self.assertEqual(self.approved_to(zero), SORTED + '\\Фрай Макс\\Сновидения Ехо\\Сновидения Ехо - 7 - Мертвый ноль - Фрай Макс.m4b')
        two = catalog[ROOT + '\\' + parent + 'Frai_Maks_Slishkom_mnogo_koshmarov (Ovuor)']
        self.split_asked(two, 'Сновидения Ехо', '2', 'Слишком много кошмаров')  # ruling 53, in the one spelling (ruling 46)
        self.in_sorted('Сновидения Ехо', 'Фрай Макс')
        result = self.lookup(zero)
        self.assertEqual((result['reasons'], result['review']['title'], result['review']['series'], result['review']['number']), ([], 'Мертвый ноль', 'Сновидения Ехо', '7'))
        self.assertEqual(self.goes_to(zero, result), SORTED + '\\Фрай Макс\\Сновидения Ехо\\Сновидения Ехо - 7 - Мертвый ноль - Фрай Макс.m4b')
        result = self.lookup(two)
        self.assertEqual((result['reasons'], result['review']['series'], result['review']['number']), ([], 'Сновидения Ехо', '2'), 'the set follows')
        # Controls: alone, the name decides (no sibling says otherwise), asked filled in until confirmed (ruling 52); a
        # sibling already holding the number is another series.
        alone = self.catalog([file_row(parent + 'Макс Фрай_Мертвый ноль_Гмыза Игорь\\%02d.m4a' % n, title='%02d' % n, artist='Макс Фрай', album='Мертвый ноль 7. Мертвый ноль', track='%d/-1' % n) for n in (1, 2)])
        self.split_asked(next(iter(alone.values())), 'Мертвый ноль', '7', 'Мертвый ноль')
        other = 'Иванов Петр\\Разное\\'
        rows = [file_row(other + folder + '\\%02d.mp3' % n, title='%02d' % n, artist='Петр Иванов', album=album, track='%d' % n)
                for folder, album in (('a', 'Серия А 1. Первая'), ('b', 'Серия А 2. Вторая'), ('c', 'Серия Б 1. Третья')) for n in (1, 2)]
        catalog = self.catalog(rows)
        self.split_asked(catalog[ROOT + '\\' + other + 'c'], 'Серия Б', '1', 'Третья')  # Серия А already has a book 1: not this series
        # Senua's 0.22.3 review, M2 (ruling 45 as worded): a name that names another series keeps it, number free or not.
        rows = [file_row(other + folder + '\\%02d.mp3' % n, title='%02d' % n, artist='Петр Иванов', album=album, track='%d' % n)
                for folder, album in (('a', 'Серия А 1. Первая'), ('b', 'Серия А 2. Вторая'), ('d', 'Серия Б 3. Третья')) for n in (1, 2)]
        catalog = self.catalog(rows)
        self.split_asked(catalog[ROOT + '\\' + other + 'd'], 'Серия Б', '3', 'Третья')
        self.assertEqual(self.approved_to(catalog[ROOT + '\\' + other + 'd']), SORTED + '\\Иванов Петр\\Серия Б\\Серия Б - 3 - Третья - Иванов Петр.m4b')
        # Senua's 0.22.3 review, m4: the split's misfires are not split; a padded half number is the folder's form.
        for name in ('Война и мир. Том 1. Часть 2', 'Apollo 13: The Untold Story', 'Агент 007 - Казино Рояль'):
            self.assertIsNone(local_identity.series_title_parts(name), name)
        self.assertEqual(local_identity.series_title_parts('Ведьмак 01.5. Меч'), {'series': 'Ведьмак', 'number': '1.5', 'title': 'Меч'})
        self.assertTrue(local_identity._same_number('01.5', '1.5'))
        self.assertEqual(local_identity.series_title_parts('Сновидения Ехо #3 - Вся правда о нас'), {'series': 'Сновидения Ехо', 'number': '3', 'title': 'Вся правда о нас'}, 'positive control')

    def test_m12_a_colon_a_padded_number_or_a_part_word_still_split_and_the_misfires_do_not(self):
        # Senua's 0.22.3 review, m12: the m4 fix also stopped "Series N: Title", "Series 00N. Title" and "Cycle. Книга N.
        # Title": those books filed with the series inside the title, the shape ruling 41 removed.
        splits = (('Гарри Поттер 1: Философский камень', ('Философский камень', 'Гарри Поттер', '1'), 'Иванов Петр\\Гарри Поттер\\Гарри Поттер - 1 - Философский камень - Иванов Петр.m4b'),
                  ('Перри Родан 001. Звездная пыль', ('Звездная пыль', 'Перри Родан', '1'), 'Иванов Петр\\Перри Родан\\Перри Родан - 1 - Звездная пыль - Иванов Петр.m4b'),
                  ('Хроники Амбера. Книга 1. Девять принцев Амбера', ('Девять принцев Амбера', 'Хроники Амбера', '1'), 'Иванов Петр\\Хроники Амбера\\Хроники Амбера - 1 - Девять принцев Амбера - Иванов Петр.m4b'),
                  ('Ведьмак 3: Кровь эльфов', ('Кровь эльфов', 'Ведьмак', '3'), None),
                  ('Конан 005 - Час дракона', ('Час дракона', 'Конан', '5'), None))
        for album, (title, series, number), path in splits:
            with self.subTest(album=album):
                # Ruling 52: asked with the split filled in, and filed by itself once Sorted holds the series.
                row = self.book('Unsorted\\Петр Иванов - ' + album.replace(':', '_'), ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Петр Иванов', album=album, track='%d')
                self.split_asked(row, series, number, title)
                self.in_sorted(series, 'Иванов Петр')
                result = self.lookup(row)
                self.assertEqual((result['reasons'], result.get('ask')), ([], None))
                self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), (title, series, number))
                if path:
                    self.assertEqual(self.goes_to(row, result), SORTED + '\\' + path)
        self.assertEqual(local_identity.series_title_parts('Dune 2: Dune Messiah'), {'series': 'Dune', 'number': '2', 'title': 'Dune Messiah'})
        # Ruling 51: «Черная книга 2» and "Star Wars Episode 4" end their series name in a marker word: asked (M6 test).
        # The misfires m4 stopped stay unsplit: a code number files as it is, a part of one work is never a series book,
        # and a two-digit number before ":" ("Apollo 13: The Untold Story") may be the title's own: it is asked.
        for name in ('Война и мир. Том 1. Часть 2', 'Apollo 13: The Untold Story', 'Агент 007 - Казино Рояль'):
            self.assertIsNone(local_identity.series_title_parts(name), name)
        row = self.book('Unsorted\\Петр Иванов - Агент 007 - Казино Рояль', ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Петр Иванов', album='Агент 007 - Казино Рояль', track='%d')
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result['review']['title'], result['review']['series']), ([], 'Агент 007 - Казино Рояль', ''))
        self.assertEqual(self.goes_to(row, result), SORTED + '\\Иванов Петр\\Агент 007 - Казино Рояль - Иванов Петр.m4b')
        row = self.book('Unsorted\\Jim Lovell - Apollo 13_ The Untold Story', ['%02d.mp3' % n for n in (1, 2)], title='Chapter %d', artist='Jim Lovell', album='Apollo 13: The Untold Story', track='%d')
        result = self.asked(row, 'title_author', 'title_series')
        self.assertEqual(result['ask']['fields']['title']['proposal'], 'Apollo 13: The Untold Story', 'nothing renamed')
        row = self.book('Unsorted\\Лев Толстой - Война и мир. Том 1. Часть 2', ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Лев Толстой', album='Война и мир. Том 1. Часть 2', track='%d')
        result = self.lookup(row)
        self.assertNotEqual(((result.get('review') or {}).get('series'), (result.get('review') or {}).get('title')), ('Война и мир', 'Часть 2'), 'never series «Война и мир», book 1')

    def warhammer(self, album):
        row = self.book('Unsorted\\Петр Иванов - ' + album.replace(':', '_'), ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Петр Иванов', album=album, track='%d')
        return row, self.lookup(row)

    def test_m5_a_thousands_group_is_one_number_never_series_warhammer_40_book_0(self):
        # Senua's 0.22.3 review, M5: «Warhammer 40 000: …» split at its last digit group and filed silently as
        # `Warhammer 40\Warhammer 40 - 0 - …`, the series «Warhammer 40», book 0. Russian editions write the setting so.
        for album in ('Warhammer 40 000. Ересь Хоруса', 'Warhammer 40 000 - Ересь Хоруса', 'Warhammer 40,000: Dawn of War',
                      'Вселенная Warhammer 40 000: Кайафас Каин. Герой Империума'):
            with self.subTest(album=album):
                row, result = self.warhammer(album)
                self.assertEqual((result['review']['title'], result['review']['series'], result['review']['number']), (album, '', ''), 'filed as it is named')
                self.assertEqual((result['reasons'], result.get('ask')), ([], None))
                self.assertEqual(self.goes_to(row, result), SORTED + '\\Иванов Петр\\' + album.replace(':', '_') + ' - Иванов Петр.m4b')
        # Its own series and number come after the setting: not sure which is the series, so it is asked, never filed in «Warhammer 40».
        with self.subTest(album='Warhammer 40 000: Ересь Хоруса. Книга 1. Возвышение Хоруса'):
            row, result = self.warhammer('Warhammer 40 000: Ересь Хоруса. Книга 1. Возвышение Хоруса')
            self.assertEqual(((result.get('ask') or {}).get('kind'), (result.get('ask') or {}).get('why')), ('title_author', 'title_series'), (result.get('review') or {}).get('series'))
            self.assertEqual(result['ask']['fields']['title']['proposal'], 'Warhammer 40 000: Ересь Хоруса. Книга 1. Возвышение Хоруса', 'nothing renamed')
        for name in ('Warhammer 40 000: Ересь Хоруса', 'Warhammer 40 000 - 1. Ересь', 'Ведьмак 0. Дорога без возврата'):
            self.assertIsNone(local_identity.series_title_parts(name), name)
        self.assertEqual(local_identity._series_split('Ведьмак 0. Дорога без возврата')[1], 'ask', 'never position 0 by the name alone: asked')
        self.assertEqual(local_identity.series_title_parts('Ведьмак 1. Последнее желание'), {'series': 'Ведьмак', 'number': '1', 'title': 'Последнее желание'}, 'positive control')

    def test_ruling_50_a_disc_volume_part_or_chapter_is_a_part_of_one_book_never_a_series_number(self):
        # Ruling 50 (Sergei 2026-10-27, "A"; Senua's 0.22.3 review, m16): «Мастер и Маргарита. CD 1. Главы 1-10» filed as
        # `Мастер и Маргарита\Мастер и Маргарита - 1 - Главы 1-10`, series book 1.
        album = 'Мастер и Маргарита. CD 1. Главы 1-10'
        row = self.book('Unsorted\\Михаил Булгаков - ' + album, ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Михаил Булгаков', album=album, track='%d')
        result = self.lookup(row)
        self.assertNotEqual(((result.get('review') or {}).get('series'), (result.get('review') or {}).get('number')), ('Мастер и Маргарита', '1'))
        self.assertEqual(((result.get('review') or {}).get('title'), (result.get('review') or {}).get('series')), (album, ''), (result['reasons'], result.get('ask')))
        for name in (album, 'Мастер и Маргарита. Диск 2. Главы 11-20', 'Мастер и Маргарита CD 1. Главы 1-10', 'Отцы и дети. Глава 1. Приезд',
                     'Двенадцать стульев. Часть 1. Одиссея', 'Граф Монте-Кристо. Том 2. Узник замка Иф', 'Сага о Копье. Т. 3. Драконы',
                     'Война и мир. Том 1 - Аудиоспектакль', 'Kill Bill Vol 2. The Bride', 'Зеленая миля. Часть 2 - Мышь на миле'):
            self.assertIsNone(local_identity.series_title_parts(name), name)
        # A word that numbers a book still splits; one written into the series name is part of it.
        self.assertEqual(local_identity.series_title_parts('Ересь Хоруса. Книга 2. Лживые боги'), {'series': 'Ересь Хоруса', 'number': '2', 'title': 'Лживые боги'})
        self.assertEqual(local_identity.series_title_parts('The Wheel of Time, Book 3: The Dragon Reborn'), {'series': 'The Wheel of Time', 'number': '3', 'title': 'The Dragon Reborn'})

    def outcome(self, n, album, author='', filled=False, confirm=False):
        """How one name files end to end: ('split', series, number, title), ('whole', title), ('ask', why) or ('held', reasons).
        filled: an ask also gives the split it fills in; confirm: a split asked is looked up again once Sorted holds its
        series for the author Approve would file it under (ruling 52)."""
        row = self.book('Unsorted\\%03d' % n, ['%02d.mp3' % k for k in (1, 2)], title='Глава %d', artist=author or 'Петр Иванов', album=album, track='%d')
        result = self.lookup(row); ask = result.get('ask') or {}; review = result.get('review') or {}
        if confirm and ask.get('split'):
            self.in_sorted(ask['split']['series'], self.research.approved(row, ROOT)['review']['author'])
            result = self.lookup(row); ask = result.get('ask') or {}; review = result.get('review') or {}
        if ask:
            split = ask.get('split') or {}
            return ('ask', ask.get('why') or ask.get('kind')) + (((split.get('series'), split.get('number'), split.get('title')),) if filled else ())
        if review.get('series'):
            return ('split', review['series'], review.get('number'), review.get('title'))
        return ('whole', review.get('title')) if review else ('held', '; '.join(result.get('reasons') or []))

    def test_m6_a_series_name_that_is_not_clean_is_asked_never_filed_under_it(self):
        # Ruling 51 (Sergei 2026-10-27: "When unsure, ask; never guess a series"; Senua's 0.22.3 review, M6): a marker the
        # split's word lists did not hold stayed in the series name, and the book filed silently under a junk series
        # folder: "Harry Potter Book", «Хроники Амбера №», «Отцы и дети. Гл.», "Discworld No.", a Cyrillic «СD».
        for n, album in enumerate(RULING_51_M6):
            with self.subTest(album=album):
                self.assertEqual(self.outcome(n, album), ('ask', 'title_series'))
        # A marker word written into the series name is just as unsure: asked, never guessed.
        for n, album in enumerate(RULING_51_MARKER_IN_NAME, 50):
            with self.subTest(album=album):
                self.assertEqual(self.outcome(n, album), ('ask', 'title_series'))
        self.assertEqual(local_identity._skeleton('\u0421D'), local_identity._skeleton('CD'), 'look-alike letters are one letter')

    def test_ruling_51_every_other_name_keeps_how_it_filed_before(self):
        # Senua's pass-4 name hunt, rebuilt (98 names, end to end on 92376c7): every name kept whole stays whole, every
        # question stays a question, and every split stays the same split. Ruling 52: a split is asked with exactly those
        # values filled in until Sorted holds its series, then files by itself as before. m18: a title the split leaves
        # that starts with a number is asked either way.
        for n, (album, author, expected) in enumerate(RULING_51_KEPT, 100):
            with self.subTest(album=album):
                if author and local_identity.unknown_given(author):
                    # 0.24.0 (POST-023-01, rulings 39 and 59): a Cyrillic credit whose first name the app does not know
                    # («Робин Хобб») is looked up first; offline nothing is found, so its English spelling is asked.
                    self.assertEqual(self.outcome(n, album, author), ('ask', 'english_spelling'))
                    continue
                if album in RULING_52_M18:
                    self.assertEqual(self.outcome(n, album, author, confirm=True), ('ask', 'title_series'))
                elif expected[0] == 'split':
                    self.assertEqual(self.outcome(n, album, author, filled=True), ('ask', 'title_series', expected[1:]))
                    self.assertEqual(self.outcome(n, album, author, confirm=True), expected)
                else:
                    self.assertEqual(self.outcome(n, album, author), expected)

    def test_a_numbered_set_is_asked_once_and_its_first_approved_book_files_the_rest(self):
        # Measured on the live copy: the plain "<Series> N. Title" pattern alone asked 91 books, 31 of them «Червь», one-file
        # books side by side in one folder. Ruling 53 (Sergei 2026-10-28): a set that only confirms itself is asked; once
        # Sergei approves its first book (its series is then filed), the rest file by themselves. Ruling 55: the folder
        # named «Червь» confirms nothing.
        worm = [('Червь %d. %s' % (n, t), 'Червь %d. %s.m4b' % (n, t)) for n, t in ((1, 'Созревание'), (2, 'Насекомые'), (3, 'Порка'))]
        books = self.catalog([file_row('Червь\\' + name, title=album, artist='Джон МакКрэй', album=album) for album, name in worm])
        self.assertEqual(len(books), 3, 'positive control: three books')
        first, second = books[ROOT + '\\Червь\\Червь 1. Созревание.m4b'], books[ROOT + '\\Червь\\Червь 2. Насекомые.m4b']
        self.split_asked(first, 'Червь', '1', 'Созревание')
        self.split_asked(second, 'Червь', '2', 'Насекомые')
        self.in_sorted('Червь', self.research.approved(first, ROOT)['review']['author'])  # his Approve of the first book
        result = self.lookup(second)
        self.assertEqual((result['reasons'], result.get('ask'), result['review']['series'], result['review']['number'], result['review']['title']), ([], None, 'Червь', '2', 'Насекомые'))
        for folder, name, tags, split in (('Wheel of Time\\Колесо времени - 01. Око мира', 'Джордан Роберт (2013) - Колесо времени - 01. Око мира.m4b',
                                           dict(title='Колесо времени - 01. Око мира', artist='Джордан Роберт', album='Колесо времени - 01. Око мира'), ('Колесо времени', '1', 'Око мира')),
                                          ('Terry Pratchet\\Discworld\\City Watch', 'Discworld 19. Feet of Clay.m4b', dict(title='Discworld 19. Feet of Clay', artist='Terry Pratchett', album='Discworld 19. Feet of Clay'),
                                           ('Discworld', '19', 'Feet of Clay'))):
            self.split_asked(next(iter(self.catalog([file_row(folder + '\\' + name, **tags)]).values())), *split)
        # "40000" is no series 40 and book 000, though the folder names the story (live).
        books = self.catalog([file_row('Unsorted\\WH40K\\Брукс Майк-Месть Гоббо+Агрессивное вождение+Самые сообразительные и выдающиеся(Casper Valter)\\Warhammer 40000. Месть Гоббо.m4b',
                                       title='Warhammer 40000. Месть Гоббо', artist='Майк Брукс', album='Warhammer 40000. Месть Гоббо')])
        result = self.lookup(next(iter(books.values())))
        self.assertNotEqual((result.get('ask') or {}).get('why'), 'title_series', (result.get('ask'), result['reasons']))

    def test_ruling_52_a_split_files_by_itself_only_when_its_series_is_confirmed(self):
        # Ruling 52 (Sergei 2026-10-27, "a"): «Профессия: инквизитор 1. Леди не движется» with no series folder in Sorted is
        # asked with Series, Number and Title filled in, and Approve files them; with «Профессия: инквизитор» in Sorted under
        # Дивов Олег it files by itself. It filed by itself before. Ruling 53 (2026-10-28): sibling books carrying the same
        # pattern confirm nothing; the set is asked until Sergei's Approve files its series.
        album = 'Профессия: инквизитор 1. Леди не движется'
        path = SORTED + '\\Дивов Олег\\Профессия_ инквизитор\\Профессия_ инквизитор - 1 - Леди не движется - Дивов Олег.m4b'
        tags = dict(title='Глава %d', artist='Олег Дивов', album=album, track='%d')
        row = self.book('Unsorted\\Дивов Олег\\Профессия_ инквизитор 1. Леди не движется', ['%02d.mp3' % n for n in (1, 2)], **tags)
        self.split_asked(row, 'Профессия: инквизитор', '1', 'Леди не движется')
        self.assertEqual(self.approved_to(row), path, 'Approve once files the values filled in')
        self.in_sorted('Профессия: инквизитор', 'Петров Иван')
        self.split_asked(row, 'Профессия: инквизитор', '1', 'Леди не движется')  # another author's folder confirms nothing
        self.in_sorted('Профессия: инквизитор', 'Дивов Олег')
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result.get('ask'), self.goes_to(row, result)), ([], None, path), 'Sorted holds the series')
        parent = 'Unsorted\\Дивов Олег\\'
        rows = [file_row(parent + folder + '\\%02d.mp3' % n, title='Глава %d' % n, artist='Олег Дивов', album=name, track='%d' % n)
                for folder, name in (('1', album), ('2', 'Профессия: инквизитор 2. Живые и мертвые'), ('3', 'Профессия: инквизитор 3. Вниз по кроличьей норе')) for n in (1, 2)]
        catalog = self.catalog(rows)
        first = catalog[ROOT + '\\' + parent + '1']
        self.split_asked(first, 'Профессия: инквизитор', '1', 'Леди не движется')  # its siblings only repeat its pattern
        self.in_sorted('Профессия: инквизитор', 'Дивов Олег')
        result = self.lookup(first)
        self.assertEqual((result['reasons'], result.get('ask'), self.goes_to(first, result)), ([], None, path), 'its set answered once')
        # The guards still ask when the series is confirmed: an unclear marker (ruling 51) or no title of its own (m18).
        for name, series in (('Ведьмак №1. Последнее желание', 'Ведьмак №'), ('Ведьмак 1 - 2. Последнее желание. Меч предназначения', 'Ведьмак')):
            with self.subTest(name=name):
                row = self.book('Unsorted\\Петр Иванов - ' + name, ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Петр Иванов', album=name, track='%d')
                self.in_sorted('Ведьмак', 'Иванов Петр')
                result = self.lookup(row)
                self.assertEqual(((result.get('ask') or {}).get('why'), (result.get('ask') or {}).get('split')), ('title_series', None), 'asked about the name, nothing filled in')

    def test_ruling_53_a_set_that_only_confirms_itself_is_asked_until_its_first_book_is_approved(self):
        # Ruling 53 (Sergei 2026-10-28, "a"; Senua's 0.22.3 review, M8): two siblings carrying the same name pattern
        # confirmed each other's series, so «Шерлок Холмс. Аудиоспектакль 3. Финал» filed silently under the junk folder
        # «Шерлок Холмс. Аудиоспектакль», and «Курс истории. Лекция 3. …» under «Курс истории. Лекция».
        for parent, series, books in (('Иванов Петр\\Шерлок Холмс\\', 'Шерлок Холмс. Аудиоспектакль', ('Этюд в багровых тонах', 'Знак четырех', 'Финал')),
                                      ('Иванов Петр\\Курс истории\\', 'Курс истории. Лекция', ('Греция', 'Рим', 'Египет'))):
            with self.subTest(series=series):
                rows = [file_row(parent + '%d\\%02d.mp3' % (n, k), title='Глава %d' % k, artist='Петр Иванов', album='%s %d. %s' % (series, n, title), track='%d' % k)
                        for n, title in enumerate(books, 1) for k in (1, 2)]
                catalog = self.catalog(rows)
                third = catalog[ROOT + '\\' + parent + '3']
                self.split_asked(third, series, '3', books[2])
                self.split_asked(catalog[ROOT + '\\' + parent + '1'], series, '1', books[0])
                # Sergei approves the set's first book: its series is filed, and the rest of the set follows it.
                self.in_sorted(series, self.research.approved(catalog[ROOT + '\\' + parent + '1'], ROOT)['review']['author'])
                result = self.lookup(third)
                self.assertEqual((result['reasons'], result.get('ask'), result['review']['series'], result['review']['number']), ([], None, series, '3'))

    def test_ruling_54_one_file_siblings_vote_once_per_book_by_the_same_author_never_in_the_library_root(self):
        # Ruling 54 (Sergei 2026-10-28; Senua's 0.22.3 review, m20): one-file siblings counted files, not books, ran in the
        # library root and ignored the author: one 4-file «Лабиринты Ехо 3» book outvoted two «Сновидения Ехо» books, and
        # another author's «Червь» books made «Мертвый ноль 7. Мертвый ноль» book 7 of «Червь».
        folder = 'Макс Фрай\\'
        rows = [file_row(folder + name, title=album, artist='Макс Фрай', album=album) for album, name in (
                    ('Мертвый ноль 7. Мертвый ноль', 'Мертвый ноль 7. Мертвый ноль.m4b'), ('Сновидения Ехо 4. Я иду искать', 'Сновидения Ехо 4. Я иду искать.m4b'),
                    ('Сновидения Ехо 5. Сундук мертвеца', 'Сновидения Ехо 5. Сундук мертвеца.m4b'))]
        rows += [file_row(folder + 'Лабиринты Ехо 3 - %02d.mp3' % n, title='Глава %d' % n, artist='Макс Фрай', album='Лабиринты Ехо 3. Темная сторона', track='%d/4' % n) for n in (1, 2, 3, 4)]
        catalog = self.catalog(rows)
        self.assertEqual(sorted(len(book['members']) for book in catalog.values()), [1, 1, 1, 4], 'positive control: a 4-file book in the same folder')
        zero = catalog[ROOT + '\\' + folder + 'Мертвый ноль 7. Мертвый ноль.m4b']
        self.split_asked(zero, 'Сновидения Ехо', '7', 'Мертвый ноль')  # two books outvote one, whatever its files (m22: asked until confirmed)
        self.in_sorted('Сновидения Ехо', 'Фрай Макс')
        result = self.lookup(zero)
        self.assertEqual((result['reasons'], result['review']['series'], result['review']['number']), ([], 'Сновидения Ехо', '7'), 'two books outvote one, whatever its files')
        for place in ('', 'Unsorted\\'):
            with self.subTest(place=place or 'the library root'):
                rows = [file_row(place + 'Червь %d. %s.m4b' % (n, t), title='Червь %d. %s' % (n, t), artist='Джон МакКрэй', album='Червь %d. %s' % (n, t)) for n, t in ((1, 'Созревание'), (2, 'Насекомые'))]
                rows.append(file_row(place + 'Мертвый ноль 7. Мертвый ноль.m4b', title='Мертвый ноль 7. Мертвый ноль', artist='Макс Фрай', album='Мертвый ноль 7. Мертвый ноль'))
                catalog = self.catalog(rows)
                zero = catalog[ROOT + '\\' + place + 'Мертвый ноль 7. Мертвый ноль.m4b']
                self.split_asked(zero, 'Мертвый ноль', '7', 'Мертвый ноль')  # never book 7 of another author's «Червь»

    def test_m22_ruling_45_confirms_a_siblings_series_only_when_something_confirms_it(self):
        # Senua's 0.22.3 review, m22: ruling 45's override confirmed whatever series two siblings carried, so «Финал 3. Финал»
        # filed silently into «Шерлок Холмс. Аудиоспектакль» while the two siblings themselves were asked (ruling 53).
        parent = 'Иванов Петр\\Шерлок Холмс\\'
        rows = [file_row(parent + folder + '\\%02d.mp3' % k, title='Глава %d' % k, artist='Петр Иванов', album=album, track='%d' % k)
                for folder, album in (('1', 'Шерлок Холмс. Аудиоспектакль 1. Этюд в багровых тонах'), ('2', 'Шерлок Холмс. Аудиоспектакль 2. Знак четырех'), ('3', 'Финал 3. Финал')) for k in (1, 2)]
        catalog = self.catalog(rows)
        final = catalog[ROOT + '\\' + parent + '3']
        self.split_asked(final, 'Шерлок Холмс. Аудиоспектакль', '3', 'Финал')  # the override, filled in
        self.in_sorted('Шерлок Холмс. Аудиоспектакль', 'Иванов Петр')  # his answer for the set
        result = self.lookup(final)
        self.assertEqual((result['reasons'], result.get('ask'), result['review']['series'], result['review']['number']), ([], None, 'Шерлок Холмс. Аудиоспектакль', '3'))

    def test_m20_uncredited_siblings_and_two_album_spellings_of_one_book_never_decide_the_series(self):
        # Senua's 0.22.3 review, m20 (ruling 54): siblings with no author credit voted for any author's book, and one book
        # whose files carry two album spellings was two votes; either filed «Мертвый ноль 7. Мертвый ноль» into a series
        # it is not in.
        for place in ('Unsorted\\', 'Макс Фрай\\'):
            with self.subTest(place=place):
                rows = [file_row(place + 'Червь %d. %s.m4b' % (n, t), title='Червь %d. %s' % (n, t), album='Червь %d. %s' % (n, t)) for n, t in ((1, 'Созревание'), (2, 'Насекомые'))]
                rows.append(file_row(place + 'Мертвый ноль 7. Мертвый ноль.m4b', title='Мертвый ноль 7. Мертвый ноль', artist='Макс Фрай', album='Мертвый ноль 7. Мертвый ноль'))
                catalog = self.catalog(rows)
                self.split_asked(catalog[ROOT + '\\' + place + 'Мертвый ноль 7. Мертвый ноль.m4b'], 'Мертвый ноль', '7', 'Мертвый ноль')
        folder = 'Макс Фрай\\'
        rows = [file_row(folder + 'Лабиринты Ехо 3 - %02d.mp3' % n, title='Глава %d' % n, artist='Макс Фрай', album=album, track='%d/2' % n)
                for n, album in ((1, 'Лабиринты Ехо 3. Темная сторона'), (2, 'Лабиринты Ехо 3. Тёмная сторона'))]
        rows.append(file_row(folder + 'Мертвый ноль 7. Мертвый ноль.m4b', title='Мертвый ноль 7. Мертвый ноль', artist='Макс Фрай', album='Мертвый ноль 7. Мертвый ноль'))
        catalog = self.catalog(rows)
        self.assertEqual(sorted(len(book['members']) for book in catalog.values()), [1, 2], 'positive control: one two-file book beside it')
        self.split_asked(catalog[ROOT + '\\' + folder + 'Мертвый ноль 7. Мертвый ноль.m4b'], 'Мертвый ноль', '7', 'Мертвый ноль')

    def test_ruling_55_a_source_folder_merely_named_like_the_series_confirms_nothing(self):
        # Ruling 55 (Sergei 2026-10-28, "Yes"): a book folder inside a folder named like its series asks, filled in.
        row = self.book('Олег Дивов\\Профессия_ инквизитор\\Профессия_ инквизитор 2. Живые и мертвые', ['%02d.mp3' % n for n in (1, 2)],
                        title='Глава %d', artist='Олег Дивов', album='Профессия: инквизитор 2. Живые и мертвые', track='%d')
        self.split_asked(row, 'Профессия: инквизитор', '2', 'Живые и мертвые')
        self.assertEqual(self.approved_to(row), SORTED + '\\Дивов Олег\\Профессия_ инквизитор\\Профессия_ инквизитор - 2 - Живые и мертвые - Дивов Олег.m4b')

    def test_m9_rulings_33_and_39_come_before_the_series_question(self):
        # Senua's 0.22.3 review, M9: the ruling-52 question came first, and Approve then settled the author, so ruling 33's
        # spelling question was never asked: «Мир драконов 1. Начало» by "Ilya Marchenko" filed as `Marchenko Ilya\…`.
        row = self.book('Unsorted\\Ilya Marchenko - Мир драконов 1. Начало', ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Ilya Marchenko', album='Мир драконов 1. Начало', track='%d')
        result = self.lookup(row)
        self.assertEqual((result['ask']['kind'], result['ask']['why']), ('author_unclear', 'name_language'), 'the spelling is asked first')

    def test_m7_an_upper_case_cyrillic_look_alike_in_a_latin_series_folder_is_read_as_latin(self):
        # Senua's 0.22.3 review, M7: ruling 51's fold was bound as _LOOKALIKE, the name of latin_lookalikes' table, so «Аnita
        # Blake» (a Cyrillic А) filed under a second folder that looks the same as "Anita Blake".
        for value, latin in (('Аnita Blake', 'Anita Blake'), ('Тhe Expanse', 'The Expanse'), ('Сlive Barker', 'Clive Barker'), ('Sigmа Force', 'Sigma Force')):
            self.assertEqual(local_identity.latin_lookalikes(value), latin, value)
        books = self.catalog([file_row('Laurell K Hamilton\\Аnita Blake\\1. Guilty Pleasures\\%02d.mp3' % n, title='Глава %d' % n, artist='Laurell K. Hamilton', album='Guilty Pleasures', track='%d' % n) for n in (1, 2)])
        row = next(iter(books.values()))
        result = self.lookup(row)
        self.assertEqual((result['review']['series'], result['review']['number']), ('Anita Blake', '1'), result['reasons'])
        self.assertIn('\\Anita Blake\\Anita Blake - 1 - ', self.goes_to(row, result))

    def test_m8_the_live_names_are_asked_or_filed_into_their_confirmed_series_never_a_junk_folder(self):
        # Senua's 0.22.3 review, M8: «Отряд Сигма_01. Песчанный дьявол» (Rollins James) filed as `Отряд Сигма_\…`, and «Карр
        # Д Д - ШХ 06. Тайна закрытой комнаты» as `Карр Д Д - ШХ\…`, silently.
        sigma = 'Отряд Сигма_01. Песчанный дьявол'
        row = self.book('James Rollins\\Отряд Сигма_01. Песчанный дьявол', ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Джеймс Роллинс', album=sigma, track='%d')
        self.split_asked(row, 'Отряд Сигма', '1', 'Песчанный дьявол')
        folder = self.research.approved(row, ROOT)['review']['author']
        self.in_sorted('Отряд Сигма', folder)
        result = self.lookup(row)
        self.assertEqual((result['reasons'], result['review']['series'], result['review']['number']), ([], 'Отряд Сигма', '1'), 'its series in Sorted')
        self.assertIn('\\Отряд Сигма\\Отряд Сигма - 1 - Песчанный дьявол - ', self.goes_to(row, result))
        carr = 'Карр Д Д - ШХ 06. Тайна закрытой комнаты'
        row = self.book('Unsorted\\Карр Д Д - ШХ 06. Тайна закрытой комнаты', ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Артур Конан Дойл', album=carr, track='%d')
        result = self.lookup(row)
        self.assertEqual((result.get('ask') or {}).get('why'), 'title_series', ('asked, never filed under a junk series', result['reasons'], (result.get('review') or {}).get('series')))

    def test_m18_a_title_left_that_starts_with_a_number_or_a_part_word_is_asked(self):
        # Senua's 0.22.3 review, m18: the title after the split was not checked: «Ведьмак 1 - 2. …» filed as book 1 titled
        # «2. Последнее желание. …», «Хроники Амбера 1. Гл. 2» as book 1 titled «Гл. 2».
        for name in ('Ведьмак 1 - 2. Последнее желание. Меч предназначения', 'Гарри Поттер 1 - 3. Сборник', 'Хроники Амбера 2. 1. Карты судьбы',
                     'Хроники Амбера 1. Гл. 2', 'Хроники Амбера 1. Ch. 2', 'Хроники Амбера 1. Вып. 2', 'Хроники Амбера 1. Части 1-2'):
            with self.subTest(name=name):
                self.assertEqual(local_identity._series_split(name)[1], 'ask')
                row = self.book('Unsorted\\Петр Иванов - ' + name, ['%02d.mp3' % n for n in (1, 2)], title='Глава %d', artist='Петр Иванов', album=name, track='%d')
                self.in_sorted(local_identity._series_split(name)[0]['series'], 'Иванов Петр')
                result = self.lookup(row)
                self.assertNotEqual((result.get('review') or {}).get('series'), local_identity._series_split(name)[0]['series'], 'never filed as a series book')

    def test_m19_siblings_asked_about_still_name_the_series_ruling_45_picks(self):
        # Senua's 0.22.3 review, m19: siblings whose names ruling 51 asks about no longer voted, so «Мертвый ноль 7. Мертвый
        # ноль» beside «Сновидения Ехо №4 - …» and «… №5. …» filed as series «Мертвый ноль»; add two «Лабиринты Ехо» books
        # and it filed into «Лабиринты Ехо», a series it is not in.
        parent = 'Max Fray\\Сновидения Эхо\\'
        siblings = [('a', 'Сновидения Ехо №4 - Я иду искать'), ('b', 'Сновидения Ехо №5. Сундук мертвеца'), ('z', 'Мертвый ноль 7. Мертвый ноль')]
        def catalog(books):
            return self.catalog([file_row(parent + folder + '\\%02d.m4a' % n, title='%02d' % n, artist='Макс Фрай', album=album, track='%d/-1' % n) for folder, album in books for n in (1, 2)])
        zero = catalog(siblings)[ROOT + '\\' + parent + 'z']
        self.split_asked(zero, 'Сновидения Ехо', '7', 'Мертвый ноль')  # m22: the siblings' series is unconfirmed itself
        self.in_sorted('Сновидения Ехо', 'Фрай Макс')
        result = self.lookup(zero)
        self.assertEqual((result['reasons'], result['review']['series'], result['review']['number']), ([], 'Сновидения Ехо', '7'))
        tie = catalog(siblings + [('c', 'Лабиринты Ехо 1. Лабиринт Менина'), ('d', 'Лабиринты Ехо 2. Волонтеры вечности')])[ROOT + '\\' + parent + 'z']
        result = self.lookup(tie)
        self.assertNotEqual((result.get('review') or {}).get('series'), 'Лабиринты Ехо')
        self.split_asked(tie, 'Мертвый ноль', '7', 'Мертвый ноль')  # the siblings disagree: nothing confirms the series

    def test_russian_written_in_latin_letters_as_the_title_is_asked(self):
        row = self.book('Max Fray\\Сновидения Эхо\\Frai_Maks_Master_vetrov_i_zakatov (Ovuor)', ['Maks Frai - Master vetrov i zakatov - 00 - %03d Snovideniya Eho 1 (Ovuor).m4a' % n for n in (1, 2)],
                        title='%03d Snovideniya Eho 1 (Ovuor)', artist='Макс Фрай', album='Master vetrov i zakatov', track='%d')
        self.asked(row, 'title_author', 'title_latin')

    def test_controls_clean_names_are_still_filed_by_themselves(self):
        for folder, names, tags in (('Мецрих Бен - Кожа128', ['Mezrich_Kozha_%02d.mp3' % n for n in (1, 2)], dict(title='Mezrich_Kozha_%02d', artist='Бен Мецрих', album='Кожа', track='%d')),
                                    ('Matheson Richard\\I Am Legend', ['%02d.mp3' % n for n in (1, 2)], dict(title='I Am Legend', artist='Richard Matheson', album='I Am Legend', track='%d')),
                                    ('Грей Майкл', ['Комната ужасов 2 - %02d.mp3' % n for n in (1, 2)], dict(title='Комната ужасов 2', artist='Майкл Грей', album='Комната ужасов 2', track='%d')),
                                    ('Sapkowski\\Ostatnie zyczenie', ['%02d.mp3' % n for n in (1, 2)], dict(title='Ostatnie zyczenie', artist='Sapkowski, Andrzej', album='Ostatnie zyczenie', track='%d'))):
            result = self.lookup(self.book(folder, names, **tags))
            self.assertFalse(result.get('ask'), (folder, result.get('ask'), result['reasons']))




# Ruling 51 (Senua's 0.22.3 review, pass 4): the names read end to end on 92376c7 and what each did there.
RULING_51_KEPT = (
    ('Крысы 1. Крысы', '', ('split', 'Крысы', '1', 'Крысы')),
    ('Профессия: инквизитор 1. Леди не движется', '', ('split', 'Профессия: инквизитор', '1', 'Леди не движется')),
    ('Колесо времени - 01. Око мира', '', ('split', 'Колесо времени', '1', 'Око мира')),
    ('Сновидения Ехо #3 - Вся правда о нас', '', ('split', 'Сновидения Ехо', '3', 'Вся правда о нас')),
    ('Мертвый ноль 7. Мертвый ноль', '', ('split', 'Мертвый ноль', '7', 'Мертвый ноль')),
    ('Профессия: инквизитор 7. Война миров', '', ('split', 'Профессия: инквизитор', '7', 'Война миров')),
    ('Оттенки магии 03. Сотворение света', '', ('split', 'Оттенки магии', '3', 'Сотворение света')),
    ('Робин Хобб - Сага о Видящих 2. Королевский убийца', 'Робин Хобб', ('split', 'Сага о Видящих', '2', 'Королевский убийца')),
    ('Ведьмак 01.5. Меч', '', ('split', 'Ведьмак', '1.5', 'Меч')),
    ('Гарри Поттер 1: Философский камень', '', ('split', 'Гарри Поттер', '1', 'Философский камень')),
    ('Перри Родан 001. Звездная пыль', '', ('split', 'Перри Родан', '1', 'Звездная пыль')),
    ('Хроники Амбера. Книга 1. Девять принцев Амбера', '', ('split', 'Хроники Амбера', '1', 'Девять принцев Амбера')),
    ('Ведьмак 3: Кровь эльфов', '', ('split', 'Ведьмак', '3', 'Кровь эльфов')),
    ('Конан 005 - Час дракона', '', ('split', 'Конан', '5', 'Час дракона')),
    ('Dune 2: Dune Messiah', '', ('split', 'Dune', '2', 'Dune Messiah')),
    ('Ересь Хоруса. Книга 2. Лживые боги', '', ('split', 'Ересь Хоруса', '2', 'Лживые боги')),
    ('The Wheel of Time, Book 3: The Dragon Reborn', '', ('split', 'The Wheel of Time', '3', 'The Dragon Reborn')),
    ('Ведьмак. Кн. 1. Последнее желание', '', ('split', 'Ведьмак', '1', 'Последнее желание')),
    ('Ведьмак - книга 1 - Последнее желание', '', ('split', 'Ведьмак', '1', 'Последнее желание')),
    ('Ведьмак, книга 1: Последнее желание', '', ('split', 'Ведьмак', '1', 'Последнее желание')),
    ('Тёмная Башня. Книга 4.5. Ветер сквозь замочную скважину', '', ('split', 'Тёмная Башня', '4.5', 'Ветер сквозь замочную скважину')),
    ('Ведьмак 1. Последнее желание', '', ('split', 'Ведьмак', '1', 'Последнее желание')),
    ('Серия А 1. Первая', '', ('split', 'Серия А', '1', 'Первая')),
    ('Серия Б 3. Третья', '', ('split', 'Серия Б', '3', 'Третья')),
    ('Сновидения Эхо 2 - Слишком много кошмаров', '', ('split', 'Сновидения Ехо', '2', 'Слишком много кошмаров')),
    ('Сновидения Ехо 5. Сундук мертвеца', '', ('split', 'Сновидения Ехо', '5', 'Сундук мертвеца')),
    ('Discworld 19. Feet of Clay', '', ('split', 'Discworld', '19', 'Feet of Clay')),
    ('Червь 1. Созревание', '', ('split', 'Червь', '1', 'Созревание')),
    ('Перерождение 3. Город зеркал', '', ('split', 'Перерождение', '3', 'Город зеркал')),
    ('Anita Blake 0.5 - Beauty', '', ('split', 'Anita Blake', '0.5', 'Beauty')),
    ('S.T.A.L.K.E.R. 2 - 1. Зона', '', ('split', 'S.T.A.L.K.E.R.', '2', '1. Зона')),
    ('Sigma Force 2. Map of Bones', '', ('split', 'Sigma Force', '2', 'Map of Bones')),
    ('Ведьмак 0.5. Дорога', '', ('split', 'Ведьмак', '0.5', 'Дорога')),
    ('Книга 1. Начало', '', ('whole', 'Книга 1. Начало')),
    ('Warhammer 40000. Месть Гоббо', '', ('whole', 'Warhammer 40000. Месть Гоббо')),
    ('Комната ужасов 2', '', ('held', 'One part of a bigger book')),
    ('Война и мир. Том 1. Часть 2', '', ('held', 'One part of a bigger book')),
    ('Агент 007 - Казино Рояль', '', ('whole', 'Агент 007 - Казино Рояль')),
    ('Warhammer 40 000. Ересь Хоруса', '', ('whole', 'Warhammer 40 000. Ересь Хоруса')),
    ('Warhammer 40 000 - Ересь Хоруса', '', ('whole', 'Warhammer 40 000 - Ересь Хоруса')),
    ('Warhammer 40,000: Dawn of War', '', ('whole', 'Warhammer 40,000: Dawn of War')),
    ('Вселенная Warhammer 40 000: Кайафас Каин. Герой Империума', '', ('whole', 'Вселенная Warhammer 40 000: Кайафас Каин. Герой Империума')),
    ('Warhammer 40.000: Dawn of War', '', ('whole', 'Warhammer 40.000: Dawn of War')),
    ('Warhammer 40\xa0000: Ересь Хоруса', '', ('whole', 'Warhammer 40 000: Ересь Хоруса')),
    ('Warhammer 40\u202f000: Ересь Хоруса', '', ('whole', 'Warhammer 40 000: Ересь Хоруса')),
    ('Warhammer 40  000: Ересь Хоруса', '', ('whole', 'Warhammer 40 000: Ересь Хоруса')),
    ('Warhammer 40 000 1. Ересь Хоруса', '', ('whole', 'Warhammer 40 000 1. Ересь Хоруса')),
    ('Колесо времени 1.2. Око мира', '', ('whole', 'Колесо времени 1.2. Око мира')),
    ('Мастер и Маргарита. CD 1. Главы 1-10', '', ('whole', 'Мастер и Маргарита. CD 1. Главы 1-10')),
    ('Мастер и Маргарита. Диск 2. Главы 11-20', '', ('whole', 'Мастер и Маргарита. Диск 2. Главы 11-20')),
    ('Мастер и Маргарита CD 1. Главы 1-10', '', ('whole', 'Мастер и Маргарита CD 1. Главы 1-10')),
    ('Мастер и Маргарита - CD1 - Главы 1-10', '', ('whole', 'Мастер и Маргарита - CD1 - Главы 1-10')),
    ('Мастер и Маргарита CD-1. Главы 1-10', '', ('whole', 'Мастер и Маргарита CD-1. Главы 1-10')),
    ('Мастер и Маргарита. CD 01. Главы 1-10', '', ('whole', 'Мастер и Маргарита. CD 01. Главы 1-10')),
    ('Мастер и Маргарита, диск 1: Главы 1-10', '', ('whole', 'Мастер и Маргарита, диск 1: Главы 1-10')),
    ('Мастер и Маргарита. Disc 1. Главы 1-10', '', ('whole', 'Мастер и Маргарита. Disc 1. Главы 1-10')),
    ('Двенадцать стульев. Часть 1. Одиссея', '', ('whole', 'Двенадцать стульев. Часть 1. Одиссея')),
    ('Двенадцать стульев. Ч. 1. Одиссея', '', ('whole', 'Двенадцать стульев. Ч. 1. Одиссея')),
    ('Двенадцать стульев. Ч.1. Одиссея', '', ('whole', 'Двенадцать стульев. Ч.1. Одиссея')),
    ('Зеленая миля. Часть 2 - Мышь на миле', '', ('whole', 'Зеленая миля. Часть 2 - Мышь на миле')),
    ('Граф Монте-Кристо. Том 2. Узник замка Иф', '', ('whole', 'Граф Монте-Кристо. Том 2. Узник замка Иф')),
    ('Граф Монте-Кристо, т.2. Узник замка Иф', '', ('whole', 'Граф Монте-Кристо, т.2. Узник замка Иф')),
    ('Граф Монте-Кристо т2. Узник замка Иф', '', ('whole', 'Граф Монте-Кристо т2. Узник замка Иф')),
    ('Граф Монте-Кристо - Том 2 - Узник замка Иф', '', ('whole', 'Граф Монте-Кристо - Том 2 - Узник замка Иф')),
    ('Сага о Копье. Т. 3. Драконы', '', ('whole', 'Сага о Копье. Т. 3. Драконы')),
    ('Война и мир. Том 1 - Аудиоспектакль', '', ('whole', 'Война и мир. Том 1 - Аудиоспектакль')),
    ('Отцы и дети. Глава 1. Приезд', '', ('whole', 'Отцы и дети. Глава 1. Приезд')),
    ('Treasure Island. Chapter 1. The Old Sea-dog', '', ('whole', 'Treasure Island. Chapter 1. The Old Sea-dog')),
    ('Treasure Island. Part 1. The Old Buccaneer', '', ('whole', 'Treasure Island. Part 1. The Old Buccaneer')),
    ('Treasure Island. Pt. 2. The Sea Cook', '', ('whole', 'Treasure Island. Pt. 2. The Sea Cook')),
    ('Kill Bill Vol. 2. The Bride', '', ('whole', 'Kill Bill Vol. 2. The Bride')),
    ('Kill Bill Volume 2. The Bride', '', ('whole', 'Kill Bill Volume 2. The Bride')),
    ('Kill Bill Vol 2. The Bride', '', ('whole', 'Kill Bill Vol 2. The Bride')),
    ('Звёздные войны. Эпизод 4. Новая надежда', '', ('whole', 'Звёздные войны. Эпизод 4. Новая надежда')),
    ('Радиоспектакли. Выпуск 3. Ревизор', '', ('whole', 'Радиоспектакли. Выпуск 3. Ревизор')),
    ('Метро. Сезон 2. Питер', '', ('whole', 'Метро. Сезон 2. Питер')),
    ('Иванов. Книга 1. Начало', 'Петр Иванов', ('whole', 'Иванов. Книга 1. Начало')),
    ('Метро 2033: Питер', '', ('whole', 'Метро 2033: Питер')),
    ('Apollo 13: The Untold Story', '', ('ask', 'title_series')),
    ('Warhammer 40 000: Ересь Хоруса. Книга 1. Возвышение Хоруса', '', ('ask', 'title_series')),
    ("Warhammer 40'000: Dawn of War", '', ('ask', 'title_series')),
    ('Warhammer 40’000: Dawn of War', '', ('ask', 'title_series')),
    ('Warhammer 40 000. Ересь Хоруса 2. Лживые боги', '', ('ask', 'title_series')),
    ('Warhammer 40 000. Ересь Хоруса - 02 - Лживые боги', '', ('ask', 'title_series')),
    ('Warhammer 40 000. Ересь Хоруса #3 - Галактика в огне', '', ('ask', 'title_series')),
    ('Warhammer 40 000 - 1. Ересь Хоруса', '', ('ask', 'title_series')),
    ('Warhammer 40K 1. Ересь Хоруса', '', ('ask', 'title_series')),
    ('Колесо времени 1, 2. Око мира', '', ('ask', 'title_series')),
    ('Ведьмак 0. Дорога без возврата', '', ('ask', 'title_series')),
    ('Ведьмак 00. Дорога без возврата', '', ('ask', 'title_series')),
    ('Anita Blake 0 - Those Who Seek Forgiveness', '', ('ask', 'title_series')),
    ('13-й отдел 2. Новое дело', '', ('ask', 'title_series')),
    ('Война 1812 года 2. Бородино', '', ('ask', 'title_series')),
    ('Вселенная Метро 2033. Питер 2. Война', '', ('ask', 'title_series')),
    ('Отцы и дети. Главы 1-5. Приезд', '', ('ask', 'title_series')),
    ('Хроники Амбера. Книга 12: Рыцарь теней', '', ('ask', 'title_series')),
    ('Ведьмак 12: Сезон гроз', '', ('ask', 'title_series')),
    ('Перри Родан 101: Корабль', '', ('ask', 'title_series')),
)
RULING_51_M6 = (
    "Harry Potter Book 1 - The Philosopher's Stone",
    'Discworld Book 1 - The Colour of Magic',
    'The Wheel of Time Book 3 - The Dragon Reborn',
    'The Wheel of Time Book 3: The Dragon Reborn',
    'Хроники Амбера Книга 1. Девять принцев Амбера',
    'The Hobbit, Ch. 1: An Unexpected Party',
    'Хроники Амбера №1. Девять принцев Амбера',
    'Хроники Амбера № 1. Девять принцев Амбера',
    'Калейдоскоп № 2. Мистика и ужасы',
    'Discworld No. 1. The Colour of Magic',
    'The Wheel of Time Bk. 3 - The Dragon Reborn',
    'Отцы и дети. Гл. 1. Приезд',
    'Радиоспектакли. Вып. 3. Ревизор',
    'Доктор Кто. Серия 3. Далеки',
    'Мастер и Маргарита. \u0421D 1. Главы 1-10',  # «СD» typed with a Cyrillic С
)
RULING_51_MARKER_IN_NAME = ('Черная книга 2. Возвращение', 'Star Wars Episode 4. A New Hope')
# m18: the title left starts with a number ("1. Зона"): asked, whether or not the series is confirmed.
RULING_52_M18 = {'S.T.A.L.K.E.R. 2 - 1. Зона'}


def setUpModule():
    # Ruling 29 (0.22.2) has its own tests; these fixtures predate it (tests/original_title_fixture.py).
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


class KeepLanguageTests(Base):
    def test_ruling_58_correct_cyrillic_keep_uses_surname_first_on_both_paths(self):
        row=next(iter(self.catalog([file_row('Unsorted\\Книга\\01.mp3',album='Тихий Дон',title='Тихий Дон',artist='Иван Петров')]).values()))
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db,'keep','Иван Петров',actor='user',source='test');db.commit()
        result=self.lookup(row)
        self.assertEqual(result['reasons'],[])
        self.assertEqual(result['review']['canonical_author'],'Петров Иван')
        self.assertEqual(self.approved(row)['author'],'Петров Иван')

    def test_ruling_58_foreign_canonical_english_target_wins(self):
        row=next(iter(self.catalog([file_row('Unsorted\\Книга\\01.mp3',album='Карта костей',title='Карта костей',artist='Джеймс Роллинс')]).values()))
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db,'keep','Джеймс Роллинс',actor='user',source='old answer');db.commit()
            author_rules.append(db,'same_as','Джеймс Роллинс',target='Rollins James',actor='user',source='English answer');db.commit()
        result=self.lookup(row)
        self.assertEqual(result['reasons'],[])
        self.assertEqual(result['review']['canonical_author'],'Rollins James')
        self.assertEqual(self.approved(row)['author'],'Rollins James')

    def test_ruling_59_foreign_keep_lookup_can_learn_english(self):
        from unittest import mock
        row=next(iter(self.catalog([file_row('Unsorted\\Книга\\01.mp3',album='Карта костей',title='Карта костей',artist='Джеймс Роллинс')]).values()))
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db,'keep','Джеймс Роллинс',actor='user',source='old answer');db.commit()
        with mock.patch.object(self.research,'_author_latin',return_value={'state':'found','name':'James Rollins','source_url':'https://www.wikidata.org/wiki/Q315705'}) as lookup:
            result=self.lookup(row)
        lookup.assert_called_once()
        self.assertEqual(result['review']['canonical_author'],'Rollins James')
        self.assertEqual(author_rules.load(self.research.client.database).same_as('Джеймс Роллинс'),'Rollins James')


    def test_m15_unrelated_entered_fields_never_answer_foreign_english_requirement(self):
        from unittest import mock
        import entered_names
        for values in ({'title':'My chosen title'},{'series':'Private series','number':'2'},{'author':'Роллинс Джеймс'}):
            with self.subTest(values=values):
                row=next(iter(self.catalog([file_row('Unsorted\\Книга\\01.mp3',album='Карта костей',title='Карта костей',artist='Джеймс Роллинс')]).values()))
                with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
                    author_rules.append(db,'keep','Джеймс Роллинс',actor='user',source='old answer');db.commit()
                entered_names.save(self.research.client.database,row,[('book',field,value,'','','') for field,value in values.items()])
                with mock.patch.object(self.research,'_author_latin',return_value=None) as lookup:
                    result=self.lookup(row)
                lookup.assert_called_once()
                self.assertEqual(result['ask']['why'],'english_spelling')
                approved=self.research.approved(row,ROOT,author='James Rollins')
                self.assertEqual(approved['review']['canonical_author'],'Rollins James','an actual English answer is the positive control')

    def test_m15_english_author_lookup_preserves_only_an_explicit_entered_title(self):
        from unittest import mock
        import entered_names
        for values,expected in (({'title':'My chosen title'},'My chosen title'),({'author':'Роллинс Джеймс'},'Map of Bones')):
            with self.subTest(values=values):
                row=next(iter(self.catalog([file_row('Unsorted\\Книга\\01.mp3',album='Карта костей',title='Карта костей',artist='Джеймс Роллинс')]).values()))
                with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
                    author_rules.append(db,'keep','Джеймс Роллинс',actor='user',source='old answer');db.commit()
                entered_names.save(self.research.client.database,row,[('book',field,value,'','','') for field,value in values.items()])
                with mock.patch.object(self.research,'_author_latin',return_value={'state':'found','name':'James Rollins','title':'Map of Bones','source_url':'https://www.wikidata.org/wiki/Q315705'}) as lookup:
                    result=self.lookup(row)
                lookup.assert_called_once()
                self.assertEqual((result['review']['canonical_author'],result['review']['title']),('Rollins James',expected))


class TolkienHeldTranslationTests(Base):
    """2026-10-29 (BugEvidence/2026-10-29-tolkien-lookup): «Хранители. Летопись первая», «Две твердыни. Летопись вторая» and
    «Возвращение государя. Летопись третья» by «Джон Рональд Руэл Толкин», each a folder of two .m4b halves under
    `J. R. R. Tolkien\\Джон Рональд Руэл Толкин\\`, asked "no English spelling found". They file as Tolkien J. R. R. (the
    library's own folder), in the series «Властелин колец» 1, 2, 3 (ruling 72b: his spelling, not the sources' «Властелин
    Колец»), under their original English titles (ruling 49). The
    private answers have the shape FantLab gave on 2026-10-29: the Russian edition titles are a work's Russian or other
    name (one ";"-separated text), and the parent «Властелин Колец» is a novel-epic (work type 13) whose three novels are
    its volumes. Real PublicClient (cache, pacing, pauses) on a private catalog; no network."""
    VOLUMES=(('Хранители. Летопись первая',1,('Хранители. Книга первая','Хранители. Книга вторая'),'The Fellowship of the Ring'),
             ('Две твердыни. Летопись вторая',2,('Две твердыни. Книга третья','Две твердыни. Книга четвёртая'),'The Two Towers'),
             ('Возвращение государя. Летопись третья',3,('Возвращение государя. Книга пятая','Возвращение государя. Книга шестая'),'The Return of the King'))
    SEARCH={'Хранители':{'work_id':1667,'name':'The Fellowship of the Ring','rusname':'Братство Кольца','altname':'Хранители кольца; Хранители; Дружество кольца'},
            'Две твердыни':{'work_id':1668,'name':'The Two Towers','rusname':'Две твердыни','altname':'Две башни; Две крепости'},
            'Возвращение государя':{'work_id':1669,'name':'The Return of the King','rusname':'Возвращение Короля','altname':'Возвращение Государя'}}

    def setUp(self):
        # These books are translations: the module's "no book is a translation" patch (setUpModule) is off for them.
        _no_original_title_wait.stop();self.addCleanup(_no_original_title_wait.start)

    def sources(self,closed=()):
        import urllib.error,urllib.parse
        calls=[]
        works={record['work_id']:record for record in self.SEARCH.values()}
        def fetch(url,*_):
            calls.append(url);parts=urllib.parse.urlsplit(url)
            if parts.hostname in closed:raise urllib.error.HTTPError(url,429,'private fixture',{'Retry-After':'999999999'},None)  # a pause the site asks for
            if parts.hostname=='api.fantlab.ru' and parts.path=='/search-works':
                q=urllib.parse.parse_qs(parts.query)['q'][0]
                found=[dict(self.SEARCH[q],all_autor_name='J. R. R. Tolkien',all_autor_rusname='Дж. Р. Р. Толкин')] if q in self.SEARCH else []
                return json.dumps(found,ensure_ascii=False).encode()
            if parts.hostname=='api.fantlab.ru' and parts.path=='/work/1693/extended':
                children=[{'work_id':505060,'work_type_id':11,'deep':1,'plus':1}]+[{'work_id':n,'work_type_id':1,'deep':1,'plus':None} for n in (1667,1668,1669)]+[{'work_id':183141,'work_type_id':7,'deep':1,'plus':1}]
                return json.dumps({'work_id':1693,'work_name':'Властелин Колец','work_type_id':13,'children':children},ensure_ascii=False).encode()
            if parts.hostname=='api.fantlab.ru' and parts.path.startswith('/work/'):
                work=works[int(parts.path.split('/')[2])]
                return json.dumps({'work_id':work['work_id'],'work_name':work['rusname'],'work_name_orig':work['name'],'work_type_id':1,'work_type_name':'novel','lang_code':'en',
                                   'authors':[{'type':'autor','name':'Джон Рональд Руэл Толкин','name_orig':'John Ronald Reuel Tolkien'}],
                                   'parents':{'cycles':[[{'work_id':29203,'work_name':'Легендариум Средиземья','work_type_id':4},{'work_id':1693,'work_name':'Властелин Колец','work_type_id':13}]]}},ensure_ascii=False).encode()
            if parts.hostname=='www.goodreads.com':return b'<html><body><table class="tableList"></table></body></html>'
            if parts.hostname=='www.wikidata.org':return json.dumps({'search':[],'entities':{}}).encode()
            return b'{"items":[],"results":[],"docs":[]}'
        return fetch,calls

    def books(self,closed=()):
        rows=[]
        for album,disc,titles,_ in self.VOLUMES:
            for index,title in enumerate(titles,1):
                rows.append(file_row('J. R. R. Tolkien\\Джон Рональд Руэл Толкин\\%s\\%d-%02d %s.m4b'%(album,disc,index,title),title=title,artist='Джон Рональд Руэл Толкин',
                                     album_artist='Джон Рональд Руэл Толкин',album=album,composer='Петр Маркин',genre='Фэнтези',track='%d/2'%index,disc='%d/3'%disc))
        books=self.catalog(rows)
        fetch,calls=self.sources(closed)
        minutes=iter(range(10**6,10**9,60))  # each clock read a minute after the last: no pacing wait, the cache stays fresh
        self.research=PublicResearch(PublicClient(self.research.client.database,fetch=fetch,clock=lambda:next(minutes)),leads=[])
        return [books[key] for key in sorted(books,key=lambda key:[v[0] for v in self.VOLUMES].index(Path(key).name))],calls

    def test_held_volumes_get_the_english_title_and_the_series_from_the_catalog(self):
        books,calls=self.books()
        for row,(album,number,_,english) in zip(books,self.VOLUMES):
            with self.subTest(album=album):
                result=self.lookup(row)
                self.assertEqual(result['reasons'],[local_identity.PIECE_REASON],'held for Sergei: two halves of one volume')
                approval=self.approved(row)
                self.assertEqual((approval['title'],approval['author']),(english,'Tolkien J. R. R.'))
                review=self.research.approved(row,ROOT)['review']
                self.assertEqual((review['series'],review['number'],review['canonical_author']),('Властелин колец',str(number),'Tolkien J. R. R.'))
                self.assertIn('\\Tolkien J. R. R\\Властелин колец\\',self.approved_to(row))
                self.assertIn(english,self.approved_to(row))
        self.assertFalse(any('goodreads.com/book/show' in url for url in calls))
        self.assertTrue(any('search-works?q=%D0%A5%D1%80%D0%B0%D0%BD%D0%B8%D1%82%D0%B5%D0%BB%D0%B8&' in url for url in calls),'the volume asked by its book title')

    def test_ruling_72b_the_series_is_spelled_as_sergei_spells_it_whichever_source_names_it(self):
        from public_research import series_spelling
        self.assertEqual(series_spelling('Властелин Колец'),'Властелин колец','FantLab and Goodreads capitalise it')
        self.assertEqual(series_spelling('ВЛАСТЕЛИН КОЛЕЦ'),'Властелин колец')
        for kept in ('Гарри Поттер','Ведьмак','The Lord of the Rings',''):  # controls: every other name as the source gives it
            self.assertEqual(series_spelling(kept),kept)
        # The Goodreads provider (series backfill calls it directly, like FantLab's): «Властелин Колец, #2» files under his spelling.
        from test_series_research import Sources,book_page,search_page
        sources=Sources()
        sources.goodreads_search=search_page(('166404','Две твердыни (Властелин Колец, #2)',['J.R.R. Tolkien','Дж.Р.Р. Толкин']))
        sources.goodreads_books['166404']=book_page('166404','Две твердыни',['J.R.R. Tolkien','Дж.Р.Р. Толкин'],'Властелин Колец','2')
        minutes=iter(range(10**6,10**9,60));self.catalog([])  # a private temp folder for the client's catalog
        research=PublicResearch(PublicClient(str(Path(self.research.client.database).parent/'gr.sqlite3'),fetch=sources.fetch,clock=lambda:next(minutes)),leads=[])
        found=research._series_goodreads('Две твердыни','Tolkien J. R. R.',threading.Event(),{'remaining':6},{'sources':[]})
        self.assertEqual((found['name'],found['number']),('Властелин колец','2'))

    def test_a_closed_source_files_nothing_new_and_is_never_asked_again_during_its_pause(self):
        books,calls=self.books(closed=('api.fantlab.ru',))
        row=books[0];result=self.lookup(row)
        self.assertEqual(result['reasons'],[local_identity.PIECE_REASON],'still held: Sergei decides')
        approval=self.approved(row)
        self.assertEqual(approval['title'],'Хранители. Летопись первая','nothing confirmed: the title the files give')
        self.assertFalse(self.research.approved(row,ROOT)['review'].get('series'))
        asked=sum('api.fantlab.ru' in url for url in calls);self.assertEqual(asked,1,'one request, then the pause it set')
        self.lookup(books[1])
        self.assertEqual(sum('api.fantlab.ru' in url for url in calls),asked,'no request while FantLab is paused (no bypass)')

    def test_a_series_position_that_disagrees_with_the_volume_number_is_not_used(self):
        self.SEARCH=dict(self.SEARCH,**{'Хранители':dict(self.SEARCH['Две твердыни'],altname='Хранители')})  # a wrong record: novel 2
        books,_=self.books()
        self.lookup(books[0])
        self.assertFalse(self.research.approved(books[0],ROOT)['review'].get('series'),'«Летопись первая» is never filed as book 2')

    def test_a_title_or_series_he_entered_is_never_looked_up(self):
        import entered_names
        books,calls=self.books()
        entered_names.save(self.research.client.database,books[0],[('book','title','Хранители','','',''),('book','series','Властелин колец','','',''),('book','number','1','','','')])
        self.lookup(books[0])
        self.assertEqual([url for url in calls if 'api.fantlab.ru' in url or 'goodreads.com' in url],[],'nothing looked up')
        self.assertEqual(self.approved(books[0])['title'],'Хранители','his title files the book')


def evidence_missing(result):
    """The fields the assistant's approval (review_backend.save, actor 'assistant') refuses a book for: what its policy
    records with no cited evidence ("Assistant approval requires per-field identity, author role, original language and
    series/standalone evidence")."""
    facts, review = result['metadata_facts'], result['review']
    needed = {'title', 'authors'} | ({'original_language'} if facts['original_language']['value'] else set()) | ({'series', 'number'} if review.get('series') else set())
    return needed - {e['field'] for e in result['evidence']}


class TolkienCleanLibraryTests(TolkienHeldTranslationTests):
    """Futaba's 0.24.0 QA, B1: the same three volumes as two MP3 files each in a clean library (no `J. R. R. Tolkien`
    folder), so each is a whole book, identified by its files and filed by research. The first lookup found the English
    spelling (learned as a rule, Tolkien J. R. R.) and «The Return of the King», but recorded no original-language
    evidence, so its approval was refused and retried 15 minutes later; the other two followed the rule with no request,
    under their Russian titles and no series; the retry took the catalog's "J. R. R. Tolkien" over the rule. Two author
    folders, one English title, no series. The private answers are FantLab's live answers of 2026-10-31 (the authors'
    "J. R. R. Tolkien" / «Дж. Р. Р. Толкин», «Властелин Колец» with two forewords before the three novels)."""
    SEARCH={'Хранители':{'work_id':1667,'name':'The Fellowship of the Ring','rusname':'Братство Кольца','altname':'Хранители кольца; Хранители; Дружество кольца; Содружество кольца; Товарищество кольца'},
            'Две твердыни':{'work_id':1668,'name':'The Two Towers','rusname':'Две твердыни','altname':'Две башни; Две крепости'},
            'Возвращение государя':{'work_id':1669,'name':'The Return of the King','rusname':'Возвращение Короля','altname':'Возвращение Государя'}}
    ORDER=(1667,1668,1669)  # the novel-epic's novels in FantLab's order: their positions 1, 2, 3

    def sources(self,closed=()):
        import urllib.error,urllib.parse
        fetch,calls=super().sources(closed)
        works={record['work_id']:record for record in self.SEARCH.values()}
        def live(url,*args):
            parts=urllib.parse.urlsplit(url)
            if parts.hostname in closed or parts.hostname!='api.fantlab.ru':return fetch(url,*args)
            calls.append(url)
            if parts.path=='/work/1693/extended':
                children=[{'work_id':505060,'work_type_id':11,'deep':1,'plus':1},{'work_id':143576,'work_type_id':11,'deep':1,'plus':1}]+[{'work_id':n,'work_type_id':1,'deep':1,'plus':None} for n in self.ORDER]+[{'work_id':183141,'work_type_id':7,'deep':1,'plus':1}]
                return json.dumps({'work_id':1693,'work_name':'Властелин Колец','work_name_orig':'The Lord of the Rings','work_type_id':13,'children':children},ensure_ascii=False).encode()
            if parts.path=='/search-works':
                q=urllib.parse.parse_qs(parts.query)['q'][0]
                return json.dumps([dict(self.SEARCH[q],all_autor_name='J. R. R. Tolkien',all_autor_rusname='Дж. Р. Р. Толкин')] if q in self.SEARCH else [],ensure_ascii=False).encode()
            work=works[int(parts.path.split('/')[2])]
            return json.dumps({'work_id':work['work_id'],'work_name':work['rusname'],'work_name_orig':work['name'],'work_type_id':1,'work_type_name':'novel','lang_code':'en',
                               'authors':[{'type':'autor','name':'Дж. Р. Р. Толкин','name_orig':'J. R. R. Tolkien'}],
                               'parents':{'cycles':[[{'work_id':29203,'work_name':'Легендариум Средиземья','work_type_id':4},{'work_id':1693,'work_name':'Властелин Колец','work_type_id':13}]]}},ensure_ascii=False).encode()
        return live,calls

    def books(self,closed=()):
        rows=[]
        for album,_,titles,_ in self.VOLUMES:
            for index,title in enumerate(titles,1):
                rows.append(file_row('Unsorted\\%s\\%02d.mp3'%(album,index),title=title,artist='Джон Рональд Руэл Толкин',album_artist='Джон Рональд Руэл Толкин',
                                     album=album,genre='Фэнтези',track='%d/2'%index))
        books=self.catalog(rows)
        fetch,calls=self.sources(closed)
        minutes=iter(range(10**6,10**9,60))
        self.research=PublicResearch(PublicClient(self.research.client.database,fetch=fetch,clock=lambda:next(minutes)),leads=[])
        return {Path(key).name:row for key,row in books.items()},calls

    def test_three_volumes_file_under_one_author_with_their_english_titles_and_series(self):
        books,calls=self.books()
        english={album:(number,title) for album,number,_,title in self.VOLUMES}
        # The run's order (by folder name), then the first book once more, as its retry was.
        for album in sorted(books)+sorted(books)[:1]:
            with self.subTest(album=album):
                result=self.lookup(books[album]);review=result['review'];number,title=english[album]
                self.assertEqual(result['reasons'],[],'identified by its files: research files it')
                self.assertEqual((review['canonical_author'],review['title'],review['series'],review['number']),('Tolkien J. R. R.',title,'Властелин колец',str(number)))
                self.assertEqual(evidence_missing(result),set(),'the approval has evidence for every field its policy records')
                self.assertIn('\\Tolkien J. R. R\\Властелин колец\\',self.goes_to(books[album],result))
                asked=len(calls);self.research.approved(books[album],ROOT)
                self.assertEqual(len(calls),asked,'Approve and its preview read the cache only')

    def test_a_ruled_author_whose_sources_are_paused_files_at_once_under_the_title_it_has(self):
        # Ruling 38: nothing waits for the English title; the lookup asks once and respects each pause (no bypass).
        books,calls=self.books(closed=('api.fantlab.ru','www.goodreads.com','www.wikidata.org','html.duckduckgo.com','www.litres.ru'))
        with contextlib.closing(sqlite3.connect(self.research.client.database)) as db:
            author_rules.append(db,'same_as','Джон Рональд Руэл Толкин',target='Tolkien J. R. R.',actor='assistant',source='https://fantlab.ru/work1669');db.commit()
        first=self.lookup(books['Хранители. Летопись первая'])
        self.assertEqual(first['reasons'],[])
        self.assertEqual((first['review']['canonical_author'],first['review']['title'],first['review']['series']),('Tolkien J. R. R.','Хранители. Летопись первая',''))
        asked=len(calls)
        self.assertEqual(self.lookup(books['Две твердыни. Летопись вторая'])['reasons'],[])
        self.assertEqual(len(calls),asked,'no request to a paused source')

    def test_an_english_title_found_with_the_authors_spelling_carries_its_original_language(self):
        # The ruling-39 lookup's record names the English title: the policy records English as the original language,
        # and the approval needs evidence for it (it refused the book and retried it 15 minutes later).
        from unittest import mock
        books,_=self.books(closed=('api.fantlab.ru','www.goodreads.com','www.wikidata.org','html.duckduckgo.com','www.litres.ru'))
        found={'state':'found','name':'J. R. R. Tolkien','title':'The Return of the King','source_url':'https://fantlab.ru/work1669'}
        with mock.patch.object(self.research,'_author_latin',return_value=found):
            result=self.lookup(books['Возвращение государя. Летопись третья'])
        self.assertEqual((result['reasons'],result['review']['title'],result['metadata_facts']['original_language']['value']),([],'The Return of the King','en'))
        self.assertEqual(evidence_missing(result),set())
        self.assertIn({'field':'original_language','cited_value':'en','source_url':'https://fantlab.ru/work1669'},
                      [{key:e[key] for key in ('field','cited_value','source_url')} for e in result['evidence']])

    def test_a_volume_number_the_source_disagrees_with_is_asked_and_approve_files_what_it_shows_74b(self):
        # Ruling 74b: FantLab numbers the novels 1668, 1667, 1669, so «Хранители. Летопись первая» is its book 2 and «Две
        # твердыни. Летопись вторая» its book 1; «Возвращение государя. Летопись третья» agrees (book 3): the control.
        self.ORDER=(1668,1667,1669)
        books,calls=self.books()
        control=self.lookup(books['Возвращение государя. Летопись третья'])
        self.assertEqual(control['reasons'],[],'the numbers agree: filed with no question')
        self.assertEqual((control['review']['series'],control['review']['number'],control['review']['title']),('Властелин колец','3','The Return of the King'))
        for album,title_number,source_number in (('Хранители. Летопись первая',1,'2'),('Две твердыни. Летопись вторая',2,'1')):
            with self.subTest(album=album):
                row=books[album];result=self.lookup(row);ask=result.get('ask') or {}
                self.assertEqual(result['reasons'],[local_identity.ASK_REASONS['title_author']],'held: never filed without its question')
                self.assertEqual((ask.get('kind'),ask.get('why'),ask.get('odd_name')),('title_author','number_unclear',True))
                self.assertEqual(ask['volume'],{'title_number':title_number,'series_number':source_number,'provider':'fantlab'})
                # Senua's 74b review, r2: the record that numbers it differently gives no English title; the title as it is.
                self.assertEqual({name:field['proposal'] for name,field in ask['fields'].items()},
                                 {'title':album,'author':'Tolkien J. R. R.','series':'Властелин колец','number':str(title_number)})
                # Approve with the row's values (what its Approve sends) files them, reading the cache only.
                asked=len(calls);approved=self.research.approved(row,ROOT,names={'series':'Властелин колец','number':str(title_number)})
                self.assertEqual(len(calls),asked,'Approve reads the cache only')
                review=approved['review']
                self.assertEqual((review['title'],review['canonical_author'],review['series'],review['number']),(album,'Tolkien J. R. R.','Властелин колец',str(title_number)))
                self.assertEqual(evidence_missing(approved),set(),'every field it files is evidenced')
                self.assertIn('\\Tolkien J. R. R\\Властелин колец\\',self.goes_to(row,approved))
                # Senua's 74b review, r1: research alone never files the disagreeing source's series (no question, no values).
                self.assertEqual(self.research.approved(row,ROOT)['review']['series'],'')
                # Numbers he types win.
                typed=self.research.approved(row,ROOT,names={'series':'Властелин колец','number':source_number})['review']
                self.assertEqual(typed['number'],source_number)

    def test_a_record_that_numbers_the_volume_differently_gives_no_english_title_r2(self):
        # Senua's 74b review, r2: FantLab's search for «Хранители» answers «Две твердыни» (its book 2). That record's English
        # title is never offered or filed for «Хранители. Летопись первая», whether the warm-up or the ruling-39 author lookup
        # read it (this volume is researched first, so the lookup reads it). Control: the agreeing volume keeps its title.
        self.SEARCH=dict(self.SEARCH,**{'Хранители':dict(self.SEARCH['Две твердыни'],altname='Хранители')})
        books,_=self.books()
        row=books['Хранители. Летопись первая'];result=self.lookup(row);ask=result.get('ask') or {}
        self.assertEqual((ask.get('why'),ask.get('volume')),('number_unclear',{'title_number':1,'series_number':'2','provider':'fantlab'}))
        self.assertEqual(ask['fields']['title']['proposal'],'Хранители. Летопись первая','never "The Two Towers"')
        self.assertEqual(self.research.approved(row,ROOT,names={'series':'Властелин колец','number':'1'})['review']['title'],'Хранители. Летопись первая')
        control=self.lookup(books['Возвращение государя. Летопись третья'])
        self.assertEqual((control['reasons'],control['review']['title'],control['review']['number']),([],'The Return of the King','3'))

    # The inherited held-volume tests are TolkienHeldTranslationTests' own.
    test_held_volumes_get_the_english_title_and_the_series_from_the_catalog=None
    test_ruling_72b_the_series_is_spelled_as_sergei_spells_it_whichever_source_names_it=None
    test_a_closed_source_files_nothing_new_and_is_never_asked_again_during_its_pause=None
    test_a_series_position_that_disagrees_with_the_volume_number_is_not_used=None
    test_a_title_or_series_he_entered_is_never_looked_up=None


def tearDownModule():
    _no_original_title_wait.stop()


if __name__ == '__main__':
    unittest.main()
