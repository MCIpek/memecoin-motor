# Memecoin Engine: System, Data and Revenue Analysis

**Date:** 14 October 2026
**Scope:** README, the design document, `src/memecoin_motor/*` (3,700 lines), 27 tests, `data/memecoin_motor.db` (10.2 GB SQLite, inspected read-only), web verification of market/price claims.
**Method:** Every finding is tagged `[VERIFIED]` (by code or data), `[INFERENCE]` (derived from data) or `[ASSUMPTION]` (could not be verified). Production data was not modified; the database was opened with `mode=ro`.

---

## A) Current state and the five most critical findings

### What does the system do?

It listens to the Pump.fun bonding-curve program (`6EF8rrec…`) over the public Solana WebSocket, decodes `Create/CreateV2` and `TradeEvent` with the official IDL, tracks the first 600 seconds of every new token, produces event-time snapshots at 2/5/10/30/60 s, issues a rule-based `GIRME/IZLE/ADAY` (REJECT/WATCH/CANDIDATE) decision and labels 60/300 s outcomes with a wallet-free paper engine. Side paths: creator/first-buyer wallet analysis, sniper and bundle evidence, X-band calibration.

The design document defines the audience as "our own trades" (§17). **Right now it is not a product that works for anyone; it is research infrastructure.**

### Working / half-done / documentation only

| State | Feature | Evidence |
|---|---|---|
| Working | IDL decoding, idempotent storage, slot-gap detection, snapshots, risk rule, paper-v2 fill/exit math, sniper score | 27/27 tests pass; `pump.json` SHA-256 matches README; 58,316 launches, 2,094,977 trades; 0 FK/orphan violations |
| Half-done | Paper-v2 historical pass | 144,047 of 174,796 decisions (82%) never became a paper position; 9,005 of 11,155 open positions have no 300 s outcome; canonical outcomes exist only for **1-4 Sep** |
| Half-done | Wallet/sniper enrichment | 111,194 wallet jobs and 20,557 transaction jobs pending; sniper scores on 4,890 of 58,316 mints (8%) |
| Half-done | Gap backfill | 1,276 gaps skipped as "too large" (11.6M slots); 28 FAILED |
| Documentation only | PumpSwap tracking, ML models, agentic audit, dynamic fee/Jito replay, RugCheck/GoPlus/DEX Screener enrichment, PostgreSQL | No counterpart in code (verified by grep) |
| Dead/legacy code | `paper_positions`, `paper_outcomes`, `market_outcomes` (v1), `parser.extract_token_mints`, `paper.market_outcome` | Not used by the v2 engine; the CLI still shows them; `Storage.initialize()` runs an UPDATE on a legacy table at every start |

### The five most critical findings

**1. The collector was up for only 9.6% of the calendar; the "data pipeline" is not continuous yet. [VERIFIED]**
Gaps longer than 15 minutes between launch timestamps give 36 separate sessions. Total coverage 84.6 hours out of 885 calendar hours. Sessions almost always fall between 05:00 and 14:00 UTC, a workday pattern. README says "18 days"; true but incomplete: most days are 1-2 hour fragments.

**2. Chain-to-client latency on the public RPC is a median of 22.5 s; 2/5/10 s snapshots are physically impossible with this source. [VERIFIED]**
On a 20,000-launch sample, `first_seen_at - event_timestamp`: p10 4.3 s, p50 22.5 s, p90 173 s, p99 396 s. This is the root cause of ON_TIME rates of 4% at 2 s and 22% at 10 s. Worse: **41.7%** of snapshots labelled ON_TIME (3,000 sample) were generated before the trades inside their window had reached the client. Recomputing 400 mints, 21.9% of snapshots disagree with raw trades on `trade_count` and `net_quote_flow`. So even "ON_TIME" is incomplete; `snapshot_quality` only measures generation delay, not data completeness (`storage.py:1432-1433`).

