# Memecoin Engine

A Solana research engine for Pump.fun launches: an event-time data pipeline (WebSocket + official IDL decoding), rule-based risk scoring and wallet-free, bonding-curve-aware paper trading. Between 1 Sep and 8 Oct 2026 it recorded 58,316 launches and 2.09M trades; every coin's fate was then read back from chain (graduation flag) and PumpSwap price history.

**Verdict (Nov 2026):** 63% of graduates are filled in the launch block by insiders; the dev sells at a median of 8 s; every outsider entry strategy tested (early-feature selection, post-dev-exit entry, smart-wallet copying, enter-and-ride, post-graduation minute trading) has negative expected value after costs. The only positive edge exists at 0-second (same-block) latency. The project is archived; see [CLOSING_NOTE_2026-11-04.md](CLOSING_NOTE_2026-11-04.md).

Documents:
- [ANALYSIS_REPORT_2026-10-14.md](ANALYSIS_REPORT_2026-10-14.md): system, data quality and revenue-model review
- [HIGH_X_COINS_ANALYSIS_2026-10-23.md](HIGH_X_COINS_ANALYSIS_2026-10-23.md): what happened to all 58,316 coins, and every strategy test
- [CLOSING_NOTE_2026-11-04.md](CLOSING_NOTE_2026-11-04.md): decision, results, conditions to reopen
- [DESIGN_v2.md](DESIGN_v2.md): the original design document the code implements
- [TURKCE.md](TURKCE.md): all original Turkish documents in one file
- `analiz_ekleri/`: raw outputs and read-only analysis scripts (the 10 GB SQLite database is not in the repo)

The rest of this file is the operational README of the engine as it was at the end of collection.

> Status as of 14 Oct 2026: the system uses the ~10.2 GB SQLite database `data/memecoin_motor.db`, not PostgreSQL. The last collected launch is dated 8 Oct 2026. Results are research data; there is no evidence of sufficient performance or data continuity for live capital.

## Current scope

- Watch a single Solana program with `logsSubscribe`
- Track every slot with `slotSubscribe`
- Record slot gaps and run bounded HTTP backfill
- Keep event time, arrival time and RPC enrichment delay separately
- Idempotent event storage in SQLite WAL
- Decode `Create`/`CreateV2` with the official Pump IDL discriminators
- Exact mint, creator, bonding curve, quote and reserves from `CreateEvent`
- Minimal token table for verified launch mints
- Decode Buy/Sell from WebSocket `TradeEvent` without RPC calls
- Track new tokens for 600 s (default) only while the collector is running
- Per-wallet buy/sell and net token position
- Event-time snapshots at 2/5/10/30/60 s
- Asynchronous analysis queue for the creator and a bounded set of first-10-second buyers
- Bounded signature history, funder candidate from explicit SOL transfers, wallet graph
- Local repeat-creator and creator-sell history
- Explainable `GIRME/IZLE/ADAY` (REJECT/WATCH/CANDIDATE) rule baseline from snapshot + creator + wallet graph (`baseline-v1`)
- Wallet-free virtual entry for `ADAY` with latency, fees, slippage and reserve impact
- 60/300 s net X, target-hit and drawdown outcome labels
- Raw market X labels for all decisions, regardless of class
- Sniper behaviour score for the first 5 buyers in the first 10 s
- Fee payer, priority fee, Jito tip and bundle-likelihood evidence from bounded full-transaction enrichment
- RPC, program and limits configured via `.env`
- In-memory queue that separates launch `getTransaction` calls from the WebSocket read loop, three attempts, slot backfill on failure
- Live paper worker bounded to the last 120 s; large historical passes run via `paper-run`

## Collected data and current result

In the local database at the end of 8 Oct 2026:

| Record | Count |
|---|---:|
| Pump launches | 58,316 |
| Pump trades | 2,094,977 |
| Tokens with at least one trade | 53,591 |
| Snapshots / risk decisions | 291,358 |
| Token-wallet positions | 608,540 |
| Analyzed wallets | 14,568 |
| Sniper scores | 5,615 |
| Paper-v2 entry attempts | 30,749 |
| Executable paper outcomes | 4,389 |

Although the data spans 1 Sep to 8 Oct 2026, the collector ran on only 18 distinct days (36 sessions, 84.6 hours in total, 9.6% of the calendar). It is not a continuous 37-day series. Trade capture was healthy only on 1-17 Sep; after 18 Sep the launch `getTransaction` queue backed up on the free RPC and trades of most coins were dropped (see the high-X analysis, section 2).

### Snapshot quality

| Target age | On time | Late | On-time share |
|---|---:|---:|---:|
| 2 s | 2,313 | 55,968 | 4.0% |
| 5 s | 5,880 | 52,401 | 10.1% |
| 10 s | 13,089 | 45,190 | 22.5% |
| 30 s | 15,485 | 42,781 | 26.6% |
| 60 s | 16,438 | 41,813 | 28.2% |

The restart logic closes previous open `snapshot_tracking` rows at the new process start and can then produce the missing snapshots retroactively. Those rows carry `LATE` but do not reliably represent the interval during which the collector was down. Models, calibration and headline performance should use only `ON_TIME + CONTINUOUS` samples produced inside an uninterrupted session.

