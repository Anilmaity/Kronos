# External cross-reference — a second opinion on the TTrades corpus

**Status:** standalone second opinion. Written 2026-08-25 (analysis phase, workstream 5).
**Nothing in this file has been, or may be, merged into `concepts/`, `raw/`, `notes/` or
`RESUME.md`.** The library's value is that every claim traces to a specific video; backfilling
external material into it would destroy that property. This document sits *beside* the corpus and
disagrees with it where it does.

The corpus is entirely self-referential by design — 505 concepts, all sourced to one YouTube
channel. Several of its hardest calls (CISD's level, the C2 wick asymmetry, the kill-zone settled
negative) were adjudicated from internal evidence alone. This is a check of those calls against
independent public material.

---

## 0. Method, and how sources are graded

Every external claim below carries a grade. They are not equal evidence and the document never
treats them as such.

| grade | what it is | how it is used here |
|---|---|---|
| **A** | Peer-reviewed journal article or a preprint with a reproducible method and stated sample | Can falsify or support a quantitative claim |
| **B** | Independent quantitative study with disclosed method, sample size and cost assumptions, published outside academia | Can support a claim, and can raise a methodological red flag that must be answered |
| **C** | Vendor concept library or indicator with an *implemented, mechanical* definition (LuxAlgo, FluxCharts, TradingFinder, TradingView script authors) | Evidence of **convention**, i.e. what a working detector elsewhere actually computes. Not evidence of doctrine. Commercial incentive to appear authoritative. |
| **D** | SEO education content — the large ICT-tutorial site cluster | Evidence only that a wording is *widespread*. These sites copy each other; five of them agreeing is one source, not five. Never counted as corroboration on its own. |
| **E** | Forum posts, anonymous Medium backtests, social media, Scribd/Studocu re-uploads | Anecdote. Recorded only when it is the sole thing that exists, and labelled as such. |
| **X — NOT EXTERNAL** | `ttrades.com`, the `@TTrades_edu` X account, TradingView scripts published by TTrades | **The corpus itself, in another wrapper.** Must never be counted as corroboration. |

### The contamination hazard, stated up front

Searching any of these terms — *CISD*, *fractal model*, *candle 2 closure*, *expansion candle*,
*IC-CISD* — puts `ttrades.com` and `@TTrades_edu` in the top results. On the C2 wick question the
**entire first page** of a targeted search was the channel's own website and X posts. A careless
external check on this corpus will corroborate the corpus with the corpus. Every X-graded hit
below was found and discarded on exactly that basis, and I have not counted a single one.

### Honest statement of search failure

I could **not** obtain ICT primary material — no mentorship transcripts, no lecture recordings, no
authored text by Michael Huddleston is publicly retrievable in a citable form. Every "ICT says…"
claim below is second-hand, reported by grade-C or grade-D sites without attribution to a specific
lecture. There is therefore **no grade-B-or-better primary ICT source anywhere in this document**,
and the "ICT primary material" leg of the brief could not be executed. Where the public literature
is unanimous I have called it *convention*, not *doctrine*. This is a finding in itself: the
tradition that this corpus belongs to has no citable canonical text.

---

## 1. CISD — Change In The State Of Delivery

**Corpus:** `entry/cisd.yaml` (`contested`, 76 rules, 55 sources), with `entry/ic-cisd.yaml`,
`entry/early-cisd.yaml`, `entry/hourly-cisd-confirmation.yaml`. Adjudicated as: a close plus
displacement beyond the **opening price of the opposing candle series**, where the **point of
interest is part of the definition rather than an extra filter**; explicitly distinct from MSS,
which is displacement through a swing high/low; CISD fires **before** the MSS. Open residual:
*which* price of the series — first candle's open vs highest open — with the extreme reading ruled
out internally. `meta/cisd_reading_comparison.md` measures the readings at Jaccard 0.56–0.59
(`series_open` vs `series_extreme`) and 0.22–0.29 (`series_open` vs `series_close`).

### 1a. CISD is open/close-based; MSS is high/low-based — **CONFIRMS**