**3. Future information leaks into the risk decision; paper results are therefore not decision-time results. [VERIFIED, code]**
`service.py:420-423` and `493-495`: when wallet analysis or sniper enrichment completes hours later, `score_snapshots(storage, mint, False)` recomputes **all** snapshot decisions of that mint and overwrites `risk_decisions` (upsert in `save_risk_decision`). In the data, 44% of ADAY decisions (2,213/5,000) were evaluated more than 60 s after the snapshot cutoff; p90 is 16.5 hours later. The paper engine opens the position at the "cutoff + 2 s" price but takes the decision with information from hours later. Also `features_json` exists in two schemas (with/without sniper fields, 1,034 vs 966 in the sample) while `ruleset_version` is always `baseline-v1` (`scoring.py:9`); results are not comparable.

**4. The rule engine's ADAY class is worse than random selection; the "paper baseline is negative" claim is correct but rests on 2 days. [VERIFIED]**
The 163 canonical outcomes in README were reproduced exactly (median peak 0.945x, final 0.804x, staged 0.872x, 2x seen 9.2%). However:
- Unconditional base rate in the same window (3,000-mint sample, first trade after 10 s, 300 s, raw price): 2x seen **16.5%**, 1.5x **27.2%**.
- IZLE group (n=1,194, executable): 2x 17.4%, mean final 1.026x.
- GIRME group (n=493): 2x 7.3%, mean final 0.755x.
- ADAY (n=163): 2x 9.2%, mean final 0.807x.
ADAY picks fewer risers than both IZLE and the unconditional base rate. The rule selects "safe-looking but motionless" tokens. Staged strategy total PnL: 163 × 0.1 SOL = 16.3 SOL deployed, **-2.23 SOL (-13.7%)**. All canonical CONTINUOUS outcomes come from 1-4 Sep; paper was never run on the following 34 days. Neither the negative finding nor a hypothetical positive one is statistically robust yet.

**5. The restart logic counts collector downtime as "tracked"; LATE rows are therefore fake. [VERIFIED, code + data]**
`service.py:47`: on startup the new process calls `end_snapshot_tracking(int(time.time()))`, writing the **restart time** as `ended_at` instead of the crash time. The hours between crash and restart look tracked, and `create_due_snapshots` produces LATE snapshots for them (LATE delay p50 994 s, p90 24 h, max 4.7 days). 6,080 tracking rows still have `ended_at IS NULL` (last session did not close cleanly), 9 snapshots have a cutoff after `ended_at`, 2 rows have `ended_at < launch_timestamp`. Despite this, LATE snapshots still produce ADAY: **3,802 of 8,195 ADAY decisions (46%)** come from LATE snapshots (the -0.20 LATE penalty brings confidence to 0.47 while the threshold is 0.45).

### Other important findings

- **No version control. [VERIFIED]** `git log`: "branch 'main' does not have any commits yet". 3,700 lines of code and 10 GB of data with no backup.
- **Storage is bloated and queries are slow. [VERIFIED]** `pump_trades` carries `raw_event_json` on every row (a copy of decoded fields); `chain_events` holds `logs_json` on 2.02M LOG_EVENT rows (avg 628 B) and 61,790 raw transaction JSONs (avg 29.7 KB ≈ 1.8 GB). A full scan takes 200-400 s. `create_due_snapshots` (`storage.py:1371-1376`) loads all `token_snapshots` keys (291k rows) every 0.5 s; the snapshot worker will choke itself as data grows.
- **The launch-transaction queue backed up for hours. [VERIFIED]** `ingestion_latency_ms` on COMPLETE events: p50 452 ms but p90 23 hours, max 4.7 days. Public RPC `getTransaction` bottleneck; because tracking starts only after the transaction arrives, snapshots are born LATE.
- **The gap policy counts restart gaps as stream gaps. [INFERENCE]** The 8 largest gaps (up to 1.89M slots) coincide with restarts because `SlotTracker` resumes from the previous session's last slot. Everything above `MAX_BACKFILL_SLOTS=32` (~13 s) is skipped.
- **Launch coverage is probably incomplete. [ASSUMPTION]** ~835 launches/hour inside sessions (~20k/day pace). Public Sep 2026 figures report ~32-34k launches/day. Time-of-day effects are possible; whether the public WS drops events should be verified against an external source (Bitquery/Dune, same hour window).
- **Non-SOL quote tokens are mixed in. [VERIFIED]** 3,412 launches (5.9%) have a non-SOL quote (USDC 828, `pumpCm…` 580, etc.); 45,501 trade rows have `virtual_sol_reserves=0`; 17,058 snapshots have NULL price; paper fails 883 as `UNSUPPORTED_QUOTE`. The risk rule scores these tokens with the same thresholds as SOL (`net_quote_flow` in different decimals).
- **Test coverage skips the core.** Zero tests for `service.py` (565 lines, the collector); no tests for `run_paper_cycle`, `calibrate_x_bands` or WebSocket replay. Existing tests cover pure functions.
- **Security.** No wallet/private key, no `sendTransaction`; `.env` contains only public URLs and is gitignored. SQL string concatenation comes from fixed lists (`counts()`, `where` fragments); no injection surface. No externally exposed service. Low risk. One note: `_stream_once` raises `message.data` on a WS error object, which can produce a type error depending on the `aiohttp` version.

