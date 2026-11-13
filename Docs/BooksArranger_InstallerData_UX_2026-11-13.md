# Books Arranger installer and retained-data UX — 2026-11-13

**Active scope:** Sergei explicitly requested an installer option to discover/use an old database or start anew, and an uninstaller option to keep data or completely clean Books Arranger's data at an old location. This is the current authorized extension of 0.27.0. Local I: replaces the earlier NAS target. `BooksArranger_Storage_UX_2026-11-13.md` remains an earlier cancelled draft; this document is the active installer/uninstaller spec.

No live installation, data switch or deletion is authorized by this spec. Ender owns discovery, native file identity, migration and cleanup safety. Sully must commit this prerequisite before implementation cites it.

## Native wizard and scope

Use the existing assisted per-user NSIS wizard, stock Windows controls, native font, system colors, keyboard navigation and DPI scaling. Add the pages below; do not create a second application-style installer. Preserve the actual installation directory on upgrade and the normal per-machine default on a fresh second computer. Do not hardcode I: for every installation.

The installer selects an application folder and a database; **using an existing database does not move or reset it**. The separate approved migration operation handles relocation. Existing source/output library folders are never installation/cleanup targets. Closing Books Arranger's window may leave jobs running: wizard copy must request **Quit**, not merely Close.

Pinned-source feasibility: `node_modules/app-builder-lib/templates/nsis/assistedInstaller.nsh` has `customPageAfterChangeDir` before installation and `customUnWelcomePage` before uninstallation. Its `customUninstallPage` is after the uninstall progress page and cannot collect advance destructive consent. Directory normalization may append the application name in `instFilesPre`; the review page must show the final resolved target. This is evidence of extension points, not a tested integration or permission to bypass the canonical build.

## Installer sequence

1. Existing native application-directory page.
2. **Database** page, with automatic bounded discovery and explicit existing/new choice.
3. **Ready to install** summary; the stock Install action commits the reviewed choices.
4. Existing install progress and completion page.

### Database page

Intro: **Use an existing database to keep its books, settings and job history, or start with a separate empty database.** Existing profile/settings association must be verified by the helper before the wizard claims it can preserve those settings; display **Settings location not confirmed** when association is unknown.

Two radio choices, in this order:

- **Use an existing database** — selected initially. On an upgrade, preserve the installation's verified configured database as the selected result. Otherwise one valid result may be highlighted, but the user still reviews it before Install; multiple distinct results have no implicit winner.
- **Start with a new database** — explicit opt-in. Subtitle: **Your existing databases and libraries will be kept.**

Under the existing choice, show **Looking for databases…**, then a single-select result list. Each row shows a full path and one short state: **Available**, **In use**, **Access denied**, **Location unavailable**, **Unsupported database**, or **Could not check**. A selected row's details show database size, associated data/profile locations where known, and the native resolved location if it differs from the displayed path. Never display a database's book titles, credentials or secret settings in this wizard.

Discover only bounded known installation registrations/configuration and known Books Arranger locations on available drives. Do not scan every folder on every disk or follow library trees. The UI does not claim broader coverage than the helper actually checked. Duplicate paths to the same native database are one result with aliases visible in details; two different databases remain distinct even if their names match. Inspection is read-only and WAL-aware; the wizard never changes journal mode, initializes a schema or upgrades a discovered file to identify it.

Actions below the list: **Browse…** and **Check again**. Browse opens a native existing-file picker for SQLite database files, with an All files option, and then applies the same checks. Cancel leaves the current choice intact. Check again refreshes bounded discovery and the selected result without changing existing/new choice or selecting another catalog silently. Next is disabled while inspection runs or until the chosen result is usable.

Empty scan copy: **No database was found in the locations checked. Browse for one or start with a new database.** If any location failed inspection, instead show **Some locations could not be checked. Review their status or browse for your database.** Keep failed locations visible; never turn an access/network failure into a false no-database result.

