# shorts_01 — study notes

**Unit**: `shorts_01` (batch 1 of 4 of the Shorts playlist), 60 videos, 2886 s of runtime.
**Transcripts available**: 57 of 60. Three have no transcript on disk and were skipped:
`vg_6_aWpm1Y`, `V7ENE6si7DQ`, `gSzKofrQchI`.
**Output**: 34 YAMLs in `concepts/_inbox/shorts_01__*.yaml`, carrying 134 verified source
entries across 54 distinct videos. **One new concept id; 33 reuse existing ids.**

---

## The genre, and what fraction was substantive

Each Short is 30–62 seconds and around 100–250 words. The format is almost always the same:
a chart is already marked up, he replays a few bars, and he narrates the decision. There is no
motivational content and only two promotional tails in the whole batch (both pointing at the
website PDF or the YouTube channel), so the "skip it entirely, it is promotion" case barely
arises here — the Shorts are dense.

What they are *not* is new. This batch is a compression of material already studied at length:
54 of 57 Shorts restated something that is already among the 383 concepts in `INDEX.md`, and
the right action for those was to reuse the id and attach the Short as one more `sources` entry.
Exactly **one** Short pair produced a claim I could not place anywhere in the library.

The genre's one real advantage held up. Because a 30-second clip has no room for a worked
example *and* a hedge, he sometimes states a rule as a bare sentence where the hour-long version
buries it inside a chart walk. Three of those one-liners are worth more than everything else in
the batch and are called out below.

Nine of the 57 are **duplicate uploads** — the same clip published twice under two ids. Three
pairs: `xZQOxWQagTA` / `_WGmLTcIv-E`, `QIGVXzsVER8` / `zgRhc0gxFrs`, and `B_tHxplbxV0` /
`oSrXv92fIzc` (this last pair is word-identical apart from "timeframe" vs "time frame").
I cited both members of each pair where I used them, and flagged the duplication in the
relevant `ambiguities` so a later counter does not read two uploads as two independent
witnesses.

---

## Transcript hygiene

All 57 are `yt-dlp-auto` captions with no timestamps, so **every YAML in this unit omits
`approx_time`**. The recurring auto-caption artifacts, all confirmed by reading around them:

- **"candle 2" → "candle to"**, without exception. Every C2 reference in this batch reads
  "a candle to closure". `JoFxG1TrnDA` and `hTsltdflraY` are wall-to-wall with it. Quotes are
  preserved verbatim including the artifact — do not "fix" them, the validator compares against
  the raw file.
- **"reach" → "wretch"** is the documented sibling artifact; it does not appear in this batch,
  but the same class does: **"stop raid" → "stop rate"** and **"2R" → "2our"** (both in
  `kv9aH7fb2Hc`), **"down close" → "downlo"/"downclo"** (`ZfATvEJryV8`, `QIGVXzsVER8`,
  `x4qJFQAyvaY`), **"broadening" → "broading"/"groin"** (`x5tvr59lX44`, `RhvalhK2Ulc`),
  and **"5 minute" → "5minut"** (`R_KRKwYpzdE`, `4629-YQ7_9g`).
- `Gpp8vicZo10` contains a raw HTML entity, `S&amp;P`.
- Two transcripts stop mid-sentence: `ZPCFCPzNWic` ends at "Once again, a smaller wick relative
  to the" and `qvHCAcLVz7g` at "taking a look for a break". `ZPCFCPzNWic`'s truncation costs
  real content — see below.

Where an artifact sat inside a sentence I wanted, I took the quote from a clean passage of the
same clip rather than quoting the corruption.

---

## What the Shorts contributed, by theme

### 1. Wick size — the one genuine advance, and it is a denominator not a number

The unit does **not** produce a ratio, and I want to be blunt about that. What it does produce
is the measurement **basis**, stated in a single clause in `ZPCFCPzNWic`:

> generally with directional candles, this wick is smaller relative to the body

