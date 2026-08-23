# Understanding this codebase

Read this before touching anything. It is a map, not a tutorial.

---

## 1. Run it

Two processes. Both must be running. Two terminals.

**Terminal 1 — the engine (Python):**

```bash
cd C:/projects/medicalstartup/sanhita/engine/backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — the demo web UI:**

```bash
cd C:/projects/medicalstartup/sanhita/engine/frontend
npm run dev
```

Then open <http://localhost:5173>.

Notes that will save you an hour:

- The README also gives `uv run uvicorn ...`. **`uv` is not installed on this
  machine** — use the `.venv/Scripts/python.exe` form above. Both work
  elsewhere; only one works here.
- Port 5173 is not optional. The backend's CORS allow-list names it exactly
  (`backend/app/config.py`). On any other port the browser blocks every call.
- `--reload` matters. Without it uvicorn keeps running your old code and you
  debug a ghost.
- The database is `backend/vitalis.db`, SQLite, created on first start. There
  are no migrations. If you pull a schema change and see column errors, delete
  the file and restart. It is demo data only.

**Without a browser** — three scripted consultations, printed as a transcript:

```bash
cd C:/projects/medicalstartup/sanhita/engine/backend && .venv/Scripts/python.exe demo_consultation.py
```

**Tests** (117 of them):

```bash
cd C:/projects/medicalstartup/sanhita/engine/backend && .venv/Scripts/python.exe -m pytest -q
```

---

## 2. The one idea everything else follows from

**Clinical content is data. The engine is code that knows no medicine.**

A disease lives in a JSON file. The Python never mentions angina. Adding a
disease means writing a new JSON file — not editing the engine.

If you ever find yourself writing `if disease == "angina"` in Python, stop.
That is the mistake this whole design exists to prevent.

---

## 3. Two layers

**Layer 1 — narrowing.** Open world. Takes the symptom set, raises a tiered
list of possibilities, and lets findings eliminate them. It is allowed to say
"I don't cover this." It is *not* a tree.

**Layer 2 — the protocol.** Closed world. Once Layer 1 has decided which
disease modules are worth opening, each module runs a deterministic ICMR
decision tree to a named endpoint. This is the only part that is a tree.

The system routes to a protocol. It never diagnoses. That distinction is
regulatory, not stylistic — it is what keeps this in the low-risk CDSCO class.

---

## 4. Where things live

```
engine/
├── backend/          Python. The engine. All the real logic.
│   ├── app/
│   │   ├── engine/           ← generic rules engine, ZERO medical knowledge
│   │   ├── protocols/        ← the diseases, as JSON data
│   │   ├── routers/          ← the HTTP endpoints
│   │   ├── ai/               ← optional second opinion (off unless a key is set)
│   │   └── *.py              ← intake, differential, orchestration
│   └── tests/                ← 162 tests
└── frontend/         React. A thin demo client. No clinical logic at all.
```

### The files that matter, biggest first

| File | Lines | What it is |
|---|---|---|
| `app/engine_service.py` | 487 | **The orchestrator.** Works out the next question, applies answers, serializes responses. Start here. |
| `app/engine/evaluator.py` | 468 | **The rules engine.** Walks a protocol's blocks. Knows no diseases. |
| `app/differential_table.json` | 423 | **The differential, as data.** 16 possibilities, 10 findings, the links between them. |
| `app/differential_engine.py` | 362 | **Layer 1.** Symptoms in, tiered differential out; applies the four safety rules. |
| `app/models_protocol.py` | 285 | The protocol schema, as pydantic models. What a valid protocol JSON may contain. |
| `app/engine/expr.py` | 177 | A tiny expression language used inside protocol JSON (`skip_when` and friends). |
| `app/core_intake.json` | 144 | The shared intake questions — facility, patient, risk factors, symptoms, ECG, vitals. |

### The diseases

| File | Lines | State |
|---|---|---|
| `protocols/angina_stable_v1.json` | 466 | Full fidelity. The reference implementation. |
| `protocols/rhd_v1.json` | 346 | Full fidelity. |
| `protocols/af_placeholder_v1.json` | 197 | **Reduced-fidelity placeholder.** Declares no drug block at all. Known gap. |

---

## 5. What actually happens when a doctor taps a button

This is the loop. Everything is this loop.

```
1. Browser POSTs the answer
      POST /encounters/{id}/answer   { field_path, value }

2. app/routers/answers.py  ->  engine_service.submit_answer()
      Rejects the answer if that field is not currently askable.
      Otherwise writes it to SQLite.

3. engine_service.compute_next_step()
      a. Reads every answer so far into one "namespace" dict
      b. Layer 1: differential_engine works out what is still standing
      c. Decides which protocol modules that opens
      d. For each active module: engine/evaluator.evaluate_protocol()
      e. Collects the FRONTIER -- the questions still outstanding

4. Returns the whole new state as JSON