207 small slot gaps were backfilled; 1,276 large gaps were skipped due to the limit. The skipped intervals total 11.6 million slots, which includes long periods with the collector down, and must not be read as continuous coverage.

### Paper-v2 baseline result

In the 300 s, `CONTINUOUS`, canonical `ADAY` group there are only 163 outcomes:

| Metric | Result |
|---|---:|
| Median visible peak | 0.945x |
| Median final | 0.804x |
| Median staged strategy | 0.872x |
| Median max drawdown | 27.3% |
| Saw 1.5x | 12.9% |
| Saw 2x | 9.2% |
| Saw 3x | 2.5% |
| Saw 5x | 0.6% |
| Profitable under the staged strategy | 17.2% |

This baseline shows no positive expectancy and the sample is small. It cannot be used for real capital. The `IZLE` group contains more rising tokens than `ADAY`, which shows that the single candidate class over-penalizes concentrated momentum in the early Pump market; thresholds must not be loosened without a blind test.

The Pump IDL is pinned from the official `pump-fun/pump-public-docs` repository at `src/memecoin_motor/resources/pump.json`. Live transactions are decoded with IDL instruction and event discriminators; a mint seen in a transaction is no longer assumed to be a new launch.

## Requirements

- Python 3.11 or newer
- Solana HTTP and WebSocket RPC with internet access

## Setup

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

