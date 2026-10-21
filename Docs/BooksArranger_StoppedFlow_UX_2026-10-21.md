# Books Arranger — stopped flow and refused retry feedback

2026-10-21, Judy. EXTEND the existing automatic-processing status, Start/Stop controls, attention rows and shared retry receipt. Spec only; no code, Git, live app/API actions or scratch output. Sully commits this document before Ender receives an implementation brief citing it. Preserve other agents' edits.

## Evidence and limits

Supplied v0.20.2 screenshots show **Automatic processing: Needs attention**, stale **Starting automatic processing…**, both Start/Stop unavailable, research 0 researching / 1218 waiting / 65 held, and a separate failed discovery scan showing database is locked. The retry screenshot shows **Can retry · 0**, **Other · 46**, 46 selected / 44 new retries available, alongside a completed submission with 0 accepted / 44 refused and zero conversion progress. The parent reports a newer automatic-run launch failure under investigation by Ender. Neither the old discovery error nor generic file-problem copy proves the current automatic blocker or any of the 44 refusal causes.

Ender's subsequent diagnosis, supplied by Jane: automatic launch tried to resume both a previously failed scan and a source never scanned, so launch failed before a fresh scan began. Bulk submission rejected the 44 Other rows by group even though their retry permission was true, before fresh file checks. These findings explain the launch/refusal mismatch; they do not establish a file problem in those books. Ender owns both backend corrections.

This extends BulkRetryFeedback UX (2026-10-20) and RefusedRetry UX (2026-10-19). It overrides their wording where a terminal refusal or conditional retry currently looks like progress or guaranteed eligibility. No independent backend diagnosis or release clearance is supplied.

## Current state before historical detail

Within the existing automatic-processing card, put the current state, reason and applicable next action together immediately after Start/Stop. Move the existing state/reason text here; do not add a competing status panel. Order: controls; **Automatic processing: Stopped — needs attention**; one readable current cause; one short action sentence if an action is known. Keep progress/research counts below this block.

- **Starting automatic processing…** exists only while the current start is genuinely pending. Replace it on acknowledgement, refusal, terminal failure or loss of confirmed state. A settled failure cannot retain an in-flight message or spinner.
- Use the current automatic run's typed reason and action. Example only when confirmed: **Automatic processing could not start.** followed by the specific readable reason. If no usable cause is supplied: **Automatic processing stopped. The app did not report a specific reason.** Do not substitute a scanner's older error or guess that folders need fixing.
- A known app fault must not tell Sergei to change his files or repeatedly click Start. Ender supplies the supported action; if none is available say **No action is available here yet.** Keep technical exception/path/stack in existing technical details, not the main status.
- For the confirmed launch fault, readable cause: **The app could not start discovery for all source folders.** Present a supported restart only after the corrected launch path can actually start/resume the appropriate sources. For the confirmed pre-check bulk refusal, readable cause: **The app rejected these retries before checking the files.** Do not show **couldn't read or write a file** for that refusal.
- Retain the discovery failure in Discovery, identified as **Last scan: failed** when it describes an earlier scan. Existing research counts remain factual: waiting is not running. Keep **Nothing running** when no worker is active. Saved work and completed outputs are described only to the extent confirmed by the backend.

## Start and Stop

| Confirmed state | Start automatic processing | Stop automatic processing | Visible explanation |
|---|---|---|---|
| Stopped/failed, backend allows start | Enabled | Disabled | Current failure/reason; **Start automatic processing to continue.** only when that action can continue saved work |
| Stopped/failed, backend blocks start | Disabled | Disabled | Exact current readable block and supported remedy adjacent to controls |
| Start request pending | Disabled | Enabled only if this pending start can be cancelled | **Starting automatic processing…** |
| Active | Disabled | Enabled | Actual active stage |
| Stopping | Disabled | Disabled | **Stopping automatic processing…** until settled |
| Status cannot be confirmed | Disable commands whose safety requires confirmation | Same rule | **Current processing status unavailable.** Last confirmed facts are marked stale |

Button state comes from the authoritative current action permissions, including ownership/launch guards. Conversion queue size, research waiting counts and an old scan failure cannot independently disable Start or imply activity. Both disabled is acceptable only with its current reason visible. Disabled Stop tooltip: **Automatic processing is stopped.** Disabled Start tooltip repeats its visible block reason. Enabled Start/Stop retain their established operation/tooltips; do not silently change Start into a different mode. Server rejection updates the same reason and controls; never leave an optimistic Starting message after rejection.

## Retry eligibility and results

Keep **Can retry** for confirmed new-request eligibility. Preserve **Other** membership for unresolved file problems where a conditional recheck is still supported. Selection summary must distinguish those scopes: for example **46 selected · 44 can be checked again · 2 left out**, with **Previous attempts were refused. Check each book's reason before retrying.** Do not call 44 conditional checks **44 new retries available** when the Can retry group is zero. If no new check can be accepted, show zero actionable targets and disable the bulk button with the actual reason.

Row action, selected count, confirmation target IDs, group membership and server admission must use one coherent projection. Pending requests are never new targets. A current refusal suppresses repeat admission until its supported recheck condition changes or the existing file-problem policy explicitly permits a user-triggered recheck. No change to checked selections. Genuine changing eligibility is revalidated at submission; resulting refusals remain visible.

After this observed zero-accepted batch, shared receipt reads **No retry requests accepted. 44 refused. No conversion started from this request.** Replace **Retry work completed** with **Retry checks finished** only when checks actually finished; submission completion alone says **Retry request finished.** Zero accepted/zero child jobs cannot be presented as conversion success. Mixed outcomes retain **Retry requested for A of T books. R refused.** and the existing correlated lifecycle counts. Never infer zero from missing telemetry.

Every refused row shows its actual readable cause and supported remedy. **Check the folder, then retry** is reserved for a confirmed actionable file access problem; unknown refusal reads **Retry was refused. The app did not report a specific reason.** No invented file diagnosis. Keep technical evidence in existing details. A refused row cannot continue to promise ready-to-retry while that refusal still prohibits admission. Do not add a new button, dialog or provider/metadata choice.

## Verification and accessibility

Apply NN/g system-status/error-recovery principles and WCAG 2.2 AA using existing theme tokens and control geometry. Reasons wrap in normal flow, remain readable without hover, and do not cover controls. Preserve keyboard focus through asynchronous updates; no scrolling, dialogs or focus theft. Existing polite status announces meaningful start/refusal/block/finish changes once; routine counts remain accessible non-live text. Retain visible focus and minimum 24×24 CSS px targets (existing 32px control height).

Futaba checks committed isolated fixtures for terminal automatic launch failure with stale Starting cleared; real start block and remedy; permitted restart with queue zero; active/stopping controls; failed or unknown start acknowledgement; earlier scan error beside a different current blocker; zero accepted/44 refused; conditional Other checks versus Can retry counts; mixed/pending selection; cause-specific and unknown refusal copy. Exercise keyboard and long wrapping reasons at 1440/1024/700px and 200% zoom in supported themes. Report measured target rectangles and intersections for controls affected by wrapping. No hit-area, runtime, contrast or screen-reader measurements claimed in this spec.
