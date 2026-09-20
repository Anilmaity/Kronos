# Mean-Reversion / Snap-Fade Research — Session Handoff

**Date:** 2026-06-26 · **Instrument:** XAUUSD · **Data:** `reports/xau_m5_3y.csv` (246k M5 bars, 2023-01 → 2026-06-24)

## Goal (user's words)
Build a strategy that prints like the real account `5216074f` — a 2-day mobile scalp that did
**67 trades, 92.5% WR, +$452.44, max losing trade −$13.80** (Jun 21–24 2026, no stops, all hours).
User wants high win rate / high activity (10–20 trades/day) over short recent windows.

## THE BOTTOM LINE (read this first)
The high-WR, high-frequency, no-stop shape the user wants is a **−EV illusion** — proven repeatedly
this session. There IS a real but **thin, low-frequency, maker-only** mean-reversion edge, packaged as
`bot/snap_ict_maker.py`. Frequency and profitability are **inversely related** for this edge — there is
no setting with both high activity and long-run profit.

**ONE UNRESOLVED GATING QUESTION** that decides whether any of this is tradeable for the user:
> Is account `6c7ce166` (FundingPips $5k→$5.5k) **maker-capable** (can post limits, earn/save spread,
> ECN/raw) or **spread-only** (permanent taker)? If taker-only, this entire edge is inaccessible →
> default to the trend-follower `bot/challenge_xau.py` (PF 1.83). ASK THE USER FIRST NEXT SESSION.

## The validated model — `bot/snap_ict_maker.py`
Maker fade in 03–09 UTC quiet window, low-tempo gate (causal trailing-month vol threshold), entered only
**with** the Daily ICT structure bias (swing-fractal BOS/CHoCH state machine), passive-limit execution
with adverse selection, proportional stop (target 0.5×overshoot / stop 1.5×overshoot), spread 0.20pt.
Run it: `.venv/Scripts/python.exe bot/snap_ict_maker.py`

**Walk-forward (0.10 lot, $10/pt), positive every year:**
| 2023 | 2024 | 2025(OOS) | 2026YTD(OOS) | Total |
|---|---|---|---|---|
| +$285 PF1.08 | +$760 PF1.16 | +$186 PF1.02 | +$1,525 PF1.32 | **+$2,757** |
~1.6 trades/day, ~65–73% WR. Control (fade AGAINST daily bias) collapses 3 of 4 years (2023 is the exception).

**One-month daily reality (May 24–Jun 24 2026):** 44 trades, 65.9% WR, **+$15.7 net (≈flat)**, PF 1.02,
**max losing trade −$110**, 6/13 green days, traded only 13 of 28 calendar days. Edge is thin & long-horizon,
NOT a monthly money-maker.

## What was DISPROVEN this session (don't re-litigate)
- **High-WR fade** (tiny TP / wide stop, all hours): 83–95% WR in EVERY 2-month window 2025–26, **loses
  every one** (−$4k to −$27k). `s5_highwr_demo.py`
- **Averaging / martingale add**: lifts WR to 93% but turns the one profitable config (+$1,003) into
  **−$782** and fattens the tail. It's the worst idea, not a risk reducer. `s5_highwr_filtered.py`
- **Hard stop cap** (L5, cap 3/5/8pt): bounds worst trade to −$32 but **loses every year** (tight stop
  stops out the reversions that ARE the edge). `bot/snap_ict_l5.py`
- **Volume filter** (low-vol reverts): fails OOS, backwards from theory. `s5_snap_volume.py`
- **All sessions / all hours**: walk-forward −$3,572; **frequency dial** shows full-history P&L falls
  monotonically as trades/day rises (1.6/day +$2,757 → 11/day −$1,358 → 44/day −$48,642). `s5_frequency_dial.py`, `s5_sessions_compare.py`
- **Kronos foundation model**: 45.5% directional accuracy = no skill.
- **Explicit overfit replication**: 98.8% WR in-sample → negative OOS.
- **EMA-cross HTF bias**: marginal/inconsistent (the *ICT* daily bias is what worked; H4 bias did not).

## Key methodology notes
- Fixed a **look-ahead bug**: low-tempo threshold was the whole-sample vol median → made model dormant in
  high-vol 2026. Now CAUSAL trailing ~1-month (`LOWTEMPO_WIN=5760`). All current numbers use the fix.
- Real account stats reproduced from `reports/acct_5216074f_trades.csv` (67 trades, +$452.44, max loss −$13.80).
- Over the order window the disciplined model takes ~1–17 trades (vs 67) BY DESIGN — it sits out high-vol
  all-hours bursts. The account's small −$13.80 max loss is a 2-day lucky sample with no tail event, NOT safety.

