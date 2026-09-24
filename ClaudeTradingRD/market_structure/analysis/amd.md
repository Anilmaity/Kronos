# XAU/USD — AMD (Accumulation → Manipulation → Distribution) Structural Study

*HTF "Power of 3" / market-maker-model read of 16 months of gold. Strictly through the AMD lens. Every claim anchored to a date + price from the daily/H4/zigzag artifacts. Author: ICT AMD analyst pass, 2026-05-24.*

---

## AMD framework recap (one paragraph)

The algorithm does not move price on supply/demand — it moves price to **engineer and harvest liquidity**, cycling through three phases on every timeframe: **Accumulation** (a range builds; BSL stacks above equal highs and SSL below equal lows; retail waits for the "breakout"; the desk loads quietly), **Manipulation / Judas swing** (a sharp false move sweeps one liquidity pool — the *wrong* direction — to induce retail entries and trip stops), and **Distribution** (the real, displaced delivery in the opposite direction toward the untouched pool, leaving FVGs behind and breaking structure). The three standing objectives at every turn are: **induce** traders the wrong way, **create fear/panic**, and **hit stops**. Premium (above the 50% of the dealing range) is where the algo *sells*; discount (below 50%) is where it *buys*. Money transfers from BSL-delivery to SSL-delivery once the cleared side flips.

> **Data reality (binding):** the feed is two disjoint regimes split by a ~233-day hole (2025-04-01 .. 2025-11-19). **Segment A** (2025-01-06 → 03-30, 76 bars) and **Segment B** (2025-11-19 → 05-19, 155 bars) are analyzed as fully independent AMD studies. Nothing is carried across the gap.

---

## SEGMENT A — 2025-01-06 .. 2025-03-30 (2615 → 3098, +18.5%)

A single clean **bullish AMD cycle**: discount accumulation in January, a shallow late-February manipulation pullback, then a textbook discount-to-premium markup distribution into the 3098 quarter-high. Dealing range 2614.6 → 3097.978; **equilibrium 2856.3**.

### Seg-A AMD phase table

| Phase | Dates | Price range | Equilibrium (50%) | Prem/Disc at entry | Swept liquidity | Displacement |
|---|---|---|---|---|---|---|
| **A — Accumulation** | 01-06 → 01-20 | 2614.6 – 2724.8 | 2669.7 (of the base) | Deep **discount** of the eventual range | SSL below 01-06 low **2614.6** swept (year-open lows) | base build, ~110 pt |
| **M — Manipulation** | 02-24 → 02-28 | 2956.3 H → 2832.7 L | 2894.5 | Pullback into **discount** of the Feb leg | BSL at 02-24 high **2956.3** tagged, then SSL grab to **2832.7** (-4.2% shake-out) | -123.6 pt down-shake |
| **D — Distribution** | 03-02 → 03-30 | 2832.7 → 3097.978 | 2856.3 (range mid, cleared early) | Delivered from discount **through** equilibrium into **premium** | BSL above prior highs (2956 → 3057 → 3098) progressively run | **+265 pt markup (+9.4%)** to the 3098 top |

**Read:** the 02-24→02-28 dip is the classic *manipulation before the final markup* — it grabbed sell-side under the rising structure (2832.7) to fund the last leg, never breaking the January discount base. The 3098 top printed at **100% of the range (pure premium)** with no completing distribution leg inside the window (the data simply ends), so Seg A is best labeled **A → M → D, cycle incomplete at the right edge** (no markdown observed; the gap follows).

---

## SEGMENT B — 2025-11-19 .. 2026-05-19 (opens ~4077, peaks 5602 on 01-28, ends 4550)

The rich regime. Contains a full **bullish AMD cycle to the 5602 all-time high**, a violent **distribution + markdown** to 4099, and a fresh **re-accumulation** that is still resolving at the right edge. Two dealing ranges dominate:
- **Markup range (Nov–Jan):** 4022.26 (11-21 low) → 5602.225 (01-28 high); **equilibrium 4812.2**.
- **Markdown range (Jan–Mar):** 5602.225 → 4099.125 (03-23 low); **equilibrium 4850.7**.

### Seg-B AMD phase table

