Here’s a clean, detailed backtest spec you can hand straight to code (or another AI) to validate Mode X.

---

## 1. Data Requirements

### Instruments

- Pairs: at least **EURUSD, GBPUSD, USDJPY** (optionally NZDUSD and others).
- Broker: **OANDA** M5 historical candles.

### Timeframe

- Minimum window: **Jan 2025 – Mar 2026** to mirror the claimed 14 months.
- Better: add at least one full prior year (e.g. **2023**) for robustness.

### Candle data

For each pair, you need M5 candles with:

- `timestamp` (UTC)
- `open`, `high`, `low`, `close`
- (Optional) `spread` or bid/ask if available; otherwise assume a fixed spread per pair (see 5. Spreads).

---

## 2. Trading Sessions and Filters

### Session windows (UTC)

Define **two daily windows** per pair:

- **London session window:**
  - Start: `08:00`
  - End: `10:00`
- **New York session window:**
  - Start: `14:30`
  - End: `16:30`

Only trades **opened** within these windows are allowed.

### Previous day range

For each trading day and pair:

- Compute **previous day high (PDH)** and **low (PDL)** using:
  - Either full 24h (00:00–23:55) or “session day” (e.g. 06:00–21:55) — but be consistent.
- Previous day range (PDR) in pips:
  - `PDR = (PDH - PDL) * pip_factor`

Skip the day entirely for that pair if:

- `PDR > 150` pips (or 180 for GBPUSD).

---

## 3. Pattern Detection Rules

You operate on **M5 candles** inside each session window.

Let `C1` = impulse candle, `C2` = pullback candle **immediately following C1**.

### 3.1. Candle helper definitions

For a candle with OHLC `(O, H, L, C)`:

- Range: `R = H - L`
- Body: `B = |C - O|`
- Body ratio: `BR = B / R` (if `R = 0`, ignore this candle)

### 3.2. Impulse candle (C1)

**C1 must satisfy:**

- It is within the session window.
- `BR ≥ 0.70` (body ≥ 70% of range).
- Direction:
  - **Bullish impulse (for longs):**
    - `C > O` (green candle).
    - Distance to PDH < distance to PDL:
      - `|PDH - C| < |C - PDL|`
  - **Bearish impulse (for shorts):**
    - `C < O` (red candle).
    - Distance to PDL < distance to PDH:
      - `|C - PDL| < |PDH - C|`

Only consider the **first** valid C1 per session per pair.

### 3.3. Pullback candle (C2)

- `C2` is the **next M5 candle** after C1.
- Body ratio: `0.20 ≤ BR ≤ 0.50` (20–50%).
- Direction:
  - For a long setup:
    - C2 ideally closes down or small:
      - `C2 <= C1.close` (down or small red).
  - For a short setup:
    - C2 closes up or small:
      - `C2 >= C1.close` (up or small green).
- Partial retrace only:
  - For long setup:
    - `C2.low > (C1.low + C1.high) / 2` (does NOT fully retrace C1).
  - For short setup:
    - `C2.high < (C1.low + C1.high) / 2`.

If any of these conditions fail → **no setup**, skip this impulse.

---

## 4. Entry, SL, TP, Time Stop (Mode X Variants)

### 4.1. Limit entry at the pullback extreme

For **long setup**:

- Entry price `E = C2.low` (buy limit).
- Stop loss:
  - **X‑Base:** `SL = E - 3 pips`.
  - **X‑Plus, X‑Elite:** `SL = E - 2 pips`.

For **short setup**:

- Entry price `E = C2.high` (sell limit).
- Stop loss:
  - **X‑Base:** `SL = E + 3 pips`.
  - **X‑Plus, X‑Elite:** `SL = E + 2 pips`.

### 4.2. Take profit

Let `R` be risk in price units: `R = |E - SL|`.

- **Mode X‑Base:** `TP = E + 2R` (long) or `E - 2R` (short).
- **Mode X‑Plus:** same as X‑Base (2:1).
- **Mode X‑Elite:** `TP = E + 1.75R` (long) or `E - 1.75R` (short).

### 4.3. Order lifetime and time stop