---

## B) Data quality report (with evidence)

**Source:** only `api.mainnet-beta.solana.com` (confirmed), all 2,078,144 events. Update mechanism: manually started `memecoin-motor collect`; no scheduler/service. Last data 8 Oct 2026 05:49 UTC.

### Coverage and date range

| Metric | Value |
|---|---|
| Launch range | 2026-09-01 07:46 → 2026-10-08 05:49 UTC |
| Distinct days | 18 (matches README) |
| Sessions (>15 min gap) | 36 |
| Covered time | 84.6 h / 885 h (9.6%) |
| Longest uninterrupted session | 9.1 h (7 Sep) |
| In-session launch rate | ~835/hour |

### README figures verified

| Table | README | Database | Result |
|---|---:|---:|---|
| pump_launches | 58,316 | 58,316 | ✔ |
| pump_trades | 2,094,977 | 2,094,977 | ✔ |
| Tokens with trades | 53,591 | 53,591 | ✔ |
| token_snapshots / risk_decisions | 291,358 | 291,358 / 291,358 | ✔ |
| wallet_positions | 608,540 | 608,540 | ✔ |
| wallet_profiles | 14,568 | 14,568 | ✔ |
| sniper_scores | 5,615 | 5,615 | ✔ |
| paper_v2_positions | 30,749 | 30,749 | ✔ |
| executable_outcomes_v2 | 4,389 | 4,389 | ✔ |
| Snapshot ON_TIME rates (2/5/10/30/60 s) | 4.0 / 10.1 / 22.5 / 26.6 / 28.2% | same | ✔ |
| Backfilled / skipped gaps | 207 / 1,276 | 207 / 1,276 (+28 FAILED, 1 DETECTED) | ✔ |
| Skipped slots | 11.6M | 11,626,799 | ✔ |
| Canonical 300 s CONTINUOUS | 163 | 163 | ✔ |
| Pending wallet queue | ~111k | 111,194 | ✔ |
| Pending tx queue | ~20k | 20,557 | ✔ |

The README numbers are honest. What is missing is the **time coverage and data completeness** behind them.

### Integrity checks

| Check | Result |
|---|---|
| Duplicates (PK: signature, event_index / mint) | 0 |
| Trade → launch orphans | 0 |
| Trade → chain_event FK | 0 |
| Launch → chain_event / tokens_minimal | 0 / 0 |
| Trade age < 0 or > 600 s | 0 / 0 |
| `block_time ≠ event_timestamp` (launch) | 0 |
| `quote_amount=0` trades | 248 |
| `virtual_sol_reserves=0` trades (non-SOL quote) | 45,501 |
| Reserve monotonicity violations (300 mints, slot order) | 143 / 38,260 (0.37%) |
| Snapshot `cutoff > ended_at` | 9 |
| `ended_at < launch_timestamp` | 2 |
| Tracking `ended_at IS NULL` (never closed) | 6,080 |
| Launch without tracking | 34 |
| `wallet_behavior_stats` stored / recomputed | 39,759 / 40,015 (drift) |
| Protocol fee (fee/quote) | 95 bps in 95% of the sample; 0 in 25% (quote=0 or mayhem) |

### Timing accuracy

