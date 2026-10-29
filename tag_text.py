"""Read-side repair of mis-encoded tag text (POST-023-04, 2026-10-29).

Some MP3 uploads store cp1251 bytes in ID3v2 frames marked ISO-8859-1 (encoding byte 0), so ffprobe reads «Терри
Пратчетт» as "Òåððè Ïðàò÷åòò". Thirteen of the 118 files of «Шляпа полная небес» carry such tags: their album and
artist differed from the other 105 files only by that encoding, which split one folder into two books, and the clue
columns showed the raw mojibake. The catalog and the source files keep the raw values (sources are never written);
every reader that groups or identifies a book reads the repaired text through tags() instead.

A value is repaired only when the result is certain: the raw text is mojibake (local_identity.garbled), every
character fits one byte, and the decoded text is readable Cyrillic (at least three Cyrillic letters, itself not
garbled). Text with replacement characters stays as it is: its bytes are lost. Readable Latin names with accents
("Ángel Béjar") are never touched, because they are not garbled. Pure: strings in, strings out.
"""
import re

_CYRILLIC = re.compile('[А-Яа-яЁё]')
# UTF-8 bytes read as cp1251 ("РўРµСЂСЂРё"): the second repair, the same certainty rules.
_UTF8_AS_CP1251 = re.compile('(?:[РС][Ѐ-Џѐ-џҐґ -¿‐-›№™]){2,}')


def _readable(text):
    from local_identity import garbled
    return len(_CYRILLIC.findall(text)) >= 3 and not garbled(text)


def repair(value):
    """(text, repaired): the readable text of a mis-encoded tag value, else the value unchanged and False."""
    if not isinstance(value, str) or not value or value.isascii():
        return value, False
    from local_identity import garbled
    if not garbled(value) or '�' in value:
        return value, False
    if all(ord(c) <= 0xFF for c in value):
        try:
            fixed = value.encode('latin-1').decode('cp1251')
        except (UnicodeEncodeError, UnicodeDecodeError):
            fixed = ''
        if fixed and _readable(fixed):
            return fixed, True
    if _UTF8_AS_CP1251.search(value):
        try:
            fixed = value.encode('cp1251').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            fixed = ''
        if fixed and _readable(fixed):
            return fixed, True
    return value, False


def text(value):
    return repair(value)[0]


def tags(metadata):
    """The tags of one catalog metadata record, keys casefolded, string values repaired. Lists and numbers as stored."""
    found = {}
    for key, value in ((metadata or {}).get('tags') or {}).items():
        found[str(key).casefold()] = repair(value)[0] if isinstance(value, str) else value
    return found


def repaired(metadata):
    """{casefolded key: raw value} of the tags tags() repairs: the clue lines say the text was repaired."""
    found = {}
    for key, value in ((metadata or {}).get('tags') or {}).items():
        if isinstance(value, str) and repair(value)[1]:
            found[str(key).casefold()] = value
    return found


def member_tags(member):
    return tags((member or {}).get('metadata') or {})
