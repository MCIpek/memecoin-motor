# The Fate of 58,316 Coins: Can a High-X Coin Be Detected Early?

**Date:** 23-26 October 2026 (final version: chain state for all 58,316 coins; PumpSwap peak data for all 1,853 graduate pools), with additional tests appended on 3-4 November 2026.
**Question:** Looking at what happened afterwards to the 58,316 Pump.fun launches in our 10 GB database, is it possible to pick out a coin that will do a high X in its first minutes? If so, should we trade it ourselves or sell the capability as a tool?
**Method:**
1. The bonding-curve account of every one of the 58,316 mints was read from the public Solana RPC (`getMultipleAccounts`, 584 calls, 0 errors). This gives the **definitive** chain state per coin: graduated or not (`complete`), current reserves, mayhem flag.
2. For the 2,020 graduated coins, the PumpSwap pool and its daily price history were fetched from GeckoTerminal (free API, ~7 requests/minute, ~5 hours).
3. These were joined with the database's first-10/30/60-second features, risk decisions and creator history.
4. All queries are read-only; production data was not modified. Raw outputs are under `analiz_ekleri/15x/`.

Tags: `[VERIFIED]` by chain or database; `[INFERENCE]` derived from data; `[ASSUMPTION]` could not be verified.

---

## 1. The conclusion in five sentences

1. **In this data, "high X" effectively means "graduated".** The Pump.fun curve travels exactly 14.7x from launch price to the full-curve price; no 15x before the curve fills, and every coin that fills the curve is by definition 14.7x. `[VERIFIED]`
2. **3.7% of the 58,316 coins (2,020) graduated;** 4.1% (1,436) among non-mayhem SOL coins. The remaining 96% died in the first 1% of the curve and reverted to the launch price. `[VERIFIED]`
3. **63% of graduates (906) are "bundled instant fills" that filled in the same second as the launch, with an average of 2.8 wallets and a single buyer doing 79% of the buying.** These are over before we see them; our only role would be exit liquidity. The reachable target is the **398 coins (1.1%)** that graduate after 600 s. `[VERIFIED]`
4. **First-60-second features can enrich this 1.1% target 4-12x** (e.g. with 15 SOL+ net inflow at 60 s and the curve not yet full, the graduation rate is 7.3%). **But entering at 60 s and exiting at real PumpSwap prices loses money under every realistic scenario (-6% to -49%); even the most optimistic scenario's best rule is +5%, i.e. zero.** Reachable graduates' post-fill run is a median of 1.83x and collapses the same day; 89% are below launch price today. Signal, yes; money, no. `[VERIFIED, all 1,853 graduate pools]`
5. **Only 1-17 September is usable for feature analysis.** After 18 September the collector recorded launches but almost no trades (trades per launch fell from 60-84 to 0.6-10). This is the biggest data error missed in the 14 October report. `[VERIFIED]`

---

## 2. Trade capture collapsed on 18 September `[VERIFIED]`

Non-mayhem SOL launches by day:

| Day | Launches | Trades/launch | With ≥1 trade | ≥6 buyers at 60 s | Graduated | State |
|---|---:|---:|---:|---:|---:|---|
| 09-03 | 489 | 57.9 | 97.1% | 35.0% | 4.1% | healthy |
| 09-04 | 3,718 | 69.5 | 94.8% | 36.5% | 5.2% | healthy |
| 09-07 | 4,696 | 84.4 | 94.6% | 38.8% | 5.1% | healthy |
| 09-08 | 3,972 | 60.2 | 93.6% | 38.2% | 3.9% | healthy |
| 09-16 | 2,142 | 60.1 | 98.3% | 38.4% | 6.1% | healthy |
| 09-17 | 2,175 | 50.5 | 96.6% | 35.2% | 4.5% | healthy |
| 09-18 | 2,621 | 9.7 | 82.1% | 8.1% | 3.3% | **broken** |
| 09-21 | 2,518 | 3.0 | 84.4% | 0.4% | 4.0% | **broken** |
| 09-30 | 2,976 | 1.1 | 89.7% | 0.1% | 2.9% | **broken** |
| 10-01 | 3,121 | 1.0 | 93.5% | 0.0% | 4.1% | **broken** |
| 10-07 | 3,794 | 0.6 | 63.1% | 0.0% | 2.5% | **broken** |