| source | grade | what it says |
|---|---|---|
| [TradingFinder, MSS vs CISD](https://tradingfinder.com/education/forex/mss-vs-cisd/) | C | CISD is defined on candle opening and closing prices; MSS is defined on candle highs and lows |
| [LuxAlgo concept library — CISD](https://www.luxalgo.com/library/concept/change-in-state-of-delivery/) | C | A change of character requires breaking a prior swing point; CISD needs only a body close through the run's opening price |
| [innercircletrader.org](https://innercircletrader.org/ict/ict-change-in-the-state-of-delivery/) | D | CISD reads closes against opens; MSS tracks breaks of major highs and lows |
| [innercircletrader.net](https://innercircletrader.net/tutorials/ict-cisd-and-ict-mss/) | D | Same split, framed as a decision guide |

The corpus's central CISD adjudication — the one the previous session spent a unit resolving — is
**independently and unanimously confirmed**, including the secondary claims that CISD fires earlier
than MSS and is the less reliable of the two. Nothing outside contradicts it. The corpus's
statement that a detector firing on a close through a swing was a mislabelled MSS is exactly the
distinction the outside literature draws.

*Detector impact:* none — it validates what is already built. It does raise the priority of keeping
CISD and MSS as **two separate detectors with separate stats**, since the outside consensus is that
they have materially different false-signal rates.

### 1b. The series-level residual — **partially settled, grade C only**

Two independently implemented detectors both anchor on the **open of the first candle of the final
unbroken run**:

| source | grade | level used |
|---|---|---|
| [LuxAlgo](https://www.luxalgo.com/library/concept/change-in-state-of-delivery/) | C | Opening price of the *first* candle in the final unbroken series of same-direction closes; body close required, wicks do not count |
| [FluxCharts](https://www.fluxcharts.com/articles/change-in-state-of-delivery-cisd-explained-how-to-identify-and-trade-it) | C | The opening price that initiated the most recent run of same-direction candles — explicitly the first candle, not the extreme |
| [TradingFinder education](https://tradingfinder.com/education/forex/ict-cisd-trading-style/) | C/D | Opens and closes only, wicks disregarded; **declines to name which candle's open**; no candle-count rule |

**Verdict: EXTENDS, tipping the residual toward first-candle-open.** Two working implementations
agree, and neither uses the run's extreme. But this is grade-C convention from two vendors who may
share lineage, not a settlement of what *this channel* means — and the corpus's own internal
evidence (*"Mark out the opening price in that series"*) remains the better authority on that
question.

**The one genuinely actionable change:** *nobody outside uses `series_close`.* That reading is not
attested anywhere in the public literature, and it is the one the corpus measures at Jaccard
0.22–0.29 against `series_open` — i.e. a different trading system wearing the same name.
Recommendation: keep `series_open` (first-candle open) as the **default**, keep `series_extreme` as
the reported alternative, and **demote `series_close` from a co-equal reading to a diagnostic**.
That halves the CISD parameter grid without picking a winner on the question the corpus actually
left open.

### 1c. Is the point of interest part of the definition? — **CONTRADICTS, weakly; external opinion is split**

| source | grade | position |
|---|---|---|
| [FluxCharts](https://www.fluxcharts.com/articles/change-in-state-of-delivery-cisd-explained-how-to-identify-and-trade-it) | C | A sweep of a key level **is required** — price must trade through the level and return before the reversal counts |
| [LuxAlgo](https://www.luxalgo.com/library/concept/change-in-state-of-delivery/) | C | **Not strictly definitional.** Any qualifying body close satisfies it; sweeps and displacement are quality filters commonly demanded on top |
| [innercircletrader.org](https://innercircletrader.org/ict/ict-change-in-the-state-of-delivery/) | D | No mention of a sweep or point of interest at all |
| [TradingFinder](https://tradingfinder.com/education/forex/ict-cisd-trading-style/) | C/D | No mention of a sweep |

The corpus's reading (POI is constitutive — a bare close-through with no swept level or FVG does
not qualify) is **stricter than the external mainstream**. One vendor agrees, one explicitly
disagrees, two are silent. This does not overturn the corpus — its internal evidence is multiple
videos stating the two-part form — but it means the corpus is recording a **channel-specific
tightening**, not the general ICT definition, and the concept file should be read that way.

*Detector impact:* material and measurable. Build the POI gate as a **switch**, not a hard-wired
precondition, and report event counts and any downstream statistic both ways. The gate is the
single biggest frequency lever in the CISD detector and the external literature does not agree it
belongs inside the definition.

### 1d. IC-CISD (intracandle CISD) — **SILENT**

Searching the exact terms returns `ttrades.com` and the channel's own video (grade X), plus one
grade-C page ([FluxCharts](https://www.fluxcharts.com/articles/change-in-state-of-delivery-cisd-explained-how-to-identify-and-trade-it)-adjacent
community material) that lists *intraweek / intraday / intracandle* as CISD variants without
defining the intracandle case mechanically. There is **no independent definition of IC-CISD
anywhere.** The corpus's own claim that it is the channel's invention is consistent with what the
web shows.

The corpus's adjudication — IC-CISD is the same test relocated inside a continuation candle, not a
rival system — is therefore **uncheckable externally**, and stands on internal evidence alone. It
also inherits the unresolved series-level question, as `entry/ic-cisd.yaml` already records.

---

## 2. The fractal model (C1–C2–C3–C4) vs ICT's Power of Three

**Corpus:** `model/fractal-model-c2.yaml`, `-c3`, `-c4` (all `contested`),
`model/power-of-three-amd.yaml` (`contested`), `meta/fractal_reading_comparison.md`.

### External account of PO3 — **CONFIRMS the corpus's AMD entry**

Grade-C/D sources ([LuxAlgo](https://www.luxalgo.com/library/concept/accumulation-manipulation-distribution/),
[FXOpen](https://fxopen.com/blog/en/what-is-ict-po3-and-how-do-traders-use-it/),
[ictkillzone.com](https://www.ictkillzone.com/ict-power-of-three)) describe PO3 in terms that match
`power-of-three-amd.yaml` almost line for line: consolidation near the period open, a manipulation
excursion that sweeps stops in the direction *opposite* the intended move, then distribution to the
real objective; the manipulation forms the candle's **wick** and the distribution forms its
**body**; the sequence is applied fractally to daily, weekly, monthly and quarterly candles; the
session mapping is Asia accumulates / London manipulates / New York distributes.

All three of the corpus's readings — session form, candle form anchored on the **opening price**,
and range-level AMD via failure to displace — are attested outside. Nothing contradicts it.

### Is the C1–C4 model a rebranding of PO3? — **EXTENDS. It is distinct, and the overlap is narrower than it looks.**

The two describe different objects:

- **PO3 is intra-candle.** Three phases *inside one* HTF candle (or one session/week).
- **The fractal model is inter-candle.** A sequence of *four consecutive* HTF candles with
  mechanical closure tests between them: C2 sweeps C1's extreme and closes back inside
  (`fractal-model-c2`); C3 closes beyond C2's body/opening price (`fractal-model-c3`); C4 is a
  continuation gated by the half-of-C3's-range wick filter (`fractal-model-c4`). None of these
  tests exists in any external PO3 description.

They meet at exactly one place: **IC-CISD is PO3 applied inside a single candle** — the wick is the
manipulation, the body is the distribution, and the IC-CISD is the mechanical trigger that declares
the manipulation over. That is a genuine extension of PO3, not a renaming of it.

So the honest verdict is layered: the AMD/PO3 layer is **inherited and externally confirmed**; the
C1–C4 sequence layer is **original and externally unattested**; the wick-formation trigger is an
**extension** of the inherited layer.

### One concrete hazard found: a naming collision

Third-party descriptions of the *TTrades Fractal Model indicator* (grade C/X-adjacent, e.g. the
[Fractal Model \[Pro+\]](https://tradingview.com/script/XdwK9qQQ-Fractal-Model-Pro-TTrades) listing
and [ZakAlgoTrade's Fractal Structure Model](https://in.tradingview.com/script/70aYMnxa-Fractal-Structure-Model-Pro/))
use **C1/C2/C3/C4 to mean "how many HTF candles have elapsed since the setup triggered"** — a
setup-age counter with colour coding for exhaustion — *in addition to* the closure semantics. The
corpus uses C1 = the candle before the sweep, C2 = the sweep candle, C3 = the continuation. These
are two different indexings that can coincide by accident.

*Detector impact:* if the C2/C3/C4 detectors are ever compared against indicator screenshots or
third-party output, **assert the indexing first**. `RESUME.md` already records that the indicator's
real C2/C3/C4 conditions are paywalled; this adds that even its *labels* may not mean what the
corpus's labels mean.

---

## 3. The C2 "small wick implies expansion" claim

**Corpus:** `model/small-wick-expansion-rule.yaml`, `structure/wick-size-test.yaml`
(`underspecified`), `structure/small-wick-supports-expansion.yaml`. The measured asymmetry in
`meta/fractal_reading_comparison.md`: small-wick C2s deliver beyond the C2 open 78.1 / 81.0 / 82.9 %
(1h / 4h / 1D) vs 63.1 / 64.7 / 65.6 % for large-wick, stable over three years.

### Verdict: **SILENT.** No independent attestation, and no published numbers.

Every hit on a targeted search was grade **X** — `ttrades.com` articles and an `@TTrades_edu` X post
restating the rule. That is the corpus, not corroboration. Outside the channel:

| source | grade | what it supports |
|---|---|---|
| [FXOpen — candlestick wick analysis](https://fxopen.com/blog/en/candlestick-wick-meaning-and-trading-strategies/) | D | The *generic* claim only: large body with small wicks reads as sustained directional pressure, typical at breakouts and trend continuation |
| general candlestick literature (marubozu) | D | Same generic claim, centuries old |

The generic momentum-candle reading is universal folklore. The corpus's claim is **much more
specific** — a *conditional* asymmetry, on a *sweep-and-close-back-inside candle*, measured against
*that candle's own open*, on the *next* candle. No one outside has stated that conditional, let
alone measured it. **The corpus's own table is, as far as public material goes, the only number
that exists for it.**

### Negative external evidence that bears on it

| source | grade | finding |
|---|---|---|
| Marshall, Young & Rose (2006), *Candlestick technical trading strategies: Can they create value for investors?*, J. Banking & Finance 30(8) 2303–2323 — [RePEc](https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html) | **A** | Candlestick strategies produced no statistically significant excess returns on DJIA components 1992–2002, tested against bootstrapped random OHLC series |
| [Tharavanij et al. (2017), SAGE Open](https://journals.sagepub.com/doi/10.1177/2158244017736799) | A | Mixed-to-negative profitability for candlestick patterns in an emerging market |

These are a **prior against OHLC-shape signals**, not a refutation of this specific one: they test
named reversal patterns on daily equities, not a continuous wick-ratio conditional on FX/metals
intraday. But they establish that "the shape looked predictive in-sample" has failed before, under
better statistical control than anything in this project so far.

### The single most useful external fact in this document

[MPM Markets research, *Does the Fair Value Gap Strategy Work?*](https://mpmmarkets.com/research/does-the-fair-value-gap-strategy-work)
(grade **B** — 7 years, 4 liquid futures markets, 3 timeframes, ~40,000 detected occurrences,
published 2026-07-05; the site 403s direct fetches, so this is reconstructed from indexed summaries
and should be re-read in a browser before being relied on):

- The FVG **reaction is real** — roughly **five percentage points above a random baseline at the
  same distance**.
- Across five independent trade constructions, the edge is a coin flip or is exactly consumed by
  realistic costs.
- **The one construction that looked strongly profitable was an artifact of resolving exits on
  coarse (hourly) bars. Measured on 1-minute resolution the edge disappeared** — reported elsewhere
  as roughly 73 % → 50 % win rate.

Their study design is the one to copy: *compare the effect against a random-entry baseline at the
same distance*, because that is the only test that separates a signal from the base rate. The
corpus already knows the base-rate problem (`meta/primitive_base_rates.md`: ~40–44 % of candles
sweep the prior candle's range). MPM adds the second half of it: **an intrabar-resolution artifact
can manufacture a 20-point win-rate swing out of nothing.**

*Detector / backtest impact — this is the concrete deliverable of this whole document:*
1. Resolve the C2-wick backtest on **1-minute (or finer) data**, never on the signal timeframe's
   OHLC. A 1h C2 test whose target and stop are both resolved on 1h bars is exactly the construction
   MPM showed to be fake.
2. Report against a **matched random control** — same instrument, same timeframe, same target
   distance, random entry — not against 50 %.
3. The 78–83 % vs 63–66 % gap is currently a **directional-delivery rate, not an edge**: no target,
   no stop, no spread, no slippage, and an arbitrary median split. Until points 1 and 2 are done it
   should not be described as an asymmetry that survives testing — only as one that survives
   *counting*.

---

## 4. Kill-zone hours

**Corpus:** `time/killzones.yaml` (`contested`, voice `mixed`), plus
`time/new-york-am-session-only.yaml`, `entry/killzone-execution-sequence.yaml`.
`RESUME.md` finding 8 records a **settled negative**: the hours are never stated, "kill zone" is
used as a hard gate with no clock attached, and the widest usable TTrades statement is 08:30–12:00.

### First, a correction to how that negative is likely to be read

The negative is about **TTrades' own voice**. The corpus is *not* empty of clock times:
`time/killzones.yaml` already carries full windows from one video (`MPeeE55rNOw`) —
FOREX Asia 20:00–00:00, London 02:00–05:00, New York AM 07:00–10:00, London Close 10:00–12:00;
INDICES New York AM 08:30–11:00, New York PM 13:30–16:00, all New York time — plus three guests who
each name a *different* window. So the accurate statement is: **the channel's own gate has no clock
attached; the corpus does contain published windows, in `mixed`/`guest` voice.**

### What the public literature publishes — **EXTENDS (external convention, not this channel's rule)**

| window | consensus (ET) | variance found | sources |
|---|---|---|---|
| London Open | **02:00–05:00** | none found | [tradingrage](https://tradingrage.com/learn/ict-killzone-explained) C/D, [EBC](https://www.ebc.com/forex/what-are-ict-killzone-times-simple-trading-hours-guide) D, [LiteFinance](https://www.litefinance.org/blog/for-beginners/trading-strategies/ict-killzones/) D |
| New York (forex) | **07:00–10:00** | some sites give 08:00–11:00 | as above |
| New York (index futures) | **08:30–11:00** | consistent | [Trinity Trading](https://blog.trinitytrading.io/ict-kill-zones-best-times-trade-futures-2026/) D, [ictkillzone.com](https://www.ictkillzone.com/ict-kill-zones) D |
| London Close | **10:00–12:00** | none found | as above |
| Asian | **contested: 20:00–00:00 vs 19:00–22:00 vs 20:00–23:00** | the widest disagreement of the four | as above |
| "Silver Bullet" sub-window | **10:00–11:00** | consistent | [ictkillzone.com](https://www.ictkillzone.com/ict-kill-zones), [innercircletrader.net](https://innercircletrader.net/tutorials/master-ict-kill-zones/) D |

Two things follow. First, the public windows **match the corpus's forex row from `MPeeE55rNOw`
exactly** on three of four sessions — so that video was reporting the standard convention, not an
idiosyncratic reading, and the Asian session is the one place even the outside world disagrees with
itself. Second, and more important: **none of this is TTrades' stated rule.** Adopting 07:00–10:00
because the internet says so would be precisely the silent backfill the project prohibits. It is a
*default for a knob*, and it must be labelled as external convention wherever it is used.

Every source also flags the EST/EDT trap, which matches `RESUME.md` finding 1 — the anchor is
US-Eastern-with-DST, not a fixed UTC-5.

### Independent support that time-of-day conditioning is real at all — grade **A**

| source | grade | finding |
|---|---|---|
| Andersen & Bollerslev, *Intraday periodicity and volatility persistence in financial markets*, J. Empirical Finance (1997) — [PDF](https://finance.martinsewell.com/stylized-facts/volatility/AndersenBollerslev1997b.pdf) | A | Strong, robust intraday periodicity in FX and equity return volatility, with peaks tied to the opening and closing of regional markets; ignoring it distorts high-frequency dynamics |
| Andersen & Bollerslev (1998), DEM–USD | A | Intraday periodicity, long memory and macro-announcement effects modelled simultaneously; the announcement component is separable |
| [arXiv 2605.04004, Mesfin — MNQ falsification study](https://arxiv.org/abs/2605.04004) | A (preprint) | Its two *positive controls* were session-conditioned: an RTH confluence signal (T=5.83, N=538) and a London-session signal (T=5.15, N=289) |

This is the most defensible thing in the entire external record: **session/time-of-day conditioning
carries real, statistically robust information.** ICT's specific clock boundaries are convention
with no published derivation; the *practice* of conditioning on session is supported by mainstream
econometrics. That is a good reason to keep the session gate as a fitted parameter rather than
dropping it, and 08:30 is independently interesting because it is a scheduled-announcement boundary
(the corpus's own `killzones.yaml` notes 08:30 as the news-embargo lift).

---

## 5. Displacement / "aggressive"

**Corpus:** `structure/displacement.yaml` (`contested`), `structure/displacement-range.yaml`,
`structure/failure-to-displace.yaml`, `structure/expansion-signature.yaml`. The corpus's finding:
qualitative everywhere, except one comparative procedure — fix a candle window (four in the worked
example), compare the window's range and the distance travelled beyond the broken high against a
non-displacing instance of the same event.

### Verdict: **CONFIRMS the negative — and the corpus is *more* specified than the public literature.**

| source | grade | what it gives |
|---|---|---|
| [LuxAlgo — displacement](https://www.luxalgo.com/library/concept/displacement/) | C | Qualitative: unusually large body relative to recent volatility, minimal wicks in the direction of travel |
| [howtotrade](https://howtotrade.com/blog/ict-displacement/) | D | Heuristic: at least 3 consecutive large-bodied same-direction candles with small/no wicks, minimal retracement, and an FVG left behind |
| [ICT Displacement Scanner \[EmpArchitect\]](https://www.tradingview.com/script/1GmKYyyl-ICT-Displacement-Scanner-EmpArchitect/), [FibAlgo](https://www.tradingview.com/script/9OYOAKNU-FibAlgo-ICT-Displacement/) | C | **The only numbers anywhere:** dual detection by ATR multiple *and* body/range ratio; "strong" displacement characterised at roughly **2–3× ATR**; a **body-to-range ratio above 0.60** as a mechanical per-candle test; composite 0–100 "quality scores" |

No source outside gives a *doctrinal* threshold. The numbers that exist are **vendor
parameterisations invented to make an indicator fire** — grade C, no derivation, no validation, and
different vendors pick different ones. That is a clean confirmation of the corpus's finding, and it
is worth noting that the corpus's comparative four-candle procedure appears **nowhere** in the
public literature: on this concept the channel is the more rigorous source.

*Detector impact:* implement three and report their disagreement, exactly as with CISD readings —
(i) the corpus's relative window comparison, (ii) body/range ≥ 0.60, (iii) body ≥ k×ATR with
k ∈ {1.5, 2, 3}. Use (ii) and (iii) as **fitting candidates against the channel's narrated
accept/reject calls** (the plan already in `RESUME.md` next-step 2), not as adopted definitions.
The same applies to "aggressive", which the public literature treats as a pure synonym for
displacement — no source distinguishes them, which is mild external support for collapsing the two
in the detector.

---

## 6. Order blocks, breakers, FVG — definitional variance

This is the section where external disagreement is the *product*: a detector has to be
parameterised over exactly the axes the public literature argues about.

### 6a. Order block — **EXTENDS / partially CONTRADICTS**

**Corpus:** `structure/order-block.yaml` (`contested`, voice `mixed`) — the opposing candle **or
series** inside the move that swept a swing into an important level; validated only by a **close
back through it**; the traded level is the block's **opening price**. `entry/mean-threshold.yaml`
carries the 50 % reading. `structure/order-block-requires-bos.yaml` carries the BOS precondition.

| axis | corpus | public literature | grade |
|---|---|---|---|
| single candle or series | **series** allowed and often preferred | mainstream is the **last opposing candle**; sources explicitly acknowledge the single-vs-cluster disagreement as unsettled | C/D ([liquidityfinder](https://liquidityfinder.com/news/anatomy-of-a-valid-order-block-in-smart-money-concepts-67221), [tradingstrategyguides](https://tradingstrategyguides.com/day-5-order-blocks-explained-ict-vs-smc-guide-to-bullish-bearish-obs/)) |
| the traded level | the block's **opening price** | most commonly the **whole candle range** as a zone, or its **50 % mean threshold** | C/D |
| what validates it | a **close back through** the block | displacement / BOS after it | C/D |
| open/close vs wick edges | not settled in-corpus | not settled outside either | C/D |

The corpus's "trade the opening price" is a notably tighter reading than the mainstream zone
approach, and it is structurally the *same* anchor as its CISD reading — which is internally
coherent and worth noting as a signature of this channel rather than a general ICT rule. One
grade-C/D source states the subjectivity outright: most interpretations use a single candle's
range, but others do not, and this is why two traders mark the same chart differently.

*Detector impact:* parameterise on three axes and cross them —
`series_len ∈ {1, n}` × `zone ∈ {full_range, body, open_only, mean_threshold_50}` ×
`validation ∈ {close_through, displacement, bos}`. Report the pairwise agreement matrix the way
`cisd_reading_comparison.md` already does. Do **not** pick the mainstream reading because it is
mainstream — the corpus is the authority on what this channel teaches.

### 6b. Breaker block — **EXTENDS; the corpus's definition is not the mainstream one**

**Corpus:** `entry/breaker-block.yaml` (`contested`, 62 rules, 38 sources) — a **pure four-point
geometric sequence**: bearish = high → low → higher high → **lower low**, zone = the down-close
candles spanning the *first* high to the *first* low; incomplete until the fourth point prints;
requires a HTF bias. A later video narrows the zone to the lowest down-close candle before the
higher high (recorded as evolution, both kept).

**Public literature:** a breaker is a **failed order block** — an order block price traded through,
which then flips polarity and works from the other side — and the stricter (majority) formulation
requires a **liquidity sweep plus a market-structure shift** before it is valid. The discriminator
against a **mitigation block** is stated crisply and consistently outside: *mitigation block = the
same failure without the preceding liquidity sweep*
([Alchemy Markets](https://alchemymarkets.com/education/strategies/breaker-block-explained/) C/D,
[tradingstrategyguides day 12](https://tradingstrategyguides.com/day-12-breaker-blocks-mitigation-blocks-explained-ict-smc-deep-dive/) D,
[FluxCharts](https://www.fluxcharts.com/articles/breaker-blocks-bb-explained) C).

These are not the same construction. The corpus's version never mentions an order block at all and
is decidable from four swing points; the external version is defined by an object's *failure* and
requires a sweep. They will frequently coincide on a chart and will not always.

*Detector impact:* two consequences. (1) Interoperability risk — a "breaker" detector built purely
from the corpus will not reproduce what anyone else labels a breaker, so any comparison against
third-party output or a labelled dataset must state which definition is in force. (2) A concrete
check to run against `entry/mitigation-block.yaml` (not read in depth for this document): does the
corpus's mitigation block also turn on the *absence of a preceding sweep*? If it does, that is an
independent external confirmation of the corpus's discriminator; if it does not, the corpus is
using the term differently from everyone else and the concept file should say so.

### 6c. Fair value gap — **CONFIRMS the variance the corpus already records**

**Corpus:** `structure/fair-value-gap.yaml` (`contested`, voice `mixed`) — measured pre-move extreme
to post-move opposing extreme, with a merge rule for consecutive same-direction candles; "efficient"
only when fully closed; invalidation by candle *close* beyond the defending edge, wicks tolerated.
Open questions recorded: wick vs body fill, partial fill, whether exactly-touching prices count.

The public literature agrees on the three-candle non-overlap core and **disagrees on precisely the
axes the corpus flagged as open** — fill measured by wick or body, whether a partial fill consumes
the gap, whether consecutive candles merge into one block. The corpus's `ambiguities` list is a
faithful map of the real external disagreement, which is a good sign about the extraction method.

One quantitative note, and a warning attached to it: [tradingstats.net](https://tradingstats.net/gap-fill-strategy/)
(grade B/C) reports a **60.3 % baseline fill rate over 2,791 NQ days (2015–2025)**, and
[fxnx.com](https://fxnx.com/en/blog/fair-value-gap-fill-rates-volatility-indices) (grade D/E)
reports 48 % partial-fill-with-rejection over 500 H1 setups on synthetic volatility indices. **Do
not import either number.** The first measures *session gaps* (a different object from an FVG); the
second is on synthetic instruments with no relation to XAUUSD. They are listed to show what the
public numbers actually measure, which is usually not the thing they are cited for.

The [mkscienceset PDF](https://mkscienceset.com/articles_file/862-_article1772532938.pdf) proposing
a "degree of fair value gaps" metric with a 3.2× reaction-strength claim is graded **E**: the
publisher shows the signatures of a predatory outlet, and the claim is not independently
replicated. It is recorded here only so a later session does not rediscover it and mistake it for
grade A.

---

## 7. Broader sweep: published quantitative testing of ICT/SMC

### There is no peer-reviewed literature on ICT or SMC. That is the headline finding.

Targeted searches of arXiv/SSRN and general academic search returned **zero** peer-reviewed papers
testing ICT or SMC constructs by name. One grade-C/D source states the position plainly and
correctly: no rigorous public study shows the methodology is profitable on its own, and its patterns
are defined loosely enough that two traders mark the same chart differently. That second clause is
the same problem this corpus has spent 505 concepts documenting.

What does exist, graded:

| study | grade | scope | result |
|---|---|---|---|
| [MPM Markets — FVG](https://mpmmarkets.com/research/does-the-fair-value-gap-strategy-work) | **B** | 7 yrs, 4 futures markets, 3 TFs, ~40k occurrences | Reaction ~5pp above random; **no tradeable edge after costs**; the profitable construction was an intrabar look-ahead artifact (≈73 %→50 % win rate on 1-min resolution) |
| [arXiv 2605.04004 — Mesfin, MNQ falsification](https://arxiv.org/abs/2605.04004) | **A** (preprint) | 14 signal families, 5-min MNQ, 947 trading days (2021–2025) | **None** cleared a 2-point round-trip friction cost with statistical significance; gross edges 0.07–1.50 pts/trade. Not ICT-specific, but a hard prior on OHLCV intraday signals |
| Marshall, Young & Rose (2006), JBF | **A** | DJIA components, 1992–2002, bootstrap control | Candlestick strategies create no value |
| [offbeatforex — mechanical ICT bot](https://offbeatforex.com/is-ict-strategy-profitable/) | **B/C** | EURUSD 15m, 24,908 candles, Jul 2025–Jul 2026, thresholds frozen pre-run | **Mechanical: 125 trades, 29.6 % WR, PF 0.81, −45 % on a $10k account, max DD $5,121.** Its discretionary/AI arm made +83 % on 47 trades over 2 months — too small a sample to mean anything, and self-selected. **Costs excluded from both.** |
| ["I backtested 2,600 trades using SMC"](https://medium.com/@QuantumAlgo/i-backtested-2-600-trades-using-smart-money-concepts-heres-what-actually-works-bb3c671098c6) | **E** | claimed 2,600 trades, 10 assets, 26 months | Claims 61 % WR, PF 2.17, +2.27R avg. **No method disclosure, author is an indicator vendor.** Treat as marketing, not evidence |
| [Liberty University honors thesis](https://digitalcommons.liberty.edu/honors/67) | C | general TA backtesting | Adjacent, not ICT-specific |

### What this means for this project

The best-documented mechanical test of the full ICT vocabulary that exists publicly **lost money**:
PF 0.81 over a year, before costs, with pre-frozen thresholds. Its author's framing is worth
carrying: a curve-fit "ICT works" number would be worthless, so the thresholds were frozen before
the run. That is the correct instinct and it is also the trap this project is closest to —
`RESUME.md` next-step 2 proposes **fitting** the expansion-wick threshold to the channel's narrated
labels. Fitting to *his labels* is legitimate (it is a supervised reconstruction of what he
teaches); fitting to *P&L* is not, and the two must not be allowed to merge. Fit the threshold on
the label task, freeze it, and only then run the backtest.

---

## 8. Which corpus adjudications the external evidence puts at risk

Ranked by how much a wrong call would cost, times how much the external record actually moves it.

### 1. The C2 small-wick asymmetry, treated as an *edge* — HIGH RISK

The corpus is careful in `fractal_reading_comparison.md` ("only a raw directional-delivery rate"),
but `RESUME.md` finding 4 says the claim "survives testing" and next-step 1 calls it the best
backtest candidate. The MPM study is a direct warning: a same-family ICT construct showed a large,
stable-looking effect that **vanished entirely** when exits were resolved intrabar rather than on
the signal timeframe's OHLC. Marshall et al. is a second, independent prior against OHLC-shape
signals. And the effect is externally unattested by anyone.

**To settle:** re-run with (a) 1-minute-or-finer exit resolution, (b) a matched random-entry control
at the same target distance, (c) real spread/slippage for XAUUSD, (d) the split point varied rather
than fixed at the median. If the 15-point gap survives all four it is the most interesting finding
in the project. If it does not, that is a clean, publishable negative and the corpus loses its only
falsifiable prediction — which is worth knowing before any capital is committed.

### 2. "The point of interest is part of the CISD definition" — MEDIUM-HIGH RISK

External opinion is genuinely split (one vendor requires the sweep, one explicitly says it is a
quality filter and not definitional, two are silent). If the corpus has folded a filter into a
definition, every CISD frequency number it reports is conditioned on an assumption the wider
literature does not share. Internal evidence is strong, so this is not a reversal — it is a
labelling risk.

**To settle:** run the detector with the POI gate on and off and report both event counts and
downstream statistics. Cheap, and it converts an interpretive dispute into a number.

### 3. The CISD series-level residual (first-candle open vs highest open) — MEDIUM RISK, now partly informed

Two independent implementations both use the first candle's open. That is grade-C convention, not
proof of what the channel means, but it is the first outside evidence to bear on the residual at
all. The actionable part is the *other* direction: `series_close` is used by nobody outside and is
the reading furthest from `series_open` (Jaccard 0.22–0.29).

**To settle:** keep `series_open` as default, `series_extreme` as the reported alternative, demote
`series_close` to a diagnostic. Full settlement would need ICT primary material, which does not
appear to be publicly retrievable.

### 4. Breaker (and mitigation) block definitional alignment — MEDIUM RISK, interoperability only

The corpus's breaker is a four-point geometry; the world's breaker is a failed order block requiring
a sweep and an MSS. Inside this project the corpus is the authority and nothing is wrong. The risk
is silent mismatch the moment the detector is compared with any external chart, dataset or
indicator.

**To settle:** name the definition in force in the detector module, and run the one concrete check
in §6b — whether `entry/mitigation-block.yaml`'s discriminator is the absence of a preceding sweep,
which is what the outside literature uses.

### 5. The kill-zone "settled negative" — LOW RISK of being wrong, MEDIUM risk of being misread

The negative is correct and external evidence cannot overturn it (it is a claim about what a
speaker did not say). Two live hazards instead: the corpus *does* contain published windows in
`mixed`/`guest` voice and a reader of `RESUME.md` alone would not know that; and the external
windows are convention that could get silently adopted as his rule.

**To settle:** nothing to settle. Label any adopted window `source: external convention` in the
config, keep 08:30–12:00 ET as the widest attested TTrades statement, and let it be a fitted knob.
Andersen & Bollerslev give real grounds for keeping session conditioning in the model at all.

### 6. The C3 reference level (C2 open vs C2 body vs C2 extreme) — MEDIUM RISK, and externally hopeless

The public literature does not contain the C3 closure concept in any form. There is no outside help
available, now or later.

**To settle:** fitting against narrated accept/reject calls is the only route, exactly as
`RESUME.md` next-step 3 already plans. This document adds nothing except the confirmation that
further searching will not help.

### 7. Displacement's lack of a threshold — NOT AT RISK; the corpus is ahead

External confirmation that no doctrinal number exists anywhere. The corpus's comparative four-candle
procedure is more specified than anything published. The only external contribution is a set of
candidate parameterisations (body/range ≥ 0.60, 2–3× ATR) to fit against, with no authority behind
them.

---

## 9. Summary of verdicts

| corpus adjudication | concept id | verdict | strongest external grade |
|---|---|---|---|
| CISD is open/close-based, MSS is swing-based, CISD fires first | `cisd` | **CONFIRMS** | C (unanimous, 4 sources) |
| CISD level = opening price of the opposing series | `cisd` | **CONFIRMS** | C |
| …specifically the *first candle's* open | `cisd` | **EXTENDS** (tips the residual; not settled) | C ×2 |
| `series_close` is a co-equal reading | `cisd` | **CONTRADICTS** — attested nowhere outside | C |
| Point of interest is constitutive, not a filter | `cisd` | **CONTRADICTS, weakly** — external split | C (both ways) |
| IC-CISD is the same test relocated inside a candle | `ic-cisd` | **SILENT** — no independent definition exists | — |
| AMD / PO3 phases, wick = manipulation, body = distribution, fractal | `power-of-three-amd` | **CONFIRMS** | C/D |
| C1–C4 is distinct from PO3, not a rebranding | `fractal-model-c2/c3/c4` | **EXTENDS** — distinct at the sequence level, PO3-derived intracandle | — (unattested) |
| Small wick implies expansion | `small-wick-expansion-rule`, `wick-size-test` | **SILENT** — generic folklore only; corpus's number is the only one that exists | A (adverse prior) |
| Wick size has no stated threshold | `wick-size-test` | **CONFIRMS** the negative | C |
| Kill-zone hours never stated by the channel | `killzones` | **CONFIRMS**; external convention supplies windows | C/D + A (for session effects generally) |
| Displacement is qualitative; only a relative procedure exists | `displacement` | **CONFIRMS**; corpus is more specified than the public literature | C |
| Order block level = the block's opening price | `order-block` | **EXTENDS / partly CONTRADICTS** mainstream zone reading | C/D |
| Breaker = four-point geometry | `breaker-block` | **EXTENDS** — mainstream defines it as a failed order block | C/D |
| FVG fill/invalidation is unsettled | `fair-value-gap` | **CONFIRMS** the variance exactly | C/D |
| ICT/SMC has published quantitative validation | — | **CONTRADICTS** — no peer-reviewed literature exists; best public tests are negative | A, B |

---

## 10. Sources, with grades

**Grade A — peer-reviewed or reproducible preprint**
- Marshall, Young & Rose (2006), *Candlestick technical trading strategies: Can they create value for investors?*, J. Banking & Finance 30(8):2303–2323 — https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html
- Andersen & Bollerslev (1997), *Intraday periodicity and volatility persistence in financial markets*, J. Empirical Finance — https://finance.martinsewell.com/stylized-facts/volatility/AndersenBollerslev1997b.pdf
- Tharavanij, Siraprapasiri & Rajchamaha (2017), SAGE Open — https://journals.sagepub.com/doi/10.1177/2158244017736799
- Mesfin (2026), *Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures* — https://arxiv.org/abs/2605.04004

**Grade B — disclosed-method quantitative work outside academia**
- MPM Markets, *Does the Fair Value Gap Strategy Work?* — https://mpmmarkets.com/research/does-the-fair-value-gap-strategy-work *(403s to automated fetch; re-read in a browser before relying on the exact figures)*
- offbeatforex, *Is ICT Strategy Profitable? I Backtested It Using AI* — https://offbeatforex.com/is-ict-strategy-profitable/
- tradingstats.net, NQ gap-fill study — https://tradingstats.net/gap-fill-strategy/

**Grade C — implemented mechanical definitions (convention, not doctrine)**
- LuxAlgo concept library: [CISD](https://www.luxalgo.com/library/concept/change-in-state-of-delivery/), [AMD](https://www.luxalgo.com/library/concept/accumulation-manipulation-distribution/), [displacement](https://www.luxalgo.com/library/concept/displacement/)
- FluxCharts: [CISD](https://www.fluxcharts.com/articles/change-in-state-of-delivery-cisd-explained-how-to-identify-and-trade-it), [breaker blocks](https://www.fluxcharts.com/articles/breaker-blocks-bb-explained)
- TradingFinder: [CISD](https://tradingfinder.com/education/forex/ict-cisd-trading-style/), [MSS vs CISD](https://tradingfinder.com/education/forex/mss-vs-cisd/)
- TradingView displacement scripts: [EmpArchitect](https://www.tradingview.com/script/1GmKYyyl-ICT-Displacement-Scanner-EmpArchitect/), [FibAlgo](https://www.tradingview.com/script/9OYOAKNU-FibAlgo-ICT-Displacement/)
- liquidityfinder, *Anatomy of a Valid Order Block* — https://liquidityfinder.com/news/anatomy-of-a-valid-order-block-in-smart-money-concepts-67221

**Grade D — SEO education cluster (widespread wording; one source, not many)**
- innercircletrader.org, innercircletrader.net, tradingrage, EBC, LiteFinance, ictkillzone.com,
  Trinity Trading, howtotrade, alchemymarkets, tradingstrategyguides, FXOpen, arongroups, plisio

**Grade E — anecdote / unverifiable**
- Medium "2,600 trades" SMC backtest — https://medium.com/@QuantumAlgo/i-backtested-2-600-trades-using-smart-money-concepts-heres-what-actually-works-bb3c671098c6
- mkscienceset "degree of fair value gaps" PDF — https://mkscienceset.com/articles_file/862-_article1772532938.pdf
- Scribd / Studocu re-uploads of ICT notes; Forex Factory and CryptoCraft threads
- Sentient Trading Society, *Dumb Money Concepts and Backtest Limitations* (403s to fetch; listed only so it is not rediscovered as new)

**Grade X — NOT EXTERNAL. The corpus in another wrapper. Cited by no claim above.**
- `ttrades.com` (all articles), `@TTrades_edu` on X, TradingView scripts published under TTrades

---

*Written without modifying anything under `concepts/`, `raw/`, `notes/`, `python/` or `RESUME.md`.
No git commands were run.*