The default `.env` watches the official Pump bonding-curve program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`. No Pump.fun account or API key is needed; data is read from Solana RPC/WebSocket.

The default public Solana RPC is free but has no rate-limit or latency guarantee (measured chain-to-client latency: median 22 s). A more reliable provider's HTTP and WebSocket URLs can be set in `.env`.

## Running

```powershell
memecoin-motor doctor
memecoin-motor init-db
memecoin-motor redecode
memecoin-motor collect
```

In another terminal:

```powershell
memecoin-motor status
memecoin-motor snapshots --limit 20
memecoin-motor wallets MINT_ADDRESS --limit 20
memecoin-motor wallet WALLET_ADDRESS
memecoin-motor creators --limit 20
memecoin-motor creator CREATOR_ADDRESS
memecoin-motor score
memecoin-motor score --mint MINT_ADDRESS
memecoin-motor scores --limit 20
memecoin-motor paper-run
memecoin-motor paper --limit 20
memecoin-motor outcomes --limit 20
memecoin-motor labels --limit 20
memecoin-motor outcomes-v2 --limit 20
memecoin-motor missed-watchlist --horizon 300 --minimum-x 1.5
memecoin-motor calibrate-x --horizon 300 --minimum-samples 30
memecoin-motor x-bands --horizon 300 --limit 30
memecoin-motor sniper MINT_ADDRESS --limit 20
memecoin-motor snipers --limit 50
memecoin-motor sniper-backfill
```

`collect` is the live pipeline. The live paper worker only processes recent decisions in small batches. `paper-run` pushes historical data through the paper-v2 engine in large batches; with SQLite, running it alongside the live collector causes lock waits.

Tests:

```powershell
pytest
```

## Tables

- `chain_events`: program-related transactions with timing and completeness
- `tokens_minimal`: minimal record per observed mint
- `pump_launches`: decoded Pump launch details and initial reserves
- `pump_trades`: IDL-decoded Buy/Sell events inside the tracking window
- `wallet_positions`: per token/wallet buys, sells and net position
- `snapshot_tracking`: start/end of the uninterrupted tracking window
- `token_snapshots`: 2/5/10/30/60 s flow and concentration features
- `stream_gaps`: detected and backfilled slot gaps
- `wallet_analysis_queue`: creator/first-buyer work queue, separated from the fast path
- `wallet_profiles`: scan coverage and likely-funder result
- `wallet_edges`: funding-graph edges with the evidence transaction
- `risk_decisions`: score, confidence, reasons and a frozen copy of the features per snapshot age
- `paper_positions`: legacy-v1 virtual entry or explicit failure reason
- `paper_outcomes`: legacy-v1 60/300 s outcome labels
- `market_outcomes`: legacy-v1 raw market X labels
- `transaction_enrichment_queue`: bounded RPC queue for first buyers only
- `early_trade_metadata`: fee payer, compute budget, priority fee and Jito tip trace
- `sniper_scores`: explainable sniper score (repeat early entry, quick sell, same slot/funder/fee payer)
- `wallet_behavior_stats`: per-wallet counter of early entries across launches
- `paper_v2_positions`: 8 s fill window, reserve inputs and 10/30/60 s experiment groups
- `executable_outcomes_v2`: reserve-aware X for 0.1 SOL, staged exit and gap quality
- `x_band_calibration`: empirical X bands from `CONTINUOUS` outcomes only
- `service_state`: collector checkpoint

The database defaults to `data/memecoin_motor.db` and is not committed. The code does not use PostgreSQL. `redecode` re-decodes stored raw transactions with the current IDL and removes unverified Pump mints left by the old coarse extractor from the minimal table.

## Risk baseline-v1

This layer is not a prediction model and opens no positions. It scores net quote flow, unique buyers, single/top-5 buyer concentration, creator sells/history, snapshot quality, wallet-analysis coverage and shared funders. `ADAY` is given at 10 s at the earliest and only with enough confidence. Apart from a critical creator sell, insufficient data at 2/5 s yields `IZLE`, not `GIRME`. Every decision is stored with reasons and warnings.

## Wallet-free paper test

The paper engine only reads events from the database; it uses no private key, seed phrase, wallet address or `sendTransaction`. The V2 engine looks for a fill from 2 s after the decision up to 8 s. It does not multiply a position by the last micro-trade price; it computes the executable entry/exit value of a 0.1 SOL position on the virtual reserves, including fees, slippage and reserve impact.

This is a first cost baseline: priority fee/Jito values are constant and real block landing or Jito auctions are not replayed. The result is therefore not proof of live executability but a conservative filter against optimistic backtests.

`executable_outcomes_v2` labels all decision classes, not only `ADAY`, to avoid selection bias. Only `is_canonical=1` rows are headline paper performance; the rest are for experiments and rule audits.

## Paper-v2 and X calibration

The V2 engine looks for a fill within 8 s of the decision. It computes how many tokens 0.1 SOL buys on that slot's virtual quote/token reserves and the net SOL those tokens could be sold for, applying network fees, the Pump event fee estimate, slippage and reserve impact. An outcome overlapping an unresolved slot gap is `GAP_AFFECTED` and excluded from calibration.

The first successful `ADAY` entry per token is canonical. 10/30/60 s outcomes are stored as experiment groups; `IZLE/GIRME` virtual labels are only for rule audits. The strategy sells 40% at 1.5x, 30% at 2x, 20% at 3x and exits the remainder when buyer/seller momentum, negative flow and a 15% pullback coincide.

Calibration reports p25/p50/p75/p90 executable X and 1.5x/2x/3x/5x hit rates per decision age, decision class, risk and opportunity bucket.

## Sniper and bundle evidence

The sniper layer binds no wallet and sends no transactions. For up to 5 unique buyers in the first 10 s after launch, the full transaction is read via slow, asynchronous RPC. First entry age, same-slot buyers, repeat early entries across launches, quick sells, shared funder, shared fee payer, priority fee, transfers to official Jito tip accounts and the `jitodontfront` marker are scored.

`JITO_ROUTED` only means a transfer to one of the official tip accounts was seen; `bundle_likelihood=HIGH/MEDIUM/LOW` is a heuristic from on-chain evidence. Without the bundle ID, same slot or a Jito tip alone is not proof, so the system never emits `BUNDLE_CONFIRMED`.

## Known limits

- Free RPC is not adequate for live trading.
- Launch `getTransaction` calls run in an in-memory queue with three attempts; the queue is not persistent and pending work is lost on shutdown. On the free RPC this queue backed up to hours after 18 Sep 2026 and the 600 s trade window of most coins was missed. Fix: decode the launch from the WebSocket log (`CreateEvent` is present in 97% of launch logs) and use RPC only as fallback.
- Gap backfill skips large gaps for cost/rate-limit reasons.
- Pump launch and bonding-curve Buy/Sell decoders exist; post-migration PumpSwap trades are not covered.
- Wallet scans are bounded to 2x100 signatures by default to protect the free RPC.
- `TRADE_TRACK_SECONDS` defaults to 600 s; the whole Pump market is not recorded.
- Time with the collector down is not complete. The restart logic can produce missing snapshots as `LATE`; those rows are not training or headline data.
- SQLite: heavy `paper-run`, report or enrichment passes alongside the live collector cause lock waits.
- Roughly 111k wallet-enrichment and 20k transaction-enrichment jobs are pending; sniper/wallet coverage does not represent all tokens.
- The reliable canonical paper sample at 300 s is only 163 rows; not a balanced training set.
- Dynamic landing/Jito replay, PumpSwap, ML and agentic layers do not exist.
- Mayhem-mode coins (36% of launches) inflate virtual reserves without real SOL; their prices are not executable and must be excluded from analysis.

## Development priorities (as they stood before closure)

1. **Collection sessions and continuity:** record each collector run as a session; on unexpected shutdown use the last real slot/time; never produce snapshots across a gap.
2. **Data usability flag:** keep old `LATE` rows but mark them `LEGACY_LATE/UNUSABLE`; run models and reports on `ON_TIME + CONTINUOUS` only.
3. **Decode launches from logs:** remove the RPC queue bottleneck.
4. **Reliable RPC/Geyser:** separate the live collector from wallet/sniper research calls; keep latency, timeout, 429 and gap metrics.
5. **Complete paper-v2:** backfill canonical outcomes without counting 10/30/60 experiments as separate successes; time-ordered train/test periods.
6. **Two candidate classes:** A/B paper test organic vs concentrated-momentum candidates with different position, fill and exit rules.
7. **PumpSwap tracking:** post-migration pool, swaps, reserves and 1h/6h/24h executable X.
8. **ML last:** only after a few thousand reliable canonical outcomes across several market regimes.