| Metric | p10 | p50 | p90 | p99 |
|---|---:|---:|---:|---:|
| WS arrival − block time (launch) | 4.3 s | 22.5 s | 173 s | 396 s |
| LATE snapshot delay | – | 994 s | 24 h | 84 h |
| COMPLETE event processing delay | – | 452 ms | 23 h | 84 h |
| ADAY `evaluated_at − cutoff` | – | 31 s | 16.5 h | – |

### Processed output vs raw data

| Check | Sample | Result |
|---|---|---|
| Snapshot recomputation | 400 mints, 2,000 snapshots | trade_count 21.9%, unique_buyers 13.3%, creator_sold 4.5% mismatched |
| ON_TIME snapshot with trades arriving later | 3,000 snapshots | 41.7% |
| `features_json` → `evaluate()` re-evaluation | 20,000 decisions | **0 differences** on the 10,036 full-schema rows (rule is deterministic); 9,964 rows in the old schema (no sniper fields) |
| Paper fill delay (entry − cutoff) | 11,155 OPEN | 2 s: 56%, 8 s: 3% |
| Paper reserve impact (OPEN) | – | p50 33 bps, p90 145 bps |

### Decision distribution (risk_decisions)

| Age | ADAY | IZLE | GIRME |
|---|---:|---:|---:|
| 2 s | 0 | 56,823 | 1,458 |
| 5 s | 0 | 55,657 | 2,624 |
| 10 s | 2,190 (3.8%) | 46,719 | 9,370 |
| 30 s | 3,089 (5.3%) | 40,732 | 14,445 |
| 60 s | 2,916 (5.0%) | 37,773 | 17,562 |

### Paper-v2 and outcome labels (300 s, CONTINUOUS)

| Group | n | Median peak | Median final | Median staged | 1.5x | 2x | 3x | Staged profitable | Staged PnL (0.1 SOL) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Base rate (raw price, no fees) | 2,544 | 1.104 | 0.866 | – | 27.2% | 16.5% | 7.6% | – | – |
| ADAY canonical | 163 | 0.945 | 0.804 | 0.872 | 12.9% | 9.2% | 2.5% | 17.2% | −2.23 SOL |
| IZLE | 1,194 | 1.038 | 0.788 | 0.903 | 27.5% | 17.4% | 8.0% | 27.7% | −9.17 SOL |
| GIRME | 493 | 0.936 | 0.827 | 0.879 | 15.2% | 7.3% | 2.2% | 17.2% | −6.70 SOL |

No group shows positive expectancy after fees. The calibration table (`x_band_calibration`, 10 rows) was built on 18 Sep from the same 1-4 Sep sample; the largest bucket has 205 samples.

### Checks that could not be run

- Launch coverage (Create events missed by the public WS) could not be measured without an external reference. Suggested query: count `create_v2` in Bitquery `Solana.Instructions` for 4 Sep 05:41-13:41 UTC and compare with 6,670.
- `wallet_positions` vs trade aggregates: all 608,540 positions match the trade totals (buy tokens, buy/sell counts) with **0 mismatches** (full scan, 263 s). This table is reliable.
- Graduation proximity could only be measured inside the 600 s window; no post-PumpSwap data. Within 600 s: 1,859 of 50,739 SOL-quote mints (3.7%) reached `virtual_sol_reserves ≥ 115 SOL` (≈ 85 SOL real, curve full); 2,747 reached ≥ 85, 4,700 reached ≥ 60. Consistent with the public 1-3% graduation band but an upper bound because nothing after 600 s is tracked. (The 23 Oct analysis later read the chain directly for all mints.)

Raw check outputs and the script are in `turkish/analiz_ekleri/` (`dq_check.py`, `dq_results*.txt`); the script opens the database read-only.

---

## C) Revenue models and the chosen model

### Who pays, for what outcome?

The only sellable asset the system has today is **"event-time-honest Pump.fun launch-window data labelled with executable prices, and the pipeline that produces it"**. Not sellable: the signal (ADAY is below the base rate), real-time alerts (22 s latency), returns (negative).

