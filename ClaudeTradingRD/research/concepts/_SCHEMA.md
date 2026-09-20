# Concept schema

Every concept extracted from the TTrades_edu corpus is stored as **one YAML file**
in `research/concepts/<category>/<concept-id>.yaml`. The schema exists so that a
later analysis pass — or a strategy build — can consume these mechanically
instead of re-reading prose.

The guiding rule: **a concept is only useful here if it is decidable.** If you
cannot say, given a chart and a bar index, whether the concept is present or
absent, the entry is incomplete and must be marked `status: underspecified`.

## Fields

```yaml
id: fractal-model-c2                 # kebab-case, unique, stable
name: "Candle 2 (Manipulation Candle)"
aliases: ["C2", "the sweep candle"]
category: model                      # structure|liquidity|time|entry|risk|model|psychology
status: specified                    # specified | underspecified | contested

definition: >
  One-paragraph precise statement. No hedging, no "basically". If the source
  is ambiguous, say so in `ambiguities` rather than smoothing it over.

timeframes:
  htf: ["1D", "4H"]                  # where the concept is identified
  ltf: ["5m", "1m"]                  # where it is executed, if applicable
  fractal: true                      # does it self-repeat across scales?

preconditions:                       # what must already be true
  - "A completed C1 range exists with a defined high and low."

detection_rules:                     # ordered, algorithmic, testable
  - "C2 trades above C1.high (buy-side sweep) OR below C1.low (sell-side sweep)."
  - "C2 closes back inside the C1 range."

invalidation:                        # what kills it
  - "C2 closes outside the C1 range (expansion, not manipulation)."

# Only for tradeable setups; omit otherwise.
execution:
  bias: "Opposite the swept side."
  entry: "LTF CISD after the HTF C2 close."
  stop: "Beyond the C2 extreme."
  targets: ["C1 opposite extreme", "50% of the C1..C2 range"]

measurable:                          # what a backtest would count
  - "count of C2 formations per month"
  - "hit rate of the C1-opposite-extreme target"

sources:                             # provenance — REQUIRED, never invent
  - video_id: TNybDCtwBnc
    title: "Fractal Model Fundamentals"
    quote: "price has to form a swing point to reverse"   # <=15 words
    approx_time: "07:20"

external_corroboration:              # optional, from web search
  - url: "https://ttrades.com/trading-education-center/ttfm/"
    note: "Confirms CISD naming and C2/C3/C4 sequence."

ambiguities:                         # be honest; this drives follow-up work
  - "Whether the C2 close must be a body close or a wick close is not stated."

python_detector: "research/python/detectors/fractal_c2.py"   # or null
related: ["cisd", "liquidity-sweep", "protected-swing"]
```

## Rules for whoever fills this in

1. **Never invent a source.** Every `sources` entry must be a video actually
   read, with a real `video_id` from the corpus. No quote may exceed 15 words.
2. **Separate what was said from what you inferred.** Inference belongs in
   `ambiguities` or a `notes` field, never in `definition` or `detection_rules`.
3. **Prefer the speaker's own words for `name` and `aliases`.** The corpus is the
   authority on naming, even where it conflicts with generic ICT usage — note
   the conflict in `ambiguities`.
4. **If two videos contradict each other**, set `status: contested`, record both
   readings, and cite both.
5. **Do not pad.** A short, correct entry beats a long, speculative one.
