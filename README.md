# Bingo/Tombola Card Generator (Technical Spec)

## 1) Project Summary

A deterministic, audit-friendly generator of Bingo/Tombola number sets under
fairness and uniqueness constraints. Outputs machine-readable artifacts
(`cards.json`, `report.json`, logs). Supports config-file driven runs,
interactive prompts for missing parameters, colored console output, and
reproducible runs via a minimal seed.

## 2) Core Concepts & Definitions

- **Number range**: integers `1..R` (inclusive).
- **Card**: an `m×n` matrix (no “free” cells in the base variant).
- **Row/column combination**: a **set without order** (no duplicates inside the
  set).
- **Uniqueness scope**:

  - `row_sets`: no row-set repeats across **all** cards.
  - `col_sets`: no column-set repeats across **all** cards.

- **Uniformity of frequencies**:

  - `strict`: every number appears equally often (requires `(T*m*n) % R == 0`).
  - `near`: difference between any two numbers’ frequencies ≤ 1 (allowed when
    `(T*m*n) % R != 0`).

- **No duplicates on a card**: the same number must not appear more than once
  **within the same card**.
- **Card identity**: cards are compared by their full `m×n` content.

> **Implied coherence:** If `row_sets` or `col_sets` uniqueness is enforced
> globally, **identical cards cannot occur** (they would replicate all
> row/column sets). The generator still performs an explicit final “no identical
> cards” check as a safety guard.

## 3) Inputs & Configuration

### 3.1 CLI

```bash
bingo-gen \
  --config config.yaml \
  --out-cards cards.json \
  --out-report report.json \
  --log-file run.log \
  --colors auto \
  --log-level INFO
```

### 3.2 Config file (JSON or YAML)

Both JSON (`.json`) and YAML (`.yaml`/`.yml`) are supported. Missing fields are
prompted interactively.

**Schema:**

```yaml
# ---- Required core parameters ----
R: 75 # upper bound of the number range (inclusive), integer >= max(m,n)
T: 150 # number of cards to generate, integer >= 1
m: 3 # rows per card, integer >= 1
n: 4 # columns per card, integer >= 1

# ---- Constraints & fairness ----
unique_scope: # any subset of: ["row_sets", "col_sets"]
  - row_sets
  - col_sets
uniformity: strict # "strict" | "near"
position_balance: true # try to balance frequencies by position (soft constraint)

# ---- Randomness / reproducibility ----
seed:
  mode: "integer" # minimal seed procedure
  value: 20250824 # integer; if missing -> asked interactively
  engine: "py_random" # "py_random" (default) | "numpy_pcg64" (if available)

# ---- IDs / numbering ----
card_id_mode: "sequential" # "uuid" | "sequential"
card_number_start: 1 # starting number if sequential

# ---- Algorithm strategy ----
bbd_mode: "auto" # attempt BIBD/Balanced design when feasible; fallback otherwise
build_timeout_sec: 90
swap_iterations: 20000

# ---- Output & UX ----
colors: "auto" # "auto" | "always" | "never"
log_level: "INFO" # "DEBUG" | "INFO" | "WARN" | "ERROR"
log_format: "text" # "text" | "json"
log_file: "run.log"
out_cards: "cards.json"
out_report: "report.json"
summary_csv: "summary.csv" # optional
```

**Interactive prompts** (when fields are missing):

- Prompts display defaults in brackets, e.g. `R [75]:`
- Enter `?` to see help and acceptable ranges.
- On invalid input, the prompt reappears with a short, colored hint.

### 3.3 Parameter Feasibility Pre-Check

Let `P = T * m * n` be the total number of placed numbers.

- **Uniformity requirement**:

  - `strict`: require `P % R == 0`.
  - `near`: target frequencies are `base = P // R` and `base+1` for
    `remainder = P % R` numbers.

- **Uniqueness capacity**:

  - Max unique row-sets of size `n` from `R`: `C(R, n)`.
  - Max unique col-sets of size `m` from `R`: `C(R, m)`.
  - Required unique counts:

    - If `row_sets` in scope: need `T * m` unique row-sets.
    - If `col_sets` in scope: need `T * n` unique col-sets.

  - The generator validates these bounds and explains infeasible configurations
    clearly.

## 4) Generation Workflow

### Step 1 — Global frequency layout

- Build a multiset of numbers according to `uniformity` (strict or near).
- If `position_balance=true`, aim for approximate per-position balancing (soft).

### Step 2 — Card construction

- Try **BIBD-like strategy** (`bbd_mode=auto`) when parameters permit.
- Otherwise, use a **heuristic fill**:

  - Fill cards position by position, respecting:

    - available global frequencies,
    - no duplicates within a card,
    - no row/column-set collisions globally per `unique_scope`.

  - If stuck, perform **local swaps** (across positions/cards).
  - Respect `build_timeout_sec` and `swap_iterations`. On timeout:

    - either fail with an actionable error, or
    - emit a best-effort result **only if** `--allow-best-effort` was explicitly
      set (off by default), tagging all unmet constraints in the report.

### Step 3 — Final verification (independent pass)

Check and assert all active constraints:

- No duplicates within any card.
- If `row_sets`/`col_sets` selected: no repeats globally.
- `uniformity` met (`strict` or ≤1 spread for `near`).
- **No identical cards** across the run (safety check, though implied by row/col
  uniqueness).

## 5) Outputs

### 5.1 `cards.json`

```json
{
  "run_meta": {
    "version": "1.0.0",
    "timestamp": "2025-08-22T10:00:00Z",
    "params_hash": "sha256:...",
    "seed": 20250824,
    "engine": "py_random"
  },
  "cards": [
    {
      "id": "1",                 // "uuid" or sequential number as string
      "matrix": [[12,35,7,64],[...],[...]]
    }
  ]
}
```