Market context [VERIFIED, web, Oct 2026]: Pump.fun does ~25-42k launches/day; graduation rate 0.26-2.8% depending on method; weekly protocol revenue ~$18.6M (week of 7 Oct); trading bots take ~0.9-1% per trade; paid "alpha" groups charge $100-300/month (seller claims). Data/infrastructure price anchors: Bitquery $49-299/month, Shyft gRPC $199-649/month, SolanaTracker €50-1,499/month (streaming from €397), Helius Business $499/month (LaserStream included), Birdeye Premium ~$199/month. Sources at the end.

### Three models

| | M1: Early risk/sniper feed (API + Telegram) | M2: Research dataset + paper harness licence | M3: Own capital / performance fee |
|---|---|---|---|
| Customer | Trenches traders, small bot teams | Bot/quant developers, academic researchers, data teams of bot companies | Ourselves; later copy-trade subscribers |
| Offer | Risk score, creator history, bundle/sniper evidence within ≤10 s of launch | Launch-window (0-600 s) event-time data, latency labels, executable X labels, paper engine; Parquet + API | Live trading with proven positive expectancy |
| Pricing logic | $49-149/month subscription; small next to bot fees | $149-299/month API or $499-999 one-off dataset; enterprise $999+/month | 20% performance fee |
| Sales channel | X/Telegram trenches communities, bot referrals | Solana dev Discords, X, direct outreach to bot teams, GitHub sample notebook | – |
| Operating cost | ≥$499/month RPC (gRPC required) + 24/7 VPS + on-call | $199-499/month RPC + VPS + storage ≈ $300-700/month | Capital + loss risk |
| Prerequisite | Latency <3 s, uptime >99%, rule beating the base rate (**not met today**) | 30+ days of continuous data, P0 fixes | Positive expectancy (**none**), legal review |
| Competition | RugCheck, Bubblemaps, GMGN/Axiom built-in filters (free) | Bitquery/Dune raw data; "executable labels + latency" niche | Thousands of bots |
| Weak point | Free competitors, latency, trust building | Niche, small market; weak data moat | No proof |

### Chosen model: M2 (research dataset + harness), with an M1 upgrade option

Rationale:
1. M2's prerequisites are only the P0 fixes; it does not require the rule engine to produce alpha. M1 and M3 depend on conditions not met today.
2. The system's real differentiator (measuring data latency, not labelling backfill as live, computing fills from reserves instead of micro-trade prices) is exactly what M2's buyer cares about.
3. The M2 customer can be tested cheaply: willingness to pay is measured in 14 days without writing code (see E).
4. Even if M2 earns nothing, 30-90 days of continuous data is mandatory infrastructure for M1; the effort is not wasted.

Criticism: the M2 market is small and raw data is free/cheap. The buyer is the bot team that wants clean labelled data now rather than "collect it myself in a week". The size of that audience is an **[ASSUMPTION]** the experiment tests.

### Revenue and profit scenarios (monthly, USD)

Assumptions: RPC $499 (Helius Business; Shyft Build $199 in the low scenario), VPS $60, Postgres/storage $50, payments/tools $40 → opex $350-650. Founder time excluded. Payment fees 4%.

| Scenario | Customers | ARPU | Revenue | Opex | Profit |
|---|---:|---:|---:|---:|---:|
| Low | 3 | $99 | $297 | $350 | −$65 |
| Mid | 10 | $149 | $1,490 | $650 | +$780 |
| High | 30 + 2 enterprise | $199 / $999 | $7,970 | $900 | +$6,750 |

**Break-even:** 5 customers at $149 for $650 opex (or 7 at $99). Adding founder time of 20 h/month × $50, break-even is 12 customers.

### "Does it make money?" test

README makes no such claim; it says the opposite. Confirmed with data: 163 canonical ADAY, 0.1 SOL per position, staged strategy **−13.7%**; even the best subgroup (30 s ADAY, n=63) averages 0.908x. No paper outcome exists outside 1-4 Sep; no evidence for the future.

---

## D) Prioritized technical backlog

Format: Problem → Evidence → Change → Impact → Effort → Dependency → Acceptance.

### P0: Data correctness and blockers

