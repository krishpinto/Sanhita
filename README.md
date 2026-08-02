# The Manual Protocol System — from scratch

This is a different system from the transcription pipeline. Not a variant of
it, not a mode of it — different problem, different architecture. This doc
explains why, and what the real components are.

## Why it was wrong to fuse it into your existing architecture

Complaint Classifier, Template Registry, and Extractor-LLM exist to solve one
specific hard problem: **a doctor and patient are having a free, messy,
Hinglish conversation, and something has to guess what matters and pull
structured fields out of it.** That's a genuine inference problem — you don't
know what the patient is going to say, so you need a component that
*classifies* (what is this consult about?) and *extracts* (what facts are
buried in this sentence?). That's exactly why your own diagram marks those
boxes "AI · probabilistic" — there's real uncertainty to resolve.

The manual system has **no uncertainty to resolve at the point of use.** A
health worker is looking at an explicit, pre-written question and clicking an
explicit, pre-written answer. There is nothing to classify and nothing to
extract — the structure was never messy to begin with. Running that through
a classifier and a template registry doesn't add safety, it adds fake
complexity: components built for ambiguity, applied to a place with no
ambiguity.

Different problem → different architecture. Here's the real one.

## The one idea that matters

This class of system — walk a person through a published clinical algorithm,
step by step, and land on a cited recommendation — is not new. It's the same
family as **expert systems** (MYCIN, 1970s Stanford — the original
rule-based diagnostic system), **DXplain**, and what WHO itself ships today
as **SMART Guidelines** (clinical protocols encoded as executable logic —
CQL / CDS Hooks — separate from any particular app). They all converge on
the same one non-negotiable split:

> **The clinical content (the protocol) and the code that runs it (the
> engine) must be two different things.**

The protocol — "ask about danger signs, if any present go to X, else ask
about duration" — is *data*: authored by a clinician, versioned, reviewed,
citable, changeable without a code deploy. The engine that walks that data
is *generic code* that has zero idea what "danger sign" or "dengue" mean —
it just knows how to follow a graph. One engine, any number of protocols.
Adding a new condition means adding a new content file, not writing new
logic. This is the whole reason the architecture scales to "any illness,
any hospital" without turning into an unmaintainable pile of if/else per
condition.

Everything below is just this idea, named out.

## The components

### 1. Protocol Definition — the content layer

One file per condition. Not code — data a clinician could plausibly review
line by line without reading a stack trace. Each protocol is a graph of
**Steps**:

```
Step
  id            "f2"
  answerType    choice
  question      "Any danger signs — difficulty breathing, confusion,
                 fainting, severe weakness, non-blanching rash, SpO2<90?"
  options: [
    { label: "Yes",              → outcome "danger-sign-severe" }
    { label: "No",                → step "f3" }
    { label: "Don't know / n/a",  → step "f3-cautious" }   ← always present
  ]
```

A step's `answerType` is either **choice** (a small fixed set of buttons,
like above) or **value** (a number — "how many days has the fever
lasted?" — which the step itself buckets into ranges: `<3 → step X`,
`≥3 → step Y`). Either way, an **Unknown / not available** option is always
there — no vitals monitor, no problem, but it must route somewhere safe
(usually the more cautious branch), never get silently skipped.

An **outcome** (a leaf) isn't a one-line answer — it's a short instruction
sheet, in four labeled parts, mirroring how real government/WHO guidelines
are already structured (a "likely diagnosis" section plus a "management"
section):

```
Outcome "dengue-suspected"
  LIKELY            "Dengue fever"
  DO_NOW             [ "Check platelet count / hematocrit if available",
                        "Start oral fluids — no NSAIDs/aspirin (bleeding risk)" ]
  TELL_THE_PATIENT   "You likely have dengue. Drink plenty of fluids, take
                       only paracetamol for fever, and watch for the warning
                       signs below over the next 2 days."
  REFER_NOW_IF        [ "Bleeding gums/nose", "Persistent vomiting",
                         "Severe abdominal pain", "Drowsiness" ]
  FOLLOW_UP           "Recheck platelet count in 24h if fever continues past day 3"
  citations: { DO_NOW: "NVBDCP Dengue Guidelines §4.2",
               REFER_NOW_IF: "NVBDCP Dengue Guidelines §4.5" }
```

