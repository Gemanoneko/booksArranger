"""Bounded metadata proposals. Catalog matches never establish recording identity.

MetadataClient.lookup(query, author='') returns a list of proposal dictionaries.
Injected transport(url, timeout, max_bytes) returns bytes; it must obey those bounds.
Production transport refuses redirects. No arbitrary source/cover URL is fetched.
"""
import datetime as dt
import ipaddress
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 512 * 1024
MAX_RESULTS = 5
_PROVIDER_NEXT = {}
_PROVIDER_LOCK = threading.Lock()
FIELDS = {'title', 'authors', 'original_language', 'series', 'number', 'cover_url',
          'narrator', 'author_folder', 'standalone'}


class SourceUnavailable(Exception):
    """Sanitized provider error; manual review remains possible."""
    def __init__(self, provider, code, retry_after=None):
        self.provider, self.code, self.retry_after = provider, code, retry_after
        super().__init__('Metadata source unavailable. Review cached evidence or enter verified metadata manually.')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _transport(url, timeout, max_bytes):
    request = urllib.request.Request(url, headers={'User-Agent': 'BooksArranger/metadata-review',
                                                 'Accept': 'application/json'})
    # Disable environment proxy forwarding; the only destinations are fixed HTTPS APIs.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=timeout) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError('Response exceeds bound')
        return data


def _text(value, limit=1000):
    return value[:limit].strip() if isinstance(value, str) else ''


def public_source_url(value):
    """Validate a public HTTPS citation syntactically, without fetching or DNS lookup."""
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 33 for c in value):
        raise ValueError('Source URL must be a public HTTPS URL')
    try:
        parsed = urllib.parse.urlsplit(value)
        host = (parsed.hostname or '').lower().rstrip('.')
        port = parsed.port
    except ValueError:
        raise ValueError('Invalid source URL') from None
    if parsed.scheme != 'https' or parsed.username or parsed.password or port not in (None, 443):
        raise ValueError('Source URL must use HTTPS without credentials')
    if not host or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.test')):
        raise ValueError('Source URL must identify a public source')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if '.' not in host or not re.fullmatch(r'[a-z0-9.-]+', host) or any(not label or label.startswith('-') or label.endswith('-') for label in host.split('.')):
            raise ValueError('Source URL must identify a public source')
    else:
        if not address.is_global:
            raise ValueError('Source URL must identify a public source')
    return value


def manual_evidence(field, cited_value, source_url, retrieved_utc, reviewer_actor,
                    reviewer_identity, basis):
    """Return validated evidence only; this does not approve a field or fetch its URL."""
    if field not in FIELDS or reviewer_actor not in ('user', 'assistant'):
        raise ValueError('Unknown evidence field or reviewer actor')
    if not isinstance(cited_value, (str, list, bool)) or (isinstance(cited_value, str) and (not cited_value.strip() or len(cited_value) > 2000)):
        raise ValueError('Supply the cited field value')
    if isinstance(cited_value, list) and (not cited_value or len(cited_value) > 30 or any(not isinstance(v, str) or not v.strip() or len(v) > 200 for v in cited_value)):
        raise ValueError('Invalid cited values')
    for value in (reviewer_identity, basis):
        if not isinstance(value, str) or not value.strip() or len(value) > 4000:
            raise ValueError('Reviewer identity and evidence basis are required')
    try:
        stamp = dt.datetime.fromisoformat(retrieved_utc.replace('Z', '+00:00'))
        if stamp.utcoffset() != dt.timedelta(0):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Retrieval date must be UTC ISO 8601') from None
    return {'field': field, 'cited_value': list(cited_value) if isinstance(cited_value, list) else cited_value, 'source_url': public_source_url(source_url),
            'retrieved_utc': stamp.isoformat().replace('+00:00', 'Z'),
            'reviewer_actor': reviewer_actor, 'reviewer_identity': reviewer_identity.strip(),
            'basis': basis.strip(), 'verification': 'manual review', 'needs_review': True}


