# Bingo/Tombola Card Generator — Simple, Audit‑Friendly Spec

## What this tool does

Deterministic generator of Bingo/Tombola cards that is easy to run, verify, and
audit. Focus: a minimal, robust contract that is simple to implement now and
extensible later.

## Minimal scope (always on)

- Numbers are drawn from `1..R`.
- Card is an `m×n` matrix with no duplicates within a card.
- Uniformity of global frequencies:
  - `strict` if `(T*m*n) % R == 0` (all numbers appear equally often), otherwise
  - `near` (difference between max and min frequency ≤ 1).
- All cards are different by full `m×n` content.

## Recommended extras (enable via config)

- `unique_scope: [row_sets]` — forbid repeated row‑sets across all cards (treat
  rows as sets).
- `unique_scope: [row_sets, col_sets]` — also forbid repeated column‑sets.
- `position_balance: true` — softly equalize per‑position usage to reduce bias.

These improve variety and perceived fairness but are not required for the
minimal contract.

## Quick start

```yaml
# config.yaml (minimal)
R: 75
T: 150
m: 3
n: 4
uniformity: strict # falls back to near if not divisible
unique_scope: [row_sets] # safer & simpler default
seed: { mode: integer, value: 20250824, engine: py_random }
```

```bash
# Run
bingo-gen run --config config.yaml --out-cards cards.json --out-report report.json

# Dry-run (only checks & plan)
bingo-gen run --config config.yaml --dry-run

# Verify artifacts
bingo-gen verify --cards cards.json --report report.json --strict
```

## Feasibility guardrails (pre‑checks)

Let `P = T*m*n`.

- Duplicates avoidance: require `R ≥ m*n`.
- Uniformity:
  - strict requires `P % R == 0`;
  - near targets `⌊P/R⌋` or `⌈P/R⌉` per number.
- Uniqueness capacity (if enabled):
  - rows: `T*m ≤ C(R, n)`; columns: `T*n ≤ C(R, m)`.

Errors explain which bound fails and how to fix (increase `R`, relax uniqueness,
or switch to `near`).

## Build strategy (simple & reproducible)

Heuristic fill with local swaps under global frequency quotas:

- Respect remaining global frequencies and “no duplicates in a card”.
- Avoid row/column‑set collisions when `unique_scope` is set (hash sets).
- Keep runs deterministic via a fixed `seed` and stable tie‑breaking.

## Outputs (machine‑readable)

- `cards.json` — cards list plus `run_meta` (version, `params_hash`, seed,
  engine) and hashes.
- `report.json` — frequencies, uniformity summary, uniqueness summary (if
  checked), basic build metrics.

`params_hash` binds outputs to inputs for audit.

## Verification

`bingo-gen verify` re‑checks: no duplicates per card, card uniqueness,
uniformity (strict/near), and row/column‑set uniqueness if requested.

## Safe defaults (suggested)

- `uniformity: strict` (auto‑fallback to near)
- `unique_scope: [row_sets]`
- `position_balance: false` (enable when you want gentler per‑position spread)
- `card_id_mode: sequential`, `seed.engine: py_random`

These defaults minimize complexity while preserving fairness and auditability.

## Performance & determinism

- Time grows with `T`, `m*n`, and strictness of uniqueness.
- Determinism: same config + same seed ⇒ identical outputs (single‑threaded).
- Parallel mode can change outputs due to scheduling; prefer single‑thread for
  audits.

## Why this is simpler yet reliable

- Minimal constraints (no duplicates, card uniqueness, strict/near uniformity)
  are sufficient for fairness in common bingo play.
- Optional row/column‑set uniqueness and position balancing can be enabled when
  variety matters more than ease of construction.
- Deterministic seed, explicit `params_hash`, and JSON artifacts provide a
  strong audit trail.

## Further simplifications (optional)

- Drop `col_sets` from `unique_scope` — keep only `row_sets` for simpler builds.
- Disable `position_balance` — reduces search pressure under tight bounds.
- Use `near` uniformity when `(T*m*n) % R != 0` instead of forcing strict.
- Prefer `card_id_mode: sequential` and `seed.engine: py_random` for clarity.

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

Subcommands:

- `bingo-gen run` — construct cards and reports
- `bingo-gen verify` — verify produced artifacts

Examples:

