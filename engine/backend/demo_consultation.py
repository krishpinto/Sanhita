"""Drive complete consultations through the real API and print them as a
readable transcript.

    python demo_consultation.py            # all cases
    python demo_consultation.py 1          # just case 1

Nothing here is a mock. It boots the actual FastAPI app against an in-memory
database and talks to it over HTTP the same way a phone app would: ask for the
next step, post an answer, repeat, then read the result. What it prints is what
the engine actually said.
"""

from __future__ import annotations

import sys
import textwrap

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

import app.db as db_module

db_module.engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

W = 78


def rule(char: str = "-") -> None:
    print(char * W)


def heading(text: str) -> None:
    print()
    rule("=")
    print(f"  {text}")
    rule("=")


def wrap(text: str, indent: str = "     ") -> None:
    for line in textwrap.wrap(text, W - len(indent)):
        print(indent + line)


def show(value) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "(none)"
    if isinstance(value, dict):
        return ", ".join(f"{k}={show(v)}" for k, v in value.items() if v is not None)
    return str(value)


# ---------------------------------------------------------------- the cases


class Case:
    """One scripted patient. `answers` is keyed by field id; anything not
    listed falls through to a conservative default, which is how we prove the
    engine never needs a hand-held answer to stay safe."""

    def __init__(self, title, story, answers, findings, confirmations=None):
        self.title = title
        self.story = story
        self.answers = answers
        self.findings = findings
        self.confirmations = confirmations or []


CASE_1 = Case(
    title="Case 1 - exertional chest pain at a PHC",
    story=(
        "Ramesh, 58, walks into a primary health centre. Chest tightness when he "
        "climbs the stairs, gone after a couple of minutes of sitting. Also more "
        "breathless than he used to be. Known hypertensive, diabetic, smokes."
    ),
    answers={
        "facility_tier": "phc",
        "name": "Ramesh K.",
        "age": 58,
        "sex": "M",
        "symptoms": ["chest_pain", "exertional_breathlessness_or_fatigue"],
        "htn_dx": True,
        "diabetes": True,
        "current_smoker": True,
        "ecg": {
            "availability": "performed_reviewed",
            "rhythm": "normal_sinus",
            "rate": 78,
            "q_waves": False,
            "st_t_changes": False,
            "st_elevation": False,
            "bbb": False,
            "chamber_enlargement": False,
            "pre_excitation": False,
            "qt_interval": "normal",
        },
        "vitals": {"hr": 78, "bp_systolic": 148, "bp_diastolic": 88, "spo2": 97, "rr": 16},
        # --- inside the angina protocol ---
        "duration": "1_to_20_min",       # each episode lasts a few minutes
        "A1_quality_site": "diffuse_retrosternal",
        "A2_provocation": "exertion_predictable",
        "A3_relief": "rest_or_ntg_1_2min",
        "B2_breathlessness": True,       # the exertional breathlessness he reported
        "dyslipidaemia": True,
        # The prescribing safety screen. He is a smoker with wheeze.
        "asthma_or_bronchospastic_copd": True,
    },
    findings={
        # The bedside examination, recorded as observations rather than as
        # conclusions. Note "pulses equal: yes" is the reassuring answer.
        "pulses_equal": True,
        "pleuritic_pain": False,
        "constitutional": False,
        "chest_wall_reproducible": False,
        "exertional_relieved_by_rest": True,  # this is what makes it angina
        "murmur": False,
        "irregular_pulse": False,
        "pallor": False,
        "reflux_pattern": False,
    },
    # The doctor deliberately takes the four killers off the list.
    confirmations=["aortic_dissection", "pulmonary_embolism", "pneumothorax", "severe_aortic_stenosis"],
)

CASE_2 = Case(
    title="Case 2 - the same intake, but the ECG shows ST elevation",
    story=(
        "Identical patient, identical answers, one difference: the tracing shows "
        "ST elevation. Everything the engine was about to do stops."
    ),
    answers={
        **CASE_1.answers,
        "ecg": {**CASE_1.answers["ecg"], "st_elevation": True, "st_t_changes": True},
    },
    findings=dict(CASE_1.findings),
    confirmations=list(CASE_1.confirmations),
)