The on-chain graduation rate is still 2.5-4% on the broken days, so the coins did not change; what changed was the collector's ability to see trades.

**Cause (confirmed 3 Nov) `[VERIFIED]`:** The collector was up and saw launches on the WebSocket. But the `getTransaction` call it makes per launch backed up in a queue on the free public RPC. Median time from seeing the launch on the WebSocket to the launch being processed and tracking starting:

| Day | 1-17 Sep | 18 Sep | 21 Sep | 29 Sep | 30 Sep | 1 Oct | 7 Oct |
|---|---:|---:|---:|---:|---:|---:|---:|
| Delay | 0 s | 16 min | 84 min | 22 min | 17 h | 24 h | 20 h |
| Delayed >600 s | 0% | 64% | 86% | 81% | 95% | 100% | 99% |

The code (`service.py` `_handle_logs`) records a coin's trades only after that coin is under tracking, and tracking starts once the launch transaction arrives from RPC. When the queue exceeded 600 s, all of the coin's trades were dropped. On 1 Oct, 99% of the remaining trades are the dev buy inside the launch transaction itself. This is a code/infrastructure bottleneck, not a shutdown, and it will recur if the same code is run again.

**Free fix:** `CreateEvent` is already inside the WebSocket logs for 97% of launch transactions (300 launches checked). Decoding the launch from the log instead of calling RPC removes the bottleneck entirely; `getTransaction` stays only as a fallback.

The feature analyses in this report rely only on the 9 healthy days (17,543 coins with a 60 s price).

---

## 3. What happened to the coins: definitive chain state `[VERIFIED]`

| Group | n | Graduated | Rate |
|---|---:|---:|---:|
| All SOL-quote launches | 54,904 | 2,020 | 3.68% |
| Non-mayhem | 35,021 | 1,436 | 4.10% |
| Mayhem | 19,883 | 584 | 2.94% |
| Non-SOL quote (USDC etc.) | 3,412 | 78 | 2.29% |

Today's state of the 52,884 non-graduates: 99.8% are below 1% curve progress; the curve price has reverted to launch price (median 1.000x). A "dead coin" does not go to zero: once buyers sell out, the curve returns to its starting point. A 0.1 SOL position can still be sold at roughly its entry price today; the loss is small but capital stays locked for weeks.

Mayhem check: of the 1,859 coins that appeared to "reach 115 SOL on the curve" in our data, 753 did not graduate on chain, and **all 753 are mayhem**. In mayhem mode the virtual reserve inflates without real SOL; the "fake 15x" artefact found in the previous report is confirmed on chain. Mayhem coins are excluded from the rest of this analysis.

### Composition of graduates (non-mayhem, 1,436)

| When it filled | n | Share | Comment |
|---|---:|---:|---|
| Same second as launch (age 0) | 906 | 63% | Bundle launch: avg 2.8 buyers, single buyer 79% of buys |
| 1-600 s | 132 | 9% | Fast organic or semi-bundled |
| After 600 s | 398 | 28% | **Reachable target**: not yet full when we see it |

The reachable target is **1.1%** of non-mayhem launches. Joining the "instant fill" group is impossible: with our median 22 s chain latency, by the time we see it the curve is full and selling has moved to PumpSwap.

---

## 4. Where does high X happen?

- Distance from launch price to curve full: **14.7x** (price grows with the square of the virtual SOL reserve; 30 → 115 SOL).
- The entry price we see at 60 s is a median **1.02x** of launch (p90: 2.09x). So from a healthy 60 s entry about 14x remains to graduation.
- How far does the PumpSwap run go after graduation? See section 8.
- Non-mayhem coins, 15x from a 10 s entry within 600 s: **0 / 4,209** (previous report). No 15x before the curve fills.

Result: "catching the high-X coin" reduces in practice to "picking, in the first 60 seconds, the 1.1% that will graduate after 600 s, and catching the post-graduation run".

---

## 5. Do first-60-second features separate the target? `[VERIFIED, 9 healthy days, non-mayhem]`

Base rate (all coins): graduated 4.8%; graduated after 600 s 0.59%.

