# Memecoin Early Decision, X-Potential and Agentic Audit Engine

**Version:** 2.1
**First target chain:** Solana
**First scope:** a single launchpad/program
**Approach:** deterministic rules + classical ML + agentic research/audit

This is the English version of the original design document (`memecoin_analiz_motoru_v2.md`, kept in `TURKCE.md`). Sections 19-20 describe what was actually implemented; the ML and agentic layers (sections 9, 13) were never built.

## 1. Purpose

Detect newly launched memecoins early and answer, probabilistically:

1. Is the token technically buyable and sellable?
2. How high is the rug, honeypot or hard-dump risk?
3. What is the probability of reaching 1.5x, 2x, 3x and 5x?
4. Is it worth entering once latency, cost and risk are included?

The engine never says "will certainly X" or "certainly no rug". Every result carries a probability, a data-quality grade and a confidence level.

```text
Token: ABC
Chain age: 14.2 s
Data latency: 1.4 s
P(2x within 1 hour): 31%
P(70% drop within 10 minutes): 48%
Estimated fill probability: 62%
Decision: REJECT
Confidence: low
```

## 2. Principles

- No definitive decision in the first seconds; only risk reduction.
- No LLM/agent on the fast decision path.
- Obvious technical risks are eliminated by deterministic rules.
- X and dump probabilities are estimated by classical ML.
- Agentic AI works in slow research, audit, explanation and operations.
- A snapshot is not training data unless its data latency is measured.
- Paper trading never assumes an automatic fill at the theoretical price.
- No real capital without sufficient paper and blind tests.

## 3. Hybrid architecture

```text
Solana WebSocket/RPC (later Geyser)
                 |
                 v
        Event and slot recording
                 |
        +--------+---------+
        |                  |
        v                  v
 FAST DECISION PATH   SLOW AGENTIC PATH
 - Technical rules    - Creator research
 - Instant features   - Deep clustering
 - Classical ML       - Social/web review
 - Fill model         - Data/model audit
 - Risk engine        - Error analysis
        |                  |
        v                  v
 REJECT/WATCH/CANDIDATE   Reports/alerts/suggestions
        |
        v
 Paper trade
```

The agentic path never changes a fast decision retroactively. Late information is only used in the next score or an exit warning.

## 4. Decision gates by second

| Target age | Work | Confidence |
|---|---|---|
| 0-2 s | Transaction structure, authorities, liquidity, obvious technical risk | very low |
| 2-5 s | First trades, creator movement, visible concentration | low |
| 5-10 s | Unique-buyer growth, first sells, net flow | low-medium |
| 10-30 s | Momentum, wash trading and bot behaviour | medium |
| 30-60 s | Holders and asynchronous analysis results | medium |

These are target times, not guarantees. Late data is never written as an early snapshot.

```text
NEW -> REJECTED
NEW -> WATCH -> REJECTED
NEW -> WATCH -> CANDIDATE -> PAPER BUY
CANDIDATE/PAPER BUY -> RISK UP -> EXIT WARNING
```

## 5. Data time and integrity

Free RPC/WebSocket can lag, drop or skip slots. The client clock is not the single truth.

Mandatory fields per event:

```text
slot
block_time
tx_index_in_block
signature
commitment
provider_name
client_received_at
processed_at
ingestion_latency_ms
is_backfilled
stream_gap_detected
data_completeness
```

`block_time` is approximate and has second resolution; it is used together with slot, transaction order and local arrival time.

```text
target_age_ms: 2000
actual_chain_age_ms: 7800
ingestion_delay_ms: 6100
snapshot_quality: LATE
```

### Gap and backfill policy

- The last seen slot is stored.
- A slot jump opens a gap record.
- Missing slots are backfilled through a separate RPC.
- Backfilled data is never labelled as seen live.
- Confirmed/finalized data is reconciled later.
- Missing or late samples are excluded from live fill tests.
- Data quality is both a filter and a feature in the model.

## 6. Data sources

### Directly from Solana

- Mint, launch, pool, swap and transfer events
- Mint/freeze authorities and Token-2022 extensions
- Creator/deployer
- Liquidity and reserve changes
- First buyers/sellers
- Creator and insider sells

### Enrichment

- DEX Screener: price, volume, liquidity, trades and pair info
- RugCheck: Solana risk report
- GoPlus: supported security checks

REST services are not the primary event detector; because indexing can lag they are used for cross-checks and enrichment only.

### Market context

- SOL direction and volatility
- Launchpad activity
- General memecoin risk appetite
- Recent ratio of successful/failed launches

