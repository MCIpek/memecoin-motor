# Closing Note: Memecoin Engine

**Date:** 4 November 2026
**Decision:** Active development and the goal of "catch high-X coins early and trade them with our own capital" are stopped. Code, data and reports are archived.

## What existed

A Python system that listens to Pump.fun launches on Solana through the public WebSocket, records the first 600 seconds of every coin and produces rule-based decisions and wallet-free paper trades. Between 1 Sep and 8 Oct 2026 it collected 58,316 launches and 2.09 million trades (10.2 GB SQLite). The collector was up for 9.6% of the calendar; trade data is healthy only for 1-17 Sep (after 18 Sep the free-RPC queue dropped most trades; cause and free fix in `HIGH_X_COINS_ANALYSIS_2026-10-23.md` §2).

## What was tried, what came out

All tests are time-split (train 1-8 Sep, test 9-17 Sep), include 3% costs and exclude mayhem-mode coins.

| Path | Result |
|---|---|
| Select coins from 10-60 s features and enter | Every rule negative (-6% … -49%). Selection power exists (graduation rate rises 4-12x) but so does the entry price |
| The existing ADAY rule | Worse than random (2x seen 9% vs 16% base rate) |
| Enter after the creator sells | 2x rate goes from 4% to 7%; EV -8% … -14%. The 437 winners' common trait: "already crowded and expensive" |
| Smart-wallet copying | Skill persists; +10-14% in the same block, 0 at 1 s delay, negative at 5 s |
| Enter early and ride (144 combinations, 2/5/22 s entry) | All negative; no difference between 2 s and 22 s |
| Post-graduation PumpSwap (minute candles, 1,278 pools) | Price at 15 min: median 0.19x. Only non-negative cell: enter ≤1 min after migration, 1.5x target / -25% stop → test +2% (±2.6) under optimistic fill assumptions |
| Blind sniping | Early buys average +1-3% at second 0, negative afterwards; all profit is in the first block |

Structural findings: high X (15x and above) effectively means graduation; the bonding curve travels 14.7x from launch price to full. 63% of graduates are insider bundle launches filled in the launch second. The dev sells at a median of 8 s. Rising coins peak at a median of 9 s. Mayhem-mode coin prices are fake because of virtual-reserve inflation. Our chain latency was a median of 22 s.

**Conclusion:** There is no edge in this market that an outsider can find by analysis. Money goes to whoever launches/bundles the coin and to sub-second bots in the first block. The only edge is speed; speed starts at $150-500/month of infrastructure plus a dedicated server and Jito, and even there it is not guaranteed.

## Under what conditions it reopens

1. **Budget:** $200-300/month (gRPC stream + Frankfurt/Amsterdam VPS) for at least 2 months. First month without a wallet: measure latency and slot placement; go/no-go when ≥50% of simulated entries land in the same or the next slot as the first buyer and paper EV > +5%.
2. **Different window:** live paper-test the PumpSwap "≤1 min entry, 1.5x/-25%" cell with free infrastructure for 2-4 weeks (the only latency-insensitive candidate). If it holds, small capital can be discussed.
3. **Product/content path:** not to make money directly but to build an audience: free bot for bundle-launch detection, mayhem warning and dev-exit signal, with terminal referral links. Plan in `ANALYSIS_REPORT_2026-10-14.md` §C and the 3 Nov notes.

If reopened, the first task does not change: decode launches from the WebSocket log (removes the RPC queue), disable wallet/sniper enrichment during collection, add the session model and decision freezing (leak fix).

## Where things are

| What | Where |
|---|---|
| Code (3,700 lines, 27 tests) | `src/`, `tests/`; Git repository (first commit 4 Nov 2026) |
| Database (10.2 GB) | Original deleted on 4 Nov 2026. Single copy: `../memecoin_backup_2026-11-04/memecoin_motor.db.gz` (2.2 GB gzip; verified byte for byte). Restore: `gzip -dc memecoin_motor.db.gz > data/memecoin_motor.db` (needs 10.2 GB free). Old small `.bak` files in the same folder |
| System/data/revenue report | `ANALYSIS_REPORT_2026-10-14.md` |
| Fate of 58,316 coins, all strategy tests | `HIGH_X_COINS_ANALYSIS_2026-10-23.md` (§1-12) |
| Per-coin autopsy (max X, who sold) | `analiz_ekleri/coin_otopsi.csv` |
| Post-creator-sell, smart-wallet, ride and PumpSwap tests | `analiz_ekleri/*.txt`, `analiz_ekleri/*.csv` |
| Chain state (graduation), PumpSwap daily/minute candles | `analiz_ekleri/15x/` |
| All scripts (read-only, re-runnable) | `analiz_ekleri/*.py`, `analiz_ekleri/15x/*.py` |
| Original Turkish documents | `TURKCE.md` |

The scripts open the database with `mode=ro` only; no test modified production data and no real transaction was ever sent.
