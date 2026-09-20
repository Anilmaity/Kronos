# Fractal model — contested C2 / C3 readings, measured

Both concepts carry `status: contested`. These tables make the disagreements numeric instead of rhetorical.

## C2 — which reference gets swept?

`prior_candle` sweeps the immediately preceding candle's extreme; `lookback_extreme` sweeps the extreme of the prior 5 candles (the 'nearby liquidity pool' reading). `-> jaccard` is the agreement between them on identical (direction, bar).

| TF | reading | bars | events | rate / jaccard |
|---|---|---:|---:|---:|
| 1h | prior_candle | 17,981 | 4,949 | 27.5% |
| 1h | lookback_extreme | 17,981 | 2,127 | 11.8% |
| 1h | -> jaccard | 17,981 | 2,117 | 0.427 |
| 4h | prior_candle | 4,863 | 1,385 | 28.5% |
| 4h | lookback_extreme | 4,863 | 514 | 10.6% |
| 4h | -> jaccard | 4,863 | 510 | 0.367 |
| 1D | prior_candle | 949 | 257 | 27.1% |
| 1D | lookback_extreme | 949 | 101 | 10.6% |
| 1D | -> jaccard | 949 | 100 | 0.388 |

## Does the C2 wick size predict expansion?

The corpus claims a **small wick supports expansion**, while a large wick suggests a trade back to the opening price. Splitting C2s at the median sweeping-wick ratio, this is how often the *next* candle closed beyond the C2 open.

| TF | median wick | small-wick n | delivered | large-wick n | delivered |
|---|---:|---:|---:|---:|---:|
| 1h | 0.395 | 2,475 | 78.1% | 2,474 | 63.1% |
| 4h | 0.382 | 693 | 81.0% | 692 | 64.7% |
| 1D | 0.351 | 129 | 82.9% | 128 | 65.6% |

## C3 — sequential vs standalone

| TF | bars | sequential | rate | standalone | rate |
|---|---:|---:|---:|---:|---:|
| 1h | 17,981 | 3,495 | 19.4% | 17,977 | 100.0% |
| 4h | 4,863 | 1,009 | 20.7% | 4,862 | 100.0% |
| 1D | 949 | 191 | 20.1% | 948 | 99.9% |

## Reading this

**The standalone C3 reading is degenerate as operationalised here — ~100% of candles qualify.** That is not a measurement of the corpus's idea, it is a demonstration that the idea is under-determined: every candle closes either above or below the prior candle's EQ, so 'closes beyond EQ in the trend direction' classifies everything unless the trend direction is supplied from outside the rule. The corpus never says where that direction comes from. Treat the standalone column as a red flag on the concept, not as a result.

The sequential reading is the usable one (~20% of candles), and it is the reading that names its own precondition.

**The wick claim survives testing.** It is the first falsifiable, non-definitional prediction in the corpus: small-wick C2s are followed by delivery beyond the C2 open far more often than large-wick ones, and the gap is stable across 1h/4h/1D on three years of data. That is a real asymmetry worth carrying forward.

It is still only a raw directional-delivery rate, not an edge: no target, stop, spread or slippage is modelled, and the median split is arbitrary. See `primitive_base_rates.md` for why frequency alone proves nothing.