## Open research directions (user wants to continue)
1. **Vol-aware low-tempo stop** — make the stop tight when the low-tempo regime says moves should be small,
   to cut the −$110 tail toward ~−$40 WITHOUT the blunt hard cap that killed the edge. (Most promising next step.)
2. The **2023 control exception** — why daily-bias edge inverted that year; tighten the bias filter.
3. **Fundamental knowledge graphs** (user offered) — structural reasons a window is information-free, to
   raise fill quality / beat adverse selection. The one genuinely-different information source left.
4. If user wants natural high-frequency: it must be a **different edge family** (true market-making infra /
   different instrument), NOT this fade cranked harder.

## Artifacts
- **Strategy:** `bot/snap_ict_maker.py` (THE model) · `bot/snap_ict_l5.py` (failed hard-cap attempt)
- **Report:** `reports/REPORT-meanrev-snap-2026-06-26.md` (sections 1–9 + Appendix A) · narrative
  `journal/research-2026-06-26-meanrev-liquidity-edge.md`
- **Scripts (run with `.venv/Scripts/python.exe <file>`):** `s5_meanrev_diag.py` (hourly VR/autocorr +
  z-fade), `s5_snap_harvest.py`, `s5_snap_adverse.py`, `s5_snap_spread.py`, `s5_final_report.py`,
  `s5_snap_volume.py`, `s5_period_table.py`, `s5_lastweek_table.py`, `s5_snap_htf.py`, `s5_snap_ict.py`,
  `s5_ict_validate.py`, `s5_highwr_demo.py`, `s5_highwr_filtered.py`, `s5_window_allsessions.py`,
  `s5_sessions_compare.py`, `s5_frequency_dial.py`
- **Data:** `reports/xau_m5_3y.csv` (main), `xau_m1_2026ytd.csv`, `acct_5216074f_trades.csv` (real trades)
- **Memory:** `memory/meanrev-liquidity-edge-floor.md` + `memory/mobile-scalp-no-edge.md`

## Telegram tooling (added end of session)
- **Daily account alert:** `bot/daily_telegram.py` (read-only equity/goal/positions/day-Δ → Telegram),
  helper `bot/tg_chatid.py`. NEEDS: user creates @BotFather bot → `telegram_token` in .env → message bot
  → run tg_chatid.py (writes `telegram_chat_id`). Schedule via the `schtasks` line in the script.
- **Channel ingestion (Swappy Trading / Gold Syndicate, t.me/SNTrading786):** `bot/tg_channel_reader.py`
  (Telethon installed). NEEDS: user gets `telegram_api_id`/`telegram_api_hash` from my.telegram.org →
  add to .env → ONE-TIME interactive login run by the USER via `!` (phone + code) → creates
  bot/sntrading.session. Then it downloads posts+images to `tg_channel/index.json` + `tg_channel/images/`.
- **Interpretation skill:** `~/.claude/skills/tg-ict-analysis/SKILL.md` — read each chart image, extract
  structured ICT bias (levels/OB/FVG/liquidity/direction), compare to live price + snap_ict_maker daily
  bias, keep a scorecard. Images only (no video/voice). Channel = unknown edge → validate, don't follow blindly.
- **Blocked on user creds:** nothing here runs until the user supplies bot token (alert) and api_id/api_hash
  + does the one-time Telethon login (channel). Both are read-only.

## Channel decode + verification pipeline (built; XAUUSD-only)
- **Login DONE** (bot/sntrading.session exists). Reader pulls history → `tg_channel/index.json` +
  `tg_channel/images/`. 500-msg pull = May 1→Jun 26 2026 (214 imgs). 2yr ≈ ~6000 msgs/~2500 imgs (big,
  ongoing download — re-run `bot/tg_channel_reader.py <N>` or background it).
- **Channel method decoded:** daily "levels" charts = ICT STDV ladder + TDO (true day open) + red premium
  (sell) / blue discount (buy) zones; also HTF-bias charts ("XAUUSD D1/H4 Bias", "Daily ICT Outlook") with
  a drawn direction + target + invalidation levels. Channel posts MANY symbols — decode XAUUSD/Gold ONLY.
- **Verify engine:** `bot/tg_verify.py` reads `tg_channel/bias/decoded.json` (per-call bias/entry/target/
  invalidation/horizon_days), scans `reports/xau_m5_3y.csv` (covers 2023→Jun24), reports MFE/MAE/target_hit/
  verdict → `tg_channel/bias/scorecard.json`. Price scales verified to match (OANDA both sides).