**P0-1. Session model and honest `ended_at`**
Problem: restart time is counted as tracking end. → Evidence: `service.py:47`; LATE p90 24 h; 6,080 open trackings. → Change: `collection_sessions` table (id, started_at, last_heartbeat_slot/time, ended_at, ended_reason). Write a heartbeat per slot; on startup close the previous session with `ended_at = last_heartbeat`. Add `snapshot_tracking.session_id`; `create_due_snapshots` produces snapshots only when cutoff ≤ heartbeat. → Impact: no more fake LATE rows; "continuous" becomes machine-provable. → Effort: 1.5 days. → Dependency: none. → Acceptance: in a synthetic outage test (stop the collector 10 min) no snapshot is produced inside the gap; existing LATE rows are marked `LEGACY_LATE`, not deleted.

**P0-2. Decision freezing (look-ahead leak)**
Problem: late wallet/sniper info overwrites old decisions. → Evidence: `service.py:420-423, 493-495`; ADAY `evaluated_at − cutoff` p90 16.5 h. → Change: `risk_decisions` append-only (`decision_seq`), add a feature-schema hash to `ruleset_version`; the paper engine uses only the first decision with `evaluated_at ≤ cutoff + latency`; later decisions stored separately as `REVISED`. → Impact: paper results become true decision-time results. → Effort: 1 day. → Dependency: none. → Acceptance: re-scoring a mint never changes its first decision row; paper positions bind to `decision_seq=1`; a leak test (inject late info, paper entry must not change) passes.

**P0-3. Snapshot completeness watermark**
Problem: 41.7% of ON_TIME snapshots are built on incomplete data. → Evidence: section B recomputation. → Change: add `watermark_slot` and `completeness` (LIVE/SETTLED) to snapshots; regenerate as `SETTLED` once cutoff + lag has passed; models/calibration use SETTLED, live decisions use LIVE. → Impact: training data correct, live data honest. → Effort: 1 day. → Dependency: P0-1. → Acceptance: 1,000 random SETTLED snapshots recomputed from raw trades match 100%.

**P0-4. Latency measurement and a paid WS/gRPC trial**
Problem: median 22.5 s chain→client latency. → Evidence: B. → Change: write `chain_lag_ms = received − block_time` on every event; measure the same metric on a 7-day Helius Business or Shyft Build trial. → Impact: early snapshots become meaningful, or the project is proven unable to live at this latency. → Effort: 0.5 day + provider cost. → Dependency: none. → Acceptance: in a 24 h run `chain_lag_ms` p50 < 2,000, p90 < 5,000; otherwise change provider.

**P0-5. Run the paper engine over the whole history**
Problem: 82% of decisions never entered paper; canonical outcomes are squeezed into 2 days. → Evidence: 144,047 / 174,796; by-day table. → Change: after P0-2 run `paper-run` in bulk; exclude `GAP_AFFECTED` and `LEGACY_LATE`; report by date. → Impact: the rule engine's value is measured on 18 days for the first time. → Effort: 0.5 day + compute. → Dependency: P0-1, P0-2, P1-1. → Acceptance: every 10/30/60 s ADAY/IZLE/GIRME decision has a 300 s outcome; a per-day report exists.

**P0-6. Git and backup**
Problem: no commits at all. → Change: `git init`, first commit, remote; weekly `VACUUM INTO` backup of the DB. → Effort: 1 hour. → Acceptance: code on a remote; a backup file restores and `status` runs.

### P1: Enablers for first paid use

**P1-1. Storage diet and O(n) loops**
Problem: 10 GB, 200-400 s scans, 291k rows read every 0.5 s. → Evidence: `storage.py:1371-1376`; size measurements. → Change: drop `pump_trades.raw_event_json` (decoded fields suffice; keep the IDL version); move raw tx JSON to zstd files; a `snapshot_due` queue table (mint, age, due_at) for the snapshot worker; pre-aggregated `mint_wallet_stats` instead of correlated subqueries in `risk_feature_rows`. → Impact: DB ≈ 3 GB; constant-time worker. → Effort: 2 days. → Dependency: P0-6. → Acceptance: `status` < 5 s; snapshot loop < 50 ms with 100k trackings.

**P1-2. Non-SOL quote normalization**
Change: store `quote_decimals`, convert `net_quote_flow` to SOL equivalent, or explicitly exclude non-SOL as `UNSUPPORTED` from decisions/calibration. → Effort: 0.5 day. → Acceptance: NULL price only on `quote_asset≠SOL` rows and those have `decision='UNSUPPORTED'`.

