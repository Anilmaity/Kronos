# CISD — the three contested readings, measured

`concepts/entry/cisd.yaml` carries `status: contested` because the corpus gives three incompatible answers to *which level* price must close through. One speaker explicitly rejects the opening-price rule. This table makes the disagreement measurable rather than rhetorical.

- **series_close** — close beyond the last run candle's close (loosest)
- **series_open** — close beyond the first run candle's open
- **series_extreme** — close beyond the run's opposite extreme (strictest)

Runs require >= 2 candles (`min_series=2`), matching the corpus's insistence that a CISD comes from a *series*, never a single candle.

| TF | reading | bars | events | per 1k bars | median wait | median series |
|---|---|---:|---:|---:|---:|---:|
| 15min | series_open | 71,873 | 9,146 | 127.3 | 5.0 | 2.0 |
| 15min | series_extreme | 71,873 | 8,643 | 120.3 | 7.0 | 2.0 |
| 15min | series_close | 71,873 | 11,760 | 163.6 | 4.0 | 3.0 |
| 1h | series_open | 17,981 | 2,192 | 121.9 | 6.0 | 2.0 |
| 1h | series_extreme | 17,981 | 2,084 | 115.9 | 7.0 | 2.0 |
| 1h | series_close | 17,981 | 2,901 | 161.3 | 4.0 | 3.0 |
| 4h | series_open | 4,863 | 617 | 126.9 | 6.0 | 2.0 |
| 4h | series_extreme | 4,863 | 584 | 120.1 | 7.0 | 2.0 |
| 4h | series_close | 4,863 | 810 | 166.6 | 4.0 | 3.0 |
| 1D | series_open | 949 | 108 | 113.8 | 5.0 | 2.0 |
| 1D | series_extreme | 949 | 103 | 108.5 | 6.0 | 2.0 |
| 1D | series_close | 949 | 146 | 153.8 | 4.0 | 3.0 |

## Do the readings actually pick different moments?

Agreement between `series_open` and each rival, counted as confirming the same direction on the same bar (Jaccard over the event sets).

| TF | vs | same-bar events | Jaccard |
|---|---|---:|---:|
| 15min | series_extreme | 5,677 | 0.588 |
| 15min | series_close | 3,683 | 0.23 |
| 1h | series_extreme | 1,369 | 0.586 |
| 1h | series_close | 859 | 0.218 |
| 4h | series_extreme | 367 | 0.557 |
| 4h | series_close | 254 | 0.234 |
| 1D | series_extreme | 68 | 0.562 |
| 1D | series_close | 54 | 0.289 |

## Reading this

A low Jaccard means the three readings are genuinely different trading systems wearing one name, and any result quoted for 'CISD' is under-specified until the reading is stated. A high one would mean the corpus's disagreement is cosmetic. Either way this is a prerequisite for attaching a performance number to the concept.

Note these are *detections*, not trades — no direction filter, no target, no risk. Frequency alone says nothing about edge; see `primitive_base_rates.md` for why.