| Phase | Dates | Price range | Equilibrium (50%) | Prem/Disc | Swept liquidity | Displacement |
|---|---|---|---|---|---|---|
| **A1 — Accumulation (base)** | 11-19 → 12-26 | 4022.26 – 4550.15 | 4286.2 | Built in **discount**, topped at range high | SSL below **4022.26** (11-21) swept first | range build, ~528 pt |
| **M1 — Manipulation (Judas down)** | 12-26 → 12-31 | 4550.15 → 4274.025 | 4412.1 | False break **down** out of the base | BSL at **4550.15** tagged, then SSL grab to **4274.0** (12-29 -225 pt flush) | -276 pt down-shake (-6.1%) |
| **D1 — Distribution / markup** | 12-31 → 01-28 | 4274.0 → **5602.225** | 4938.1 | Delivered discount → **deep premium** | Ran every BSL: 4550 → 4960 (01-22) → 5190 (01-27) → **5602** | **+1328 pt (+31.1%)** — explosive markup |
| **M2 — Manipulation (Judas above range / blow-off)** | **01-28 → 01-29** | 5602.225 ↔ 5097/5595 intraday | n/a | **100% premium** (range top) — buy-side raid | **THE BSL grab**: 5602 tags all stops above; 01-29 round-trips 5595→5097 (-499 pt intraday) | blow-off + reversal print |
| **D2 — Distribution / markdown** | 01-30 → 02-02 | 5439 → **4402.38** | 4920.7 | Premium → **discount** delivery | SSL under 4679 (01-30) then 4402 capitulation low | **-1200 pt (-21.4%)** in 4 sessions |
| **M3 — Retracement / lower-high ladder** | 02-04 → 03-02 | 5092 → 4655 → **5419.66** | varies | Bounce into **premium** of the markdown range (87.9%) | BSL at 5092 (02-04), 5119 (02-11), then 5420 (03-02) — a **bearish SMT lower high** vs silver | failed-high ladder |
| **D3 — Distribution / second markdown** | 03-02 → 03-23 | 5419.66 → **4099.125** | 4759.4 | Premium → deep **discount** | Stops under 4842 / 4804 / 4477 cascaded to **4099** (03-23 -414 pt day) | **-1320 pt (-24.4%)** |
| **A2 — Re-accumulation** | 03-23 → 05-19 | 4099.125 – 4891.54 | 4495.3 | Discount → equilibrium oscillation | SSL below 4099 swept (cycle low); BSL at 4892 (04-17), 4774 (05-12) tagged as lower highs | range, drifting; ends 4480/4550 at **~48% (equilibrium)** |

**Read of the 5602 top (the headline question):** Yes — **5602 is a manipulation/judas above the range, deep in premium (100% of the Nov-low→5602 dealing range, equilibrium 4812.2).** It is the BSL raid that completed the markup, induced the last breakout buyers, then immediately reversed: 01-29 round-tripped 5595→5097 intraday and 01-30 ignited the markdown (open 5439 → low 4679, -760 pt). The subsequent 5420 (03-02) is a **weak / lower high** — a failed retest into premium that set up the second markdown to 4099. Classic Strong-High (5602) → Weak-High (5420) sequence.

---

## Manipulation sweeps log (every datable stop-raid)

| # | Date | Seg | Type | Price level swept | What it raided | Outcome / reversal |
|---|---|---|---|---|---|---|
| A-1 | 2025-01-06 | A | SSL grab | **2614.6** | year-open lows / Jan SSL | reversed up → markup base |
| A-2 | 2025-02-24 | A | BSL tag | **2956.3** | prior swing-high stops | failed, rolled into shake-out |
| A-3 | 2025-02-28 | A | SSL grab | **2832.7** | longs under rising structure | reversed up → final markup to 3098 |
| A-4 | 2025-03-30 | A | BSL grab | **3097.978** | breakout buyers (premium top) | range right-edge (no reversal seen) |
| B-1 | 2025-11-21 | B | SSL grab | **4022.26** | base lows (cycle SSL) | reversed up → +528 pt |
| B-2 | 2025-12-29/31 | B | SSL grab | **4274.0** | base longs (Judas down) | reversed up → +1328 pt markup |
| B-3 | **2026-01-28** | B | **BSL grab (judas above range)** | **5602.225** | all breakout stops above range | **reversed down → -1200 pt** |
| B-4 | 2026-01-29 | B | BSL retest | 5595.77 | residual buy stops | round-trip to 5097 |
| B-5 | 2026-02-02 | B | SSL grab | **4402.38** | panic capitulation longs | reversed up (M3 bounce) |
| B-6 | 2026-02-04 | B | BSL tag | 5091.93 | shorts' stops on bounce | failed (lower high) |
| B-7 | **2026-03-02** | B | BSL grab (weak high) | **5419.66** | shorts' stops; **bearish SMT vs silver** | reversed down → -1320 pt |
| B-8 | **2026-03-23** | B | SSL grab | **4099.125** | trend-long stops (cycle low) | reversed up → re-accumulation |
| B-9 | 2026-04-17 | B | BSL tag | 4891.54 | range-high stops | lower high, rejected |
| B-10 | 2026-05-12 | B | BSL tag | 4773.575 | range-high stops | lower high → drift to 4480 |

---

## Cycles identified (AMD lens)

| Segment | Complete AMD cycles | Phase rhythm | Typical duration |
|---|---|---|---|
| **A** | ~1 (A→M→D, **markdown not observed** before data ends) | accumulation ~2 wk → manipulation ~4 day → markup distribution ~4 wk | full markup ≈ 11 weeks |
| **B** | **2 full cycles** + 1 in progress | (1) A1→M1→D1 markup to 5602; (2) M2 blow-off → D2/D3 double markdown to 4099; (3) A2 re-accumulation, unresolved | bullish cycle ≈ 10 wk; markdown cycle ≈ 8 wk; re-accum ≈ 8 wk and counting |

