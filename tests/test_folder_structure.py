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
            self.assertEqual((found['title'], found['position'], found['series']),
                             (expected[name[:2]], str(int(name[:2])), 'Вселенная Дозоров - Межавторский'), name)
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
        self.assertEqual(self.lookup(row)['review']['title'], 'Жозеф Фуше - Портрет политического деятеля')
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

    def test_a_series_or_number_inside_the_title_is_asked(self):
        cases = (('Max Fray\\Сновидения Эхо\\Frai_Maks_Vsya_pravda_o_nas (Ovuor)', ['Макс Фрай - Сновидения Ехо #3 - Вся правда о нас  - %02d - %02d - Maks Frai - Vsya pravda o nas - (Ovuor).m4a' % (n, n) for n in (1, 2)],
                  dict(title='%02d - Maks Frai - Vsya pravda o nas - (Ovuor)', artist='Макс Фрай', album='Сновидения Ехо #3 - Вся правда о нас ', track='%d')),
                 ('Max Fray\\Сновидения Эхо\\Макс Фрай_Мертвый ноль_Гмыза Игорь', ['Макс Фрай - Мертвый ноль 7. Мертвый ноль - %02d - %02d.m4a' % (n, n) for n in (1, 2)],
                  dict(title='%02d', artist='Макс Фрай', album='Мертвый ноль 7. Мертвый ноль', track='%d/-1')),
                 ('Unsorted\\Дивов. Профессия инквизитор\\7\\Олег Дивов_ Война миров_Ирина Зубкова', ['%02d  Война миров.mp3' % n for n in (0, 1)],
                  dict(title='Глава %d', artist='Олег Дивов', album='Профессия: инквизитор 7. Война миров', album_artist='И. Зубкова', track='%d')))
        for folder, names, tags in cases:
            self.asked(self.book(folder, names, **tags), 'title_author', 'title_series')
        # The book folder names the title without the series (Шваб, live): asked.
        row = self.book('Unsorted\\Шваб Виктория - Сотворение света (Иванов_С)', ['01_Razrushennyy mir.mp3', '02_Razrushennyy mir.mp3'],
                        title='Глава %d', artist='Виктория Шваб', album='Оттенки магии 03. Сотворение света', track='%d')
        self.asked(row, 'title_author', 'title_series')

    def test_a_series_named_the_same_way_everywhere_is_still_filed_by_itself(self):
        # Measured on the live copy: the plain "<Series> N. Title" pattern alone asked 91 books, 31 of them «Червь». When
        # the files and folders all carry the name the same way, nothing disagrees, so the app files it as before.
        for folder, names, tags in (('Червь', ['Червь 1. Созревание.m4b'], dict(title='Червь 1. Созревание', artist='Джон МакКрэй', album='Червь 1. Созревание')),
                                    ('Wheel of Time\\Колесо времени - 01. Око мира', ['Джордан Роберт (2013) - Колесо времени - 01. Око мира.m4b'],
                                     dict(title='Колесо времени - 01. Око мира', artist='Джордан Роберт', album='Колесо времени - 01. Око мира')),
                                    ('Terry Pratchet\\Discworld\\City Watch', ['Discworld 19. Feet of Clay.m4b'], dict(title='Discworld 19. Feet of Clay', artist='Terry Pratchett', album='Discworld 19. Feet of Clay')),
                                    # "40000" is no series 40 and book 000, though the folder names the story (live).
                                    ('Unsorted\\WH40K\\Брукс Майк-Месть Гоббо+Агрессивное вождение+Самые сообразительные и выдающиеся(Casper Valter)', ['Warhammer 40000. Месть Гоббо.m4b'],
                                     dict(title='Warhammer 40000. Месть Гоббо', artist='Майк Брукс', album='Warhammer 40000. Месть Гоббо'))):
            books = self.catalog([file_row(folder + '\\' + name, **tags) for name in names])
            self.assertEqual(len(books), 1, 'positive control: one book')
            result = self.lookup(next(iter(books.values())))
            self.assertNotEqual((result.get('ask') or {}).get('why'), 'title_series', (folder, result.get('ask'), result['reasons']))

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




def setUpModule():
    # Ruling 29 (0.22.2) has its own tests; these fixtures predate it (tests/original_title_fixture.py).
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()


if __name__ == '__main__':
    unittest.main()
