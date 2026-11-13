# Books Arranger portable storage UX — 2026-11-13

Status: cancelled draft. Sergei cancelled the separate Books Arranger storage/version work on 2026-11-13 in the coordinated whole-folder migration chat. Preserved as a checkpoint only; do not implement or treat as an active specification. No product change or release was made.

Scope: opt-in storage startup failures and the existing native installer directory page. This extends 0.27.0; it adds no Settings page or migration button. The chosen machine target is local I:, while other installations keep their existing paths until explicitly configured. Existing book libraries are not moved. This spec defines presentation, not path validation or migration authority.

## Startup failure

Use the existing native fatal-error presentation before starting the backend or opening a fallback profile. Show one error for the first actionable failure, then exit. The user fixes the location/configuration and launches again. Do not offer Retry, Continue, Use default, automatic directory selection, or a migration action. Do not create a fallback catalog to display the error.

Use the fixed title **Books Arranger cannot start**. Select the body below from the actual failure. Substitute a plain role name: **profile**, **temporary files**, **downloads**, **logs**, or **data**. Display the actual affected path; never display credentials, tokens, raw configuration contents or a traceback.

| Failure | Body |
| --- | --- |
| Configured drive/location unavailable | Books Arranger cannot reach the {role} folder at “{path}”. Reconnect the drive or restore the folder, then open Books Arranger. |
| Configured folder not writable | Books Arranger cannot write to the {role} folder at “{path}”. Restore write access or choose another folder in the storage configuration, then open Books Arranger. |
| Explicit/required configuration missing or unreadable | Books Arranger cannot read the storage configuration at “{path}”. Restore the file or correct its location, then open Books Arranger. |
| Malformed or invalid configuration | The storage configuration at “{path}” is invalid: {reason}. Correct the configuration or restore its backup, then open Books Arranger. |
| Unsafe storage root | The {role} folder at “{path}” cannot be used: {reason}. Choose another folder in the storage configuration, then open Books Arranger. |

`{reason}` is a short, nontechnical, sanitized description of the predicate actually refused. Approved forms, only where the corresponding rule is enforced: **a local disk folder is required**, **the path must be absolute**, **the required {role} location is missing**, **the configuration version is not supported**, **it overlaps a book library**, **it overlaps another storage folder**, **it points through an unsupported link**. Name an invalid field when that helps correct it; do not dump an arbitrary exception. Ender may omit unused forms. If a new predicate needs materially different copy, return it to this pass rather than mislabeling it.

An absent optional configuration on an installation that has never opted in is normal legacy startup, not an error. A missing explicitly selected or required configuration is an error. Technical discovery/activation rules belong to Ender's implementation; this distinction must survive restart and update.

The native dialog retains its standard dismiss button and keyboard behavior. Dismissing it exits; it does not reopen the installer or start work. No custom interactive control is introduced. Native wrapping must keep a long Unicode path readable; do not truncate the only actionable path. Headless mode uses the same title/body in the existing fatal-error output instead of opening a dialog.

## Installer directory page

Enable the stock NSIS directory chooser in the existing assisted per-user installer. Keep stock native layout, accessible labels, Browse interaction, Back/Next/Cancel and keyboard navigation. Do not add a custom folder picker, storage selector or migration consent page. Standard native installer controls keep their native labels/help; there is no new app-owned button requiring a custom tooltip.

Keep the normal installer default on machines without an existing installation. On an upgrade, show/preserve the actual installed application directory. Do not globally prefill I: or Z:. For this machine, the approved future application target may be selected as `I:\Books Arranger\Application`; showing that option is not authorization to move the current installation or its data.

The directory page chooses **application binaries only**. If supplemental copy is needed to avoid implying that it migrates data, use: **Choose where to install Books Arranger. Existing libraries and saved data stay in their configured locations.** Do not promise that choosing a directory migrates settings, resumable work, or the database.

Uninstall retains the existing standard native confirmation. Do not add a delete-data/libraries checkbox. The behavior must preserve configured data, profile, recovery work and book libraries; native shell shortcuts and installed binaries may be removed by the existing installer contract. No new consent wording substitutes for that behavior.

## Acceptance checks

- A configured unavailable drive, denied write access, malformed configuration and each enforced unsafe-root class produce the matching copy and exact relevant path. No backend/fallback profile/catalog starts after refusal.
- An unconfigured legacy installation starts with its existing locations. A configured installation retains its selection across restart and upgrade; an unavailable configured root remains a refusal after either.
- Native failure presentation is readable with a long path, spaces and Cyrillic characters. Dismissal terminates startup. Headless errors contain the same actionable copy and no secret values.
- The native installer directory page accepts a suitable local I: path and preserves it on upgrade. Keyboard navigation and Cancel keep their standard behavior. Installed-directory selection does not claim to migrate data.
- Uninstall preserves a private test library and retained private profile/data/recovery files. This is verified behavior, not a claim based only on installer configuration.

No live app, installer, focus or input was used to prepare this spec. No custom geometry, colors or hit areas changed; therefore no measured-layout or native-install verification is claimed here. QA verifies the actual packaged native surfaces under its separately authorized test scope.