**P1-3. Service-ification and observability**
Change: NSSM/systemd service, auto-restart, `/health` and Prometheus metrics (chain_lag, gap count, queue depth, RPC 429/timeout), Telegram alerts. → Effort: 1.5 days. → Acceptance: 7 days uninterrupted; alert within 5 min of an outage.

**P1-4. Export and product surface (M2)**
Change: daily Parquet export (launches, trades, SETTLED snapshots, decisions, outcomes, sessions); API-keyed read-only FastAPI (3-4 endpoints); data dictionary; sample notebook. Payment: Stripe Payment Link or Lemon Squeezy; key by email. → Effort: 3 days. → Dependency: P1-1. → Acceptance: a new customer runs the sample notebook with their own key within 10 minutes.

**P1-5. Core tests**
Change: `_handle_logs`/`_handle_slot` tests with a WS replay fixture, end-to-end `run_paper_cycle` test, session/outage test, leak test. → Effort: 1.5 days. → Acceptance: >70% line coverage on `service.py` and `paper_engine.py`.

**P1-6. Separate gap definitions**
Change: gaps at session start are `SESSION_GAP`, in-session gaps `STREAM_GAP`; raise `MAX_BACKFILL_SLOTS` to 300 with a paid RPC. → Effort: 0.5 day. → Acceptance: no restart-caused rows in `stream_gaps`.

### P2: Scaling and operating efficiency

**P2-1. PostgreSQL migration** (README plan) — only if still needed after P1-1; partitioned `pump_trades`, `SKIP LOCKED` queues. 3 days.
**P2-2. Post-PumpSwap tracking and 1h/6h/24h labels** — required for M1 and ML. 4 days.
**P2-3. Two candidate classes A/B and rule revision** — only after P0-5, by seeing why IZLE does better. 2 days.
**P2-4. ML** — not before a few thousand SETTLED+CONTINUOUS canonical outcomes across at least two market periods.
**P2-5. Auth/payment automation** — key management, usage metering, billing once customers exceed 10.

Not to do: rewrite, change language/framework, a Telegram signal bot (the rule does not beat the base rate), an agent layer.

---

## E) 7/30/90-day plan

### First 7 days: critical verifications and fixes

Deliverables: P0-6 (day 1), P0-1, P0-2, P0-3, P0-4 (paid RPC trial), start of P0-5. A read-only archive copy of the current DB.
Success: 72 h uninterrupted run; `chain_lag_ms` p50 < 2 s; 10 s ON_TIME ≥ 80%; zero fake snapshots in the synthetic outage test; leak test passes.
Go/no-go: if p50 latency > 5 s even on a paid RPC, the early-snapshot product (M1) is shelved permanently; focus on M2. If latency improves, M1 remains an option.

### First 30 days: minimum sellable version and a pilot

Deliverables: P1-1, P1-2, P1-3, P1-4, P1-5; 21+ days of continuous data; paper report over the full history (by day). **Willingness-to-pay experiment** (below) between days 8-21.
Success: uptime > 98%; dataset ≥ 500 hours; 3 paid pilots (total ≥ $300/month) or 2 pre-orders.
Go/no-go: 0 payments and < 5 qualified conversations in 14 days → change M2 price/audience once, 14 more days; still 0 → stop the commercial goal, keep the system as a personal research tool.

### First 90 days: demand validation, sustainable revenue, scaling

Deliverables: 10+ customers; P1-6, P2-2 (PumpSwap); rule engine compared with the base rate on 60+ days of SETTLED data; a second data product from customer feedback (e.g. sniper/bundle wallet list).
Success: MRR ≥ $1,500 (2× opex); churn < 20%/month; chain_lag p50 < 2 s for 60 days.
Go/no-go: MRR < $650 → downgrade infrastructure to the cheapest RPC and turn the product into open source + consulting. If the rule engine beats the base rate (2x seen ≥ base + 5 points, n ≥ 1,000), write a 30-day plan for M1.

### Willingness-to-pay experiment (before any large build)

