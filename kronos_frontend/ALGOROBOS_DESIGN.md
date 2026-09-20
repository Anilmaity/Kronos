# Algorobos — Redesign Specification
## Theme: Dark Academic / Alchemist's Codex (B + D Blend)

> *"As the alchemist transmutes base metal to gold, so the disciplined trader transmutes raw price into consistent edge."*
p
---

## Vibe & Concept

**Direction:** Dark Academic meets Alchemist's Codex  
**Mood:** A scholar's private library at midnight — candlelit, worn leather, parchment-aged pages, burnished gold ink, serious and unhurried  
**Anti-pattern:** No Roman monument formality, no neon, no crypto-bro noise  
**Personality:** The wise old professor who has seen every market cycle and trusts only process

The design communicates **earned authority** — not flashy gold, but tarnished, patinated gold. The kind found on old book spines, not jewelry counters. Every element should feel like it was placed deliberately, read slowly.

---

## Color Palette

All colors are in OKLCH for perceptual consistency. The palette is **cooler and deeper** than the current design — less warm amber, more aged manuscript.

### Background Scale

| Token | Value | Hex Approx | Role |
|---|---|---|---|
| `--bg-deep` | `oklch(0.10 0.010 65)` | `#09090b` | Page base, footer |
| `--bg` | `oklch(0.12 0.011 65)` | `#0d0d10` | Nav backdrop |
| `--bg-soft` | `oklch(0.15 0.012 67)` | `#121008` | Tablet/rule sections |
| `--bg-card` | `oklch(0.17 0.013 68)` | `#161208` | Cards, reading panel |

### Gold Scale — Burnished Amber (not bright)

| Token | Value | Hex Approx | Role |
|---|---|---|---|
| `--gold` | `oklch(0.68 0.105 76)` | `#c8a030` | Primary accent, highlights |
| `--gold-deep` | `oklch(0.52 0.090 72)` | `#8a6a15` | Borders, ornaments |
| `--gold-dim` | `oklch(0.38 0.065 70)` | `#4e3c0a` | Inactive, faint rules |

> **Key shift from old design:** Gold is more amber-brown (`oklch hue ~76`) vs old warm yellow (`hue ~82`). Lower lightness — it glows, not gleams.

### Text Scale — Parchment-toned

| Token | Value | Role |
|---|---|---|
| `--ink` | `oklch(0.90 0.020 78)` | `#ede0b8` — Primary headings, warm parchment white |
| `--ink-muted` | `oklch(0.72 0.028 75)` | `#c8af72` — Body copy |
| `--ink-faint` | `oklch(0.50 0.030 72)` | `#7a6840` — Labels, metadata, footer |

### Semantic

| Token | Value | Role |
|---|---|---|
| `--green` | `oklch(0.68 0.12 145)` | Market up / live pulse dot |
| `--ember` | `oklch(0.58 0.14 38)` | Market down / negative |

### Line / Border Tokens

| Token | Value |
|---|---|
| `--line` | `gold @ 18% opacity` |
| `--line-faint` | `gold @ 10% opacity` |

### Ambient Background

The page background is **not flat black** — it layers:
1. Base `--bg-deep` (`#09090b`)
2. Radial amber glow top-right — `rgba(185,140,35,.09)`, 400×400px ellipse
3. Radial amber glow bottom-left — `rgba(100,75,15,.07)`, 300×300px
4. Paper grain overlay — dual radial-dot pattern at 3px/7px, `mix-blend-mode: overlay`, 80% opacity
5. Section-level subtle glows on CTA and Why sections

---

## Typography

Three typefaces, strict role separation. No substitutions within a role.

### 1. Display — Cormorant Garamond
```
font-family: "Cormorant Garamond", "Garamond", "Times New Roman", serif
weights: 400, 500, 600, 700
styles: normal + italic
```
- **Used for:** H1, H2, H3, brand wordmark, large Roman numerals, stat numbers, reading card roman/title, "Today's Reading" pillar roman numeral
- **Character:** High-contrast Renaissance display serif — delicate hairlines, dramatic thick-to-thin strokes. More elegant and literary than the current Cinzel (which was monumental/Roman)
- **Italic** is used liberally as an accent weight inside headings (`<em>` words in gold)
- Letter-spacing: tight on large headings (`-0.01em`), moderate tracking on wordmark (`0.18em`)
- Base heading sizes: H1 `clamp(48px, 6vw, 72px)` · H2 `clamp(32px, 4vw, 48px)` · H3 `28–36px`