## 7. Fast technical safety gate

Direct rejection reasons:

- Sell simulation fails
- Dangerous mint/freeze/transfer authority
- Risky Token-2022 extension
- Liquidity insufficient to exit
- Sudden liquidity withdrawal
- Early creator/insider sell
- Obvious coordinated/artificial buying pattern
- Visible supply concentration above the risk limit

A clean RugCheck or GoPlus result does not mean the token is safe.

## 8. Wallet clustering

The full history of many wallets is not queried via RPC in the first 2-5 seconds.

### Fast path

- Same fee payer or funding transaction
- Coordinated buys in the same slot
- Link to the creator in the same transaction
- Similar amounts and timing
- Visible holder concentration

### Slow/asynchronous path

- `getSignaturesForAddress` and transfer history
- CEX/bridge funding traces
- Multi-hop transfer graph
- Creator's previous tokens
- Long-term behavioural similarity

The preferred structure is a continuously updated local wallet/funding graph. Not finding a link does not mean "no insider".

```text
observed_insider_share: 8%
estimated_linked_share: 17-31%
clustering_coverage: 42%
undetected_risk: HIGH
```

## 9. Classical ML prediction layer

First candidates for tabular data: LightGBM, XGBoost, CatBoost and logistic regression. No LLM at the centre of the numeric prediction.

### Feature groups

- Technical risk and authorities
- Liquidity/market cap and quote reserve
- Price impact and estimated slippage
- Unique-buyer growth rate
- Buy/sell ratio and net SOL flow
- Trade-size distribution
- Holder/insider density
- Creator history
- Momentum, volatility and market regime
- Wash-trading/bot probability
- Data latency and completeness score

### Separate models

1. `P(1.5x / 2x / 3x / 5x)`
2. Rug/hard dump within a horizon
3. Max upside and max drawdown
4. Landing/fill and slippage

```text
P(1.5x within 10 min): 48%
P(2x within 1 hour): 27%
P(3x within 24 hours): 9%
P(70% drop within 10 min): 41%
```

## 10. Decision engine

```text
worth_entering = expected_net_return
                 x fill_probability
                 - rug_risk_penalty
                 - liquidity_penalty
                 - data_uncertainty_penalty
```

- **REJECT (GIRME):** critical problem or negative risk-adjusted expectation
- **WATCH (IZLE):** insufficient data or borderline score
- **CANDIDATE (ADAY):** positive expectation, no trade yet
- **PAPER BUY:** virtual trade conditions met
- **EXIT WARNING:** insider sell, liquidity loss or momentum breakdown

ML cannot override deterministic safety and risk limits.

## 11. Realistic paper trading and Jito

The paper engine never writes an automatic fill at the signal price:

```text
base_fee
priority_fee
jito_tip
slippage
price_impact
ata_creation_cost
failed_attempt_cost
landing_probability
landing_latency_slots
```

A fixed $0.50-1.00 cost is only a rough baseline. Because SOL price, network load and the Jito auction vary, dynamic scenarios are used.

1. Record the decision time.
2. Add transaction build/send latency.
3. Apply the period's priority-fee and Jito-tip distribution.
4. Estimate landing probability and slot.
5. Use the pool state at the landing slot.
6. If slippage or liquidity is insufficient, count the trade as failed.
7. Add failed attempts to the net result.

Optimistic, realistic and pessimistic scenarios are reported separately.

### Implemented paper-v2 rules

- The fill window is at most 8 s from the decision.
- 0.1 SOL entry/exit is computed from virtual reserves, not from the micro-trade price.
- The first successful CANDIDATE per token is canonical; 10/30/60 s entries are experiment groups.
- An unresolved slot gap yields `GAP_AFFECTED` and is excluded from calibration.
- Sell 40% @ 1.5x, 30% @ 2x, 20% @ 3x; momentum-break exit for the remainder.
- Successful WATCH tokens are reviewed in a separate missed-opportunity report.
- X bands are calibrated from the p25/p50/p75/p90 distribution of `CONTINUOUS` outcomes.

## 12. Two-tier storage

Deleting every token creates selection bias; keeping all raw data for every token is expensive.

### Minimal tier: all tokens

```text
mint, creator, program, launch_slot, block_time,
initial_liquidity, max_volume, last_state, rejection_reason
```

### Detailed tier: promoted tokens

For tokens that pass a launchpad-specific threshold of volume/liquidity, unique buyers, lifetime or notable anomaly, swaps, holders, liquidity and time series are kept.