- **Demo result (n=2, NOT conclusive):** 8023 (May15 short→4285) WIN; 8107 (May27 short→4285) hit target but
  poked invalidation (ambiguous). Both same bearish-to-4285 thesis; gold did fall mid-4500s→~4012. Caveats:
  tiny same-thesis sample, ~100pt MAE (right bias ≠ tradeable win without a stop), cherry-picked clear charts.
- **Skill:** `~/.claude/skills/tg-ict-analysis/SKILL.md` upgraded — XAUUSD-only, HTF-bias gen, candle-test loop.
- **TODO for full ask:** deep pull (2yr) → decode the FULL gold set incl. failed/messy calls → run tg_verify
  → real hit-rate scorecard. Recent (post-Jun24) calls need fresh MetaApi candles. Daily note example:
  `tg_channel/bias/2026-06-26.md`.

## Suggested first move next session
Ask the user the maker-capable question. If yes → build the vol-aware stop (#1) and re-run the one-month
daily view. If no/taker-only → pivot to `bot/challenge_xau.py` (H4 trend, PF 1.83). Either way, do NOT
rebuild high-WR / high-frequency / no-stop / averaging variants — all disproven above.

---

## ADDENDUM 2026-06-28 — loss-tail research done; `bot/snap_ict_maker_rp.py` shipped
Open direction #1 ("vol-aware low-tempo stop") investigated and the literal idea was **refuted**, but a
better fix was found and validated. Methodology = backtest-expert (diagnose tail before fixing).

**Diagnosis (`s5_volaware_diag.py`):** loss size ∝ **overshoot** (corr +0.61), NOT the rv/thr regime
ratio (corr +0.09). Exit mix: 62.8% target (maker, +$22.7k), 17.3% stop (−$14.7k), 19.9% time (−$5.2k).
Big overshoots (top 10%) are the MOST profitable bucket (+$1,162) — why the L5 hard cap killed the edge.

**MAE analysis (`s5_volaware_mae.py`):** baseline 1.5*ov stop is far wider than winners need — 97.7% of
winners draw down <1.5*ov, 93% <1.0*ov, and big overshoots draw down LESS in ov-units (p90 0.77 vs 0.86).

**Fix 1 — tighter stop 1.5*ov → 0.9*ov (`s5_volaware_stop.py`):** fixed-lot walk-forward +$2,757 → +$3,262
(+18%), weak 2025 OOS +$186 → +$890. Plateau wide: every stop mult 0.6..1.2 positive every year; **1.5 is
the only FAIL — the current deployed baseline literally sits at the edge of the cliff.** Regime-scaled stop
(handoff #1) was the worst variant — confirms regime ratio is the wrong knob.

**Fix 2 — constant-$-risk sizing (`s5_volaware_sizing.py`):** the $ tail is intrinsic to a proportional
stop on huge overshoots; risk-parity sizing flattens it (every loss == budget, 0 trades < −$80). return/DD
~1.9 (fixed-lot base) → ~4.0–4.2. Dial RISK_USD to the target instead of over-sizing.

**Robustness (`s5_volaware_robust.py`):** plateau confirmed; slippage stress passes (note: wider spread
*helps* a maker — it earns the spread on target exits, so spread-width is not the real stress); lots
0.005–0.287, **0% hit the max-lot cap** (sizing not leaning on the cap); min-stop 1.0pt guard is free.

**Shipped:** `bot/snap_ict_maker_rp.py` (sf=0.9, $15/trade, min-stop 1.0pt, max-lot cap) →
**+$1,547, PF 1.15, maxDD $384, return/DD 4.03, worst trade −$15, PASS all 4 years incl. both OOS.**
Original `bot/snap_ict_maker.py` kept intact as the baseline. Memory updated (`meanrev-liquidity-edge-floor.md`).

**Maker-dependency UNCHANGED & re-confirmed at new params: maker +$1,604 PASS vs taker −$3,730 FAIL.**
The gating question still governs deployability. .env broker = `Winprofx-Live` (MT5); account-type not
derivable from config — must ASK the user whether acct `6c7ce166` can post limits / earn spread (raw/ECN).

**Next directions if continuing the scalper:** (a) the one-month daily reality check on the RP model (does
the bounded tail + tighter stop turn the ~flat month positive?); (b) open direction #2 (the 2023 control
exception); (c) #3 fundamental knowledge-graph signal to beat adverse selection — the only genuinely new
information source left.