### 2. Body — Libre Baskerville
```
font-family: "Libre Baskerville", "Baskerville", "Georgia", serif
weights: 400, 700
styles: normal + italic
```
- **Used for:** All body paragraphs, hero subtitle, about section, why-card descriptions, footer body
- **Character:** Sturdy, readable old-style serif — more grounded than Garamond at small sizes. Oxbridge textbook feel. Reliable and authoritative.
- Base size: `13.5px`, line-height `1.75`
- Body copy rendered in `--ink-muted` (`#c8af72`), italic for descriptive passages
- Drop-cap on the About section: Cormorant Garamond 52px, `--gold`

### 3. Accent — IM Fell English
```
font-family: "IM Fell English", "Caslon", serif
styles: italic only
```
- **Used for:** Lede text under pillar headings, reading card body, golden rule tablet paragraph, testimonial quote body, manifesto verse body, section taglines
- **Character:** A digitization of a 17th-century English typeface — irregular, humanist, feels hand-set. Gives an authentic aged-manuscript feeling to short italic passages.
- Always italic, never regular
- Size: `12–14px`, line-height `1.65`
- Color: `--ink-faint` to `--ink-muted` depending on context

### 4. Mono — JetBrains Mono (unchanged)
```
font-family: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace
weights: 400, 500
```
- **Used for:** Eyebrow labels, nav links, buttons, ticker, metadata bars, section number labels, footer, tenet lists
- Always uppercase, letter-spacing `0.16–0.30em`
- Color: `--ink-faint` baseline, `--gold-deep` for active/label states, `--gold` for highlighted values
- Size: `9–11px`

### Font Load (Google Fonts)
```
Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600
Libre+Baskerville:ital,wght@0,400;0,700;1,400
IM+Fell+English:ital@0;1
JetBrains+Mono:wght@400;500
```

---

## Logo & Brand Mark

| Element | Current | New |
|---|---|---|
| Mark | Gear image PNG, spinning | Alchemical `⚗` glyph inside gold-bordered circle with radial glow |
| Wordmark | Cinzel, 600, 0.28em tracking | Cormorant Garamond, 600, 0.18em tracking |
| Animation | 60s spin on gear | Removed — mark is static |
| Glow | Gold box-shadow | Radial-gradient inner glow, `rgba(185,140,35,.22)` |

> The gear PNG (`assets/algorobos-gear.png`) can replace the `⚗` glyph if preferred — use it as a `background-image` on the circle mark.

---

## UI Components

### Navigation
- Sticky, `backdrop-filter: blur(10px)`, `rgba(9,9,11,.88)` background
- Border-bottom: 1px `--line-faint`
- Brand mark: 28px circle, `--gold-deep` border, alchemical glow background
- Nav links: JetBrains Mono 9.5px, uppercase, `--ink-faint` default → `--gold` on hover
- CTA button: ghost style (see buttons below)

### Buttons

**Primary (amber fill)**
- Background: `linear-gradient(180deg, rgba(185,140,35,.28), rgba(120,90,15,.28))`
- Border: 1px `rgba(185,140,35,.5)`
- Text: `--gold` (`#c8a030`)
- Font: JetBrains Mono, 10px, uppercase, 0.18em tracking
- Padding: `11px 20px`
- Border-radius: `2px` (near-flat)
- Hover: border brightens to `rgba(185,140,35,.75)`, subtle lift `translateY(-1px)`

> **Key change from old:** Old had a solid gold gradient background (gold-on-dark). New uses a semi-transparent amber tint — more aged, less "buy now" energy.

**Ghost**
- Background: transparent
- Border: 1px `rgba(185,140,35,.2)`
- Text: `rgba(185,140,35,.5)`
- Hover: border → `--gold-deep`, text → `--gold`