**Nested rhythm:** the HTF cycle is fractal. The macro markup (D1) is itself built of weekly Judas-then-deliver pulses, and the markdown is a **two-stage distribution** — D2 (the fast 01-30→02-02 flush) then a premium retracement (M3, the 5092/5420 lower-high ladder) then D3 (the 03-02→03-23 second leg). The 5602 **Strong High** and 03-23 **Strong Low** are the two structural anchors of Segment B; everything between is internal liquidity being cleared en route to those external pools. Re-accumulation (A2) has so far produced only **weak/lower highs** (4892, 4774), consistent with an unfinished discount range that still has the 4099 SSL as its strong floor.

---

## Reasoning / WHY — macro ties the manipulation to fundamentals

- **The 5602 top was manufactured on peak dollar weakness.** DXY fell from **100.2 (11-21)** to **96.4 (01-28)** — its lowest reading of the segment — *exactly* into the gold blow-off. A collapsing dollar is the macro fuel that lets the algo run price into 100%-premium and trap the maximum number of late breakout buyers (objective #1, *induce*). When the dollar stopped falling (DXY 96.3→97.0 by 01-30) the prop under gold vanished and the markdown ignited.
- **Bearish SMT divergence confirmed the distribution top.** Gold made its all-time high 01-28 (5602) and on 03-02 made a **lower high at 5420**. Silver, the positively-correlated partner, topped 119.4 on 01-28 and **failed to confirm** gold's 03-02 high (silver only ~96–122 region, well off its own 01-29 121.67 peak) — silver refused to make a new high while gold ground out a weak high. That is textbook **bearish SMT**: distribution, not continuation. This is the single highest-conviction "this is the real top" signal in the dataset.
- **Fear/panic (objective #2) is visible in VIX on the markdown.** VIX was a complacent **16.4 at the 5602 top** (everyone long, no fear) and spiked to **26.1 by the 03-23 low (4099)** — a +60% volatility surge as the SSL cascade forced the panic that funded the markdown. The algo created the fear precisely where it needed capitulation sellers to harvest.
- **Stops (objective #3) at every documented turn.** Each pivot in the sweeps log is a stop-raid: SSL under 4022 / 4274 / 4402 / 4099 (long stops), BSL above 5602 / 5420 (short stops + breakout buys). Money transferred from BSL-delivery (the markup peaking at 5602) to SSL-delivery (the markdown to 4099) the instant the 5602 buy-side was cleared.
- **Segment A echoes the same logic at lower vol:** DXY drifted 108.3 → 104.0 across the markup (dollar weakness = gold strength), and the 02-28 SSL shake at 2832.7 (-4.2%) was the inducement that funded the run into the 3098 premium top.

---

## Confidence & caveats

1. **Only ~9 of 16 months have data.** The 233-day gap (2025-04 → 2025-11) is unbridgeable; Seg A and Seg B are different price regimes (2600s vs 4000–5600s) and must never be joined. Seg A's AMD cycle is **incomplete** — no markdown is observable before the data ends, so its "D" phase is inferred only as far as the 3098 premium top.
2. **HTF AMD on the daily is interpretive, not mechanical.** Phase boundaries are drawn from primary/secondary zigzag pivots (thresholds 6.0 / 3.0); a different threshold would shift the exact dates of accumulation ranges by a day or two. The *sequence* (A→M→D) is robust; the precise calendar edges are soft.
3. **SMT uses daily silver, not sub-15-min.** The framework rates SMT as a sub-15-minute *entry* tool; here it is used on the daily as **confirmation of the distribution regime**, which is a legitimate but lower-resolution application. The directional read (silver lower-high vs gold's 03-02 high) is clear, but the exact intraday divergence cannot be verified from daily bars.
4. **'ticks' is a volume proxy, not true exchange volume.** Climactic-volume claims are intentionally avoided; the AMD read here rests on price/liquidity geometry and macro, not volume.
5. **The 01-29 5097↔5595 prints are intraday noise** around the 5602 top, treated as part of the M2 blow-off, not as independent structural pivots. **5602 is THE peak.**
6. **Re-accumulation (A2) is unresolved.** Whether it resolves up (markup back toward 4892/5092) or breaks the 4099 SSL is undetermined at the right edge (price sits at equilibrium ~48% of the markup range). No directional claim is made beyond 2026-05-19.

---

### Key levels to carry forward (Seg B, live)

| Level | Price | Role |
|---|---|---|
| Strong High (anchor) | **5602.2** (01-28) | major BSL / OB; mitigated weak above |
| Weak / lower high | **5419.7** (03-02) | distribution failure high |
| Re-accum ceiling | **4891.5** (04-17) | nearest untaken BSL |
| Equilibrium (markup range) | **4495.3** | premium/discount pivot; price sits here |
| Strong Low (anchor) | **4099.1** (03-23) | cycle SSL / floor; invalidation of re-accum bull case on daily close below |