| Feature (60 s) | Bucket | n | Graduated | Graduated after 600 s |
|---|---|---:|---:|---:|
| Net SOL inflow | ≤0 | 4,179 | 0.45% | 0.43% |
| | <0.5 SOL | 15,519 | 0.92% | 0.89% |
| | 5-15 SOL | 2,389 | 1.51% | 1.34% |
| | 15-40 SOL | 879 | 9.90% | **7.17%** |
| | ≥40 SOL | 1,144 | 90.56% | 3.23% (mostly already full) |
| Unique buyers | 1-2 | 20,791 | 4.48% | 1.28% |
| | 6-10 | 2,234 | 9.00% | 0.40% |
| | 21-50 | 1,616 | 4.64% | 1.92% |
| | 51+ | 1,244 | 8.12% | **3.86%** |
| Top buyer share | <0.2 | 6,831 | 2.21% | 1.30% |
| | <0.4 | 2,992 | 9.93% | 0.87% |
| | ≥0.7 | 22,129 | 4.31% | 1.25% |
| Creator sold within 60 s | yes | 6,460 | 1.38% | 0.90% |
| | no | 28,512 | 4.72% | 1.19% |
| Creator's prior launches* | 0 | – | – | lift 1.0-1.3x |
| | 21+ | 7,299 | 0.62% | 0.48% |
| Buys in first 2 s | ≥20 SOL | 1,706 | 61.96% | 3.69% |
| | none | 4,228 | 0.47% | 0.47% |
| 60 s risk decision | ADAY | 2,523 | 14.74% | 1.70% |
| | IZLE | 21,721 | 4.39% | 1.27% |
| | GIRME | 10,728 | 1.02% | 0.73% |

\* The first version used the creator's total launch count, which included future launches and was a leak. With the corrected "launches so far" the lift fell from 1.7x to 1.0-1.3x. The "serial creator" signal is real but weak without hindsight.

Important reading: most buckets with a high graduation rate (≥40 SOL inflow, ADAY, ≥20 SOL in the first 2 s) actually capture coins that are **already full**. For the reachable target the strongest signals are **15-40 SOL net inflow with the curve not yet full**, **51+ unique buyers**, and the creator not having sold.

### Rules: time-split test and expected return

Train: healthy days ≤ 9 Sep (n=13,126). Test: 15-17 Sep (n=4,417). Entry at the 60 s price, 3% total cost. Non-graduates valued at **today's curve price** (a real measurement, not an assumption). Two exit scenarios for graduates: (A) sell at the curve-full price; (B) sell at 3× the curve-full price (a PumpSwap-run assumption, replaced by real data in section 8).

| Rule (60 s) | Test selected | Graduated after 600 s | Lift | EV (A) | EV (B, 3x) |
|---|---:|---:|---:|---:|---:|
| Buy everything | 4,417 | 0.86% | 1.0x | -10% | +3% |
| Creator's first launch | 2,451 | 1.14% | 1.3x | -9% | +9% |
| First launch & ≥6 buyers & ≥1 SOL | 716 | 3.77% | 4.4x | -18% | +30% |
| First launch & ≥11 buyers & ≥3 SOL & top buyer <0.5 | 411 | 5.60% | 6.5x | -19% | +42% |
| ≥21 buyers & ≥5 SOL | 472 | 5.30% | 6.2x | -29% | +20% |
| ≥51 buyers | 250 | 6.80% | 7.9x | -22% | +47% |
| ≥15 SOL inflow & curve not full | 238 | 9.66% | 11.2x | -30% | +49% |
| ADAY (existing rule) | 853 | 2.58% | 3.0x | -18% | +18% |
| ADAY & first launch | 649 | 2.77% | 3.2x | -15% | +28% |

Train and test agree in direction. Reading:
- **Selection power exists:** simple rules raise the reachable graduation rate from 0.9% to 4-10%, and this carries from train to test.
- **It is not enough on its own:** with a graduation-price exit every rule loses, because the 90-95% losers lose 10-35% of value on average and the winner's 14x does not cover it.
- **Profitability depends on the post-graduation run:** section 8 replaces the 3x assumption with real data.
- **Small sample:** 17-27 winners per rule in the test set; directional, with wide confidence intervals.