### Cards (Why-Us, general)
- Border: 1px `rgba(185,140,35,.12)`
- Background: `rgba(20,16,6,.5)` — very dark amber-tinted
- No border-radius (flat `0px`)
- Hover: border → `rgba(185,140,35,.35)`, lift `translateY(-2px)`, gold shadow `0 10px 28px -12px rgba(185,140,35,.2)`
- Roman numeral label: Cormorant Garamond italic, `--gold-deep` at 45% opacity

### Reading Card ("Today's Reading")
- Corner bracket decoration (CSS `::before` / `::after`) — 12×12px, `--gold-deep` at 35%
- Background: faint gold top-fade gradient + `rgba(20,17,9,.6)`
- Roman numeral: Cormorant Garamond italic, 40px, `--gold`
- Title: Cormorant Garamond, 15px, uppercase, `#d8c888`
- Body: IM Fell English italic, 12px, `--ink-faint`
- Footer: JetBrains Mono 9px, `--ink-faint`; "Draw another" in `--gold`
- Live pulse dot: green `oklch(0.68 0.12 145)`, pulsing animation

### Codex / Seven Pillars
- Left column: numbered list with Cormorant Garamond italic roman numerals (16px)
- Pillar title: Cormorant Garamond 17px weight 600
- Active item: left indent 10px, background `linear-gradient(90deg, rgba(185,140,35,.07), transparent)`
- Right detail panel: left-border `1px rgba(185,140,35,.2)`
- Large background roman numeral: 56px Cormorant Garamond, `rgba(185,140,35,.18)` — decorative ghost
- Lede text: IM Fell English italic, `rgba(185,140,35,.6)`
- Body: Libre Baskerville italic 12px, `--ink-faint`
- Tenets: JetBrains Mono 9px, `◆` bullet in `--gold-deep`

### Golden Rule Tablet
- Max-width 580px, centred
- Border: 1px `rgba(185,140,35,.3)`
- Background: gold top-fade + `rgba(12,10,4,.7)`
- Inner shadow: `inset 0 0 60px rgba(185,140,35,.03)`
- Corner brackets: 20×20px `--gold-deep` at 40%
- Heading: Cormorant Garamond italic 34px, `--gold`
- Body: IM Fell English italic 16px, `--ink-faint`

### Ornament Rule
- A centred glyph (◆ or ◈ or ❦) flanked by gradient lines fading transparent → `rgba(185,140,35,.25)` → transparent
- Used as section separators and after major headings

### Scroll Thread
- 1px vertical line on left viewport edge, fills amber from top as user scrolls
- Glow tip: `box-shadow: 0 0 10px --gold`
- Vertical label: JetBrains Mono `NNN · ALGOROBOS`

### Ticker
- Height 30px
- Background: `linear-gradient(180deg, #060609, #09090b)`
- Font: JetBrains Mono 10px, letter-spacing 0.06em
- Symbol bold: `rgba(220,190,100,.7)`
- Price: `rgba(180,155,90,.45)`
- Up: `rgba(120,185,110,.7)` (muted green)
- Down: `rgba(185,90,70,.7)` (muted ember)
- Animation: 60s horizontal loop

### Section Labels
- JetBrains Mono 9px, 0.28em tracking, uppercase
- Color: `rgba(185,140,35,.45)`
- Flanked by 28px gradient lines (`--gold-dim`)
- Format: `01 — WHO WE ARE`

---

## Ornamental Language

| Glyph | Use |
|---|---|
| `⚗` | Brand mark (alchemical still) |
| `◆` | Tenet bullet, active indicator, ornament |
| `◈` | Alternate ornament in dividers |
| `❦` | Fleuron for testimonial / quote sections |
| `✦` | Star accent in rules and taglines |

> Alchemical symbols (`⚗ ☿ ♁ ⊕`) can be used sparingly as decorative motifs in section headers or background watermarks.

---

## Animation & Motion

