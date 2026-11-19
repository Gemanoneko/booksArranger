"""0.30.0 sorting moves (Sergei 2026-11-18, items 2, 5 and 6): the explicit command that lists, and on approval runs, the
moves of books already in Audiobooks Sorted, through the running Books Arranger (its engine runs every move: the app's
usual verified move; this script only asks).

  python scripts/sorting_moves.py [--port 5210]                 list the planned moves (Markdown) and their digest
  python scripts/sorting_moves.py --apply DIGEST [--job ID ...]  approve that exact list (or some of its books) and run it

Nothing moves without --apply and the digest of the list you read; a list that changed since is refused, nothing moved.
Talks only to the local app at 127.0.0.1 (its page's own request token); writes no file."""
import argparse
import json
import pathlib
import re
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def _call(port, path, data, token):
    request = urllib.request.Request('http://127.0.0.1:%d%s' % (port, path), data=json.dumps(data).encode('utf-8'), method='POST',
                                     headers={'Content-Type': 'application/json', 'X-Books-Token': token})
    try:
        with urllib.request.urlopen(request, timeout=600) as answer:
            return json.loads(answer.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        raise SystemExit('Books Arranger refused: ' + error.read().decode('utf-8', 'replace')[:500])


def _token(port):
    with urllib.request.urlopen('http://127.0.0.1:%d/' % port, timeout=30) as page:
        found = re.search(r'name="books-token" content="([^"]+)"', page.read().decode('utf-8'))
    if not found:
        raise SystemExit('Books Arranger did not answer with its page; is it running on port %d?' % port)
    return found[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--port', type=int, default=5210)
    parser.add_argument('--apply', metavar='DIGEST')
    parser.add_argument('--job', action='append', dest='jobs')
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    token = _token(args.port)
    if not args.apply:
        import sorting_moves
        print(sorting_moves.markdown(_call(args.port, '/api/sorting-moves', {}, token)))
        print('To move exactly these books: python scripts/sorting_moves.py --apply <the digest above>')
        return 0
    body = {'digest': args.apply}
    if args.jobs:
        body['job_ids'] = args.jobs
    answer = _call(args.port, '/api/sorting-moves/apply', body, token)
    for result in answer['results']:
        print(result['job_id'], result['state'], result.get('reason') or result.get('to') or (result.get('move') or {}).get('target') or '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