```bash
# Run with config file (interactive prompts for missing fields)
bingo-gen run \
  --config config.yaml \
  --out-cards cards.json \
  --out-report report.json \
  --log-file run.log \
  --colors auto \
  --log-level INFO

# Dry-run (plan): resolve parameters, print feasibility, no construction
bingo-gen run --config config.yaml --dry-run

# Verify artifacts (optionally verify params_hash contract)
bingo-gen verify --cards cards.json --report report.json --params params.json --strict
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

# ---- Build controls ----
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

# ---- Statistics ----
stats_engine: "wilson_hilferty" # "wilson_hilferty" (default) | "scipy"

# ---- Termination & best-effort ----
allow_best_effort: false # if true, may emit partial result with violations
best_effort_zero: false # if true and violations present, exit code may be 0

# ---- Performance ----
parallel: false # non-deterministic across processes; see notes
parallelism: 1
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

### 3.4 Parameter Resolution & Environment Variables

- Precedence: CLI > ENV > config file > built-in defaults.
- Environment variables use the `BINGO_GEN_` prefix and map to config keys by
  upper-casing and replacing dots with underscores, e.g. `BINGO_GEN_R=75`,
  `BINGO_GEN_UNIQUE_SCOPE=row_sets,col_sets`, `BINGO_GEN_LOG_LEVEL=INFO`.
- Booleans accept `true/false/1/0/yes/no`. Lists accept comma-separated values.

### 3.5 Path Policy & I/O Behavior

- Paths provided in a config file are resolved relative to that config file’s
  directory. Paths provided via CLI flags are resolved relative to the current
  working directory (CWD).
- Output behavior:
  - No overwrite by default. Use `--force` to overwrite existing files.
  - Parent directories are auto-created. Use `--no-mkdirs` to disable.
  - Optional `--out-dir` can be used with default filenames.

### 3.6 Params Hash Contract

`params_hash` is a `sha256` over a canonical JSON representation (sorted keys,
no insignificant fields) of the subset of resolved parameters that strictly
influence construction results. Unless explicitly stated otherwise, file paths
and log settings are excluded.

Included fields (contract):

- `R`, `T`, `m`, `n`
- `unique_scope` (normalized: de-duplicated and sorted list)
- `uniformity`, `position_balance`
- `seed.value`, `seed.engine`
- `build_timeout_sec`, `swap_iterations`
- `parallel` (if enabled) and `parallelism` value
- `allow_best_effort` (affects termination criteria)

Excluded (do not affect combinatorial output):

- Output/input file paths, log file, log level/format, color settings

Notes:

- The canonical JSON uses stable key ordering and standard number formatting.
- The exact contract is versioned; any change will bump `run_meta.app_version`.

## 4) Generation Workflow

### Step 1 — Global frequency layout

- Build a multiset of numbers according to `uniformity` (strict or near).
- If `position_balance=true`, aim for approximate per-position balancing (soft).

### Step 2 — Card construction

- Use a **heuristic fill with local swaps**:

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
    "app_version": "1.0.0",
    "timestamp": "2025-08-22T10:00:00Z",
    "python_version": "3.11.9",
    "platform": "linux-x86_64",
    "git_commit": "abc1234",      // optional if available
    "run_id": "4e0c7d2e-...",
    "params_hash": "sha256:...",  // over resolved params per contract
    "seed": 20250824,
    "rng_engine": "py_random",     // or "numpy_pcg64"
    "hash_algorithm": "sha256",
    "parallel": false,
    "parallelism": 1
  },
  "cards": [
    {
      "id": "1",                          // "uuid" or sequential number as string
      "matrix": [[12,35,7,64],[...],[...]],
      "matrix_hash": "sha256:..."          // hash of canonical JSON of matrix
    }
  ],
  "cards_hash": "sha256:..."
}
```

### 5.2 `report.json`

```json
{
  "frequencies": { "1": 2, "2": 2, "...": "..." },
  "position_frequencies": {
    "(0,0)": { "1": 0, "2": 1, "...": 0 },
    "...": "..."
  },
  "uniqueness": {
    "row_sets_checked": true,
    "col_sets_checked": true,
    "row_set_collisions": 0,
    "col_set_collisions": 0,
    "set_representation": "sorted_tuple" // JSON emits sets as sorted tuples
  },
  "uniformity": {
    "mode": "strict",
    "max_minus_min": 0
  },
  "tests": {
    "alpha": 0.05,
    "engine": "wilson_hilferty", // allowed: "wilson_hilferty" | "scipy"
    "chi2_global": { "stat": 12.34, "df": 74, "p_value": 0.999 },
    "chi2_by_column": [
      /* one entry per column */
    ],
    "chi2_by_row": [
      /* one entry per row */
    ]
  },
  "build_metrics": {
    "swaps": 12345,
    "iterations": 20000,
    "timeouts_triggered": false,
    "cards_rebuilt": 12,
    "collisions_resolved": 87,
    "elapsed_sec": 42.5
  },
  "best_effort": false,
  "warnings": [],
  "notes": "All constraints satisfied."
}
```