---

## 6. Bundled instant-fill launches `[VERIFIED]`

Of the 1,038 non-mayhem coins that graduated within 600 s, **906 (87%) filled in the same second as the launch**. Average 2.8 buyers, single buyer 79% of buys. Of the 1,706 coins with ≥20 SOL bought in the first 2 s, 62% graduated, almost all before we could see them. For this group:
- Entering is impossible (22 s latency, already at the full price).
- But **detecting it is easy and valuable**: "this coin launched bundled, expect distribution on PumpSwap" is a concrete feature for a tool, labelled from chain data with 100% accuracy.

---

## 7. What this means: trade ourselves, or build a tool?

**Trading ourselves:** No, with this data. The selection rule enriches graduation 4-12x, but entering at 60 s and exiting at real PumpSwap prices loses under every realistic exit policy and is roughly zero even under the optimistic one (section 8). The median PumpSwap run is 1.83x and fades the same day; the winner does not cover the 35-65% erosion of the losers. There is no alpha in this window (first minutes, chain data, 22 s latency). If alpha exists it is elsewhere: staged selling on PumpSwap in the minutes after the fill (needs second-level precision and paid infrastructure) or off-chain signals (social, wallet tracking). These are separate questions this data cannot answer.

**For a tool,** three certain, sellable signals exist: (1) bundled-launch detection (definitive), (2) mayhem-artefact warning (definitive), (3) a 60 s "reachable graduate" score (4-12x lift, small sample). These are things RugCheck/Bubblemaps do not give and trenches traders want within seconds. Selling requires a pipeline that runs 24/7 and does not collapse like it did on 18 September.

**The prerequisite for both paths is the same:** find and fix the trade-capture collapse (paid WS/gRPC or log decoding), extend tracking from 600 s to 24 h and PumpSwap, and collect 14 days of clean continuous data. The same P0 list as the 14 October report, with PumpSwap tracking promoted from P2 to P0.

---

## 8. Post-graduation peak: GeckoTerminal daily candles `[VERIFIED, all 1,853 pools]`

Daily candles for all 1,853 graduated coins with a PumpSwap pool on GeckoTerminal were fetched (1,838 have trades). The peak was measured "robustly": the daily high was capped at 3× the candle body, because single-wallet pools print meaningless wicks such as 277,359x from micro-trades into an empty pool.

| Group | n | Peak vs fill price (median / p75 / p90) | ≥2x | ≥3x | ≥5x | Best day's close / fill price (median) | Today / peak (median) | Below launch price today |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| **Reachable** (non-mayhem, graduated after 600 s) | 372 | **1.83x / 3.00x / 3.33x** | 45% | 26% | 5% | **0.06x** | 2.9% | 89% |
| Instant fill (bundled) | 895 | 7.8x / 51x / 440x (unreliable: single-wallet pool, self-trading) | – | – | – | 0.05x | 0.6% | 97% |
| Mayhem | 571 | 0.00x | – | – | – | 0.00x | – | 99% |

Reading:
- **For reachable graduates the PumpSwap run is small and ends the same day.** Median peak is 1.83× the fill price; 96.5% peak on the first PumpSwap day, and by that day's close the price is at 6% of the fill price. Not "buy at graduation and hold" but "sell in the minutes after the fill".
- **"High-X coins" are dead today.** 89% of the reachable group and 97% of the bundled group are below launch price today, holding less than 3% of their peak.
- **Bundled-group peaks are fake.** The single buyer at 60 s (the wallet that bought the whole curve with 85 SOL) trades against itself in the pool and prints wicks; figures like "USPR 154,724x" are unreachable for a real buyer.

### Expected return with real prices (60 s entry, healthy days, non-mayhem, n=17,543)