class MetadataClient:
    def __init__(self, provider='openlibrary', api_key=None, transport=None,
                 timeout=10, result_limit=3, clock=time.monotonic):
        if provider not in ('openlibrary', 'googlebooks'):
            raise ValueError('Unsupported metadata provider')
        if not 0 < timeout <= 15 or not 1 <= result_limit <= MAX_RESULTS:
            raise ValueError('Invalid request bounds')
        if api_key is not None and (not isinstance(api_key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', api_key)):
            raise ValueError('Invalid optional credential')
        self.provider, self._api_key = provider, api_key
        self._transport, self._clock = transport or _transport, clock
        self._production_transport = transport is None
        self.timeout, self.result_limit = timeout, result_limit
        self._next_request = 0
        self._cache = {}
        self._lock = threading.Lock()

    def cached(self, query, author=''):
        """Copy cached proposals; failure never discards prior successful evidence."""
        return json.loads(json.dumps(self._cache.get(self._query_key(query, author), [])))

    @staticmethod
    def _query_key(query, author):
        if not isinstance(query, str) or not query.strip() or len(query) > 300 or not isinstance(author, str) or len(author) > 200:
            raise ValueError('Supply a bounded title query and optional author')
        return (' '.join(query.split()), ' '.join(author.split()))

    def lookup(self, query, author=''):
        query, author = self._query_key(query, author)
        with self._lock:
            if (query, author) in self._cache:
                return self.cached(query, author)
            if self.provider == 'googlebooks' and not self._api_key:
                raise SourceUnavailable(self.provider, 'credential_required')
            now = self._clock()
            if now < self._next_request:
                raise SourceUnavailable(self.provider, 'cooldown', self._next_request - now)
            self._next_request = now + 1.05
            if self._production_transport:
                with _PROVIDER_LOCK:
                    production_now = time.monotonic()
                    if production_now < _PROVIDER_NEXT.get(self.provider, 0):
                        raise SourceUnavailable(self.provider, 'cooldown', _PROVIDER_NEXT[self.provider] - production_now)
                    _PROVIDER_NEXT[self.provider] = production_now + 1.05
            if self.provider == 'openlibrary':
                parameters = {'title': query, 'limit': self.result_limit,
                              'fields': 'key,title,author_name,language,cover_i,edition_key'}
                if author:
                    parameters['author'] = author
                url = 'https://openlibrary.org/search.json?' + urllib.parse.urlencode(parameters)
            else:
                parameters = {'q': query + (' inauthor:' + author if author else ''),
                              'maxResults': self.result_limit, 'key': self._api_key}
                url = 'https://www.googleapis.com/books/v1/volumes?' + urllib.parse.urlencode(parameters)
            try:
                raw = self._transport(url, self.timeout, MAX_BYTES)
                if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
                    raise ValueError()
                if self._api_key and self._api_key.encode('utf-8') in raw:
                    raise SourceUnavailable(self.provider, 'provider_rejected')
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError()
                if 'error' in payload:
                    raise SourceUnavailable(self.provider, 'provider_rejected')
                proposals = self._parse(payload)
            except SourceUnavailable:
                raise
            except urllib.error.HTTPError as exc:
                code = 'rate_limited' if exc.code == 429 else 'provider_rejected'
                if exc.code == 429:
                    self._next_request = self._clock() + 30
                    if self._production_transport:
                        with _PROVIDER_LOCK:
                            _PROVIDER_NEXT[self.provider] = time.monotonic() + 30
                raise SourceUnavailable(self.provider, code) from None
            except (TimeoutError, OSError):
                raise SourceUnavailable(self.provider, 'connection_failed') from None
            except Exception:
                # Never echo transport exceptions: they can contain keyed request URLs.
                raise SourceUnavailable(self.provider, 'invalid_response') from None
            self._cache[(query, author)] = proposals
            if len(self._cache) > 100:
                del self._cache[next(iter(self._cache))]
            return self.cached(query, author)

    def _parse(self, payload):
        rows = payload.get('docs' if self.provider == 'openlibrary' else 'items', [])
        if not isinstance(rows, list):
            raise ValueError()
        stamp = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
        proposals = []
        for row in rows[:self.result_limit]:
            if not isinstance(row, dict):
                continue
            if self.provider == 'openlibrary':
                record = _text(row.get('key'))
                if not re.fullmatch(r'/works/OL[0-9]+W', record):
                    continue
                public_url = 'https://openlibrary.org' + record
                title, authors = _text(row.get('title')), row.get('author_name', [])
                languages = row.get('language', [])
                cover_id = row.get('cover_i')
                cover = 'https://covers.openlibrary.org/b/id/%s-L.jpg' % cover_id if type(cover_id) is int and 0 < cover_id < 10**12 else None
            else:
                record = _text(row.get('id'))
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', record):
                    continue
                info = row.get('volumeInfo', {})
                if not isinstance(info, dict):
                    continue
                public_url = 'https://books.google.com/books?id=' + record
                title, authors = _text(info.get('title')), info.get('authors', [])
                languages = [info.get('language')] if info.get('language') else []
                links = info.get('imageLinks', {})
                cover = None
                clue = links.get('thumbnail') if isinstance(links, dict) else None
                if isinstance(clue, str):
                    parsed = urllib.parse.urlsplit(clue)
                    if parsed.hostname in ('books.google.com', 'books.googleusercontent.com') and not parsed.username and not parsed.password and parsed.port in (None, 443) and parsed.scheme == 'https':
                        cover = clue[:2048]
            authors = [_text(item, 200) for item in authors[:30] if _text(item, 200)] if isinstance(authors, list) else []
            if not title:
                continue
            evidence = {field: {'cited_value': value, 'public_url': public_url,
                               'record_id': record, 'retrieved_utc': stamp,
                               'basis': 'Catalog work/edition record; recording unverified'}
                        for field, value in [('title', title), ('authors', authors)] if value}
            proposals.append({'provider': self.provider, 'record_id': record, 'public_url': public_url,
                              'retrieved_utc': stamp, 'title': title, 'authors': authors,
                              'original_language': None, 'series': None, 'number': None,
                              'edition_languages': [_text(x, 30) for x in languages[:30] if _text(x, 30)] if isinstance(languages, list) else [],
                              'cover_url': cover, 'cover_evidence': 'Work cover; recording edition unverified' if cover else None,
                              'per_field_evidence': evidence, 'needs_review': True,
                              'recording_verified': False,
                              'match_label': 'Catalog proposal; recording unverified',
                              'limitations': ['Original-work language not established', 'Series identity and position not established', 'Catalog authors are proposals; author role requires review']})
        return proposals
