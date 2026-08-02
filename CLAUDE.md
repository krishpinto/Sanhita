# CLAUDE.md — Sanhita

"Sanhita" (सहिता) — Sanskrit for "a systematic compilation," the word used
for the classical Indian medical texts (Charaka Samhita, Sushruta Samhita).

## What this is

A guided app that walks a health worker — not necessarily a specialist —
through a certified clinical protocol, question by question, and ends with
a diagnosis-shaped recommendation plus clear next-step instructions for the
patient. Built so it can be clinically prototype-tested for free: **no LLM
calls anywhere in this build.** Every recommendation is deterministic and
traces back to a named guideline section.

Target user: a doctor or health worker in a lower-tier facility (village /
Tier-3 hospital) who may not reliably know the right protocol path on their
own. The app is the protocol, made walkable.

## Not in scope for this build

There is a **separate, unrelated project** — an ambient consult-transcription
app (repo: `futurescope`) — that some of you may hear about. It is a different
product, a different repo, a different architecture, built for a different
purpose. Nothing from it is reused here, and nothing here feeds it. If a task
description starts sounding like "transcribe the doctor," that task belongs
in the other repo, not this one — flag it rather than build it here.

## Platform & stack

**React Native via Expo (managed workflow), not bare RN CLI.** This is a
non-negotiable, and here's the actual reason: **Expo's EAS Build compiles and
signs iOS binaries in the cloud** — nobody on this team needs to own a Mac or
run Xcode locally to ship to the App Store. Bare RN CLI's iOS build requires
a local Mac. For a small, fast-moving team without guaranteed Mac access,
that's a real bottleneck, not a minor preference. If the UI is already
started on bare RN CLI, stop and convert now — it only gets more expensive
to unwind the longer native code accumulates.

Everything else (navigation, state, styling) is an open implementation
choice for whoever's building the UI — not locked here.

## The one idea the architecture rests on

Full writeup: `README.md` in this folder. Short version — the clinical
content (a protocol's questions and branches) and the code that runs it
(the engine) are two different things:

- A **Protocol Definition** is data: a versioned graph of Steps, each a
  question plus a few answers, authored and reviewed by a clinician. Not
  code — nobody needs to touch the app to fix or extend one.
- A **Protocol Engine** is generic code with zero medical knowledge: it
  loads a Protocol Definition, shows the current question, records the
  answer, resolves what's next. The same engine runs every protocol that
  ever gets written.
- Any step can mark an answer as a **danger sign**, checked the instant
  it's given, short-circuiting straight to an urgent outcome regardless of
  where you are in the tree.
- Every completed run produces an **Encounter Record** — the full
  question/answer trail, timestamped, immutable, plus the outcome and every
  citation. This is the accountability layer.
- The outcome itself isn't a one-line diagnosis — it's four labeled parts:
  **LIKELY** (the probable classification), **DO NOW** (immediate actions),
  **TELL THE PATIENT** (plain-language advice), **REFER NOW IF** (escalation
  triggers), **FOLLOW UP** (safety-net timing) — each part cited to a
  guideline section.
- Delivery is two renderers of the *same* Protocol Definition file: **Field
  View** (one question at a time — what the health worker actually uses)
  and **Review View** (the whole tree at once, like a printed flowchart —
  what a clinician uses to sign off on a protocol before it ships).

See `architecture-map.html` in this folder for the visual version, and
`protocol-tree-demo.html` for a clickable example (the fever protocol,
fully worked through).

## The protocol content pipeline — how a protocol actually gets built and added

This is the part that scales the product, not app features. Every new
protocol goes through the same four steps:

1. **Draft.** A clinician (the funder's doctor contacts) writes out the
   decision logic against a plain template: chief complaint → each question
   in order → for each answer, either the next question or an outcome (with
   its DO NOW / TELL THE PATIENT / REFER NOW IF / FOLLOW UP + citation). A
   spreadsheet or a structured doc is enough at this stage — nobody needs to
   write JSON by hand to author a protocol.
2. **Encode.** A developer turns the draft into an actual Protocol
   Definition file matching the Step schema in `README.md`, and adds an
   entry to the Protocol Index's controlled-vocabulary table (complaint +
   synonyms → this protocol's id and version).
3. **Review.** The encoded protocol gets rendered in **Review View** and
   handed back to the authoring clinician (or a second reviewer) to confirm
   nothing was lost or misencoded in translation — sign-off happens against
   the visual tree, not the raw file.
4. **Ship.** See delivery below.

Do not build a self-serve "protocol builder" UI yet — with a handful of
protocols and one or two clinical authors, steps 1–3 above are faster than
building and maintaining an authoring tool. Revisit only once there are
enough protocols (or non-technical authors) that the spreadsheet step
becomes the bottleneck.

### Shipping new protocols without waiting on an app-store release

Bundling protocol content directly into the app build means every new
protocol requires an app update and store review — too slow for "doctors
keep adding more protocols" as an ongoing process. Instead:

- Protocol Definitions are fetched from a small remote source (a versioned
  JSON/YAML file per protocol behind a simple endpoint or static host — this
  does not need a heavy backend at this stage) and **cached locally on
  first load.**
- The app always runs off its local cache and refreshes opportunistically —
  a health worker in a low-connectivity Tier-3 facility must never be
  blocked from using an already-downloaded protocol because the network is
  down. Offline-first, not offline-only.
- Every protocol keeps its version stamp end to end — an Encounter Record
  must always be able to say exactly which version of a protocol produced
  it, even after that protocol has since been updated.

## Primary source of protocol content

Real, named starting candidates — not to be treated as final without
clinical sign-off, but the right place to start looking rather than
inventing logic from general knowledge:

- **NHSRC / MoHFW Standard Treatment Guidelines** — built specifically for
  providers at primary/lower-tier facilities, which is exactly this app's
  target user.
- **IMCI / IMNCI** (Govt of India–adapted WHO child-illness algorithms) —
  strong source for pediatric protocols specifically.
- **NVBDCP** guidelines — dengue, malaria, chikungunya case management.
- **ICMR** guidelines — condition-specific Indian clinical guidance.
- **WHO** guidelines, where no India-specific adaptation exists yet.

Whoever owns clinical content should confirm current document versions
directly — do not ship a protocol whose source citation hasn't been
verified by a clinician against the live guideline text.

## Build items — locked order

0. **Protocol Engine core** — the Step schema, the generic interpreter,
   danger-sign interrupts, Encounter Record shape. No UI yet — this is
   right the first time or everything built on top inherits the mistake.
1. **One real protocol, fully authored and reviewed** — pick one condition,
   run it through the full content pipeline above, end to end. Prove the
   pipeline before the second protocol, not after the tenth.
2. **Field View** — the guided one-question-at-a-time UI, wired to protocol
   #1.
3. **Review View** — the full-tree renderer, same Protocol Definition file.
4. **Encounter Record persistence** — local storage first; sync/backend is
   a later item, not a blocker for a pilot.
5. **Remote protocol delivery + offline cache** — unblocks adding protocols
   without an app-store cycle.
6. **Second and third protocols** — through the same pipeline, to prove it
   generalizes before treating it as done.

## What NOT to build yet

- No LLM calls, anywhere, in this build — that's a different product, on
  purpose, per the whole reason this one ships first.
- No breadth-first multi-specialty push — depth and correctness on the
  first few protocols beats a shallow library of many.
- No self-serve protocol-authoring admin tool (see content pipeline above).
- No bare-RN native modules or anything that forces leaving the Expo
  managed workflow — that's what breaks the iOS story.