No code, 14 days:
1. Produce a clean Parquet sample set from the 4 Sep session (8 hours, 6,670 launches); data dictionary and one notebook ("300 s X distribution with realistic fills").
2. One-page description + price: "30 days of continuous launch-window data + paper harness, $149/month, first 5 customers $99". Stripe/Lemon Squeezy link.
3. 20 direct outreaches (Solana dev Discords, bot-building accounts on X, 2 bot teams), 2 public posts.
4. Threshold: ≥ 3 payments or ≥ 5 written "I'll buy when the data arrives" commitments → invest in P1-4. Otherwise stop and write down why.

---

## F) First concrete task and acceptance criteria

**Task:** P0-6 + P0-1 together: put the repo under Git, then implement the `collection_sessions` table and heartbeat-based honest `ended_at`; mark existing LATE rows `LEGACY_LATE`.

**Why first:** every other measurement (paper, calibration, latency, customer data) depends on "when was the collector really up"; it is also README's own priority #1.

**Acceptance:**
1. `git log` shows at least one commit; `.env` and `data/*.db` are not in the repo.
2. `collection_sessions` exists; the collector updates `last_heartbeat_at/slot` on every slot; on startup it closes the previous open session with `ended_at = last_heartbeat_at` (not restart time).
3. Stopping the collector for 10 minutes and restarting produces **no** snapshot for cutoffs inside the gap; the gap appears as a single row in `collection_sessions`.
4. Of the existing 291,358 snapshots, those whose cutoff falls outside any session get `snapshot_quality='LEGACY_LATE'`; nothing is deleted; `calibrate-x` and paper reports exclude those rows.
5. New test `tests/test_sessions.py` covers the outage scenario; `pytest` passes 28+/28+.
6. `memecoin-motor status` prints session count and covered hours; for the existing data it agrees with 36 sessions / ~84.6 hours.

---

## Appendix: sources (web verification)

- Pump.fun launches/graduation: [Solana Compass](https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex), [DEXTools](https://www.dextools.io/news/pump-fun-graduation-collapse-solana-fees-2026), [pumpfundata](https://pumpfundata.com/blog/pumpfun-graduation-rate-analysis), [Medium cohort method](https://medium.com/coinmonks/pump-fun-api-how-to-track-bonding-curves-graduations-and-pumpswap-on-chain-879b689fbedb), [Cryptopolitan](https://www.cryptopolitan.com/pump-fun-graduating-tokens-break-to-1-15-of-new-launches/)
- Protocol revenue Oct 2026: [CoinMarketCap](https://coinmarketcap.com/cmc-ai/pump-fun/latest-updates/)
- Fee structure: [Blockworks](https://blockworks.com/news/pumpdotfun-fee-model), [The Block](https://www.theblock.co/post/354038/pumpswap-revenue-tokens), [Cointelegraph](https://cointelegraph.com/news/pump-fun-creator-fee-cap-update-memecoin-model)
- RPC/data prices: [Helius pricing](https://helius.dev/pricing), [Helius credits](https://helius.dev/docs/billing/credits), [Shyft gRPC](https://www.shyft.to/solana-yellowstone-grpc), [Bitquery Pump.fun API](https://bitquery.io/products/pumpfun-api), [SolanaTracker pricing](https://docs.solanatracker.io/pricing), [Birdeye comparison](https://madeonsol.com/api-alternatives/birdeye), [Nansen API](https://api-docs.nansen.ai/reference/pricing)
- Bot fees: [solanatools.io](https://solanatools.io/blog/solana-trading-bot-fees-compared), [memegateway](https://memegateway.com/academy/solana-trading-bot-fees-compared-2026/), [madeonsol Trojan](https://madeonsol.com/blog/trojan-bot-review)
- Paid alpha groups (seller claim): [Gumroad listing](https://memecointrenches.gumroad.com/l/discordmembership); sniper bot case: [Transak](https://transak.com/blog/crypto-memecoin-sniping-guide)
- Graduation threshold/PumpSwap: [madeonsol PumpSwap](https://madeonsol.com/blog/what-is-pumpswap)

Note: some price and rate sources are vendor or affiliate content; confirm on official pages before budgeting.
