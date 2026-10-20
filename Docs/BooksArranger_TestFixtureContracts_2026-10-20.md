# Books Arranger test fixture contracts —2026-10-20

Scope: exactly three test methods; no product behavior changes. Baseline evidence was saved before edits. The QA-native source packet stays frozen; earlier compiler NORESULT is neither retried nor treated as closed.

## Shipped0469966 contract proof

Read-only Git show0469966:public_research.py saved exact source to C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/conflict-v019-source/public_research.py, SHA256 7945971132b819029e00c8f3f10bd91a12a0ce6451c8ea8269c453f653a5d0d4. Structured call proof and prior causal-control record: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/conflict-v019-source/fixture-contract-baseline-callproof.json.

Shipped constructor lines445–448 accepts explicit local_index; otherwise reads client.database. A NoCatalog object without database must supply the index independently before testing missing-catalog sibling fail-closed behavior:

~~~python
    def __init__(self,client,leads=None,local_index=None):
        from pathlib import Path
        self.client=client;self.leads=source_leads() if leads is None else leads
        self.local_index=Path(local_index) if local_index is not None else Path(client.database).parent/'openlibrary-index'
~~~

Shipped _gap_fill already asks _series_publisher only after the optional series gap remains unanswered. Its Wikipedia revision/reference bridge and DuckDuckGo publisher-page search discover primary pages; they do not authorize identity replacement or narrative series order themselves:

~~~python
            if series:found['series']=series
            if not series:
                series=attempt('publisher',lambda:self._series_publisher(title,author,stop,budget,result))
                if series:found['series']=series
        if not urls:
            # Wikipedia's fetched revision/reference bridge is discovery only. Its
            # text, infobox or list positions do not authorize an ordinal here.
            wiki_wait=None
            try:
                wiki=self.client.wikipedia('"'+title+'" '+author,stop,budget)
                result['sources'].extend(wiki['sources']);urls.extend(wiki['leads'])
            except ResearchWait as wait:wiki_wait=wait
            if not urls:
                try:urls.extend(self.client.discover('"'+title+'" '+author+' publisher',stop,budget))
                except ResearchWait:
                    if wiki_wait:raise wiki_wait
                    raise
            if not urls and wiki_wait:raise wiki_wait
        for url in list(dict.fromkeys(urls))[:2]:
            if not re.fullmatch(r'https://www\.penguinrandomhouse\.com/books/[1-9]\d{0,11}/[a-z0-9-]+/',str(url)):continue
            raw=self.client.read(url,stop,budget)
            found=prh_series(raw,url,title,author,title_key,_same_people)
            if found:
                self._gap_receipt(url,result,url,['title','authors','series','number'])
                if local_match:found['local_identity']={'work':local_match,'index_sha256':local['receipt']['sha256'],'source_manifest':local['receipt']['source_manifest']}
                return found
        return None
~~~

The current _series_publisher retains this same discovery chain. These fixture expectations therefore predate today's product edits.

## Prior causal evidence and limits

Docs/BooksArranger_MetadataConflicts_2026-10-20.md records all three exact failures rerun with public_research.source_gate replaced by the immutable0469966 function; they reproduced unchanged. The127-test related run passed with these exact three excluded, in36.507sec, native supervisor ok/closed true, active0/unsignaled0/zero true. Original immutable source_identity.py/local_identity.py snapshots remain beside the new shipped public_research.py under shared/conflict-v019-source. No separate earlier raw causal-run receipt was persisted; the structured evidence explicitly records that limit instead of fabricating one.

Correction plan: the NoCatalog fixture passes self.database.parent/'openlibrary-index', preserving _siblings→UNREADABLE. The two local-agreement gap tests return EMPTY Wikipedia leads/sources and EMPTY publisher discovery from narrowly bounded mocks, retain strict original network host restrictions, require exactly one fixture-bound discovery query of each kind, and preserve title/author identity, source/citation and optional-gap assertions. No series may be adopted from these empty responses.

Focused execution pending; only one coherent group of these three methods will run under existing reviewed native owner600000. No canonical QA/release receipt is implied.


## Exact correction and focused result

Only the assigned three methods changed; byte comparison confirms all bytes outside those method bodies stayed unchanged. Exact before/after method diff is saved to C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/conflict-v019-source/fixture-method-diff.json, SHA256 79998b1254e4e9365c38cc282fd8b47d58c6e2821f9ff533ec49861d40b01741.

- C3 NoCatalog passes explicit local_index=self.database.parent/'openlibrary-index'; the original missing-catalog _siblings→UNREADABLE assertion remains.
- Both gap tests now mock wikipedia→{sources:[],leads:[]} and discover→[]. Each must be called exactly once. Wikipedia query must equal the fixture title plus either of its two accepted exact author spellings; DuckDuckGo publisher query must be exactly that same query+' publisher'. Original strict real-fetch host set remains api.fantlab.ru/www.wikidata.org/www.goodreads.com. No broad host allowance was added.
- All original title/author/work/source/citation/wait/policy assertions remain. Both tests explicitly reject any verified_series and require series_state=omitted_unknown; discovery cannot supply an unproven series or replace local identity.

One coherent focused invocation ran exactly those three methods once. Result:3/3 PASS in0.159sec; native owner elapsed605.1742ms, ok=true, closed=true, forced=false, timedOut=false, truncated=false, active0, retained4, unsignaled0, zero=true. Receipt C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/conflict-v019-source/fixture-contracts-focused-receipt.json, SHA256 80be97e4f4c6a9263d25e9f0e6375089fba003cb674616f1d6caf009f086856e. Fixtures use private per-method temporary databases below session shared/fixture-contracts; no live catalog/provider/network/media/app was touched. No further suite was run. This is focused test evidence, not a canonical QA/release receipt.

Current test-file pins: tests/test_local_identity_fixes.py SHA256 4b851ea005889c5b98be489a8dd809b0a271a215a60b862dc58288ca9d963005; tests/test_local_identity.py SHA256 890c77b735f0b96e8ad5de1937199699a64e35b765f52cc7dae97ee5c8b4b5b3. Shipped baseline snapshot and prior causal-proof record remain preserved. Earlier native launcher compiler NORESULT is still unknown and unrelated to this successful new test-owned Job; no compiler rerun/new binary execution/PID cleanup occurred.