Every step and every part of every outcome must cite something real — which
guideline, which section. That rule doesn't come from the transcription
architecture, it's just the baseline for shipping clinical software at all —
carry it forward regardless of which system you're in.

Protocols are versioned (`fever-adult v1`, `v2`, …) because guidelines
change over time and you need to know, forever, which version of the logic
produced a given recommendation. That version stamp is what makes this
auditable — closer to how a regulated device would need to work, not a
nice-to-have.

### 2. Protocol Index — picking which protocol to run

Not a classifier. A **lookup**. The health worker either picks a complaint
from a known list, or types free text that gets matched against a small
controlled vocabulary of synonyms:

```
{ complaint: "fever", synonyms: ["temperature","pyrexia"], protocol: "fever-adult" }
```

This is deterministic string matching against a table you wrote, not a
model inferring intent from ambiguous speech. If it can't find a match, it
says so honestly ("no protocol for that yet") instead of guessing — a
classifier is allowed to guess with a confidence score; a lookup table
should never pretend.

### 3. Protocol Engine — the generic interpreter

The one piece of real code. It knows nothing about medicine. Its whole job:

- load a Protocol Definition by id + version
- hold the current step + the answers given so far
- hand the UI the current question
- on an answer: record it, resolve `next` → either another step or an
  outcome
- at an outcome: return the recommendation + citation + the **full answer
  trail**

Same engine runs every protocol you ever author. If you added a chest-pain
protocol tomorrow, this code doesn't change — only the content does.

One more responsibility worth building in from day one: a step can mark an
answer as a **danger-sign check**, evaluated the moment it's answered,
regardless of where you are in the tree — so a red flag interrupts
immediately instead of waiting for the tree to naturally arrive at it. This
is what actually protects a non-specialist from missing something urgent —
arguably the single most important safety feature of the whole system, and
worth being deliberate about rather than letting it fall out of tree
structure by accident.

### 4. Encounter Record — the audit trail

The output isn't just "here's the answer" — it's the full record: which
protocol + version ran, every question actually asked (snapshot the text at
the time, don't just reference the step — protocols change later, but the
record of what was asked to *this* patient must never change), every
answer, every timestamp, the outcome, every citation, whether any red flag
fired. This is your accountability mechanism — it's the literal answer to
"how do we know the under-qualified doctor didn't just click through
randomly," and it's the artifact you'd show a regulator or an investor's
technical diligence call, not just a demo.

### 5. Delivery — thin, deliberately dumb

Renders whatever the engine hands it. Question in, answer out. No clinical
logic lives here — if you ever find yourself writing an `if` about symptoms
in the UI layer, that logic belongs in a Protocol Definition instead.

Delivery isn't necessarily one screen, though — see "field view vs review
view" below, since the same protocol data supports two very different
renderings for two very different audiences.

## Two moments of input

Input happens at two different points, and they work differently on purpose.

**Once, before opening any protocol** — an index card: age, sex, any vitals
on hand (skip what you don't have), and the complaint (picked from a short
list, or typed and matched against a small controlled vocabulary — the
*only* place free text is allowed anywhere in the system, and even then it's
just matched against known words, never interpreted). Age quietly does
double duty: "fever" + age 3 doesn't open the adult fever protocol, it opens
the child one — the index card decides which *edition* of the book, not
just which topic.

**Many times, while inside a protocol** — one question per page, and only
ever a **choice** (tap one of a few buttons) or a **value** (type a number,
the page buckets it). Never an open box asking the health worker to
"describe the symptoms" for the system to interpret — that would quietly
reintroduce the classifier/extractor problem we already ruled out.

## Simplicity is the engine's job, rigor is the content's job

These are two separate axes, not a tradeoff:

- **How hard it is to use** — one plain-language question at a time.
- **How rigorous the logic underneath is** — does it actually match the
  full certified protocol, edge cases and all.

The person answering never sees the tree, only the current page — so the
tree can be as deep and demanding as a specialist requires without the
interface getting one bit harder to use. Simplicity is a property of the
*engine* (it only ever renders one page). Rigor is a property of the
*content* (how faithfully the book matches the real guideline). You don't
trade one for the other — this is the same design philosophy WHO already
uses for training minimally-qualified community health workers under
IMCI / SMART Guidelines: dead-simple one-question-at-a-time flows on the
front end, running the real unmodified clinical algorithm underneath.