CASE_3 = Case(
    title="Case 3 - two modules running at the same time",
    story=(
        "Sunita, 24, at a district hospital. Fever with joint pains, breathless, "
        "palpitations, an irregular pulse, and a murmur. This is rheumatic fever "
        "on top of valve disease she already had, and she is in atrial "
        "fibrillation. Two protocols open and run in parallel. This is the case "
        "that shows what the engine does not yet do."
    ),
    answers={
        "facility_tier": "district",
        "name": "Sunita M.",
        "age": 24,
        "sex": "F",
        "symptoms": [
            "exertional_breathlessness_or_fatigue",
            "palpitations",
            "irregular_pulse",
            "murmur",
            "fever_with_joint_pains",
        ],
        "ecg": {
            "availability": "performed_reviewed",
            "rhythm": "af",  # auto-activates the AF module on its own
            "rate": 118,
            "q_waves": False,
            "st_t_changes": False,
            "st_elevation": False,
            "bbb": False,
            "chamber_enlargement": True,
            "pre_excitation": False,
            "qt_interval": "normal",
        },
        "vitals": {"hr": 118, "bp_systolic": 106, "bp_diastolic": 70, "spo2": 95, "temp": 38.4, "rr": 22},
        # --- inside the RHD protocol ---
        "presentation": "acute_rheumatic_fever_suspected",
        "carditis": True,
        "arthritis": True,  # two majors -> Jones criteria met
        "fever_ge_38": True,  # matches the 38.4 recorded in vitals
        "esr_ge_30_or_crp_ge_3": True,
        "streptococcal_evidence": True,
        "echo_status": "lesions_present",
        "mitral_stenosis_severity": "moderate_or_severe",  # hard-blocks DOACs
        "aetiology": "rheumatic",  # triggers lifelong secondary prophylaxis
        "had_carditis": True,
        "residual_valve_disease": True,
        # --- inside the AF protocol ---
        "af_confirmed": True,
        "duration_category": "persistent",
        "substrate": "chf",
    },
    findings={
        # murmur, irregular pulse and fever-with-joint-pains all carry
        # forward from the symptom screen -- she is never asked them twice.
        "pleuritic_pain": False,
        "constitutional": False,
        "exertional_relieved_by_rest": False,
        "pallor": False,
    },
    confirmations=["pulmonary_embolism"],
)

CASES = {1: CASE_1, 2: CASE_2, 3: CASE_3}


# ---------------------------------------------------------------- the driver


