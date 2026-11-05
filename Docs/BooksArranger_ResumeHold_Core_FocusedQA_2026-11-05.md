# Resume hold core: focused QA

**Verdict:** PASS for the committed core regression only.

Source commit: `433885d0b658e8f4096a10e85c12da51e0d4b54e` (clean; matches origin). I ran the private `WorkingLifecycleTests` class from an archive of that commit. All 31 tests passed. The bounded owner exited 0, closed with complete output, and reported zero native residue, no force and no timeout. [Raw result and hashes](Evidence/resume-hold_2026-11-05/futaba-core/summary.json) are preserved.

The normal `resume()` case with a closed prior attempt and an uncaptured producer file left that book in **needs attention**, retained its attempt, manifest, hash, journal, output and source bytes, and completed three independent books without a global stop. An active retained producer likewise held only its book while three independent jobs completed. An unknown staging ownership boundary still stopped the queue, left the peer pending, and preserved the original bytes.

The independent jobs used injected validated output. This proves the queue and lifecycle boundary on private Windows files and SQLite; it does not test actual codec output, a packaged build, the UI, or live library data. UI changes are being handled separately. This is not release clearance.
