# Vitalis — protocol-driven clinical decision-support engine (prototype)

A physician-facing tool: enter a patient's basic details, risk factors, symptoms
(multi-select — it's never just one chief complaint), ECG and optional vitals.
**Symptoms in, differential out**: the system raises a tiered list of
possibilities (must-not-miss / consider / common) with a discriminator per
item, the clinician excludes what history and exam rule out, and the
surviving possibilities decide which confirmatory modules open — the module
router is an *output* of the differential, never the doctor's first choice.
From there: adaptive follow-up questions branching on everything answered so
far, a routing recommendation (never a diagnosis), potentiating-factor and
drug-proposal blocks, an optional AI-generated second opinion, and a place
for the doctor to record their own.

**Why symptoms-first, not module-first:** an earlier version asked the
clinician to name a suspected condition before asking anything else — that's
verification, not diagnosis, and it structurally cannot surface a
possibility the doctor didn't already have in mind. The concrete failure
case: a diabetic presenting with *only* exertional breathlessness (no chest
pain) needs Stable Angina considered — Track B ischaemic-equivalent
presentations are exactly how ischaemia gets caught in diabetics, women, and
the elderly — but a single-select "what's the primary symptom" router has no
slot for that unless the doctor already suspected cardiac disease. The
differential engine raises stable angina off the breathlessness symptom
alone, every time, regardless of what the doctor was thinking going in. See
[`docs/protocol_schema.md`](docs/protocol_schema.md) and
`backend/app/differential_table.json` for the full symptom → differential
mapping.

This is the **backend engine** plus a **generic demo web frontend**. The real
frontend will eventually be a React Native / Expo mobile app; the API is a
plain bearer-token REST/JSON service with no browser-specific assumptions, so
that app can be built against it later without backend changes.

## Architecture: three layers, two built

**Part 1 — Disease module engine(s).** Each disease is a self-contained
protocol JSON: gate → parallel evidence tracks → resolve → potentiating
factors → drug proposals, all interpreted by one generic rules engine
(`backend/app/engine/`) that has zero disease-specific code in it. Adding a
disease means authoring a new protocol file, not touching the engine. See
[`docs/protocol_schema.md`](docs/protocol_schema.md) for the block-by-block
schema.

**Part 2 — Shared intake layer.** Facility tier, patient core (15 risk-factor
fields, split where two consumers want different answers — `htn_dx` vs
`htn_uncontrolled`, `stroke` vs `tia_only`, `ckd` vs `hepatic` — see
`backend/app/shared_fields.py`), symptoms, ECG, and vitals are collected once
(`backend/app/core_intake.*`) and read by every module. The differential
engine (`backend/app/differential_engine.py`) sits at the end of this layer:
it turns the symptom set into a tiered possibility list, and its survivors —
plus one ECG override (AF forces on a confirmed rhythm; Angina is suggested
on ischaemic ECG findings) — are what each protocol's `activation.offer_trigger`
/ `auto_trigger` actually reads.

**Part 3 — Cross-module reconciliation — explicitly out of scope for this
build.** The source architecture also calls for merging duplicate drug
recommendations across simultaneously-active modules, unioning interlocks
into one patient-level BLOCK/CAUTION/clear matrix, and a single unified
output. None of that is built here — each module's drug proposals and
interlocks are entirely self-contained to that module. This is the part of
the source architecture that gets harder with every additional disease
(every new module can interact with every existing one), and deserves its
own pass once several self-contained modules exist to reconcile.

## Three protocols ship today

- **`angina_stable_v1`** — Stable Angina, fully specified from the ICMR
  Standard Treatment Workflow: a blocking ACS-exit gate, two evidence tracks
  running in parallel at equal visual weight, tri-state unknowns (a skipped
  or "not tried" answer is never silently treated as negative), a
  terminal-resolution table that outputs a routing statement (never a
  diagnosis label), potentiating factors, and a full drug-proposal block
  (secondary prevention / anti-ischemic / hazard-group / tertiary-only,
  medication gated on which terminal it resolved to, six prescribing
  interlocks, ticagrelor quarantined rather than silently resolved).
- **`af_placeholder_v1`** — Atrial Fibrillation, an honestly-labeled
  **reduced-fidelity placeholder** for its risk-scoring (T1/T2 report plain
  factor counts, explicitly *not* the validated CHA₂DS₂-VASc / HAS-BLED
  scores — no field-level AF spec existed in the source repo). Its
  valve-assessment subtree (T1a), however, *is* fully real — shared verbatim
  with RHD's, so an unknown echo status genuinely blocks the anticoagulation
  decision rather than defaulting silently.
- **`rhd_v1`** — Rheumatic Heart Disease: presentation router (acute
  rheumatic fever vs. established valve disease), the Revised Jones Criteria
  2015 at high-risk-population thresholds (chorea alone / 2 major / 1 major +
  2 minor / recurrent + 3 minor, streptococcal evidence flagged-not-blocked),
  a shared valve → anticoagulant decision table (echo status → mitral
  stenosis grading → prosthetic valve type → DOAC/VKA/blocked), aetiology,
  secondary-prophylaxis drug block, and a prophylaxis-duration decision
  table. No current ICMR workflow exists for chronic RHD, so this module is
  labeled a Vitalis addition throughout rather than a digitized government
  pathway.

One real cross-module link exists (deliberately, as the one concrete case
the source gives precisely enough to encode safely): AF's rhythm-control
substrate can pre-fill from Angina's Track A resolution when both have run —
a plain data-level reference, always overridable, not a special case in code.

## Running it

Two terminals — backend and frontend are separate processes, both need to be
running at once.

### Terminal 1 — backend

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

`uv run` installs/syncs dependencies automatically on first run (no separate
`uv venv` / `uv pip install` step needed). `--reload` matters — without it,
uvicorn won't pick up code changes and you'll be debugging a stale server
that's silently running old code.

Runs on SQLite (`backend/vitalis.db`, created automatically on first start).
No external DB needed for this prototype, and no migrations — if you pull a
schema change and see column-mismatch errors, delete `vitalis.db` and restart
to let it recreate. It's demo data only.

### Terminal 2 — frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

Then open `http://localhost:5173` — that's the demo UI, talking to the
backend at `http://localhost:8000` by default (override with `VITE_API_BASE`
— see `.env.example`).

### Running the tests

```bash
cd backend && uv run pytest -q
```

Covers the expression DSL including short-circuit determinability, full
table-driven engine coverage of every Angina skip rule and drug interlock,
AF's checklist/threshold/single-choice/decision-table track modes, RHD's
Jones-criteria patterns and valve decision table, the differential engine
against every documented symptom presentation, and HTTP integration tests
walking complete encounters — including the diabetic exertional-breathlessness
case the whole v0.4 rewrite exists for.

### AI second opinion (optional)

Unset by default — the tool works normally without it; the result page shows
"Not configured on this deployment." To enable, set an xAI (Grok) API key
before starting the backend:

```bash
export XAI_API_KEY=your-key-here
```

AI output is always shown with a persistent disclaimer and is never fed back
into the engine. It is architected as a pluggable provider
(`backend/app/ai/`) — swapping providers doesn't touch the rest of the app.

## Adding a disease

1. Write `backend/protocols/<new_id>.json` following
   [`docs/protocol_schema.md`](docs/protocol_schema.md).
2. Restart the backend. `app/engine/protocol_loader.py` validates and loads
   every file in `protocols/` at startup — a malformed file fails loudly at
   boot, not mid-encounter.
3. Nothing else changes. The frontend renders whatever `field_type`s, track
   groups, and drug blocks the new protocol declares; the engine's
   block-walk algorithm (`app/engine/evaluator.py`) is entirely
   protocol-agnostic.

## What's deliberately out of scope for this build

Part 3 (cross-module reconciliation — see above). No user accounts
(bearer-token-per-encounter only). No production database, migrations, or
deployment config — this is a prototype.

---
Not for clinical use.
