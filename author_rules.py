"""Sergei's lasting author rules (ruling 12, 2026-10-24): one append-only table, author_rules, in the catalog.

Every answer Sergei gives about a name becomes a rule that applies to future books as well:
  same_as     other spellings, scripts or pen names of one person -> one folder (target);
  not_author  a reader, label, studio or uploader: never an author (ruling 14);
  collection  a series or anthology name, an editor, or a folder whose books stay together: Сборники /
              «Разные авторы»; options {'fallback': 'compiler'} files a folk-tale collection under the compiler or
              reteller its files credit, else Сборники;
  keep        a separate author Sergei confirmed: never asked again.
A rule's credit is normalised the way same_person() compares names (case, ё/е, punctuation and word order do not
matter). credit '*' with a scope covers every credit in that folder. scope is '' (the whole library) or a folder
path fragment ("Легенды школы №4 г. Пензы"); a rule applies when the book's folder path contains it. The rows refuse
UPDATE and DELETE (triggers); a changed mind is a newer row for the same credit and scope, and the newest wins.
A rule taken back (retract, Senua's 0.22.0 review m6; a seed too) is a row of its own append-only table,
author_rule_retractions: among the rules it counts as a newer row of kind 'none' for that credit and scope, which
decides nothing, so no older answer for that name and folder comes back and the app asks again; a later answer wins.
"""
import contextlib
import copy
import datetime
import hashlib
import json
import sqlite3
import unicodedata
import uuid
from pathlib import Path

KINDS = ('same_as', 'not_author', 'collection', 'keep')
APP_RETRACTION = 'app'  # 0.22.3: the actor of a retraction the app writes when the Approve carrying an answer is refused
RETRACTED = 'none'  # the kind a retraction takes among the rules (Rules): newest for its credit and scope, it decides nothing
SEED_SOURCE = 'Sergei 2026-10-24'
SEED_QUESTION = 'Team/Docs/BooksArranger_AuthorRulings_2026-10-24.md'


def key(name):
    """The credit as same_person() sees it: words casefolded, ё -> е, punctuation dropped, in sorted order."""
    from local_identity import words
    return ' '.join(sorted(words(unicodedata.normalize('NFC', str(name or '')))))


def setup(db):
    db.execute('''CREATE TABLE IF NOT EXISTS author_rules(rule_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('same_as','not_author','collection','keep')),
      credit_key TEXT NOT NULL, credit_as_seen TEXT NOT NULL, target TEXT NOT NULL DEFAULT '', scope TEXT NOT NULL DEFAULT '',
      options TEXT NOT NULL DEFAULT '{}', actor TEXT NOT NULL, source TEXT NOT NULL, question TEXT NOT NULL DEFAULT '', saved_utc TEXT NOT NULL)''')
    db.execute("CREATE TRIGGER IF NOT EXISTS author_rules_no_update BEFORE UPDATE ON author_rules BEGIN SELECT RAISE(ABORT,'author_rules is append-only: add a newer rule instead'); END")
    db.execute("CREATE TRIGGER IF NOT EXISTS author_rules_no_delete BEFORE DELETE ON author_rules BEGIN SELECT RAISE(ABORT,'author_rules is append-only: add a newer rule instead'); END")
    db.execute('''CREATE TABLE IF NOT EXISTS author_rule_retractions(retraction_id TEXT PRIMARY KEY, rule_id TEXT NOT NULL, credit_key TEXT NOT NULL,
      scope TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL, source TEXT NOT NULL, saved_utc TEXT NOT NULL)''')
    db.execute("CREATE TRIGGER IF NOT EXISTS author_rule_retractions_no_update BEFORE UPDATE ON author_rule_retractions BEGIN SELECT RAISE(ABORT,'author_rule_retractions is append-only: add a newer rule instead'); END")
    db.execute("CREATE TRIGGER IF NOT EXISTS author_rule_retractions_no_delete BEFORE DELETE ON author_rule_retractions BEGIN SELECT RAISE(ABORT,'author_rule_retractions is append-only: add a newer rule instead'); END")


