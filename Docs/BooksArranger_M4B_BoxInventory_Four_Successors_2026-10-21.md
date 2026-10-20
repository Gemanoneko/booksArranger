# Four historical structural holds: actual successor snapshot

Observed UTC **2026-10-20T21:46:00.001262+00:00**. Query-only snapshot of local `WIP/Books Arranger/data/inventory.sqlite3`: SQLite URI mode=ro, query_only=ON, timeout=0, one BEGIN, rollback/close finally. Standard-library Python through the existing default-PowerShell local read route; original tool chunk78c623, exit0 in0.6354609s. PRAGMA table_info verified required audio_jobs projection columns. No media/NAS, candidate/helper/owner/native module or shared Node kernel access.

The query selected newest non-set-aside job per each of the four exact candidate IDs (`created DESC, job_id DESC`). It did not substitute these jobs into the frozen request. All four candidates remain unsuperseded, current revision5, latest job manifest revision5. All latest reasons are empty.

| Book (label from frozen request) | Candidate ID | Actual latest job ID | State | Updated UTC | Output / intent presence |
|---|---|---|---|---|---|
| ИСТОРИЯ ОДНОЙ ЛЮБВИ | 2aec490f-dead-4b4b-a4ee-4d5c52a11866 | 72a1d4c6-e9fe-4ac5-92fb-98364fe1b928 | completed | 2026-10-20T21:23:01.688482+00:00 | non-NULL / object |
| Бегущий по лезвию бритвы | 76e0dc33-8538-4ea9-b285-5a7297a8a2f6 | 487267be-65c6-447e-ad6e-e4dbe0a33a44 | completed | 2026-10-20T21:39:02.251308+00:00 | non-NULL / object |
| Унылый незнакомец | 8b9b97d4-acfc-4392-9c35-6b935b7fb610 | 8f0591cc-33a7-43b9-95a6-21c51c5fc8b9 | running | 2026-10-20T21:45:03.308861+00:00 | NULL / absent |
| Звонок-0: Рождение | 990784b0-f8a9-48b1-82bd-b45e07a8fc24 | 2c6d6095-164b-4ea0-8c14-a2ecb050d4b5 | completed | 2026-10-20T21:14:33.534978+00:00 | non-NULL / object |

Output means the audio_jobs output column is non-NULL; intent means journal $.publication_intent is an object. This does not verify native file identity/hash, immutable receipt correctness, media integrity, playback or publish/recovery consistency. The old structural-box errors remain historical evidence, not latest errors for these candidates. Ring-3's separate completed output/intent presence observation is in Four_Preflight_Stop; it was not re-queried here.

## Bounded optional aggregate (different from UI scope)

Scope: newest non-set-aside audio job for each candidate, joined to book_groups with superseded=0 AND group revision equal to manifest candidate_revision. Candidates without jobs or without matching revisions are excluded. State counts: **431 completed, 48 needs attention, 1 running (480 total)**. This is a job-state aggregate, not an independently verified approval count or the UI attention definition.

All six state/reason groups were returned (limit48, reason text cap768 characters): completed/empty431; running/empty1; needs attention:

- 44: `Remux changed the decoder configuration or relative audio packet timing`.
- 2: `M4B preservation requires review: Sample size table`.
- 1: full audio decode failure, MP3 Header missing/invalid packet (saved reason; not a new damage diagnosis). Prior Iron Inferno zero-loss TAG proof remains separate; this aggregate did not select its identity.
- 1: `Working cleanup requires attention: A prior producer is not durably closed; another attempt is not admitted`.

There are zero latest unsupported-structural-box reason groups in this explicitly bounded aggregate. This does not prove those source structures supported by every app path; three selected successors completed and the fourth is running. No inference about source/audio harm follows from the old errors.

Global helper active-work definition independently counted **pending0/running1**, without candidate/revision filtering.

## STOP disposition

The old app is progressing. Do not interfere with running work. Frozen request-four.json remains DRAFT and unchanged (SHA89ebf9f7585e4eedb1ab456bbe0de85606c5f191e329358f06c7dda78ccdd1d3). Its historical targets fail latest-job requirements; no automatic substitution, helper execution or new media diagnostic is authorized by this snapshot. Existing v1/v2/v3 artifacts, failed/corrected-query history and scratch are preserved. No further query or live action performed.