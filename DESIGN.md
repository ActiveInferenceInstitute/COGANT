# COGANT dashboard design system

## 1. Atmosphere and identity

The existing dashboard is a dense scientific inspection surface. Dark layered
panels, readable numerical tables and labelled plots support checking individual
artifacts. Preserve its shared components in `cogant/py/cogant/viz/dashboard/assets.py`.

## 2. Color

The current palette uses background stops `#0f0f1e` and `#1a1a2e`, panel fill
`rgba(20,20,30,0.8)`, primary ink `#e0e0e0`, secondary ink `#b0b0b0`, white
emphasis, and the `#667eea` / `#764ba2` header gradient. Status colors are
`#4caf50`, `#ffc107`, `#f44336` and `#2196f3`. Inference chart geometry and
labels inherit `currentColor`; probability and energy values are never encoded
by a success/failure color. No additional palette is needed for the inference panel.

## 3. Typography

Use the existing system sans-serif stack, body line height 1.6 and browser
monospace for digests. Existing heading sizes are 2.5em (1.8em below 768px),
chart titles 1.2em and metadata 0.85–0.95em. SVG labels use the existing
12-unit chart caption size. Keep observation, action and energy labels explicit.

## 4. Spacing and layout

The document owns vertical scrolling. Shared containers have a 1400px maximum
width and 20px padding. The established spacing steps include 4, 8, 12, 20,
30 and 40px; table cells retain their existing 12px by 15px spacing.
Inference SVGs use an 800 by 300 view box with 50-unit margins, scale to their
container and have no fixed rendered height. Long digests wrap within the panel.
Record tables own horizontal scrolling on narrow screens.

## 5. Components and states

- Container: the shared `.container` primitive; no new card surface.
- Inference chart: labelled SVG with accessible name, numeric vertical ticks,
  observation-step endpoints, and a visible point for a one-record trace.
- Record table: semantic column headers, observed indices resolved to axis labels,
  selected policy score, posterior energy and probabilities. Bound display size
  and state every truncation explicitly.
- Identity block: source and matrix digests, mode, objective and horizon.
- Empty state: no trace available. Present invalid evidence raises an error before
  HTML generation; no fabricated empty-success state.

## 6. Motion and interaction

The inference panel introduces no motion. It uses the existing tab navigation
and fade-in behavior. Horizontal record scrolling is keyboard reachable, with a
visible native focus indicator. No decorative hover or animation is added.

## 7. Depth and surface

Retain the existing mixed surface system: dark gradients, translucent panels,
8px panel corners and header shadow. Inference data stays on the shared panel;
chart axes and markers convey quantities rather than decorative elevation.

## 8. Accessibility constraints and existing debt

Inference content must remain readable at phone, tablet and desktop widths,
escape source-derived labels, wrap long identities, expose chart units and
provide table values alongside the chart. Review empty, one-record, populated
and rejected-evidence states. The inherited dashboard's other tabs and external
Mermaid dependency have separate accessibility and loading behavior; panel
verification does not establish a whole-dashboard Lighthouse score or a light theme.