def retract(db, rule_id, *, actor='user', source=''):
    """Take back one rule, a seed included (Senua's 0.22.0 review, m6): a retraction row for its credit and scope. Only
    the rule in force there can be taken back: a rule already replaced by a newer answer or taken back refuses. Raises
    ValueError, nothing written; returns the retraction's id."""
    setup(db)
    row = db.execute('SELECT credit_key, scope FROM author_rules WHERE rule_id=?', (rule_id,)).fetchone()
    if row is None:
        raise ValueError('There is no such author rule. Nothing was changed.')
    credit_key, scope = row[0], row[1]
    # An answer the app undid (and its undo) is not there for this check either (Rules' own view, M1).
    undone = {r[0] for r in db.execute('SELECT rule_id FROM author_rule_retractions WHERE credit_key=? AND actor=?', (credit_key, APP_RETRACTION))}
    rows = [r for r in db.execute('SELECT rule_id, scope, saved_utc FROM author_rules WHERE credit_key=? UNION ALL '
                                  'SELECT retraction_id, scope, saved_utc FROM author_rule_retractions WHERE credit_key=? AND actor<>?', (credit_key, credit_key, APP_RETRACTION))
            if r[1].casefold() == scope.casefold() and r[0] not in undone]
    if not rows or max(rows, key=lambda r: (r[2], r[0]))[0] != rule_id:  # Rules' own order: the newest wins
        raise ValueError('This author rule was already replaced or taken back. Nothing was changed.')
    retraction_id = 'retract-' + str(uuid.uuid4())
    db.execute('INSERT INTO author_rule_retractions VALUES(?,?,?,?,?,?,?)',
               (retraction_id, rule_id, credit_key, scope, actor, source or actor, datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return retraction_id


def append(db, kind, credit, *, target='', scope='', options=None, actor='user', source='', question=''):
    """One new rule row (the newest for its credit and scope wins). Returns the rule_id."""
    if kind not in KINDS:
        raise ValueError('Unknown author rule kind')
    credit_key = '*' if credit == '*' else key(credit)
    if not credit_key:
        raise ValueError('An author rule needs a credit')
    if kind == 'same_as' and not str(target or '').strip():
        raise ValueError('A same_as rule needs its target folder name')
    if credit == '*' and not scope:
        raise ValueError('A rule for every credit needs a folder scope')
    rule_id = str(uuid.uuid4())
    db.execute('INSERT INTO author_rules VALUES(?,?,?,?,?,?,?,?,?,?,?)',
               (rule_id, kind, credit_key, str(credit), str(target or '').strip(), str(scope or ''), json.dumps(options or {}, ensure_ascii=False),
                actor, source or actor, question, datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return rule_id


def seed(db):
    """Sergei's 2026-10-24 answers, once: a seed whose id is already stored is never written again."""
    setup(db)
    have = {r[0] for r in db.execute("SELECT rule_id FROM author_rules WHERE rule_id LIKE 'seed-2026-10-24-%'")}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for kind, credit, target, scope, options in SEEDS:
        # Content-derived ids: editing the list never re-adds or loses an answer already stored.
        rule_id = 'seed-2026-10-24-' + hashlib.sha256('\x1f'.join((kind, credit, target, scope)).encode('utf-8')).hexdigest()[:16]
        if rule_id in have:
            continue
        db.execute('INSERT INTO author_rules VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (rule_id, kind, '*' if credit == '*' else key(credit), credit, target, scope, json.dumps(options or {}, ensure_ascii=False),
                    'user', SEED_SOURCE, SEED_QUESTION, now))


class Rules:
    """The effective rules (newest per credit and scope), read once. Pure lookups. A 'none' row (a retraction) stays among
    them: no lookup asks for its kind, and changed_for researches again the books whose names it takes back."""

    def __init__(self, rows=(), known_authors=()):
        rows = list(rows)
        # Senua's 0.22.3 review, M1: the app's undo of a refused Approve's answer (an 'app' retraction) removes that answer
        # and itself, so the row in force before the press decides again: an earlier answer, a learned rule or his Take back.
        undone = {row.get('retracts') for row in rows if row['kind'] == RETRACTED and row.get('actor') == APP_RETRACTION}
        effective = [row for row in rows if row['rule_id'] not in undone and not (row['kind'] == RETRACTED and row.get('actor') == APP_RETRACTION)]
        newest = {}
        for row in sorted(effective, key=lambda r: (r['saved_utc'], r['rule_id'])):
            newest[(row['credit_key'], row['scope'].casefold())] = row
        self.rules = list(newest.values())
        self.by_key = {}
        for row in self.rules:
            self.by_key.setdefault(row['credit_key'], []).append(row)
        self.seen = None
        self.folders = None
        # casefolded author folder name -> (name, converted books): the authors the library already has. A converted
        # book's author that a rule files under another name counts as that author (0.22.3, Brom: «Бром Джеральд», ruled
        # the same as Brom, made "Same author?" offer «Бром Джеральд» for «Бром» instead of the Brom folder).
        self.known_authors = {}
        for name in known_authors:
            if name:
                name = self.same_as(str(name)) or str(name)
                spelling, count = self.known_authors.get(name.casefold(), (name, 0))
                self.known_authors[name.casefold()] = (spelling, count + 1)
        for row in self.rules:
            name = row['target'] if row['kind'] == 'same_as' else row['credit_as_seen'] if row['kind'] == 'keep' else ''
            if name and name.casefold() not in self.known_authors:
                self.known_authors[name.casefold()] = (name, 0)
        self.generation = hashlib.sha256(json.dumps(sorted((r['rule_id'], r['kind'], r['target'], r['scope']) for r in self.rules)).encode()).hexdigest()[:16]
        # The newest rule's time: a research records it, and a rule saved after it is a new rule for that book.
        self.stamp = max((str(r.get('saved_utc') or '') for r in rows), default='')

    def recording(self):
        """A copy that records every credit and folder it is asked about (Senua's 0.22.0 review, G6): a research stores
        them, and a later rule re-researches only the books whose names it matches (changed_for)."""
        watch = copy.copy(self)
        watch.seen, watch.folders = set(), set()
        return watch

    SEEN_LIMIT, FOLDER_LIMIT = 500, 20

    def record(self):
        """What a research stores of a recording copy: the newest rule time and the credits and folders it asked about.
        Never cut short: past the limits the lists are None, and any later rule researches the book again."""
        seen = sorted(self.seen or ()) if len(self.seen or ()) <= self.SEEN_LIMIT else None
        folders = sorted(self.folders or ()) if len(self.folders or ()) <= self.FOLDER_LIMIT else None
        return {'rules_stamp': self.stamp, 'rules_seen': seen, 'rules_folders': folders}

    def changed_for(self, record):
        """True when a rule saved after the research in record decides one of the credits or folders it saw (or the
        record cannot tell: researched before 0.22.0's rule records). Equal generations: nothing changed."""
        if (record.get('rules_generation') or '') == self.generation:
            return False
        stamp, seen, folders = record.get('rules_stamp'), record.get('rules_seen'), record.get('rules_folders')
        if not isinstance(stamp, str) or not isinstance(seen, list) or not isinstance(folders, list):
            return True
        seen = set(seen)
        folders = [str(f).casefold() for f in folders if isinstance(f, str)]
        for row in self.rules:
            if str(row.get('saved_utc') or '') <= stamp:
                continue
            if row['credit_key'] != '*' and row['credit_key'] not in seen:
                continue
            if not row['scope'] or any(row['scope'].casefold() in folder for folder in folders):
                return True
        return False

    def _rule(self, name, folder, kinds):
        if self.seen is not None:
            self.seen.add(key(name))
            self.folders.add(str(folder or ''))
        folder = str(folder or '').casefold()
        found = None
        for row in self.by_key.get(key(name), []) + self.by_key.get('*', []):
            if row['kind'] not in kinds or row['scope'] and row['scope'].casefold() not in folder:
                continue
            # A scoped rule beats a library-wide one; among equals the newest wins (rows are oldest first).
            if found is None or bool(row['scope']) >= bool(found['scope']):
                found = row
        return found

    def rule(self, name, folder=''):
        """The rule deciding this credit here, whatever its kind, or None."""
        return self._rule(name, folder, KINDS)

    def same_as(self, name, folder=''):
        """The author this credit files under. A target that is itself ruled the same as another name follows it (0.22.3,
        «Бром»: "Бром" same as «Бром Джеральд», which a lookup ruled the same as Brom, files under Brom, never a second
        folder). Bounded, and a loop stops where it would repeat."""
        row = self.rule(name, folder)
        target = row['target'] if row and row['kind'] == 'same_as' else ''
        seen = {key(name)}
        while target and key(target) not in seen and len(seen) < 8:
            seen.add(key(target))
            row = self.rule(target, folder)
            if not row or row['kind'] != 'same_as' or not row['target']:
                break
            target = row['target']
        return target

    def not_author(self, name, folder=''):
        row = self.rule(name, folder)
        return bool(row and row['kind'] == 'not_author')

    def collection(self, name, folder=''):
        row = self.rule(name, folder)
        return bool(row and row['kind'] == 'collection')

    def taken_back(self, name, folder=''):
        """0.22.3 (Judy's question 1, its default): the newest rule for this credit is a Take back, so research asks Sergei
        once (ruling 39's question) instead of looking the name up online again and learning the same match."""
        row = self._rule(name, folder, KINDS + (RETRACTED,))
        # The app's own retraction of a refused Approve's answer (actor 'app') is no Take back: it only undoes that press.
        return bool(row and row['kind'] == RETRACTED and row.get('actor') != APP_RETRACTION)

    def keep(self, name, folder=''):
        row = self.rule(name, folder)
        return bool(row and row['kind'] == 'keep')

    def options(self, name, folder=''):
        row = self.rule(name, folder)
        return json.loads(row['options']) if row else {}

    def rule_id(self, name, folder=''):
        row = self.rule(name, folder)
        return row['rule_id'] if row else ''

    def folder_rule(self, folders):
        """A same_as or collection rule named after one of the book's own folders ("Гробница Саргераса" ->
        Brooks Robert): (kind, target, rule_id) or None. Only folder-specific answers count, never credit '*'."""
        if self.seen is not None:
            self.seen.update(key(name) for name in folders)
        for name in folders:
            for row in self.by_key.get(key(name), []):
                if row['kind'] in ('same_as', 'collection') and not row['scope']:
                    return row['kind'], row['target'], row['rule_id']
        return None


_CACHE = {}


def learned(database):
    """0.22.3 (Judy 4.1): the rules research learned online (actor 'assistant': a Cyrillic credit filed under its English
    spelling, or kept as written for a Russian-writing author) still in force, newest first: [{'rule_id', 'kind', 'credit',
    'target', 'source', 'saved_utc', 'question'}]. Sergei's own answers and the seeds are not listed. Read-only."""
    rules = load(database)
    if rules is None:
        return []
    found = [r for r in rules.rules if r['kind'] in ('same_as', 'keep') and r.get('actor') == 'assistant']
    found.sort(key=lambda r: (str(r.get('saved_utc') or ''), str(r['rule_id'])), reverse=True)
    return [{'rule_id': r['rule_id'], 'kind': r['kind'], 'credit': r.get('credit_as_seen') or r['credit_key'], 'target': r.get('target') or '',
             'source': r.get('source') or '', 'saved_utc': str(r.get('saved_utc') or ''), 'question': r.get('question') or ''} for r in found]


def load(database):
    """The effective rules of a catalog, read-only; None when the catalog has no rules table."""
    path = Path(database).resolve()
    try:
        with contextlib.closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='author_rules'").fetchone():
                return None
            stamp = tuple(db.execute('SELECT count(*), max(saved_utc) FROM author_rules').fetchone())
            retractions = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='author_rule_retractions'").fetchone()
            if retractions:
                stamp += tuple(db.execute('SELECT count(*), max(saved_utc) FROM author_rule_retractions').fetchone())
            jobs = tuple(db.execute('SELECT count(*), max(updated) FROM audio_jobs').fetchone()) if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_jobs'").fetchone() else ()
            cache_key = (str(path), stamp, jobs)
            if cache_key in _CACHE:
                return _CACHE[cache_key]
            rows = [dict(r) for r in db.execute('SELECT * FROM author_rules')]
            if retractions:  # each a newer 'none' row for the credit and scope it took back
                rows += [{'rule_id': r['retraction_id'], 'kind': RETRACTED, 'credit_key': r['credit_key'], 'credit_as_seen': '', 'target': '',
                          'scope': r['scope'], 'options': '{}', 'actor': r['actor'], 'source': r['source'], 'question': '', 'saved_utc': r['saved_utc'],
                          'retracts': r['rule_id']} for r in db.execute('SELECT * FROM author_rule_retractions')]
            known = []
            if jobs:
                for (manifest,) in db.execute('SELECT manifest FROM audio_jobs'):
                    try:
                        value = (json.loads(manifest).get('metadata') or {}).get('author')
                    except (ValueError, TypeError, AttributeError):
                        continue
                    if isinstance(value, str) and value.strip():
                        known.append(value.strip())
    except (sqlite3.Error, OSError):
        return None
    rules = Rules(rows, known)
    _CACHE.clear()
    _CACHE[cache_key] = rules
    return rules


# ---------------------------------------------------------------- Sergei's answers, 2026-10-24
# (kind, credit as seen, target, scope, options). Folder language rule: an English folder name for an author who
# does not write in Russian, a Russian one for an author who does (AuthorRulings, "Folder language rule").
_SAME = [
    # Pratchett: two t's; every Pratchett book goes there.
    ('Pratchet Terry', 'Pratchett Terry'), ('Terry Pratchet', 'Pratchett Terry'), ('Terry Pratchett', 'Pratchett Terry'),
    ('Терри Пратчетт', 'Pratchett Terry'), ('Пратчетт Терри', 'Pratchett Terry'), ('Т. Пратчетт', 'Pratchett Terry'),
    ('Т.Пратчетт. Зимних дел мастер', 'Pratchett Terry'), ('Терри Пратчетт. Шляпа полная небес', 'Pratchett Terry'),
    # The 15 misspellings of authors already in Sorted; the target follows the language rule.
    ('Kuntz Dean', 'Koontz Dean'), ('Dean Kuntz', 'Koontz Dean'), ('Кунц Дин', 'Koontz Dean'), ('Дин Кунц', 'Koontz Dean'),
    ('Niel Gaiman', 'Gaiman Neil'), ('Нил Гейман', 'Gaiman Neil'),
    ('Maks Frai', 'Фрай Макс'), ('Max Fray', 'Фрай Макс'), ('Макс Фрай', 'Фрай Макс'),
    ('H. Rider Haggard', 'Haggard H. Rider'), ('Хаггард Райдер', 'Haggard H. Rider'), ('Хаггард Генри Райдер', 'Haggard H. Rider'),
    ('Генри Райдер Хаггард', 'Haggard H. Rider'), ('Khaggard-"Ledyanye bogi"', 'Haggard H. Rider'),
    ('Джордж Мартин', 'Martin George R. R'), ('Мартин Джордж', 'Martin George R. R'), ('George R. R. Martin', 'Martin George R. R'),
    ('О.Дивов', 'Дивов Олег'), ('О. Дивов', 'Дивов Олег'),
    ('Дэн Абнетт «Первый и Единственный»', 'Abnett Dan'), ('Дэн Абнетт', 'Abnett Dan'),
    ('Мэтью Фарерр', 'Farrer Matthew'), ('Мэтью Фаррер', 'Farrer Matthew'), ('Фаррер Мэтью', 'Farrer Matthew'),
    ('Наталья Тимошенкова', 'Тимошенко Наталья'),
    ('Грэм Мастертон Пария Ugrum Ugrumov', 'Masterton Graham'), ('Грэм Мастертон', 'Masterton Graham'),
    ('Кинг___Легенда_о_пуле', 'King Stephen'), ('Стивен Кинг', 'King Stephen'), ('Кинг Стивен', 'King Stephen'),
    # Bachman is King's pen name.
    ('Бахман Ричард \\ Кинг Стивен', 'King Stephen'), ('Ричард Бахман', 'King Stephen'), ('Richard Bachman', 'King Stephen'),
    # Clive Barker is English-speaking.
    ('Баркер Клайв', 'Barker Clive'), ('Клайв Баркер', 'Barker Clive'), ('Клайв Баркер/Spichkin', 'Barker Clive'),
    # «Лена Летняя» is Лена Обухова's pen name.
    ('Лена Летняя', 'Обухова Лена'), ('Летняя Лена', 'Обухова Лена'),
    # Two spellings among the new names: one folder each (the language rule picks the script).
    ('Юн Айвиде Линдквист', 'Lindqvist John Ajvide'), ('Линдквист Йон Айвиде', 'Lindqvist John Ajvide'), ('John Ajvide Lindqvist', 'Lindqvist John Ajvide'),
    ('Юкито Аяцудзи', 'Ayatsuji Yukito'), ('Аякудзи Юкито', 'Ayatsuji Yukito'), ('Аяцудзи Юкито', 'Ayatsuji Yukito'), ('Yukito Ayatsuji', 'Ayatsuji Yukito'),
    ('Риггз Рэнсом', 'Riggs Ransom'), ('Риггз Ренсом', 'Riggs Ransom'), ('Ransom Riggs', 'Riggs Ransom'),
    ('Orson Scott Card', 'Card Orson Scott'), ('О. С. Кард', 'Card Orson Scott'), ('Орсон Скотт Кард Голос тех кого нет', 'Card Orson Scott'), ('Орсон Скотт Кард', 'Card Orson Scott'),
    ('Кристофер Мур', 'Moore Christopher'), ('Кристофер Мур пер М. Немцова', 'Moore Christopher'),
    ('R.L. Stajn', 'Stine R. L.'), ('Роберт Лоуренс Стайн', 'Stine R. L.'), ('R. L. Stine', 'Stine R. L.'),
    # Monogatari: series names in the author slot; the author is Нисио Исин (NISIOISIN, Japanese name order).
    ('Моногатари короткие истории', 'Nisio Isin'), ('Ёимоногатари', 'Nisio Isin'), ('Хякумоногатари', 'Nisio Isin'), ('Нисио Исин', 'Nisio Isin'),
    # Garbled or glued tags, fixed from the file or folder name (the corrected author goes into the output tags).
    ('Ìàêñ Áðóêñ', 'Brooks Max'), ('Макс Брукс', 'Brooks Max'),
    ('Ж. Батай. История глаза', 'Bataille Georges'), ('Жорж Батай', 'Bataille Georges'),
    ('Марк Фрост-Последнее досье(genagame)', 'Frost Mark'), ('Марк Фрост', 'Frost Mark'),
    # Co-authors: one joint folder with both names, like «Moor and Kuttner».
    ('Маргарет Уэйс, Трейси Хикмен', 'Weis and Hickman'), ('Стивен Кинг, Питер Страуб', 'King and Straub'),
    ('Стивен Кинг, Ричард Чизмар', 'King and Chizmar'), ('Мэрион Зиммер Брэдли, Дайана Паксон', 'Bradley and Paxson'),
    ('Джон Ллойд, Джон Митчинсон', 'Lloyd and Mitchinson'), ('Адольф де Кастро, Амброз Бирс', 'de Castro and Bierce'),
    ('Стив и Стефани Перри', 'Perry Steve and Stephani'),
    # Duplicate folder pairs already in Sorted: the language rule picks the one.
    # Where an English folder of the pair exists, it is the target as it is (fewest renames).
    ('Карпишин Дрю', 'Drew Karpyshyn'), ('Дрю Карпишин', 'Drew Karpyshyn'),
    ('Zahn Thimoty', 'Zahn Timothy'), ('Тимоти Зан', 'Zahn Timothy'),
    ('Лаймон Ричард Карл', 'Laymon Richard'), ('Ричард Лаймон', 'Laymon Richard'),
    ('Ходжсон Уильям Хоуп', 'Hodgson William Hope'), ('Ходжсон Уильям', 'Hodgson William Hope'),
    ('Хардинг Фрэнсис', 'Frances Hardinge'), ('Фрэнсис Хардинг', 'Frances Hardinge'),
    ('Роулинг Джоан', 'Rowling J. K'), ('Джоан Роулинг', 'Rowling J. K'),
    ('Шваб Виктория', 'Schwab Victoria'), ('Виктория Шваб', 'Schwab Victoria'),
    ('Скальци Джон', 'Scalzi John'), ('Джон Скальци', 'Scalzi John'),
    ('Судзуки Кодзи', 'Suzuki Koji'), ('Кодзи Судзуки', 'Suzuki Koji'),
    ('Вилсон Фрэнсис Пол', 'Wilson F. Paul'), ('Фрэнсис Пол Вилсон', 'Wilson F. Paul'), ('Вилсон Полл', 'Wilson F. Paul'),
    ('Хайнлайн Роберт', 'Heinlein Robert A'), ('Роберт Хайнлайн', 'Heinlein Robert A'),
    ('Симада Содзи', 'Shimada Sōji'), ('島田 荘司 _ Shimada Sōji', 'Shimada Sōji'),
    ('Гжендович Ярослав', 'Jarosław J. Grzędowicz'), ('Ярослав Гжендович', 'Jarosław J. Grzędowicz'),
]
_FOLDERS = [
    # A title in the author slot or folder: the real author (questions 14 and 15; question 7's «На странных берегах»).
    ('same_as', 'Гробница Саргераса', 'Brooks Robert'), ('same_as', 'Пристань желтых кораблей', 'Лукьяненко Сергей'),
    ('same_as', 'Na strannyh beregah', 'Powers Tim'),
    # Anthology series, editors' books and the anthologies that stay together: Сборники / «Разные авторы».
    ('collection', 'Созвездие Льва', ''), ('collection', 'Манускрипты Аркхэма', ''), ('collection', 'Мистика и Ужасы', ''),
    ('collection', 'Пять Вечеров', ''), ('collection', 'Тёмные Аллеи', ''), ('collection', 'Вселенная Дозоров', ''),
    ('collection', 'Разные писатели', ''), ('collection', 'Не Спать!', ''), ('collection', 'ne-spat-german-shenderov', ''),
    ('collection', 'Датлоу Эллен', ''), ("collection", "Мари О'Риган, Пол Кейн", ''), ('collection', 'Д.Костюкевич, М.Парфенов', ''),
    ('collection', 'Стивен Кинг, Бев Винсент', ''), ('collection', 'Хищнец', ''), ('collection', 'home2', ''),
]
_READERS = [
    # Readers or uploaders in the author slot (questions 6-8, 23, 25, 26; ruling 14).
    'BIGBAG', 'Владимир Князев', 'Сергей Бурунов', 'Светлана Смелова', 'Илья Сланевский', 'Юлия Яблонская', 'Puffin Cafe', 'Puffin Сafe',
    'vendigo', 'Пухов Сергей', 'Григорий Перель', 'Максим Суханов', 'Чайцын Александр', 'Петроник', 'Петров Никита',
    'Зачиняев Александр', 'Anna Samoilova', 'Sanyendis',
    'Александр Клюквин', 'Степан Дружинин', 'Олег Булдаков', 'Головин Кирилл', 'Антон Ческидов', 'Игорь Князев', 'Пожилой Ксеноморф',
    'Валерий Смекалов', 'Иванов Станислав', 'Кирсанов Сергей', 'Александр Аравушкин', 'Вероника Райциз', 'Владимир Маслаков',
    'Ксения Большакова', 'Людмила Солоха', 'Михаил Прокопов', 'Айгель Гайсина', 'Александр Дунин', 'Андрей Зверев', 'Артем Пахомов',
    'Беляев Юрий', 'Владимир Зайцев', 'Воробьёва Ирина', 'Вячеслав Герасимов', 'Герасимов В', 'Дементьев Илья', 'Екатерина Бранд',
    'Ирина Зубкова', 'Капитан Абр', 'Кирилл Радциг', 'Макс Потёмкин', 'Максим Суслов', 'Максимова Елена', 'Марк Попов', 'Овуор Владимир',
    'Олег Воротилин', 'Руслан Покровский', 'Семён Мендельсон', 'Сергей Зимин', 'Тамара Швец',
    'sendok', 'Олег Троицкий', 'Воронецкий Станислав', 'Carolyn McCormick', 'Виктор Бабков', 'Юрий Красиков', 'Sonata', 'Алексей Данков',
    'Вероника Чепегина', 'Max Plissken', 'Mystery Basket', 'Stix37', 'nikto1971', 'Алексей Комиссаров', 'Алексей Тихонов', 'Андрей Кузнецов',
    'Библиотекарь', 'Евгения Меркулова', 'И. Зубкова', 'Константиновский Павел', 'Максим Сергеев', 'Мартынова Наталья', 'Никитина Марина',
    'Панкрашкин Андрей', 'Полонецкая Елена', 'Постригайло Г', 'Сергей Габриэлян', 'Стаховский Е', 'Юрий Кузаков',
]
SEEDS = ([('same_as', credit, target, '', None) for credit, target in _SAME]
         + [(kind, credit, target, '', None) for kind, credit, target in _FOLDERS]
         + [('not_author', credit, '', '', None) for credit in _READERS]
         + [
             # «Опочтарение» tagged «Albert Kramer» goes to Pratchett if Kramer is the reader: he is not Pratchett.
             ('not_author', 'Albert Kramer', '', 'Terry Pratchet', None),
             # Titles sitting in the author tag beside the real author.
             ('not_author', 'Ключ судного дня', '', 'James Rollins', None), ('not_author', '22 Лабиринт Менина', '', 'Max Fray', None),
             ('not_author', 'Часть Шестая', '', 'Первый и Единственный', None), ('not_author', 'Goosebumps HorrorLand', '', 'R.L.Stine', None),
             # «Легенды школы №4 г. Пензы»: the author is Волков Роман (a reader on other books).
             ('keep', 'Волков Роман', '', 'Легенды школы №4 г. Пензы', None),
             # Real authors Sergei confirmed (questions 22-24).
             ('keep', 'Джеймс Д. Прескотт', '', '', None), ('keep', 'Прескотт Джеймс Д', '', '', None), ('keep', 'Имакаев Владимир', '', '', None),
             ('keep', 'Андрей Прил', '', '', None), ('keep', 'Баошу', '', '', None),
             # «Лавкрафт» on «Тёмные аллеи 2.2» is the anthology's, not his.
             ('collection', 'Лавкрафт Говард Филлипс', '', 'Тёмные Аллеи', None),
             # The three anthologies stay together in Сборники (question 20): every credit in them is the anthology's.
             ('collection', '*', '', 'Самая страшная книга 2025', None), ('collection', '*', '', 'Калейдоскоп 1-5 (Сборник)', None),
             ('collection', '*', '', 'Сборник рассказов Warhammer 40000 (Casper Valter)', None),
             # Folk tales (Sergei 2026-10-24): the compiler or reteller the files credit, else Сборники.
             ('collection', 'Народный фольклор', '', '', {'fallback': 'compiler'}), ('collection', 'Народные сказки', '', '', {'fallback': 'compiler'}),
             ('collection', 'Русские народные сказки', '', '', {'fallback': 'compiler'}), ('collection', 'Фольклор', '', '', {'fallback': 'compiler'}),
         ])