### 5.3 Serialization Conventions

- Row/column combinations are conceptually sets; for JSON compatibility they are
  serialized as sorted tuples (ascending order) wherever included (e.g., in
  collision diagnostics). This ensures stable ordering, Schema compatibility,
  and reproducibility.
- Internal fast lookups use `frozenset` hashed containers; report does not dump
  the full uniqueness index by default to keep size manageable.

### 5.4 Optional `summary.csv`

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

Security note:

- The tool does not execute arbitrary code from configuration files; only data
  is parsed (YAML/JSON). No template rendering or dynamic evaluation occurs.

## 7) Exit Codes

- `0` — success; all constraints satisfied.
- `2` — invalid configuration (feasibility pre-check failed).
- `3` — construction failed within timeout/iterations or best-effort emitted
  with violations.
- `4` — verification failed (post-check found violations).
- `5` — I/O or serialization error.

Notes on best-effort:

- If `--allow-best-effort` is set and violations remain, exit code defaults to
  `3` while emitting artifacts with `"best_effort": true` in `report.json`.
- If `--best-effort-zero` is additionally set, exit code may be `0` despite
  violations; CI users should rely on `report.json.best_effort` for gating.

## 8) Minimal Seed Procedure (extensible)

- **Mode**: `integer`.
- **Value**: user-provided integer (CLI/config; prompt if missing).
- **Engine**: default `py_random` (Python’s MT19937). Optional `numpy_pcg64` if
  available.
- **Future-proofing**: design allows later upgrade to multi-party commit-reveal
  without breaking the current interface (e.g.,
  `seed: { mode: "commit_reveal", ... }`).

### 8.1 Parallel seed scheme (non-deterministic warning)

- When `--parallel` is enabled, per-card seeds may be derived as
  `seed_i = sha256(run_seed || card_index || "build")` to reduce inter-card
  correlations.
- Despite per-card seeding, final outputs may still differ between runs due to
  scheduling and non-deterministic swap ordering. For audit-critical runs,
  prefer single-threaded mode.

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
colors: auto
log_level: INFO
out_cards: cards.json
out_report: report.json
```

### 10.2 Run with interactive prompts

````bash
bingo-gen run --config missing.yaml
# Prompts will ask for any missing fields with colored hints and validation.

### 10.3 Verify-only example

```bash
# Verify artifacts strictly (fail on any deviation)
bingo-gen verify --cards cards.json --report report.json --strict

# Verify and also check params contract against a saved params.json
bingo-gen verify --cards cards.json --report report.json --params params.json --strict
````

## 11) Tests & Verification

- Built-in verifier reruns all checks on produced artifacts via the `verify`
  subcommand (see CLI examples).
- Property checks (dev): determinism given the same seed; invariants for
  duplicates & uniqueness; uniformity bounds.

### 11.1 JSON Schemas

- Provide JSON Schemas for `cards.json` and `report.json` under
  `docs/schemas/cards.schema.json` and `docs/schemas/report.schema.json`.
- Schemas specify required/optional fields, types, and enums (`tests.engine`).
- `bingo-gen verify --report-only` may validate only `report.json` against the
  schema without recomputing checks.

## 12) Performance Notes

- Complexity scales with `T`, `m*n`, and strictness of uniqueness.
- For large `T` with both `row_sets` and `col_sets` uniqueness, expect more swap
  iterations.
- Tune `swap_iterations`, `build_timeout_sec`. If needed, disable
  `position_balance` to ease construction.
- Parallel mode (`--parallel`) may improve throughput but is not guaranteed to
  be bit-deterministic across runs/platforms due to scheduling effects; use with
  caution for audit-critical scenarios.

---

## Versioning Policy

- Semantic Versioning (SemVer) is used for `app_version`.
- Breaking changes include (non-exhaustive):
  - Changes to the `params_hash` contract or its included fields
  - Backward-incompatible updates to JSON Schemas of `cards.json` or
    `report.json`
  - Change of default RNG engine
- Contract updates result in a new major version; minor versions may add fields
  that are explicitly optional in Schemas.

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

4. **Single algorithm policy:** The generator uses one heuristic algorithm with
   local swaps. This keeps the system simpler to reason about, easier to audit,
   and deterministic under a fixed seed.

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
