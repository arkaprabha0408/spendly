---
name: spendly-ui-designer
description: >
  Generates modern, production-ready UI components and pages for the Spendly
  personal expense tracker (Flask/Jinja2/HTML/CSS). Use this skill whenever the
  user says things like "design the __ page", "create UI for __", "build a
  component for __", "redesign/improve __", or any similar phrasing — especially
  for Spendly-related pages like dashboard, expense list, add expense form,
  analytics, profile, or budget. Also trigger for any request to improve or
  redesign existing Spendly screens, or to add new sections to an existing page.
  Always use this skill before writing any Spendly UI code — it contains the
  canonical design system and output rules that ensure consistency.
---

# Spendly UI Designer

Generates clean, consistent, production-ready UI for the Spendly expense
tracker. Read this skill fully before writing any HTML, CSS, or Jinja2 template.

---

## Project Stack

- **Backend:** Python / Flask
- **Templates:** Jinja2 (`.html` files in `templates/`)
- **Styles:** Vanilla CSS (`static/css/style.css`) — no CSS frameworks
- **Icons:** Lucide Icons via CDN (preferred), or inline SVG — never images
- **JS:** Vanilla JS only (`static/js/main.js` + page-specific `{% block scripts %}`)
- **Charts:** Chart.js (when data visualisation is needed)
- **Currency:** Indian Rupee (₹) throughout

---

## Design System

Read `references/design-tokens.md` for the full token reference.
Key values at a glance:

### Color Palette

```css
--ink: #0f0f0f; /* primary text */
--ink-soft: #2d2d2d; /* secondary text */
--ink-muted: #6b6b6b; /* muted/label text */
--ink-faint: #a0a0a0; /* placeholder text */
--paper: #f7f6f3; /* page background */
--paper-warm: #f0ede6; /* section backgrounds */
--paper-card: #ffffff; /* card surfaces */
--accent: #1a472a; /* primary brand green */
--accent-light: #e8f0eb; /* green tints */
--accent-2: #c17f24; /* amber accent */
--accent-2-light: #fdf3e3;
--danger: #c0392b; /* errors / overspend */
--danger-light: #fdecea;
--border: #e4e1da; /* standard border */
--border-soft: #eeebe4; /* subtle dividers */
```

### Typography

```css
--font-display: "DM Serif Display", Georgia, serif; /* headings, big numbers */
--font-body: "DM Sans", system-ui, sans-serif; /* body, labels, buttons */
```

### Spacing Grid

Use multiples of 8px: `0.5rem (8px)`, `1rem (16px)`, `1.5rem (24px)`, `2rem (32px)`, `3rem (48px)`.

### Border Radius

```css
--radius-sm: 6px; /* buttons, inputs, small chips */
--radius-md: 12px; /* cards, panels */
--radius-lg: 20px; /* hero visuals, large containers */
```

### Shadows

```css
box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06); /* subtle card lift */
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); /* hover / featured card */
box-shadow: 0 12px 48px rgba(0, 0, 0, 0.08); /* hero / modal */
```

---

## Existing Components (reuse, don't reinvent)

### From `style.css`:

- `.btn-primary` — dark fill button, hover turns accent green
- `.btn-ghost` — border-only button
- `.btn-submit` — full-width form submit
- `.form-group`, `.form-input` — labelled input blocks
- `.auth-card`, `.auth-error`, `.auth-success` — auth page cards + alerts
- `.feature-card` — bordered card with icon + title + body
- `.lp-stat` — stat box (label / large number / sub-label)
- `.lp-bar-track` / `.lp-bar` — progress bar rows

### Lucide Icons

Add to `{% block head %}`:

```html
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
```

Use in HTML:

```html
<i data-lucide="trending-up" class="icon"></i>
```

Init in `{% block scripts %}`:

```js
lucide.createIcons();
```

Preferred icon names for Spendly:

- `wallet` — overall balance/spending
- `trending-up` / `trending-down` — spend trends
- `receipt` — transaction / expense
- `tag` — category
- `calendar` — date / period
- `pie-chart` — analytics
- `plus-circle` — add expense
- `pencil` — edit
- `trash-2` — delete
- `user` — profile
- `bar-chart-2` — budget overview
- `filter` — filter controls
- `check-circle` — success / saved
- `alert-circle` — warning / over budget

---

## Output Format

For every UI request, produce output in three sections:

### 1 — Layout Brief (prose, ~100 words)

Describe the page layout: key sections, visual hierarchy, and one or two
important UX decisions and why you made them. Keep it short.

### 2 — Jinja2 Template (`templates/<name>.html`)

```jinja
{% extends "base.html" %}
{% block title %}Page Title — Spendly{% endblock %}

{% block head %}
<!-- Lucide if icons needed -->
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
{% endblock %}

{% block content %}
<!-- clean, semantic HTML using design tokens -->
{% endblock %}

{% block scripts %}
<script>
lucide.createIcons();
// page-specific JS here
</script>
{% endblock %}
```

### 3 — CSS additions (`style.css` additions)

Only new rules not already in `style.css`. Prefix classes with a page/component
namespace (e.g. `.dashboard-`, `.expense-`, `.analytics-`). Never duplicate
existing classes. If no new CSS is needed, say so explicitly.

---

## Design Rules

1. **Fintech-minimal aesthetic** — clean whitespace, strong typographic
   hierarchy, no decoration for decoration's sake.
2. **Card-based layout** — group related info in `.paper-card` surface cards
   with `border: 1px solid var(--border)` and `border-radius: var(--radius-md)`.
3. **8px spacing grid** — all margin/padding in multiples of 0.5rem.
4. **Colour discipline** — use `--accent` (green) for positive/primary actions,
   `--accent-2` (amber) for warnings/secondary, `--danger` for errors/overspend.
   Never introduce new colours without strong reason.
5. **Responsive by default** — use CSS Grid with `repeat(auto-fit, minmax())` or
   named breakpoints (`@media (max-width: 768px)`).
6. **No clutter** — if unsure whether an element adds value, leave it out.
7. **Semantic HTML** — use `<section>`, `<article>`, `<header>`, `<nav>`, `<aside>`
   appropriately. Never use a `<div>` when a semantic element fits.
8. **Icons must add meaning** — every Lucide icon must communicate something;
   never use icons purely as decoration.
9. **Indian Rupee first** — all currency amounts use ₹, not $ or generic symbols.
10. **Ask before guessing** — if the existing design is unclear or a screenshot
    would help match an existing page's style, ask the user for one.

---

## Consistency Check (run before outputting)

Before writing the final template, ask yourself:

- [ ] Are all colours CSS variables from the design system?
- [ ] Does every new class follow the namespace convention?
- [ ] Are icon names valid Lucide icons?
- [ ] Is the spacing consistent with the 8px grid?
- [ ] Does the page extend `base.html` correctly?
- [ ] Are there any hardcoded font sizes / hex values that should be variables?
- [ ] Does the page work without JS (progressive enhancement)?

---

## Avoid

- Generic Bootstrap/Tailwind look — this is a hand-crafted design system
- Random font sizes or weights not in the type scale
- More than 2 accent colours per page
- Tables for layout
- Inline styles (except dynamic values that must come from Jinja)
- Importing external CSS frameworks
- Vague placeholder text like "Lorem ipsum" — use realistic INR values and
  expense categories (Food, Travel, Bills, Health, Shopping, Others)

---

## Reference Files

- `references/design-tokens.md` — full CSS variable listing + usage examples
- `references/page-inventory.md` — existing pages and their route names

Read these when you need more detail or are unsure about a specific pattern.
