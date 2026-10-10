# Books Arranger — recovery copy expiry and manual deletion

Date: 2026-10-10. Judy UX specification. EXTEND existing source cleanup and created-audiobook View; preserve scanning, metadata, artwork, chapters, conversion and output publication. Sergei approved automatic recovery deletion after **1 day** and a manual deletion button. This spec supersedes recovery retention and temporary-file copy in the previous source-cleanup UX spec.

## Policy and visible scope

One day means **24 hours after source cleanup successfully completes**, not after encoding starts, the first original disappears, or the app is reopened. Automatic checks run at startup and periodically while the app runs. If the app is stopped at expiry, deletion waits until it next runs. No countdown animation or daily notification is needed.

Only backend-confirmed, registered recovery copies belonging to an eligible completed cleanup can expire or be manually deleted. Active backup, original removal, restore or recovery deletion prevents eligibility. Interrupted, incomplete, unverified, changed or otherwise blocked recovery sets remain available for attention. Current M4Bs, metadata, covers, original-library companions and unregistered evidence are outside this action. This UI must reflect Ender's actual deletion eligibility; it must not infer eligibility from missing original paths or a folder name.

Before creation, use: **Creates one audiobook, verifies it, then removes the included originals. Recovery copies are kept for 24 hours after source cleanup completes, then deleted automatically while the app is running.** Keep this notice in the existing Audiobook output section. Retained-source jobs keep their existing accurate notice. Tooltip: **Create and verify this audiobook, then remove its included originals. Recovery copies expire 24 hours after successful source cleanup.**

Successful source removal reads **Originals removed; recovery copies kept until [date and time]**. Do not retain the current promise that recovery copies are automatically removed immediately after cleanup succeeds. Temporary encoding files and retained original recovery copies must use separate labels and states.

## Created-book View

Add a compact **Recovery copies** block immediately after the created output facts in the existing inspector, before optional raw-tag details. Reuse the current section, definition-list, path and toolbar styling. This block belongs to the selected created book; selecting another row must clear its pending action and facts. Keep cover and Open output folder intact.

Show authoritative **Status**, **Original tracks backed up**, **Space on C:**, **Recovery location**, and **Automatic deletion**. Dates use local date/time with a timezone label, including minutes. For example: **11 Oct 2026, 15:40 (Asia/Jerusalem)**. Store/use the backend deadline; polling never extends it. Byte values come from the actual registered files and may be shown as **115 MB (114,906,562 bytes)**. Unknown values read **Unavailable**, never zero. Long paths wrap and stay selectable.

Use these status variants:

- Retained and eligible: **Available until [date and time]**.
- Deadline elapsed, deletion not yet begun: **Expired; waiting for automatic cleanup**.
- Active recovery deletion: **Deleting recovery copies: [confirmed removed] of [total]**.
- Fully deleted: **Recovery copies deleted automatically on [date and time]** or **Recovery copies deleted manually on [date and time]**, according to the receipt. Storage remaining is zero only when confirmed.
- Blocked: **Recovery cleanup needs attention: [plain-language reason]**. Show the actual remaining count/bytes and explain that the app preserved the blocked files.

Adjacent help: **Deleting these copies permanently removes the app's backup of the original tracks. The finished audiobook stays in place.** For retained copies also show: **Automatic deletion happens while the app is running; overdue copies are checked when it starts.** If a recovery location remains in history after deletion, label it **Former recovery location**, not an available backup.

## Manual action and confirmation

Place **Delete recovery copies…** below the selected book's recovery facts, using a quiet button with a visible label, not a trash-only icon. Scope is **this selected book only**; this milestone adds no global bulk purge. Tooltip: **Permanently delete the verified recovery copies for this book. Keep the finished audiobook.** Associate the button with the permanent-loss help using `aria-describedby`.

The button is enabled only when the backend reports a nonempty eligible set, the app is connected, and no operation owns that set. Disable during active backup, source removal, restore, recovery deletion, unavailable server, or an ineligible set; show the concrete reason in text beside/below it. After deletion retain the receipt and disable the button with **No recovery copies remain**. Polling must not move focus or recreate a focused control.

Click opens a browser-owned confirmation dialog titled **Delete recovery copies?** Show **[book title] — [author]**, **[count] original tracks · [bytes] on C:** and the exact registered recovery location. Body: **This permanently deletes these backups. You will no longer be able to restore these original tracks from the app. Your finished audiobook will stay in place.** Buttons: **Cancel** and **Delete recovery copies**. Initially focus Cancel; Enter follows the focused button and never defaults to deletion. Escape closes; trap focus only while open and restore focus to the initiating button on close. No checkbox, typed phrase or extra confirmation page.

Freeze the exact displayed identity/count/bytes for confirmation and submit that scope to the backend. If it has changed, perform no stale deletion and show **Recovery copies changed. Review the updated details and try again.** Prevent duplicate submissions. A submitted deletion may be too late to cancel; do not claim Cancel can restore already deleted files. Use inline progress and a polite live status after submission. Failures leave the finished audiobook's successful status intact.

## Layout, accessibility and QA acceptance

Use existing dark-theme tokens and 15px body/13px help text; error/warning words accompany colors. Quiet buttons retain the existing padding, minimum 32px height and at least 24×24 CSS-pixel hit area. Confirmation width is at most 560px, viewport minus 24px; max height viewport minus 24px with internal vertical scrolling. Wrap paths and allow action rows to wrap with 10px gaps. No new keyboard accelerator or high-saturation danger fill is needed; destructive meaning is explicit in labels and body copy. Maintain 4.5:1 text contrast, 3:1 visible focus/component boundaries, and full keyboard access.

Futaba measures actual rectangles for recovery facts, help, action button and confirmation buttons at 1440px and 700px widths, plus narrow/reflow and 200% zoom. Verify no overlapping targets, clipped focus or covered controls in retained, expired, deleting, blocked, deleted and disconnected states, and with long Russian titles/paths. Test Tab/Shift+Tab, Enter, Space, Escape and focus return. Check selection changes, stale confirmation, double click, automatic deletion racing an open confirmation, expiry while app is stopped, and restart without resetting the deadline. Backend tests must prove only eligible registered recovery files are removed; UI snapshots alone cannot establish that.

Design basis: NN/g visibility and error prevention through explicit expiry/scope/receipts; user control through bounded manual deletion and cancel before submission; Jakob's Law through conventional dialog keyboard behavior; Hick's Law through one action on the existing View; WCAG 2.2 AA focus, contrast and target requirements. This is a doc-only handoff: no live deletion, browser interaction, probes, code changes or Git operations were performed. Sully commits this spec before Ender implements it.