Because a protocol is just a graph (data, not code), the same file supports
two different renderers for two different audiences, at no extra modeling
cost:

- **Field view** — what the health worker uses. One question, one page,
  nothing else visible.
- **Review view** — what a senior doctor uses to sign off on a protocol
  before it goes live. The whole tree at once, like a printed WHO flowchart
  poster, every branch and citation visible in one look.

You don't convince a skeptical specialist with a demo of the field view —
you let them read the review view. That's the actual answer to "how do I
stop a senior doctor from writing this off as a toy."

## Walking one instance through it, concretely

```
Index card: age 24, sex M, no vitals on hand, complaint "fever" (typed)
        │
        ▼
Protocol Index looks up "fever" + age 24 → protocol "fever-adult", version 3
        │
        ▼
Protocol Engine loads fever-adult v3, starts at step f1
        │
        ▼
"Fever for how many days?"        → worker types: 4
        │                              (page buckets 4 → "≥3 days" branch)
        ▼
step f_prolonged: "Mosquito exposure or travel to an endemic area?"
        │                              → worker taps "Yes"
        ▼
Engine resolves → outcome "dengue-suspected"
        │
        ▼
Encounter Record: {
  protocol: fever-adult v3,
  trail: [f1:"4 days", f_prolonged:"Yes"],
  outcome: "dengue-suspected",
  redFlags: []
}
        │
        ▼
Delivery layer (field view) shows:
  LIKELY: Dengue fever
  DO NOW: check platelets/hematocrit if available · start oral fluids,
          no NSAIDs/aspirin        — NVBDCP Dengue Guidelines §4.2
  TELL THE PATIENT: "Drink plenty of fluids, only paracetamol for fever,
          watch for warning signs over the next 2 days"
  REFER NOW IF: bleeding gums/nose, persistent vomiting, severe
          abdominal pain, drowsiness   — NVBDCP Dengue Guidelines §4.5
  FOLLOW UP: recheck platelets in 24h if fever continues past day 3
```

Nothing here classified anything. Nothing extracted anything from
unstructured text. It's a lookup, then a walk, then a record. That's the
whole system — the simplicity is the point, not a shortcut.

## What this pitches as, to him tonight

Say it in this order, it maps directly to the sections above:

1. **"Every protocol is content, not code."** A clinician can author or
   correct a protocol without an engineer touching anything — that's what
   lets this cover any illness, any hospital, without the app rewriting
   itself for each one.
2. **"One engine runs all of them."** You're not building N apps for N
   conditions, you're building one interpreter and a growing library.
3. **"Every recommendation is a full, timestamped trail back to a named
   guideline."** That's the actual defensibility answer to "how is this
   different/safer than a doctor just guessing" — not a vibe, an audit log.
4. **"Danger signs interrupt immediately, wherever they occur."** That's the
   concrete safety net for the under-qualified-doctor problem he described.
5. **"The output isn't just a diagnosis — it's DO NOW / TELL THE PATIENT /
   REFER NOW IF / FOLLOW UP, cited section by section."** That's what lets
   someone who "only has a degree for the name's sake" actually act
   correctly, not just know a label.
6. **"Simple for the field, rigorous underneath — same file, two views."**
   The field worker sees one question at a time; a specialist can review the
   entire tree at once before it ever ships. That's the answer if he asks
   how you stop senior doctors from dismissing it.

## Where this and your transcription system genuinely do meet later — not now

Don't force it tonight, but the honest future connection point is narrower
than "share components": it's the **citation discipline and the Encounter
Record concept**. Both systems should hold themselves to the same rule
(every claim traces to a source, every session leaves an audit trail). If
anything from this system feeds the other one day, it's the *protocol
content* itself — e.g. the transcription pipeline's ad hoc febrile-illness
checklist could eventually be replaced by reading a real Protocol
Definition instead of a hard-coded prompt string. That's a future data-model
question, not an architecture merge, and it's worth revisiting only after
both systems are real on their own terms.
