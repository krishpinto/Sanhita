# Protocol schema

A protocol (`backend/protocols/*.json`) is a `ProtocolDefinition`
(`backend/app/models_protocol.py`): metadata, an activation rule, and an
ordered list of `blocks`. The engine (`backend/app/engine/evaluator.py`)
walks `blocks` in order; nothing in that file ever names a specific disease
or field.

## Top level

```jsonc
{
  "id": "your_protocol_v1",              // must match the filename stem
  "name": "Human-readable name",
  "version": "1.0",
  "source_citation": "Where this came from",
  "fidelity": "full" | "reduced_fidelity_placeholder",
  "fidelity_note": "Shown on every screen if not full fidelity",
  "activation": {
    "mode": "auto" | "offer",
    "trigger": <expr>                    // evaluated against core.* once intake is complete
  },
  "blocks": [ ... ]
}
```

`"auto"` activates the moment its trigger is true, no consent asked (use
when a single objective finding proves the diagnosis, e.g. AF's ECG rhythm).
`"offer"` surfaces the module and waits for `POST .../activate-protocol/{id}`
(use when activating means a long questionnaire and the trigger is only a
hypothesis, e.g. a symptom).

## The expression DSL

Every `when`/`skip_when`/`condition`/`fire_when`/`applicable_when` is a node
in the tiny DSL implemented in `app/engine/expr.py`:

```jsonc
{"var": "core.primary_symptom"}                    // dotted-path lookup
{"==": [a, b]}  {"!=": [a, b]}
{"in": [a, b]}                                      // a in b
{">": [a, b]}  {"<": [a, b]}  {">=": [a, b]}  {"<=": [a, b]}
{"and": [expr, ...]}  {"or": [expr, ...]}  {"not": [expr]}
{"count_true": [expr, ...]}                          // -> integer count
```

Any other JSON value is a literal. Determinability is short-circuit-aware:
`{"or": [{"==": [{"var": "echo_status"}, "not_performed"]}, {"var": "ms_severity"}]}`
is decidable the moment `echo_status` is `"not_performed"`, even if
`ms_severity` doesn't exist in the namespace yet (because it was itself
skipped and will never be answered).

## Field addressing

Every answerable field has a fully-qualified path, and that path is exactly
what `{"var": ...}` references and what `POST .../answer` takes as
`field_path`:

- Core intake: `core.<field_id>` (e.g. `core.primary_symptom`, `core.ecg`)
- Shared clinical history: `shared.<shared_path>` (e.g. `shared.hypertension`)
- A gate/context/derived-tags/drug block's own field: `protocols.<id>.<block_id>.<field_id>`
- A track's field: `protocols.<id>.tracks.<track_id>.<field_id>` (note the
  fixed `tracks` segment — decoupled from the track_group block's own id, so
  multiple track_group blocks can coexist without path collisions)
- A track's computed resolution: `protocols.<id>.tracks.<track_id>.resolution`
- A terminal_table's resolved code: `protocols.<id>.<block_id>.code`

## Block types

**`gate`** — blocking. All `fields` must be answered before `fire_when` is
evaluated. If true, the protocol terminates immediately with `terminal_code`/
`terminal_headline` — nothing after it runs, not even a later drug block.
Use for hard exits (ACS suspected, AF not confirmed).

**`track_group`** — one or more `tracks`, evaluated in parallel and rendered
at equal visual weight (never a fallback of each other). Each track has a
`mode`:

| mode | use for | resolution |
|---|---|---|
| `axis_count` | classical N-of-M feature axes | count of `value_scoring: positive` fields against a `resolution_rule.thresholds` table |
| `any_true` | "any one of these present" | `"positive"` / `"negative"` |
| `checklist_score` | a plain factor count (never a validated weighted score) | `"N of M factors present"` |
| `numeric_thresholds` | one recorded number, several bands | first matching `numeric_thresholds` row's `label` |
| `single_choice` | one categorical field, optionally prefilled from elsewhere | the field's own answered value |
| `decision_table` | a multi-field decision (rows may reference `shared.*` directly, not just this track's own `fields`) | first matching `decision_rows` row's `label` |

A field's `skip_when` is evaluated once every variable it references is
itself resolved; an unresolvable `skip_when` leaves the field pending
(neither asked nor skipped) rather than guessing. Skipped fields are excluded
from scoring and always listed as "not assessed" — never silently absent.
`display_fields` are collected the same way but never scored (e.g. Angina's
radiation, RHD's aortic-stenosis flag).

**`derived_tags`** — booleans computed from already-known fields (e.g.
Angina's negative features N1–N6, RHD's referral flag). Never a source of
questions; recomputed from scratch every read.

**`context`** — a set of fields that are answered but never scored.
`render_hint: "flag_positive"` (potentiating factors: only true answers are
worth surfacing) vs `"plain"` (risk context: show every value).

**`terminal_table`** — first matching `rows` entry (checked in order) sets
the protocol's terminal `code`/`headline` **and continues the walk** (unlike
a gate) so later blocks — typically a `drug_recommendation` — can reference
`protocols.<id>.<block_id>.code`. Only once every block after it also
completes does the protocol report `status: "resolved"`.

**`drug_recommendation`** — never contributes a frontier field; purely
computed display. Each `entries[]` item:

- `tiers`: which `core.facility_tier` values show it (absence is stated as a
  count, e.g. "3 items not shown at the current facility tier" — never
  silent).
- `applicable_when`: hide the entry entirely if false (e.g. gated on which
  terminal the protocol resolved to) — this is a routing filter, distinct
  from a contraindication.
- `interlocks[]`: each `{condition, state: "block"|"caution", reason,
  vitalis_addition}`. Any matching `"block"` wins over any `"caution"`.
  Blocked entries are **struck through with the reason shown, never
  removed from the list** — a shortened list is indistinguishable from a
  source that never listed the drug.
- `quarantine_reason`: set when the source is ambiguous about an item (e.g.
  a dosing regimen that belongs to a different clinical context) — always
  rendered in its own withheld section with the reason, never silently
  resolved either way.

## Cross-protocol reuse

Two mechanisms, both scoped deliberately narrow (full cross-module
reconciliation — drug dedup across active protocols, a unified interlock
matrix — is an explicit non-goal of this build):

- **Shared fields** (`source: "shared"`, `shared_path: "..."`): a field
  answered once is visible to every protocol that declares the same
  `shared_path`. Each protocol still declares its own local `FieldDef`
  (label, options, `skip_when`) — there's no cross-protocol field-definition
  merging, so keep `skip_when` identical across protocols that share a field
  (see `echo_status`/`mitral_stenosis_severity`/`prosthetic_valve` in both
  `af_placeholder_v1.json` and `rhd_v1.json` for the canonical version).
- **Prefill**: a field can suggest a starting value from anywhere in the
  namespace (`{"source_path": ..., "value_map": {...}, "default": ...}`) —
  always just a hint the frontend shows; the doctor still submits an
  explicit answer.

## Adding a protocol

1. Write `backend/protocols/<id>.json` using the blocks above.
2. Restart the backend — `app/engine/protocol_loader.py` validates every file
   in `protocols/` at startup and fails loudly on a schema error, not
   mid-encounter.
3. Nothing else changes. The frontend's `StepRenderer` switches purely on
   `field_type`; it has no protocol-specific code to update.