| Element | Animation | Duration | Notes |
|---|---|---|---|
| Section reveal | `opacity 0→1` + `translateY 16px→0` | 0.85s ease | IntersectionObserver, threshold 0.12 |
| Headline words | Clip-mask slide up `translateY(110%→0)` | 1.0s `cubic-bezier(.22,.7,.18,1)` | Stagger per word |
| Manifesto verses | Stagger fade-up | 0.08s per item | `sup` class |
| Codex detail switch | Fade-up per element | 0.50s, staggered 0–0.20s | |
| Ticker marquee | `translateX(-50%)` loop | 60s linear infinite | |
| Live pulse dot | `opacity 1→0.3→1` | 2s ease-in-out infinite | |
| Hover lifts | `translateY(-2px)` | 0.25s `cubic-bezier(.3,.7,.4,1)` | Cards, buttons |
| Brand mark | **Static** (no spin) | — | Removed from old design |

All motion respects `prefers-reduced-motion: reduce`.

---

## Layout System

| Property | Value |
|---|---|
| Max content width | `1240px` |
| Horizontal padding | `40px` desktop / `22px` mobile |
| Section vertical padding | `56–80px` |
| Grid gutters | `32–48px` |
| Hero grid | `1.4fr 1fr` |
| Codex grid | `1fr 1.3fr` |
| Why-Us grid | `repeat(3, 1fr)` → `repeat(2,1fr)` → `1fr` |
| Border-radius | `0–2px` (near-flat throughout) |

---

## Page Sections (unchanged structure)

1. **Ticker** — scrolling market data bar
2. **Nav** — sticky, brand + links + CTA
3. **Hero** — headline + reading card
4. **About** — drop-cap paragraph, centred
5. **Manifesto** — verse layout, numbered
6. **Seven Pillars (Codex)** — interactive list + detail
7. **Why Us** — 3-column stat cards
8. **Testimonial** — centred italic quote
9. **Golden Rule Tablet** — centred bordered declaration
10. **CTA (Finale)** — large heading + buttons
11. **Footer** — 3-column, links + copyright

---

## Theming Variables (CSS `:root`)

```css
:root {
  --bg-deep:    oklch(0.10 0.010 65);
  --bg:         oklch(0.12 0.011 65);
  --bg-soft:    oklch(0.15 0.012 67);
  --bg-card:    oklch(0.17 0.013 68);

  --ink:        oklch(0.90 0.020 78);
  --ink-muted:  oklch(0.72 0.028 75);
  --ink-faint:  oklch(0.50 0.030 72);

  --gold:       oklch(0.68 0.105 76);
  --gold-deep:  oklch(0.52 0.090 72);
  --gold-dim:   oklch(0.38 0.065 70);

  --ember:      oklch(0.58 0.14 38);

  --line:       color-mix(in oklch, var(--gold) 18%, transparent);
  --line-faint: color-mix(in oklch, var(--gold) 10%, transparent);

  --display:    "Cormorant Garamond", "Garamond", "Times New Roman", serif;
  --serif:      "Libre Baskerville", "Baskerville", "Georgia", serif;
  --accent:     "IM Fell English", "Caslon", serif;
  --mono:       "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
```

---

## Comparison: Old vs New

| Dimension | Old (Roman/Bloomberg) | New (Alchemist/Dark Academia) |
|---|---|---|
| Background hue | Warm brown-black (70°) | Cooler near-black (65°) |
| Gold tone | Bright warm yellow-gold | Burnished amber-brown |
| Display font | Cinzel (monumental Roman) | Cormorant Garamond (literary) |
| Body font | EB Garamond | Libre Baskerville |
| Accent font | (none — just italic Garamond) | IM Fell English (irregular, hand-set feel) |
| Logo animation | Spinning gear (60s) | Static alchemical mark |
| Button fill | Solid gold gradient | Semi-transparent amber tint |
| Section numbers | Roman numerals in large Cinzel | JetBrains Mono with gradient rule flanks |
| Paper texture | `rgba(255,220,160,.014)` warm grain | `rgba(220,180,60,.016)` cooler grain |
| Ornaments | Classical (❦ ◆ ⁂ ✠) | Alchemical-leaning (⚗ ◈ ✦ ◆ ❦) |
| Overall feeling | Roman inscription, gold monument | Candlelit scholar's library, worn manuscript |

---

*Spec approved: 2026-05-09 · Algorobos Redesign — B+D Blend*