When new is selected, replace the result area with **New data folder**, a full-path field and **Browse…** folder picker. Offer the helper's per-installation default; show it explicitly. Require a distinct empty target that passes the same local-volume/access/ownership constraints. Existing files, an existing catalog or aliases to an existing catalog block creation. Never offer an overwrite/reset checkbox. Next is disabled until validation succeeds. Switching modes preserves the user's draft path and selected existing result; it does not create files.

### Installer review and commit

The summary displays the final **Application folder**, **Database** (**Use existing** or **Create new**), **Data folder**, **Settings folder**, and selected storage-root details. A long path wraps or has a native horizontal scroll/copy affordance; it is never reduced to an indistinguishable ellipsis. Existing-data mode says **Existing data will be used in place.** New mode says **A separate empty database will be created. Existing data will be kept.**

Installation revalidates the exact reviewed identities/paths immediately before committing. A changed/inaccessible/busy selection returns to Database with the corresponding error; it never switches to a new catalog. Upgrade/update preserves the existing selection without discovery-driven changes. Silent updates do not create a new database or request destructive cleanup.

Cancel before Install changes no data/configuration. A cancelled or failed install must report whether binaries/configuration were committed. It must preserve every existing database/profile; do not claim rollback if a schema or write already occurred. On successful completion show the actual selected database path. Starting the app is the existing explicit finish action, not an automatic conversion admission.

## Uninstaller sequence

1. **Keep or remove data** page before any removal, with Keep selected by default.
2. If cleanup is selected, exact target review and explicit destructive confirmation.
3. Native removal progress and a truthful completion/leftovers page.

Choices:

- **Keep my data** — default. Explanation: **Keep databases, settings, job history, recovery copies and backups for reinstalling.**
- **Remove Books Arranger data from selected locations** — explanation: **Review the locations and recovery copies before deleting them. Library folders are excluded.**

For Keep, show the retained database/profile locations and proceed with normal binary/shortcut removal. For Remove, discover only app-owned locations established by the helper's installation/configuration/ownership evidence. Do not infer ownership from a folder name, an “old” path string, age or Git-ignore status. No whole drive/profile/repository cleanup option exists.

Show a selectable target list: **Location**, **Contents**, **Size**, **Action**. Every eligible location is initially unchecked. Contents use plain roles: **Database and job history**, **Settings and credentials**, **Conversion work**, **Recovery copies**, **Caches and downloads**, **Logs**, **Backups**. Group children beneath their containing selected root to avoid double-counting; count native aliases/hardlinks once. Mark estimates or inaccessible sizes explicitly. The summary shows the selected removable total, not the size of every discovered folder.

Protected/refused locations remain visible but disabled, with a specific reason: **Used by another installation**, **In use**, **Library folder**, **Source repository**, **Ownership not confirmed**, **Location unavailable**, or **Changed since review**. Show their full resolved paths in details. `C:\...` may be a junction to the active `I:\...` location: if it identifies retained/new installation data, it is protected regardless of its old-looking spelling. A repository-owned `data` subtree may be eligible only through a reviewed exact app-data manifest; the repository source, `.git`, linked worktrees and unowned siblings are excluded.

Before Uninstall, display a confirmation in the same wizard flow:

**Delete the selected Books Arranger data?**

**This deletes the selected databases, job history, settings, credentials, work files and backups. Selected recovery copies of original audio will also be deleted.**

Show only the roles actually selected; do not imply an unselected backup is removed. Keep the exact path list and total visible. Required unchecked confirmation: **I want to permanently delete the selected data.** The destructive forward label is **Uninstall and delete selected data**. **Back** returns to review; **Cancel** leaves everything intact before mutation. No typed phrase is required. Library/source/output paths, unrelated files and data retained by another installation remain protected even after this confirmation.

Revalidate safety and identity at execution, not just at review. A busy catalog/job must block cleanup and present the Quit instruction below. Never force-kill a worker, delete a live WAL, follow an alias into retained active data, or widen an exact manifest to a recursive parent removal. The wizard does not invent a bypass/force option. Remove eligibility is not permission to delete unknown contents discovered after review.