EV = P(non-graduate) × E[today's price / entry] + P(graduate after 600 s) × E[payoff | sample] + P(instant fill) × E[payoff | sample]; 3% costs. Three exit policies: **A** sell at the fill price (bundled: hold to today); **B** sell half at 2× the fill price (if reached), hold half to today; **C** sell at half the robust peak (optimistic; requires being there within minutes).

| Rule (60 s) | n | Graduated after 600 s | Losers' value today / entry | EV A | EV B | EV C |
|---|---:|---:|---:|---:|---:|---:|
| Buy everything | 17,543 | 0.59% | 0.90 | -13% | -14% | -3% |
| Creator's first launch | 7,869 | 0.70% | 0.89 | -16% | -17% | -6% |
| First launch & ≥6 buyers & ≥1 SOL | 1,927 | 2.65% | 0.64 | -32% | -35% | -8% |
| First launch & ≥11 buyers & ≥3 SOL & top <0.5 | 1,038 | 4.14% | 0.53 | -31% | -34% | 0% |
| ≥21 buyers & ≥5 SOL | 1,694 | 4.25% | 0.47 | -39% | -44% | -34% |
| ≥51 buyers | 1,221 | 3.85% | 0.54 | -34% | -39% | -30% |
| ≥15 SOL inflow & curve not full | 901 | 7.33% | 0.33 | -41% | -49% | -34% |
| ADAY (existing rule) | 2,432 | 1.69% | 0.71 | -31% | -33% | -10% |
| ADAY & first launch | 1,574 | 1.84% | 0.70 | -33% | -35% | -1% |
| Cheap entry (price <1.5x launch) & ≥6 buyers & first launch | 1,872 | 0.48% | 0.91 | -6% | -8% | +5% |
| Already full at 60 s (x60 ≥10) | 706 | – | 0.09 | -95% | -95% | -9% |

Peak-data coverage: 732 of the 848 graduates on healthy days (103 of the 104 reachable ones).

**Under the realistic policies (A, B) every rule is negative; under the optimistic policy (C: selling at half the intraday peak) the best result is +5% and the rest hover around zero.** The mechanism: every signal that raises the graduation rate (many buyers, large SOL inflow) also means entering at an already elevated price at 60 s; 93-96% of those coins do not graduate and revert to launch price (losers lose 33-65% of entry). The winners' PumpSwap run (median 1.83x, same-day collapse) does not cover it. The cheap-entry rule shrinks losses but finds no winners (0.48%). The single positive cell (+5%) disappears if cost/slippage moves from 3% to 5% or if a third of the peak is captured instead of half; it is statistically indistinguishable from zero.

---

## 9. Limits and honesty notes

- The public WebSocket may have missed some launches (`[ASSUMPTION]`); the chain scan covers only the 58,316 coins we recorded, not all of Pump.fun.
- 42% of 60 s snapshots were produced with incomplete trades (14 Oct report); the features may be somewhat stronger in reality, not weaker.
- Valuing non-graduates at "today's price" holds for a small 0.1 SOL position; a large position selling into an empty curve does worse.
- Creator history is computed point-in-time; sniper scores exist for only 8% of coins and were not used in rules.
- All figures belong to the 1-17 Sep 2026 market regime; base rates may differ in another period.

---

## 10. Additional test (3 Nov): smart-wallet copying `[VERIFIED]`

Question: are there wallets that consistently enter early and exit with profit, and does copying them leave a profit?
Method: every wallet's first-60-second buys on 1-8 Sep (train) were scored; on 9-17 Sep (test) those wallets were copied. Copy rule: enter d seconds after the wallet buys, exit d seconds after its first sell, otherwise exit at 600 s; 3% cost. 16,722 coins, 47,852 wallets, 268k early buys. Details: `analiz_ekleri/akilli_cuzdan_ozet.txt`, list: `analiz_ekleri/akilli_cuzdan_listesi.csv`.

| Wallet quintile by train score | Test, no delay (+0 s) | Test, +1 s | Test, +2 s | Test, +5 s | Test, +22 s (our latency) |
|---|---:|---:|---:|---:|---:|
| Worst 20% | -3.8% | -9.9% | -10.0% | -10.1% | -7.0% |
| Middle 20% | -0.9% | -4.4% | -4.1% | -3.5% | -4.0% |
| Best 20% | **+10.0%** | -4.9% | -4.8% | -4.3% | -1.9% |
| Selected "smart" wallets (5 rules) | +2% … +14% | -17% … +1.6% | -17% … +1.5% | -17% … +1.6% | -6.6% … +3.9% |

Reading:
- **Skill is real and persistent.** Wallets that did well in train also do well in test; the ranking holds across all five quintiles. This is the only time-split positive result found in the project.
- **But all profit is in speed.** One second late and the gain is gone; the only positive cells at 1-5 s are +1.5% with a standard error three times larger. Being at "0 seconds" means being in the same 400 ms block as the copied wallet.
- **Conclusion:** the smart-wallet edge exists but belongs to whoever can trade in the same block with paid fast infrastructure. With free infrastructure this path is closed too.

Signal frequency for the best wallet rule: ~19 coins/hour of collection, ~13,800/month at 24/7; at +2 s and 0.1 SOL per position: +0.0015 SOL/trade (±0.005), ≈ +21 SOL/month (±70). Statistically zero.

## 11. Additional test (3 Nov): "see the coin, enter, ride" `[VERIFIED]`

Question: without picking wallets, what happens if we enter a coin as soon as we see it and ride with an exit rule? Details: `analiz_ekleri/coin_surme_testi.txt`.
Method: healthy days, non-mayhem; entry at the first trade +2 s (WebSocket scenario), +5 s, +22 s (current latency) after launch; 8 exit rules (hold, 60 s, target/stop pairs, trailing stop 25%/40%, staged); 6 launch-time filters; 3% cost; train 1-8 Sep, test 9-17 Sep.

Result: **all 144 combinations are negative in the test period.** Unfiltered +2 s entry, best rule (trailing stop 25%): train -4.5%, test -3.2%; at +22 s -3.7% / -3.5%. Cutting latency from 22 to 2 seconds does not change the result. Best filter (creator's first launch, dev first buy 0.5-3 SOL, trailing 25%): train +0.8%, test -2.9%; indistinguishable from zero. The "dev first buy ≥5 SOL" filter is the worst (-10% … -23%): those are bundled dumps. Win rate across all combinations 6-22%.

Interpretation: entering early and riding loses at every latency between 2 and 22 seconds. The only positive point is second 0, the same block as the first buyer, which comes from sniper infrastructure, not a WebSocket.

## 12. Additional test (4 Nov): post-graduation PumpSwap, minute level `[VERIFIED]`

Data: minute candles for the first ~16 hours after migration for 1,278 non-mayhem graduate pools (GeckoTerminal, free; 1,251 with ≥10 candles). Wicks capped at 1.5× the candle body; means winsorized at 10x per trade; 3% cost. Train: migration ≤ 21 Sep; test: later. Details: `analiz_ekleri/pumpswap_dakika_testi.txt`, raw candles: `analiz_ekleri/15x/minute_graduated.jsonl`.

**Price path (reachable group, 365 pools, migration open = 1.0):** +1 min median 0.99; +5 min 0.91; +15 min **0.19**; +60 min 0.07; +6 h 0.06. Peak at a median of minute 4; 57% within the first 5 minutes. No "buy and hold" on PumpSwap; at most a 1-5 minute pop, absent in half of the pools.

**Strategies (reachable group, entry +1 min after migration):**

| Exit | Train (n=176) | Test (n=189) |
|---|---:|---:|
| Hold 3 min | +13.4% | -2.6% |
| Hold 5 min | +5.7% | -13.0% |
| Hold 30 min | -36% | -45% |
| 2x target / -30% stop | +2.4% (±4.2) | +3.4% (±4.1) |
| **1.5x target / -25% stop** | **+5.1% (±2.7)** | **+2.1% (±2.6)** |
| Trailing stop 25% | -0.8% | -9.2% |

At +5 or +15 min entry every rule is negative. Filters (first-minute return, volume) give no consistent improvement in test. In the bundled group "1.5x / -25%" shows +10% in test, but those pools are full of the bundler's own trades; fills are unreliable.

**Reading:** among 150+ combinations tested in this project, the only cell not below zero is "enter within 1 minute of migration, sell at +50%, exit at -25%". Expected return +2 to +5%, within the error margin; target fills assumed at the capped wick and stop fills at the exact level, both optimistic. Pools trade sparsely (median 60 traded minutes in 16 hours). With real slippage this cell most likely goes to zero. Not a money machine, but the first strategy in this project that latency does not kill: at minute scale a 22 s delay is acceptable. It is therefore the only candidate for a free, wallet-free live paper test.