5. React re-renders from it
```

**The frontier is the thing to understand.** The engine never returns "the
next question." It returns *every question still outstanding*. The client
renders that list. This is why the UI needed an answer ledger: a question
leaves the frontier the moment it is answered, so a naive client makes
answered questions vanish off the screen.

---

## 6. The four safety rules

These are in `private/context/READ-THIS-FIRST.md` and enforced in
`differential_engine.py`. Each has a named test in `tests/test_differential.py`.
Do not weaken them to simplify anything.

1. **"Didn't check" never looks like "checked and fine."** Every finding has
   three states: yes, no, and absent. Absent stays absent.
2. **Tier-1 killers never auto-exclude.** A normal exam makes dissection
   unlikely, not impossible. Dropping one takes a separate deliberate tap.
3. **Only examination excludes.** The absence of a test result clears nothing.
4. **A positive finding promotes.** It moves an item *up* the list — it does
   not merely fail to remove it.

Rule 2 is the one people try to optimise away. Don't.

---

## 7. Common tasks

**Add a disease** → write `app/protocols/<name>_v1.json` against the schema in
`docs/protocol_schema.md`. Add its symptom links to `differential_table.json`.
Write a test file. Touch no other Python.

**Change what the differential asks** → `app/differential_table.json` only. The
findings array and the `finding` link on each item. No code change.

**Change a shared intake question** → `app/core_intake.json`.

**Change how something looks** → `frontend/src/`. Never put clinical logic
there; the client is deliberately ignorant.

---

## 7b. The answer log

`app/answer_log.py` + the `answerevent` table. Append-only; the engine never
reads it. Every submitted answer is rendered into `{question, answer}` pairs
**at write time**, while the field definition that produced the question is
still in hand -- so the record cannot drift as protocols get reworded. One
answer path can be many questions (the findings screen is nine), and each
gets its own line. A correction is written as a new row carrying the answer
it replaced, never as an edit of the old row.

Surfaced at `GET /encounters/{id}/result` as `answer_log`, and on the result
page as **"What was entered"**.

---

## 7c. The AI second opinion

Off unless an API key is set, and that is a supported state -- the tool routed
patients without it for its whole life and still does. With no key the panel
says so and nothing else changes.

**It never decides anything.** Routing comes from the rule engine; the model
is shown the finished result and asked whether it agrees. It cannot change a
protocol's output, reopen a module, or move an item in the differential.

**Every provider gets the identical briefing.** `app/ai/briefing.py` holds the
system prompt and builds the user prompt; `gemini_provider.py`,
`anthropic_provider.py` and `xai_provider.py` are transport and error handling
only. If they were briefed separately, "the AI disagreed" would mean different
things depending on which key happened to be set that week.

**What the briefing contains** is everything the result screen shows the
doctor -- the full answer log question by question, the differential with the
reason each item is where it is, what was never assessed, the routing and its
tracks, and the protocols that were never opened. Roughly 2,000 tokens for a
typical chest-pain encounter. A model briefed on less than the doctor can see
would disagree for reasons the doctor cannot check.

The prompt names the age blind spot explicitly, because that is the one
failure the engine cannot catch on its own: nothing in `differential_table.json`
or `differential_engine.py` reads age (see §8), so a protocol that fits a
60-year-old is offered to a 21-year-old with identical answers and the engine
never notices. A test asserts that instruction is still in the prompt.

The model is asked for four fixed headings -- VERDICT / READING / WORTH A
SECOND LOOK / BEFORE YOU ACT -- which the result page renders as sections. If
a model ignores the format the whole answer falls through as one unlabelled
block and is still shown in full; nothing is ever silently dropped.

`POST /encounters/{id}/ai-opinion`, stored in the `aiopinion` table, returned
with the result as `ai_opinion`. Failures degrade to a banner, never a 500,
and every failure message names the thing that is actually wrong rather than
echoing a stack trace at a doctor.

---

## 8. Known gaps — real, not hypothetical

- **No cross-module reconciliation.** Two active modules produce two separate
  drug lists. Benzathine penicillin appears twice for a patient with both RHD
  and rheumatic fever. Nothing merges them into one prescription or one
  patient-level blocked-drug matrix. This is the biggest missing piece.
- **No consolidated "tests to order" list.**
- **AF is a placeholder** with no drug content, so RHD can compute a
  `vka_hard_block_doac` while AF — which would actually prescribe the
  anticoagulant — blocks nothing.
- **A correction only invalidates what the core sequence knows about.**
  Changing an answer works (`submit_answer` takes the answer back out,
  re-asks it, and writes the new one). What it invalidates downstream is
  declared explicitly in `_CORE_DEPENDENTS` for the core steps -- symptoms
  invalidate the findings, findings invalidate the Tier-1 confirmations.
  Inside a protocol nothing is declared: a stale answer to a field that a
  correction has since made unreachable stays in the store and would be
  re-used if that field became reachable again. Not observed in the three
  shipped protocols, but not prevented either.
- **`CLAUDE.md` at the repo root says "no LLM calls anywhere in this build."**
  That sentence was written for the Expo app and is still true of it and of
  the engine's routing, which is deterministic end to end. It is no longer
  true of the product as a whole: the engine ships an optional second opinion
  (§7c) that a deployment can switch on with one key. Reword it rather than
  leaving a reader to guess which half applies.
- **The AI second opinion is not evaluated.** There is no set of encounters
  with known-correct verdicts to measure it against, so "it gave good advice
  in testing" is the only evidence there is. Before it is presented as
  anything more than a prompt for the doctor to think again, it needs a
  scored bank of cases -- including ones where the right answer is AGREE.
- **No rate limit on the AI endpoint.** Combined with the absence of any
  login, anyone with the URL can spend the key's quota.
- **`ADMIN_KEY` is one shared password, not authentication.** It gates
  `GET /consultations` (every patient on the deployment) and nothing else. It
  does not record who looked and cannot be revoked for one person. Everything
  else is still unauthenticated: anyone with the URL can start a consultation.

---

## 9. The other UI

`sanhita/ui/` is the Expo app. It has **its own separate protocol engine** in
TypeScript (`src/lib/protocol-engine.ts`) with a fever protocol hardcoded. It
does not call this backend at all.

So there are currently two implementations of the same idea in two languages.
That needs resolving before it drifts further.