If any selected location fails the final preflight, return to the review page before deleting selected data. The user may unselect that location or switch to Keep. Unexpected failures after removal starts stop further unsafe deletion and retain a result record; already deleted data is not described as rolled back. Retry must rescan/revalidate and require confirmation for its new exact remaining list.

Finish copy distinguishes **Application uninstalled. Your data was kept.**, **Application and selected data removed.**, and **Application uninstalled. Some selected data could not be removed.** List each retained/refused/failed location and reason, with the actual removed total where known. A “complete” claim is allowed only when every selected eligible item was verified absent; always list protected and unselected retained locations separately. If binaries remain, say **Uninstall incomplete** and identify the remaining application path. Do not hide failures by closing the wizard.

Automatic upgrade uninstallation is Keep-only and skips destructive selection. A manual complete-cleanup choice must not propagate into a later update or another machine.

## Copy and tooltips

Use these messages for the matching verified condition; do not expose raw exceptions or secrets:

| Condition | Message |
| --- | --- |
| Busy database/workers | Books Arranger is still using this database. Choose Quit in Books Arranger and wait for its work to finish, then choose Check again. |
| Invalid candidate | This file is not a supported Books Arranger database. Choose another database or a separate new data folder. |
| Inspection failed | This database could not be checked at “{path}”. Restore access or choose another database. |
| New folder not empty | The new data folder contains files. Choose a separate empty folder. |
| Selection changed | The selected location changed during setup. Check it again before continuing. |
| Protected alias | This location points to data used by another installation. Keep it and select only locations that are no longer used. |
| Ownership unknown | Books Arranger cannot confirm which files it owns at “{path}”. Keep this location. |
| Unavailable configured storage | Books Arranger cannot reach “{path}”. Reconnect the drive or restore the folder before continuing. |

New app-owned controls ship with native tooltip text and accessible labels:

| Control | Tooltip |
| --- | --- |
| Use an existing database | Keep using the selected database and its saved history. |
| Existing database list | Select a database; review its full path and status below. |
| Browse existing | Choose an existing Books Arranger database file. |
| Check again | Check known locations and refresh the selected database's status. |
| Start with a new database | Create a separate empty database and keep existing data. |
| New data folder field | Folder for the new database and its application data. |
| Browse new folder | Choose a separate empty data folder. |
| Keep my data | Remove the application while keeping its saved data. |
| Remove data choice | Review app-owned locations for permanent deletion. |
| Cleanup target list/checks | Select only the app-owned locations you want to delete. |
| Permanent deletion confirmation | Confirm permanent deletion of the listed selected data. |
| Uninstall and delete selected data | Remove the application and permanently delete the confirmed selected data. |

Stock wizard navigation, native dialogs and native installation-directory controls retain their standard accessible behavior. No custom palette or custom-drawn destructive button is needed. The destructive label, warning and required confirmation identify the action without relying on red.

## QA acceptance

Check the packaged wizard with a single/multiple/missing/inaccessible/busy/unsupported database; a live-WAL private fixture; cancelled Browse; explicit new target containing files; and two aliases to the same database. Distinct catalogs must stay distinct. Verify that upgrade preserves selection and that legacy second-PC startup remains unchanged.

Use private cleanup fixtures covering Keep default, selected recovery/backups, unknown sibling, library/source/Git exclusions, active-new-data alias via C junction to I, changed identity, locked WAL, interrupted cleanup and partial failure. Verify actual removals/retained bytes, not only the displayed plan. No live libraries or user data are test fixtures.

Verify native page fit at normal and high DPI, keyboard-only use, tooltip coverage, light/dark Windows settings, long spaced/Cyrillic paths and each radio/list/error state. All controls and warnings remain visible without overlap; path details remain reachable. Scroll long result lists within their area, not underneath navigation. No focus/input permission is granted by this spec. No render, native interaction or measured-layout pass has been performed here.