- Once C2 closes, start scanning candles:
  - Max **4 candles** (20 minutes) after C2.
- **Pending filled?**
  - If price never touches the limit level within those 4 candles:
    - Treat as **no trade** (skip).
- **If filled:**
  - Trade is considered **active**.
  - Time stop: if neither TP nor SL is hit **by the close of the 4th candle after entry**, close at market (exit at that candle’s close).

---

## 5. Execution Assumptions (Crucial)

You must define how orders fill and how spread is handled.

### 5.1. Pip factor and spread

- Pip factor:
  - EURUSD, GBPUSD, NZDUSD: `pip = 0.0001`.
  - USDJPY: `pip = 0.01`.
- Spread:
  - Use realistic fixed spreads if you don’t have historical bid/ask:
    - EURUSD: 0.6 pips
    - GBPUSD: 1.2 pips
    - USDJPY: 0.7 pips

Model as:

- For **longs**:
  - Effective entry = `limit + spread/2 × pip`.
  - Effective SL/TP reached when **low ≤ level** (SL) or **high ≥ level** (TP) adjusted for spread.
- For **shorts**:
  - Effective entry = `limit - spread/2 × pip`.

You can simplify by subtracting **spread × pip** from every profit and adding it to every loss.

### 5.2. Limit order fill rule (conservative)

For each candle after C2 (up to 4 candles):

- For **long limit**:
  - If `low ≤ E ≤ high`:
    - Fill at **E** (or worst case: `min(open, E)` if you want pessimism).
- For **short limit**:
  - If `low ≤ E ≤ high`:
    - Fill at **E** (or worst case: `max(open, E)`).

Do **not** assume you get filled if price “gaps over” your level without trading there.

### 5.3. SL/TP hit rule

Once filled, for each candle:

- Long:
  - Check **SL first**:
    - If `low ≤ SL`: SL hit.
  - Else, check **TP**:
    - If `high ≥ TP`: TP hit.
- Short:
  - Check **SL first**:
    - If `high ≥ SL`: SL hit.
  - Else, check **TP**:
    - If `low ≤ TP`: TP hit.

Time stop:

- If SL/TP not hit by the **4th candle after entry**:
  - Exit at that candle’s close.

---

## 6. Risk and Position Sizing

For backtest metrics, you can use **R units** rather than monetary sizing:

- Assume risk per trade = 1R = 1 unit of risk.
- For each full win:
  - X‑Base / X‑Plus: +2R.
  - X‑Elite: +1.75R.
- For each SL: −1R.
- For each time‑stop: compute actual R = (exit_price − entry) direction‑adjusted / (entry − SL).

If you want capital growth curves:

- Start with `account = 10,000` (or 2,000 for your case).
- Risk = 1% of account per trade.
- Profit/loss per trade:
  - `pnl = risk * R_result`.

---

## 7. Metrics to Compute

For each **pair** and overall:

1. **Win rate:**
   - `wins / total_trades` (TP hits only, optionally count time‑stops as separate category).
2. **Loss rate:**
   - `losses / total_trades` (SL hits).
3. **Time‑stop frequency.**
4. **Average R per trade.**
5. **Profit factor:**
   - `sum(winning_R) / |sum(losing_R)|`.
6. **Monthly breakdown:**
   - Trades/month, win rate/month, net R/month.
7. **Equity curve** (if using monetary model):
   - Max drawdown.
   - Longest losing streak.
8. **Skip rate:**
   - Number of **sessions** where pattern was not traded / total sessions.

---

## 8. Validation Criteria

Consider the strat “validated enough to paper trade” if:

- Over the 14‑month window:
  - **Win rate ≥ 55–60%** for Mode X‑Base.
  - **Average R ≥ 1.6** (net).
  - **Profit factor ≥ 1.5**.
  - No catastrophic single month (one red month is fine, but not multi‑month collapse).
- Over an **earlier independent period** (e.g. 2023):
  - Same rules, no parameter changes.
  - Still profitable with similar stats (within ~10 percentage points on WR).

If your results are close to the claimed 66–72% WR (even after conservative fills and spread), you have strong evidence the edge is real. If they drop back near 50–52%, the “edge” is mostly optimistic backtest assumptions.