Raw RPC/API JSON is not stored indefinitely; compression, deduplication and retention apply. The failed-token class is never lost entirely.

## 13. Agentic AI layer

The agent is not a second-level trading brain.

### Research agent

- Reviews the creator's previous tokens.
- Deepens wallet and funding links.
- Researches website and social history.
- Reports similar or suspicious projects.

### Risk/model audit agent

- Analyzes wrong CANDIDATE/PAPER BUY signals.
- Finds performance degradation by launchpad and period.
- Monitors data distribution and model drift.
- Proposes new rug patterns and features.

### Operations agent

- Monitors RPC latency, 429s, disconnects and slot gaps.
- Suggests pausing signals when data quality drops.
- Summarizes service failures.
- Prepares daily performance/risk reports.

### Agent authority limits

The agent cannot sign a wallet or trade on its own, raise position or loss limits, disable stop/safety filters, promote a model to live automatically, or override the deterministic risk engine. Critical agent suggestions require human approval and re-testing.

## 14. Backtest and labelling

No hand-picked tokens. All tokens stay in the minimal tier. Target snapshots:

```text
2 s, 5 s, 10 s, 30 s, 60 s,
5 min, 1 h, 6 h, 24 h, 72 h
```

Target age and real chain age are stored together. Delayed data is never fed to the model as if it existed earlier.

Labels: max attainable X after the signal, max drawdown, time to targets, drawdown before target, liquidity withdrawal and its time, creator/insider sell time, realistic paper entry/exit price, net result after all costs.

Train and test are split by date. Future information must not leak into decision-time features.

## 15. Success metrics

Rug/dump precision and recall; false safe/CANDIDATE rate; probability calibration; fill prediction agreement; net return after costs; max drawdown; uplift over a simple baseline; robustness across market periods; detection, decision and landing latency; missing/late snapshot rate.

High accuracy alone is not success. A positive result with realistic costs and acceptable risk in an unseen period is required.

## 16. Development stages

1. **Reliable data pipeline:** WebSocket, slot gaps, backfill and two-tier storage.
2. **Rule-based baseline:** technical rejection, fast features and asynchronous clustering.
3. **Realistic paper trading:** dynamic fee/Jito, landing, slippage and failed trades.
4. **Classical ML:** X, dump and fill models; time-ordered blind test.
5. **Agentic audit:** research, drift, operations and performance reports.
6. **Controlled live test:** only after a successful paper test; tiny capital and a kill switch.

## 17. Productization

No Telegram, sharing or revenue model before performance is verified.

1. Use only for our own trades
2. Analysis/signal service
3. Trade- or performance-based revenue from the user's own wallet

The third option needs separate legal review (wallet authority, custody, security, tax, consumer protection, financial regulation).

## 18. First technical success definition

The first success is not making money or running an AI agent:

> Detect tokens from the chosen launch source without interruption, detect and fill slot gaps, record the true age of the 2-60 s data correctly, and match outcomes without leaking future data.

Until this foundation is verified, no ML prediction, agent commentary or "worth entering" decision is trustworthy.

## 19. Implementation status: wallet-free paper baseline

The implementation tests `baseline-v1` CANDIDATE decisions without binding a wallet. No private key/seed phrase is stored and no transaction is sent. The first observed trade after the decision latency is the virtual entry reference. Base fee, priority fee, Jito tip, two-way slippage and a reserve-impact limit apply. With uninterrupted tracking, max X, min X, final X, target hits and drawdown after costs are recorded at 60 and 300 s.

To avoid selection bias, the raw market outcome is labelled for all decision snapshots, not only CANDIDATE. A paper position is opened only on CANDIDATE.

This is not a real landing replay. Fee/Jito assumptions are constant and post-PumpSwap prices are out of scope. A positive paper result is not permission to use live capital.

## 20. Sniper and bundle evidence layer

For a bounded number of early buyers in the first 10 s, the full transaction is read asynchronously. Fee payer, compute-budget priority fee, transfers to official Jito tip accounts, `jitodontfront`, same slot, shared funder, repeated early entry and quick-sell behaviour are turned into an `EARLY_TRADER`, `SNIPER_CANDIDATE` or `COORDINATED_SNIPER` score.

A Jito tip or a shared slot alone is not bundle proof. Without the bundle ID the result is kept as `LOW/MEDIUM/HIGH bundle likelihood`; no definitive bundle label is produced. Coordinated snipers and high bundle likelihood are added as penalties to the risk baseline.