That is the corpus's clearest statement that the wick is compared **to the candle's own body**.
It matters because the long-form treatment in `small-wick-expansion-rule` says the test is
two-dimensional and relative to the candle's **range** and **time** — a different denominator.
I recorded the conflict rather than smoothing it: both readings are now in that file's
`ambiguities` with no precedence claimed, because none is stated.

The same clip names a candle class the index does not carry, the **directional candle** —
"price went one direction throughout this time period for the most part" — but the transcript
is cut off immediately after ("the three different types of candles that I focus on" is
announced and only one is delivered). I did **not** mint a `directional-candle` id: the library
already has four overlapping wick/shape concepts (`small-wick-expansion-rule`,
`small-wick-supports-expansion`, `expansion-signature`, `daily-ohlc-candle-shape`), and a fifth
built on a truncated transcript would be sprawl. The term is filed as an alias.

The consequence side of wick size is well corroborated here.
`yvnISqEET-4` and `V8V-GdjsN84` both give the large-wick fallback targets — back towards the
**daily open**, or the **current high of day** — with a stated reason ("because daily candles
only have so much range"), and the small-wick target as the **average daily range**. Those went
to `large-wick-target-adjustment` and `wick-trust-test`.

Files: `small-wick-expansion-rule`, `large-wick-target-adjustment`, `wick-trust-test`.

### 2. The fractal model (C2 / C3) — the densest and cleanest cluster

Nine Shorts are pure fractal-model mechanics, and they are the crispest statements of it
anywhere. `JoFxG1TrnDA` gives the C2 test plus **two worked negative examples** — swings that
look like C2s but are discarded because price never closed back inside — which is exactly the
false-positive material a detector needs and which the long videos mostly omit.

`lTO4L6B0cpU` and `aZCHRSIgyFQ` independently supply the C3 closure level: price
**closes over the body of candle two**. `lTO4L6B0cpU` also frames the whole thing as a clean
binary at a point of interest — either sweep the previous extreme and print a C2, or close over
the body of C2 and print a C3 — which is a decidable branch.

`B_tHxplbxV0` / `oSrXv92fIzc` carry the fractal claim itself and add a target that is easy to
test: an hourly C2 at a point of interest marks where **the high of day** forms.

Files: `fractal-model-c2`, `fractal-model-c3`, `upper-half-eq-expansion-filter`,
`aligning-expansion-candles`, `ttfm-favorite-daily-4h-15m`, `half-wick-respect`.

### 3. Continuation failures — three Shorts on one rule, and he names it

`P8bfPTfVnDM`, `51cZ-2QlZaI` and `56gmI2Vnx_A` all state the same filter: when the closure that
forms the continuation *also* takes out a short-term high (or a range extreme), do not take it —
wait for another continuation. `51cZ-2QlZaI` calls it **"scenario two"**, which implies a
numbered scenario list that this batch never enumerates (recorded as an ambiguity). It also gives
the honest version of the dial: how aggressive to be "depend[s] on how strong your bias is",
and he personally waits. This maps cleanly onto the existing
`continuation-failure-short-term-target`, and the second, independent reason he gives — that the
protected swing is now too far for acceptable risk-to-reward — is a separate, checkable test.

The companion failure mode (`WPfkrKv0fK4`, `NlKb5FzZDxo`, `9ptXv4MBw1s`) is the retracement that
turns into a consolidation. The crisp bit is the **role flip**: once reclassified, the low stops
being a level to defend and becomes the point of interest you wait for price to reach.
`9ptXv4MBw1s` adds the breakout gate in one sentence — "we're not going to trade the breakout
unless we have a continuation" — and the disqualifier that a continuation which does not reach a
point of interest is not valid.

Files: `continuation-failure-short-term-target`, `continuation-failure-consolidation`,
`continuation-over-reversal`, `continuation-order-block`, `dont-trade-after-expansion`.

### 4. Aggressive / shallow — the only new id in the batch

`BzxmYF1Vt64` and `V0PF1DYNk9E` between them give "aggressive" an **operational** meaning, by
consequence rather than by threshold: an aggressive expansion produces **either a very shallow
retracement or none at all**, and if none comes there is simply no setup — he says twice in one
clip that he "would not get a setup". The action when you want the trade anyway is to enter at
the open, because there is nothing to wait for.

This is the one thing I could not place in the existing 383. `shallow-retracement` measures
retracement **depth** as an invalidator (a retracement to OTE flips the read); this is the
opposite direction — a prediction that no retracement will arrive, and a stand-aside/market-entry
rule that follows from it. New id: **`aggressive-expansion-no-retracement`**, status
`underspecified`, because "aggressive" itself is still ostensive.

`BzxmYF1Vt64` also *locates* shallow — "a shallow move into a fair value gap" — which is a
location, not a fraction. Better than nothing, still not a number.

`M-US3mO2Mkw` supplies a second axis for a V-shape that complements the library's candle-count
test: on a very aggressive V-shape, price must **not return back to the body**. Filed onto
`v-shape-reversal-speed`, with the note that the two tests are never reconciled.

Files: `aggressive-expansion-no-retracement` (NEW), `v-shape-reversal-speed`.

### 5. Reversal ladder, breakers, CISD

`ZfATvEJryV8` and `qvHCAcLVz7g` are the corpus's most explicitly **numbered** statement of the
reversal ladder — he says "step one", "step two", "step three", "step four and five" out loud.
One discrepancy worth flagging: this Short pairs steps four and five as "the fair value gap or
the breaker" and does not separate them, while the library's `order-of-reversal` orders breaker
as rung 4 and FVG as rung 5. Recorded, not resolved.

`EcnwfvAOo0s` gives the tightest four-point breaker definition in the corpus plus the zone
construction ("the down close candles from the first high to the first low"), and `jSIFb06gawQ`
supplies a **counter-example** — a high/low/higher-high that never makes the lower low, which he
rules out. He also states the anti-pattern-trading gate directly.

Files: `order-of-reversal`, `breaker-block`, `cisd`, `standard-deviation-projection`,
`smt-divergence`.

### 6. Structure, profiles, asset selection

`RhvalhK2Ulc` gives a genuinely detector-shaped fractal equivalence — a broadening formation on
a higher timeframe **is an outside bar**, so a day that takes both the previous day high and the
previous day low is a broadening formation one timeframe down — and `x5tvr59lX44` gives the
drawing procedure. Both were already in `broadening-formation`; the Shorts corroborate rather
than extend it.

`T3aqrI6P4G8` (intraweek reversal) carries a usable stand-aside rule: leave the second
consecutive expansion day alone "as it's already expanded a fair bit", and wait for a new swing
point. `ulH5Re5D6zQ` is a worked currency ranking (euro > pound, yen in, CAD excluded because
it is bearish alongside the dollar) — the only place in the batch where a selection procedure is
executed rather than described. `Gpp8vicZo10` isolates the **separation** input of relative
strength and shows it measured in raw points, which is not comparable across instruments — noted
as an ambiguity, since it is a real defect in the rule as stated.

Files: `broadening-formation`, `intraweek-reversal-week`, `tgif-setup`, `swing-point`,
`daily-candle-profile-open-low-first`, `equilibrium-eq`, `phases-of-price-transitions`,
`irl-erl-flowchart-model`, `timeframe-pairing`, `new-york-manipulation-profile`,
`relative-strength-weakness`, `dollar-gate-for-fx`, `po3-four-hour-opening-times`.

---

## Against the library's four blocking terms

| blocker | found? | what the batch actually says |
|---|---|---|
| **wick size** | partial — **basis, not threshold** | `ZPCFCPzNWic`: the wick is "smaller relative to the **body**". Fixes the denominator; supplies no ratio. Conflicts with the long-form range-and-time reading. |
| **kill-zone hours** | **no** | Still used as a hard gate with no clock attached. `kv9aH7fb2Hc`: "this must all be done within a kill zone"; `02yoXyIIY-w`: "if price reaches into it during a kill zone, can we frame a trade". Neither names an hour. The nearest clock times in the batch are session/candle levels, not kill zones: `R_KRKwYpzdE` gives the 4-hour opens **6 a.m.** and **10:00 a.m.**, and `4629-YQ7_9g` gives **8:30 or 9:30** as the two candidate New York manipulation times — and neither states a timezone. |
| **"aggressive"** | partial — **by consequence** | `BzxmYF1Vt64` / `V0PF1DYNk9E`: aggressive ⇒ very shallow or zero retracement ⇒ enter at the open or take no trade. `M-US3mO2Mkw`: an aggressive V-shape must not return to the body. No speed, range or candle-count classifier anywhere. |
| **"strong"** | **no** | Used twice bare — `HMYcwQwaWm0` ("we didn't get a very strong closure"), `51cZ-2QlZaI` ("how strong your bias is") — with no test either time. |
| **"shallow"** | partial — **located** | `BzxmYF1Vt64`: the shallow move goes "into a fair value gap". A location, not a fraction of the leg. |
| **CISD level: which price of the series** | partial — **an open, not the extreme** | `x4qJFQAyvaY`: "Mark out the opening price in that series." Establishes the level is an **opening price**, which rules out the extreme reading. It still does not say *which* open when the series has several candles. The same clip does give two hard preconditions: reach into an important level **and** sweep a high to the left of it. |

---

## Shorts that contained nothing new (no YAML written)

Only three of the 57 produced nothing worth recording:

- `mBl51QEPIHM` — "Applying the fractal model across multiple timeframes". Restates that the
  model is fractal and that the indicator auto-adjusts when you change chart timeframe. Both are
  already in `automatic-fractal-pairing` and `ttfm-indicator-settings`; the clip is a UI
  demonstration with no rule in it.
- `FAy1_-s10jA` — "Find Your Invalidation". A worked ES 4-hour example. Every element
  (bearish daily closure, lower half, protected swing, close through to form a new protected
  high) is already carried by `protected-swing` and `fractal-model-c3`, and the clip adds no
  threshold, level construction or ordering that those files lack.
- `ZnBZRPz9DYg` — "Expansion → Retracement → Expansion". Names accumulation / manipulation /
  distribution and says he wants "a shallow retracement into" — fully covered by
  `power-of-three-amd` and `shallow-retracement`, and the shallow claim is weaker than
  `BzxmYF1Vt64`'s, which I used instead.

Everything else in the batch earned at least one source entry. Note that "earned a source entry"
is a much lower bar than "contained something new" — 33 of the 34 files are additional evidence
attached to concepts that already existed, and that is the correct outcome for this playlist.

---

## Follow-ups this unit suggests

1. **The wick denominator is now contested and should be settled empirically.** Body-relative
   (this unit) and range-relative (long-form) give different classifications for the same candle.
   Both are cheap to compute; run them against forward expansion and see which separates better.
   That is a faster route to the missing threshold than waiting for him to say a number.
2. **Kill-zone hours are not in the Shorts playlist either.** Three batches of Shorts remain
   (`shorts_02`–`shorts_04`), but on this evidence the term is used as a gate and never defined;
   if the remaining batches also come up empty, the honest conclusion is that the corpus does not
   contain it and the 49 blocked concepts need an externally-supplied definition, flagged as such.
3. **"Scenario two" implies a numbered scenario list** for what happens when a continuation
   closure coincides with a short-term high. Worth grepping the long-form corpus for the
   enumeration — if it exists, it would upgrade `continuation-failure-short-term-target`.
4. **The `order-of-reversal` rung 4/5 ordering** is stated one way here and the other way in the
   library. One of the two units is loose; a third witness would settle it.
