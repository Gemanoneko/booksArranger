# Books Arranger: default dark web theme

Date: 2026-10-09. Sergei requests dark as the browser interface's default. This preference persists for later role, anthology and grouping interfaces. Scope: stylesheet-only default dark on the accepted v0.2.1 frontend. Preserve current typography, dimensions, spacing, responsive breakpoints, table scrolling, controls and workflow. No toggle, settings, OS-theme detection or Tk theme change.

## Semantic palette

Use CSS custom properties so later additions inherit the same roles. Exact values:

| Token | Value | Role |
|---|---|---|
| `--canvas` | `#121820` | Page background |
| `--surface` | `#1B2530` | Panels and quiet buttons |
| `--raised` | `#253445` | Sticky table header, badge and tag snapshot |
| `--field` | `#111923` | Text inputs and selects |
| `--text` | `#EDF3F8` | Body, headings, labels and entered values |
| `--muted` | `#B8C6D5` | Footer, placeholders and secondary text |
| `--border` | `#71869C` | Field/control outlines, panel and table separators |
| `--accent` | `#83BFFF` | Primary button fill, quiet button text, checkbox accent and selected-row edge |
| `--accent-hover` | `#9DCCFF` | Enabled primary button hover |
| `--accent-pressed` | `#66A9ED` | Enabled primary button active |
| `--on-accent` | `#101923` | Text on primary buttons |
| `--row-hover` | `#263B4F` | Hovered table row and enabled quiet-button hover |
| `--row-selected` | `#304E6B` | Selected table row |
| `--focus` | `#FFD58A` | Existing three-pixel focus outline |
| `--warning` | `#FFD58A` | Connection warning and current action-message text |
| `--error` | `#FFB3B3` | Explicit error presentation, if already semantically identified |
| `--disabled` | `#2B3745` | Disabled button fill |
| `--disabled-text` | `#ADB9C6` | Disabled text |
| `--notice` | `#20382F` | Read-only notice fill |
| `--notice-text` | `#D9F4E5` | Read-only notice text |
| `--notice-border` | `#739B84` | Read-only notice border |

## Existing selector mapping

- Set root `color-scheme: dark`, text and background to the listed roles. Native select menus, checkbox, search-field affordances and scrollbars use the browser's dark scheme; do not implement custom controls.
- `.panel`: surface fill, border outline. `.badge`, `th` and `pre`: raised fill and normal text; badge/table borders use border. The sticky header remains opaque and covers rows underneath.
- Inputs/selects: explicit field fill, text and border; placeholder uses muted at full opacity. Set checkbox accent to accent. Native options must remain legible when open; do not leave inputs with a white default fill.
- Enabled primary buttons: accent fill/border with on-accent text. Hover and active use their corresponding fills, without animation. Quiet buttons use surface fill, accent text and border; hover uses row-hover. Enabled-only rules must not override disabled styling.
- Disabled buttons: disabled fill, disabled-text and border, with opacity 1. Retain disabled interaction semantics and current geometry; reducing the whole control's opacity would make its label unnecessarily faint.
- Row hover uses row-hover. Selected rows use row-selected, normal text, and a three-pixel inset accent edge at the left (no added width or layout shift). Selected fill/edge must remain visible on hover. Keep text and existing `aria-selected`; selection is not indicated by color alone.
- Existing control and row focus outlines use focus, retaining current thickness/offsets. Add the same visible focus treatment to the existing tag-snapshot summary. An inset row outline must not be hidden by selected styling or table clipping.
- `.notice`: notice fill/text/border. `footer` and genuinely secondary text use muted; paths, titles, inventory entries and status remain text. Do not lower path/tag legibility through extra opacity.
- `#message` and `#connection-notice`: warning. The stylesheet does not infer whether a mixed action-message string is success or failure, and must not change the connection recovery behavior. Error is reserved for an existing explicit error selector if available; do not add JS state changes to this task. Errors and warnings remain identified by their text.

No old light fills or dark-on-light text remain on the mapped surfaces. Do not change source/library read-only copy, scan state, service lifetime or review form behavior.

## Contrast and verification

Palette ratios were calculated directly from sRGB channel linearization and relative luminance, using `(lighter + 0.05) / (darker + 0.05)`. These are palette checks, not rendered-screen QA:

| Pair | Ratio |
|---|---:|
| Normal text / panel | 13.87:1 |
| Muted text / selected row (lowest intended secondary-text pair) | 4.97:1 |
| Disabled label / disabled fill | 6.07:1 |
| Primary label / primary fill | 9.16:1 |
| Primary label / pressed fill | 7.14:1 |
| Control border / panel | 4.13:1 |
| Control border / field | 4.71:1 |
| Control border / disabled fill | 3.22:1 |
| Selected accent edge / selected fill | 4.47:1 |
| Focus or warning / panel | 11.18:1 |
| Error / panel | 9.12:1 |
| Notice text / notice fill | 10.80:1 |
| Notice border / notice fill | 4.05:1 |

Ender/QA verifies computed colors and actual text/background pairs at 700 and 1440 CSS-pixel widths, including startup, active scan, stopping, resumable scan, empty inventory, populated table, hover/selected/focused rows, open select, expanded tag snapshot, visible review fields, disabled actions and connection notice. Target normal-text contrast of at least 4.5:1 and relevant controls/focus indicators of at least 3:1. Disabled labels are intentionally readable despite their accessibility exemption. Check unchanged control rectangles and no overlap or clipping; report measured results separately. No live-window/browser interaction or screenshot claim is made in this spec.

The accepted source can receive an atomic stylesheet update without restarting the active scanner. Do not refresh Sergei's live tab or restart the server on his behalf; let the parent communicate how he can load the theme. Isolated validation must leave the active catalog and library files untouched.

## Handoff

Design basis: studio WCAG baseline for readable text and visible focus; Jakob's Law through native browser controls; NN/g visibility of status through legible disabled/selected/error states. Reference: `Team/Research/UX_AppBestPractices.md`.

Sully commits and pushes this frozen spec before Ender cites it. Keep the dark stylesheet task separate from anthology/author-role and grouping functionality. No new interactive controls, visual exports, probes or disposable artifacts were created for this spec; only this documentation file was written.