### 5.2 `report.json`

```json
{
  "frequencies": { "1": 2, "2": 2, "...": "..." },
  "position_frequencies": { "(0,0)": {"1":0, "2":1, ...}, "...": "..." },
  "uniqueness": {
    "row_sets_checked": true,
    "col_sets_checked": true,
    "row_set_collisions": 0,
    "col_set_collisions": 0
  },
  "uniformity": {
    "mode": "strict",
    "max_minus_min": 0
  },
  "tests": {
    "chi2_global": { "stat": 12.34, "df": 74, "p_value": 0.999 },
    "chi2_by_column": [ /* one entry per column */ ],
    "chi2_by_row": [ /* one entry per row */ ]
  },
  "warnings": [],
  "notes": "All constraints satisfied."
}
```

### 5.3 Optional `summary.csv`

- Flat table aggregating total frequency per number and (optionally) by
  position.

## 6) Logging, Colors, and UX

### Colors (ANSI; auto-detect TTY; support `NO_COLOR`)

- **INFO**: blue
- **SUCCESS**: green
- **WARNING**: yellow
- **ERROR**: red
- **DEBUG**: dim/cyan Flags:
- `--colors auto|always|never`
- Environment: `NO_COLOR` disables colors.

### Logging

- Console + file logging.
- `--log-level DEBUG|INFO|WARN|ERROR`
- `--log-format text|json`
- Rotating logs (size & backups configurable).
- Every run logs: config echo, `params_hash`, chosen seed/engine, timing,
  outcome, and a short summary of constraints satisfied/failed.

## 7) Exit Codes

- `0` — success; all constraints satisfied.
- `2` — invalid configuration (feasibility pre-check failed).
- `3` — construction failed within timeout/iterations.
- `4` — verification failed (post-check found violations).
- `5` — I/O or serialization error.

## 8) Minimal Seed Procedure (extensible)

- **Mode**: `integer`.
- **Value**: user-provided integer (CLI/config; prompt if missing).
- **Engine**: default `py_random` (Python’s MT19937). Optional `numpy_pcg64` if
  available.
- **Future-proofing**: design allows later upgrade to multi-party commit-reveal
  without breaking the current interface (e.g.,
  `seed: { mode: "commit_reveal", ... }`).

## 9) Constraint Coherence & Non-duplication

- If `row_sets` **or** `col_sets` uniqueness is enforced, identical cards are
  **implicitly** impossible. The generator still enforces “no identical cards”
  explicitly as a safety invariant.
- “No duplicates on a card” is independent and always enforced.
- If feasibility bounds are tight (`C(R,n)` or `C(R,m)` near the requirement),
  the generator may need more iterations; consider relaxing `position_balance`
  first.

## 10) Examples

### 10.1 Minimal config (YAML)

```yaml
R: 75
T: 150
m: 3
n: 4
unique_scope: [row_sets, col_sets]
uniformity: strict
seed: { mode: integer, value: 20250824, engine: py_random }
card_id_mode: sequential
card_number_start: 1
bbd_mode: auto
colors: auto
log_level: INFO
out_cards: cards.json
out_report: report.json
```

### 10.2 Run with interactive prompts

```bash
bingo-gen --config missing.yaml
# Prompts will ask for any missing fields with colored hints and validation.
```

## 11) Tests & Verification

- Built-in verifier reruns all checks on produced artifacts
  (`--verify-only cards.json --report report.json`).
- Property checks (dev): determinism given the same seed; invariants for
  duplicates & uniqueness; uniformity bounds.

## 12) Performance Notes

- Complexity scales with `T`, `m*n`, and strictness of uniqueness.
- For large `T` with both `row_sets` and `col_sets` uniqueness, expect more swap
  iterations.
- Tune `swap_iterations`, `build_timeout_sec`. If needed, disable
  `position_balance` to ease construction.

---

## Reasoning & Design Notes

1. **Why “set without order” for row/column combinations?** It matches the
   fairness intent (no pattern advantage from ordering) and simplifies
   uniqueness capacity: combinations are counted via `C(R, k)`.

2. **Uniformity vs. feasibility:** Strict uniformity is ideal but only feasible
   when `P % R == 0`. The `near` mode guarantees an at-most-1 spread, which is
   both fair and mathematically tight.

3. **Implied uniqueness of cards:** If any of `row_sets`/`col_sets` uniqueness
   is enforced globally, two identical cards would necessarily repeat all their
   sets, so card duplication is already impossible. We keep the explicit check
   to defend against implementation mistakes.

4. **BIBD first, heuristic second:** BIBD-like structures (when they exist)
   maximize balance and minimize collisions. When parameters don’t fit known
   designs, a greedy+swap heuristic is practical and explainable.

5. **Position balance as a soft constraint:** Prevents “favorite columns/rows”.
   It’s soft to avoid dead-ends under tight uniqueness constraints.

6. **Minimal seed today, extensible tomorrow:** A simple integer seed is
   transparent and easy to communicate. The config structure anticipates future
   multi-party/commit-reveal schemes without breaking backward compatibility.

7. **Colored UX & logging:** Colors improve operator feedback; `NO_COLOR` and
   `--colors` ensure accessibility. Logs are structured (optionally JSON) for
   audit and post-mortems; they record `params_hash` to bind outputs to inputs.

8. **Determinism & reproducibility:** Same config + same seed ⇒ identical
   outputs. Changing only the engine (e.g., PCG64) changes the stream but keeps
   the invariant: same seed → same result **under that engine**.

9. **Tight bounds guidance:** If `T*m` approaches `C(R,n)` or `T*n` approaches
   `C(R,m)`, minor tweaks (increase `R`, relax uniqueness scope, or turn off
   position balance) drastically improve constructability.
