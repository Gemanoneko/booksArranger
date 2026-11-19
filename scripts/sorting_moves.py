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


def _health(port):
    """The app answering on this port (its /api/health: name, version, process, port)."""
    with urllib.request.urlopen('http://127.0.0.1:%d/api/health' % port, timeout=30) as answer:
        return json.loads(answer.read().decode('utf-8'))


DONE = ('move_queued', 'series_update_queued', 'unchanged')


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
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    # The default port is Sergei's own app (where the moves are applied): say which app this is before anything else.
    health = _health(args.port)
    print('Talking to %s %s at 127.0.0.1:%d (process %s).' % (health.get('application') or 'an app', health.get('version') or '(version unknown)',
                                                           args.port, health.get('pid') or '?'))
    token = _token(args.port)
    plan = _call(args.port, '/api/sorting-moves', {}, token)
    print('Its list: %d book%s to move, %d left as they are. Digest: %s' % (len(plan['items']), '' if len(plan['items']) == 1 else 's',
                                                                            len(plan['refused']), plan['digest']))
    if not args.apply:
        import sorting_moves
        print(sorting_moves.markdown(plan))
        print('To move exactly these books: python scripts/sorting_moves.py --apply <the digest above>')
        return 0
    if args.apply != plan['digest']:
        print('The digest you gave is not this list\'s digest; the app will refuse it and move nothing.')
    body = {'digest': args.apply}
    if args.jobs:
        body['job_ids'] = args.jobs
    answer = _call(args.port, '/api/sorting-moves/apply', body, token)
    for result in answer['results']:
        print(result['job_id'], result['state'], result.get('reason') or result.get('to') or (result.get('move') or {}).get('target') or '')
    # Futaba's 0.30.0 QA, C3: any book that was not moved or queued (refused, not in the list) is an error exit.
    missed = [result for result in answer['results'] if result.get('state') not in DONE]
    if missed:
        print('%d of the books you named did not move; see the lines above.' % len(missed))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
