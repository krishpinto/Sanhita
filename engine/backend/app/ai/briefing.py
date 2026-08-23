"""Turns an encounter into the text a model is asked to comment on.

One builder, shared by every provider, for one reason: if two providers were
briefed differently, "the AI disagreed" would mean different things depending
on which key happened to be set that week.

What goes in is deliberately everything the doctor can see on the result
screen -- every question and the answer given, every differential item and
why it is where it is, what was never assessed. An opinion formed on a
summary the doctor cannot cross-check is not reviewable, and an unreviewable
opinion has no business next to a routing recommendation.
"""

from __future__ import annotations

from typing import Any

from app.ai.base import SecondOpinionContext

SYSTEM_PROMPT = """You are a second reader inside Sanhita, a physician-facing clinical decision-support tool used in Indian primary care (PHC/CHC and district hospitals).

Sanhita does not diagnose. It routes: a rule engine narrows a differential, then walks a published protocol (ICMR/MoHFW) to a recommendation. The engine's routing is what the doctor acts on. Your job is to be the second pair of eyes on it -- the colleague who glances at the chart and says "hold on".

You will be given the complete encounter: every question the doctor was asked and the answer they gave, the differential the engine raised and what it did with each item, the protocol it ran, and everything that was never assessed.

Read it and answer in exactly these four sections, using these headings verbatim:

VERDICT
One line, starting with one of: AGREE / AGREE WITH CAVEATS / DISAGREE. Then a half-sentence saying why.

READING
Two to four sentences in plain clinical language: what this patient most likely has, and how confident that is. Speak in likelihoods, never a definitive diagnosis.

WORTH A SECOND LOOK
Bullets, each one line, starting with "- ". Things the engine's rules cannot see. Especially:
- Age, sex, or risk-factor mismatch. The engine's differential does not weigh age at all -- a protocol that fits a 60-year-old may be a poor fit for a 21-year-old with the same answers, and the engine will not notice. Say so when it applies.
- A finding recorded as "Not assessed" that materially changes what this could be.
- Something in the answers that points somewhere the engine never raised.
- A dangerous condition the answers do not actually rule out.
If there is genuinely nothing, write "- Nothing that changes the routing."

BEFORE YOU ACT
Bullets, each one line, starting with "- ". Concrete things to confirm or order, chosen for what is realistically available at the facility tier given. Two to four of them.

Rules:
- Never contradict a hard safety exit (ST elevation, an unstable patient). If the engine escalated, back it.
- Never state a definitive diagnosis and never give a drug dose.
- Do not restate the whole history back. The doctor entered it; they know it.
- Do not add a disclaimer. The interface shows one.
- Plain words. This is read between patients, not at a desk."""

_NOT_ASSESSED = "not assessed"


def _demographics(core: dict[str, Any]) -> list[str]:
    age = core.get("age")
    sex = core.get("sex") or "?"
    tier = core.get("facility_tier") or "unknown facility"
    symptoms = core.get("symptoms") or []
    return [
        "PATIENT",
        f"{age if age is not None else '?'}-year-old {sex}, seen at: {tier}",
        f"Presenting symptoms selected: {', '.join(symptoms) if symptoms else 'none recorded'}",
    ]


def _answers(answer_log: list[dict[str, Any]]) -> list[str]:
    """Every question and answer, in the order they were entered. Corrections
    are shown as corrections -- a doctor who changed their mind mid-encounter
    is a signal, not noise to be flattened away."""
    if not answer_log:
        return []
    lines = ["", "EVERYTHING THE DOCTOR ENTERED"]
    for event in answer_log:
        section = event.get("block_label") or event.get("field_label")
        for entry in event.get("entries", []):
            mark = " [changed from an earlier answer]" if event.get("is_correction") else ""
            lines.append(f"- [{section}] {entry['question']} -> {entry['answer']}{mark}")
    return lines


def _differential(differential: dict[str, Any] | None) -> list[str]:
    if not differential:
        return []
    lines = ["", "DIFFERENTIAL THE ENGINE RAISED, AND WHAT IT DID WITH EACH"]
    for item in differential.get("items", []):
        lines.append(
            f"- {item['label']} (tier {item['tier']}): {item['status']} -- {item.get('reason') or 'no reason recorded'}"
        )
    unassessed = [
        f["short_label"] for f in differential.get("findings", []) if f.get("answer") is None
    ]
    if unassessed:
        lines.append("")
        lines.append(
            "Findings the doctor did NOT assess (these are unknown, NOT negative): "
            + ", ".join(unassessed)
        )
    return lines


def _protocols(protocols: list[dict[str, Any]]) -> list[str]:
    if not protocols:
        return ["", "PROTOCOL RUN: none reached a result."]
    lines = ["", "PROTOCOL THE ENGINE RAN"]
    for p in protocols:
        lines.append(f"--- {p['protocol_name']} (status: {p['status']}) ---")
        if p.get("source_citation"):
            lines.append(f"Source: {p['source_citation']}")
        if p.get("fidelity") == "reduced_fidelity_placeholder":
            lines.append(f"NOTE -- reduced-fidelity module: {p.get('fidelity_note')}")
        terminal = p.get("terminal") or {}
        if terminal:
            lines.append(f"Routed to: {terminal.get('headline')}")
            for key in ("do_now", "tell_the_patient", "refer_now_if", "follow_up"):
                value = terminal.get(key)
                if value:
                    lines.append(f"  {key}: {value if isinstance(value, str) else '; '.join(map(str, value))}")
        for track in p.get("tracks", []):
            lines.append(
                f"  {track['label']}: {track['resolution']} "
                f"({track['positive_count']} positive, {track['negative_count']} negative, "
                f"{track['unknown_count']} unknown of {track['total_scored_fields']})"
            )
        if p.get("unassessed"):
            lines.append("  Not assessed in this protocol: " + ", ".join(u["label"] for u in p["unassessed"]))
    return lines


def _unrun(unrun: list[dict[str, Any]]) -> list[str]:
    if not unrun:
        return []
    return ["", "PROTOCOLS CONSIDERED BUT NOT OPENED"] + [
        f"- {u['name']}: {u['reason']}" for u in unrun
    ]


def _core_terminal(core_terminal: dict[str, Any] | None) -> list[str]:
    if not core_terminal:
        return []
    return [
        "",
        "SAFETY EXIT -- the engine stopped the encounter before any protocol ran",
        f"Code: {core_terminal.get('code')}",
        f"Headline: {core_terminal.get('headline')}",
        "Back this escalation. Your job here is to say what else to watch for, not to second-guess it.",
    ]


def build_user_prompt(ctx: SecondOpinionContext) -> str:
    lines: list[str] = []
    lines += _demographics(ctx.core)
    lines += _core_terminal(ctx.core_terminal)
    lines += _differential(ctx.differential)
    lines += _protocols(ctx.protocols)
    lines += _unrun(ctx.unrun_protocols)
    lines += _answers(ctx.answer_log)
    lines += [
        "",
        "Now give your four sections.",
    ]
    return "\n".join(lines)
