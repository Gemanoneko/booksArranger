# Tolkien approval: focused QA

**Verdict:** PASS for committed source `11b1e0227812326da2ea4905a8ebedfe961d13a7`.

The independent private run passed all 74 focused tests after restoring one committed test fixture omitted from my first archive. The first run had nine fixture setup errors and is preserved alongside the successful rerun. Both bounded owners closed with complete output and zero native residue. The five changed source/test files are line ending normalized identical to the pinned commit; [raw evidence and hashes](Evidence/approve-retrieved_2026-11-05/futaba/summary.json) are retained.

The actual `approve_book` entrypoint accepted **Fellowship**, **Two Towers**, **Return of the King**, and the legacy Middle-earth choice. The tests checked persisted review and evidence after reopening, a pending job manifest, unchanged source bytes, no output destination, and no conversion attempt. Malformed or mismatched curated records were refused before writes. Generic manual evidence still required the usual HTTPS URL, time and fields.

The fixtures generated short private M4B sources and used a private catalog. This is focused source verification, not a packaged build or release clearance. No live collection, Z: source, app window or foreground focus was used.
