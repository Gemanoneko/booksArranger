"""Read source metadata and propose paths. This module never writes source files."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

AUDIO = {'.mp3', '.m4a', '.m4b', '.aac', '.flac', '.ogg', '.opus', '.wav', '.wma', '.aax', '.aa'}
EBOOK = {'.epub', '.fb2', '.pdf', '.mobi', '.azw', '.azw3', '.djvu', '.txt', '.doc', '.docx', '.rtf'}
GENRES = ('Science Fiction', 'Fantasy', 'Horror', 'Adventure', 'Mystery & Thriller', 'Nonfiction', "Children's Tales")
MAX_XML = 8 * 1024 * 1024

class ScanStopped(Exception):
    pass

def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value or '')).strip().rstrip('. ')
    if value.upper().split('.')[0] in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        value = '_' + value
    return value[:160].rstrip('. ') or '_'

def _xml(data):
    if len(data) > MAX_XML or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Oversize or entity-bearing metadata XML; review manually')
    return ET.fromstring(data)

def _text(node):
    return ' '.join(''.join(node.itertext()).split())

def read_metadata(path, kind, stop):
    result = {'title': '', 'author': '', 'series': '', 'number': '', 'edition_language': '',
              'genre': '', 'tags': {}, 'notes': [], 'method': 'filename only'}
    ext = Path(path).suffix.lower()
    if ext in AUDIO:
        probe = shutil.which('ffprobe')
        if not probe:
            result['notes'].append('ffprobe unavailable; audio metadata not read')
            return result
        # Only read bounded textual metadata; no playback, conversion or cover extraction.
        process = subprocess.Popen([probe, '-v', 'error', '-show_format', '-show_streams',
                                    '-of', 'json', str(path)], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + 15
        try:
            while True:
                if stop.is_set():
                    raise ScanStopped()
                if time.monotonic() > deadline:
                    raise TimeoutError('Audio metadata read exceeded 15 seconds')
                try:
                    stdout, stderr = process.communicate(timeout=.15)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode:
                raise ValueError(stderr.decode('utf-8', 'replace')[:300] or 'ffprobe failed')
            if len(stdout) > MAX_XML:
                raise ValueError('Metadata larger than 8 MB; review manually')
            raw = json.loads(stdout)
            tags = raw.get('format', {}).get('tags', {})
            lower = {k.lower(): v for k, v in tags.items()}
            result.update(tags=tags, probe=raw, method='embedded audio tags',
                          artist=lower.get('artist', ''),
                          album_artist=lower.get('album_artist') or lower.get('albumartist', ''),
                          title=lower.get('album') or lower.get('title', ''),
                          track_title=lower.get('title', ''),
                          author=lower.get('album_artist') or lower.get('artist', ''),
                          series=lower.get('series', ''),
                          number=lower.get('series-part') or lower.get('series_part', ''),
                          genre=lower.get('genre', ''), edition_language=lower.get('language', ''))
            result['notes'].append('Source ARTIST/ALBUMARTIST are unverified role clues; neither author nor reader is inferred')
            if ext in {'.aax', '.aa'}:
                result['notes'].append('Potentially protected format; no conversion attempted')
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
    elif ext == '.epub':
        with zipfile.ZipFile(path) as book:
            def member(name):
                item = book.getinfo(name)
                if item.file_size > MAX_XML:
                    raise ValueError('Oversize EPUB metadata; review manually')
                return book.read(item)
            container = _xml(member('META-INF/container.xml'))
            rootfile = next((n.attrib.get('full-path') for n in container.iter()
                             if n.tag.split('}')[-1] == 'rootfile'), None)
            if not rootfile:
                raise ValueError('EPUB package path unavailable')
            opf = _xml(member(rootfile))
            fields = {}
            for node in opf.iter():
                tag = node.tag.split('}')[-1]
                if tag in {'title', 'creator', 'language', 'subject', 'description', 'publisher', 'identifier'}:
                    fields.setdefault(tag, []).append(_text(node))
            result.update(title='; '.join(fields.get('title', [])), author='; '.join(fields.get('creator', [])),
                          edition_language='; '.join(fields.get('language', [])),
                          genre='; '.join(fields.get('subject', [])), tags=fields, method='EPUB package metadata')
            for node in opf.iter():
                if node.attrib.get('name') == 'calibre:series':
                    result['series'] = node.attrib.get('content', '')
                elif node.attrib.get('name') == 'calibre:series_index':
                    result['number'] = node.attrib.get('content', '')
    elif ext == '.fb2':
        with open(path, 'rb') as source:
            raw = source.read(MAX_XML + 1)
        tree = _xml(raw)
        info = next((n for n in tree.iter() if n.tag.split('}')[-1] == 'title-info'), None)
        if info is not None:
            fields = {}
            authors = []
            for node in info:
                tag = node.tag.split('}')[-1]
                fields.setdefault(tag, []).append(_text(node))
                if tag == 'author':
                    authors.append(' '.join(_text(part) for part in node if part.tag.split('}')[-1] in {'first-name', 'middle-name', 'last-name', 'nickname'}))
                elif tag == 'sequence':
                    result.update(series=node.attrib.get('name', ''), number=node.attrib.get('number', ''))
            result.update(title='; '.join(fields.get('book-title', [])), author='; '.join(authors),
                          edition_language='; '.join(fields.get('lang', [])), genre='; '.join(fields.get('genre', [])),
                          tags=fields, method='FB2 title metadata')
    else:
        result['notes'].append('Embedded metadata not read for this format in milestone 1')
    if kind == 'podcast':
        result['notes'].append('Podcast: preserve one episode/file and existing classification; never merge')
    if not result['title']:
        result['notes'].append('Title unavailable; filename remains an unverified clue')
    return result

def audiobook_sort_title(review):
    """Ignore only the leading English word The; keep the displayed title intact."""
    title = review.get('title') or ''
    if review.get('original_language') == 'Other':
        match = re.match(r'^The\s+(\S.*)$', title, re.IGNORECASE)
        if match:
            return match.group(1)
    return title


def future_audio_tags(metadata, review=None):
    """Preview roles without changing a source tag or treating source artists as authors."""
    review = review or {}
    author = (review.get('canonical_author') or review.get('author') or '').strip()
    narrator = (review.get('narrator') or '').strip()
    comments = []
    comment_fields = []
    for key,value in metadata.get('tags',{}).items():
        if key.lower() in {'comment','comments','\xa9cmt'}:
            values = value if isinstance(value,list) else [value]
            for item in values:
                comments.append(str(item))
                comment_fields.append({'field':key,'value':str(item)})
    original_comments = '\n'.join(comments)
    narrator_line = 'Narrator: ' + narrator if narrator else ''
    output_comments = original_comments
    appended = bool(narrator_line and narrator_line not in original_comments.splitlines())
    if appended:
        output_comments += ('\n' if output_comments else '') + narrator_line
    return {'ARTIST':author, 'COMMENTS':output_comments, 'SORTTITLE':audiobook_sort_title(review), 'existing_comments':original_comments,
            'comment_fields':comment_fields,'narrator':narrator,'narrator_appended':appended,
            'artist_from_folder':bool(author and not review.get('canonical_author')),
            'status':'Reviewed author identity' if author else 'Needs author verification',
            'note':'Future tag preview only. Source tags and supplemental metadata remain untouched.'}

def propose(path, root, kind, metadata, review=None):
    """A usable path requires human-confirmed canonical identity, never guessed translations."""
    if kind == 'podcast':
        return {'confidence': 'Preserve', 'path': path,
                'reason': 'Keep current podcast file and tags; no audiobook conversion proposed'}
    if kind == 'companion':
        return {'confidence': 'Needs review', 'path': '', 'reason': 'Companion/unsupported file; associate with a book before arranging'}
    if not review:
        return {'confidence': 'Needs review', 'path': '',
                'reason': 'Confirm original language, canonical title and surname-first author; embedded language describes this edition'}
    anthology = kind == 'audiobook' and review.get('anthology') is True
    required = ['title', 'original_language'] + ([] if anthology else ['author'])
    if any(not review.get(key) for key in required) or review['original_language'] not in {'Russian', 'Other'}:
        return {'confidence': 'Needs review', 'path': '', 'reason': 'Canonical identity and original language incomplete'}
    author_credit = review.get('canonical_author') or review.get('author') or ''
    if anthology and not author_credit.strip():
        return {'confidence':'Needs review','path':'','reason':'Confirm author credits for the collection; no author placeholder is invented'}
    language_names = review['title'] + (author_credit if anthology else review['author'])
    if review['original_language'] == 'Other' and re.search('[А-Яа-яЁё]', language_names):
        return {'confidence': 'Needs review', 'path': '', 'reason': 'Non-Russian originals need English canonical title and author'}
    title, author = safe_name(review['title']), safe_name(author_credit if anthology else review['author'])
    series, number = safe_name(review['series']) if review.get('series') else '', review.get('number', '').strip()
    if review.get('multi_author') and not series and not anthology:
        return {'confidence': 'Needs review', 'path': '', 'reason': 'Multi-author series routing requires a confirmed series'}
    pieces = [root]
    if kind == 'ebook':
        if review.get('genre') not in GENRES:
            return {'confidence': 'Needs review', 'path': '', 'reason': 'Choose one of the seven approved main genres'}
        # Multi-author cycles live at the ebook library root, per user instruction.
        if review.get('multi_author'):
            if not number:
                return {'confidence': 'Needs review', 'path': '', 'reason': 'Confirm the multi-author series position; do not invent a number'}
            pieces.extend([series, f'{series} - {safe_name(number)} - {title} - {author}{Path(path).suffix}'])
            return {'confidence': 'Reviewed preview', 'path': os.path.join(*pieces), 'reason': 'Reviewed path preview only; original extension/bytes preserved, no source changes'}
        else:
            pieces.append(review['genre'])
            if review['genre'] == 'Nonfiction':
                if not review.get('topic'):
                    return {'confidence': 'Needs review', 'path': '', 'reason': 'Nonfiction requires a confirmed topic'}
                pieces.append(safe_name(review['topic']))
            pieces.append(author)
            if series:
                pieces.append(series)
        pieces.extend([title, Path(path).name])
    else:
        if anthology:
            pieces.append('Сборники')
            if series:
                pieces.append(series)
        else:
            pieces.append(series if review.get('multi_author') else author)
        if series and not number:
            return {'confidence': 'Needs review', 'path': '', 'reason': 'Confirm series position; do not invent a number'}
        filename = f'{series} - {safe_name(number)} - {title} - {author}.m4b' if series else f'{title} - {author}.m4b'
        pieces.append(filename)
    note = 'Reviewed path preview only; no source changes'
    if kind == 'audiobook':
        note += '; folder/track-to-book grouping still needs verification before future conversion'
    return {'confidence': 'Reviewed preview', 'path': os.path.join(*pieces), 'reason': note}