class Consultation:
    def __init__(self, client, case):
        self.c = client
        self.case = case
        created = client.post("/encounters", json={}).json()
        self.id = created["encounter_id"]
        self.h = {"Authorization": f"Bearer {created['access_token']}"}
        self.seen_blocks: list[str] = []

    def next_step(self):
        return self.c.get(f"/encounters/{self.id}/next-step", headers=self.h).json()

    def answer(self, path, value):
        r = self.c.post(
            f"/encounters/{self.id}/answer", headers=self.h, json={"field_path": path, "value": value}
        )
        if r.status_code >= 400:
            raise SystemExit(f"answer rejected {path}: {r.status_code} {r.text}")

    def value_for(self, ff):
        """What this scripted patient answers. Anything the script does not
        name gets the safe default for its type."""
        f = ff["field"]
        fid = f["id"]

        if fid == "differential_answers":
            asked = {s["id"] for s in f["findings"]}
            return {k: v for k, v in self.case.findings.items() if k in asked}
        if fid == "differential_confirmations":
            offered = {o["value"] for o in f["options"]}
            return [i for i in self.case.confirmations if i in offered]
        if fid in self.case.answers:
            return self.case.answers[fid]

        ftype = f["field_type"]
        if ftype == "boolean":
            return False
        if ftype == "single_select":
            return f["options"][0]["value"] if f.get("options") else None
        if ftype == "multi_select":
            return []
        if ftype == "number":
            return 0
        if ftype == "text":
            return ""
        if ftype in ("structured_ecg", "structured_vitals"):
            return {}
        return None

    # -------- printing

    def announce_block(self, ff):
        key = f"{ff['protocol_id']}::{ff['block_id']}::{ff.get('track_id')}"
        if key in self.seen_blocks:
            return
        self.seen_blocks.append(key)
        print()
        where = "" if ff["protocol_id"] == "core" else f"  [{ff['protocol_id']}]"
        label = ff["block_label"]
        if ff.get("track_label"):
            label += f" -> {ff['track_label']}"
        print(f"  >> {label}{where}")
        if ff.get("block_description"):
            wrap(ff["block_description"], "     ")

    def print_differential_field(self, f, value):
        items = f["differential_items"]
        print(f"     {len(items)} possibilities raised, worst-first:")
        for i in items:
            drops = {
                "auto": "drops on a normal exam",
                "confirm": "needs a deliberate tap to drop",
                "never": "only a test can clear it",
            }[i["exclusion_policy"]]
            print(f"       T{i['tier']} {i['label']:<40}{drops}")

        asked = [s for s in f["findings"] if not s["promotes_only"] and not s["prefilled"]]
        carried = [s for s in f["findings"] if s["prefilled"]]
        optional = [s for s in f["findings"] if s["promotes_only"]]
        print()
        print(f"     ...settled by {len(asked)} questions:")
        for spec in asked:
            answered = value.get(spec["id"])
            mark = "-" if answered is None else ("yes" if answered else "no")
            print(f"       Q: {spec['question']}")
            print(f"       A: {mark}    (settles: {', '.join(spec['resolves'])})")
        for spec in carried:
            print(f"       [carried from the symptom screen] {spec['short_label']}")
        for spec in optional:
            print(f"       [optional - can only promote] {spec['short_label']}")

    def run(self):
        heading(self.case.title)
        wrap(self.case.story, "  ")
        print()

        for _ in range(200):
            step = self.next_step()

            if step["core_terminal"]:
                t = step["core_terminal"]
                print()
                rule("!")
                print(f"  STOP: {t['headline']}")
                rule("!")
                for k, v in t.items():
                    if k != "headline" and v:
                        wrap(f"{k}: {v}", "  ")
                return self.print_result()

            frontier = list(step["core_frontier"])
            if not frontier:
                for p in step["active_protocols"]:
                    frontier.extend(p["frontier"])

            if not frontier and step["offered_protocols"]:
                for o in step["offered_protocols"]:
                    print()
                    print(f"  >> Protocol offered: {o['name']}")
                    if o["fidelity"] != "full":
                        wrap(f"(fidelity: {o['fidelity']}) {o['fidelity_note']}", "     ")
                    self.c.post(
                        f"/encounters/{self.id}/activate-protocol/{o['protocol_id']}", headers=self.h
                    )
                    print("     accepted")
                continue

            if not frontier:
                if step["ready_for_result"]:
                    return self.print_result()
                print("\n  (no further questions and no result -- stopping)")
                return

            ff = frontier[0]
            f = ff["field"]
            self.announce_block(ff)

            value = self.value_for(ff)
            if f["id"] == "differential_answers":
                self.print_differential_field(f, value)
            elif f["id"] == "differential_confirmations":
                print("     The engine refuses to drop these on a normal exam alone:")
                for o in f["options"]:
                    ticked = "x" if o["value"] in value else " "
                    print(f"       [{ticked}] {o['label']}")
            else:
                print(f"     Q: {f['label']}")
                print(f"     A: {show(value)}")

            self.answer(ff["answer_path"], value)
        else:
            print("  (loop guard hit)")

    # -------- the result

    def print_result(self):
        r = self.c.get(f"/encounters/{self.id}/result", headers=self.h)
        if r.status_code >= 400:
            print(f"\n  (no result available: {r.status_code} {r.json().get('detail')})")
            return
        res = r.json()

        print()
        rule("=")
        print("  RESULT")
        rule("=")

        core = res["core"]
        print(f"  {core['name']}, {core['age']}{core['sex']}  |  {show(core['symptoms'])}")

        if res["core_terminal"]:
            print(f"\n  Stopped early: {res['core_terminal']['headline']}")
            return

        diff = res["differential"]
        if diff:
            groups = {}
            for i in diff["items"]:
                groups.setdefault(i["status"], []).append(i)
            order = [
                ("promoted", "PROMOTED - the findings point here"),
                ("pending_confirmation", "STILL ON THE LIST - unlikely, not excluded"),
                ("raised", "STILL OPEN - not settled at the bedside"),
                ("excluded", "RULED OUT"),
            ]
            for key, title in order:
                if key not in groups:
                    continue
                print(f"\n  {title}")
                for i in groups[key]:
                    print(f"    T{i['tier']} {i['label']}")
                    wrap(i["reason"], "         ")

        for p in res["protocols"]:
            print()
            rule()
            print(f"  {p['protocol_name']}  ({p['status']})")
            if p["fidelity"] != "full":
                wrap(f"FIDELITY: {p['fidelity']} - {p['fidelity_note']}", "  ")
            if p["source_citation"]:
                wrap(f"Source: {p['source_citation']}", "  ")
            if p["terminal"]:
                print(f"\n  -> {p['terminal']['headline']}")
                for k, v in p["terminal"].items():
                    if k not in ("headline", "code") and v:
                        wrap(f"{k}: {show(v)}", "     ")
            for t in p["tracks"]:
                counts = ""
                if t["mode"] == "axis_count":
                    counts = (
                        f"  ({t['positive_count']} of {t['total_scored_fields']} features present, "
                        f"{t['unknown_count']} unknown)"
                    )
                print(f"\n  Track '{t['label']}': {t['resolution']}{counts}")
            present = [t for t in p["derived_tags"] if t.get("value") is True]
            unknown = [t for t in p["derived_tags"] if t.get("value") is None]
            if present:
                print("\n  Flags raised:")
                for t in present:
                    print(f"    - {t['label']}")
            if unknown:
                print(f"\n  Flags not assessed: {len(unknown)} (not counted as absent)")
            if p["unassessed"]:
                print("\n  Not assessed (deliberately not counted as normal):")
                for u in p["unassessed"]:
                    wrap(show(u), "     ")
            for block in p["drug_blocks"]:
                if block.get("status") != "ready":
                    continue
                print(f"\n  {block.get('label', 'Medications')}   [{p['protocol_id']}]")
                group = None
                for e in block.get("entries", []):
                    if e.get("group_label") != group:
                        group = e.get("group_label")
                        if group:
                            print(f"    {group}")
                    mark = {
                        "clear": "GIVE ",
                        "caution": "CARE ",
                        "block": "BLOCK",
                        "quarantined": "HOLD ",
                    }.get(e.get("state"), "?????")
                    dose = f"  {e['dose']}" if e.get("dose") else ""
                    print(f"      [{mark}] {e.get('name') or e.get('id')}{dose}")
                    if e.get("note"):
                        wrap(e["note"], "               ")
                    for r in e.get("block_reasons", []) + e.get("caution_reasons", []):
                        tag = "  (added by Vitalis)" if r.get("vitalis_addition") else ""
                        wrap(f"why: {r['reason']}{tag}", "               ")
                if block.get("hidden_count"):
                    print(f"      ({block['hidden_count']} not stocked at this facility tier)")

        if res["unrun_protocols"]:
            print()
            rule()
            print("  Protocols that did NOT run (shown so nothing is silently absent):")
            for u in res["unrun_protocols"]:
                print(f"    - {u['name']}: {u['reason'].replace('_', ' ')}")
        print()


def main() -> None:
    wanted = [int(a) for a in sys.argv[1:]] or sorted(CASES)
    with TestClient(app) as client:
        for n in wanted:
            Consultation(client, CASES[n]).run()


if __name__ == "__main__":
    main()
