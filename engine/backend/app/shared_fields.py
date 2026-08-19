"""Registry of clinical-history field IDs that more than one protocol wants to
read. Asked once (as part of whichever protocol's context/track block first
needs one), stored in the shared_clinical_history table, and from then on
readable by any protocol via a FieldDef with source="shared" + matching
shared_path. Adding an id here is safe -- a protocol simply opts in; nothing
breaks for protocols that don't.

This is a reference list, not something the engine consults at runtime: each
protocol still declares its own local FieldDef (label, options, skip_when)
for a shared field, matching the "modules stay self-contained" design --
there's no cross-protocol field-definition merging to keep track of. Keep
skip_when identical across protocols that share a field (see rhd_v1.json's
and af_placeholder_v1.json's echo_status/mitral_stenosis_severity/
prosthetic_valve for the canonical version) so the question behaves the same
regardless of which module asks it first."""

from __future__ import annotations

from app.models_protocol import FieldDef, Option

RISK_FACTOR_FIELD_IDS: list[str] = [
    "htn_dx", "htn_uncontrolled", "known_cad", "prior_mi", "stroke", "tia_only",
    "ckd", "hepatic", "diabetes", "current_smoker", "chf", "vascular_disease", "obesity",
]
"""Split deliberately, not topically merged: htn_dx (CHA2DS2-VASc wants
'diagnosed hypertensive') != htn_uncontrolled (HAS-BLED wants 'currently
uncontrolled', and Angina's potentiating-factor screen wants this same
answer -- asked once, used twice). known_cad != prior_mi (Angina's T4
routing wants a clinical CAD diagnosis; CHA2DS2-VASc's vascular-disease
point wants a prior infarction specifically -- not always the same patient).
stroke != tia_only (both feed AF's anticoagulation checklist, as separate
factors -- deliberately not the validated weighted score, so no merging
motivation there either). ckd != hepatic (HAS-BLED-style checklists want
renal OR hepatic as independently-checkable factors, not a combined one)."""


SHARED_FIELDS: dict[str, FieldDef] = {
    f.id: f
    for f in [
        FieldDef(id="htn_dx", label="Hypertension", field_type="boolean", input_source="history",
                  description="Has the patient ever been diagnosed with hypertension?"),
        FieldDef(id="htn_uncontrolled", label="Hypertension currently uncontrolled", field_type="boolean",
                  input_source="history", description="Is it poorly controlled right now, regardless of when diagnosed?"),
        FieldDef(id="known_cad", label="Known coronary artery disease", field_type="boolean", input_source="history"),
        FieldDef(id="diabetes", label="Diabetes mellitus", field_type="boolean", input_source="history"),
        FieldDef(id="current_smoker", label="Current smoker", field_type="boolean", input_source="history"),
        FieldDef(id="prior_mi", label="Prior myocardial infarction", field_type="boolean", input_source="history"),
        FieldDef(id="stroke", label="Prior stroke", field_type="boolean", input_source="history",
                  description="A completed stroke, not a TIA — that's the next question."),
        FieldDef(id="tia_only", label="Prior TIA (no completed stroke)", field_type="boolean", input_source="history"),
        FieldDef(id="ckd", label="Chronic kidney disease / significant renal impairment", field_type="boolean",
                  input_source="investigation", description="From renal function tests, if available."),
        FieldDef(id="hepatic", label="Significant hepatic impairment", field_type="boolean", input_source="investigation"),
        FieldDef(id="chf", label="CHF or LV dysfunction", field_type="boolean", input_source="history"),
        FieldDef(id="vascular_disease", label="Vascular disease", field_type="boolean", input_source="history"),
        FieldDef(id="obesity", label="Obesity", field_type="boolean", input_source="examination"),
        # Valve assessment -- shared between Module F's (AF) anticoagulation track and
        # Module R (RHD), so a patient worked up for one doesn't get asked twice.
        FieldDef(
            id="echo_status",
            label="Echocardiogram",
            field_type="single_select",
            input_source="investigation",
            description="From the echocardiogram report. If none has been done, say so — the anticoagulation decision is blocked rather than guessed.",
            options=[
                Option(value="not_performed", label="Not performed"),
                Option(value="no_significant_lesion", label="No significant lesion"),
                Option(value="lesions_present", label="Lesions present"),
            ],
        ),
        FieldDef(
            id="mitral_stenosis_severity",
            label="Mitral stenosis severity",
            field_type="single_select",
            input_source="investigation",
            description="As graded on the echo report.",
            options=[
                Option(value="mild", label="Mild"),
                Option(value="moderate_or_severe", label="Moderate or severe"),
                Option(value="not_graded", label="Not graded"),
                Option(value="absent", label="Absent"),
            ],
            skip_when={"!=": [{"var": "shared.echo_status"}, "lesions_present"]},
        ),
        FieldDef(
            id="prosthetic_valve",
            label="Prosthetic valve",
            field_type="single_select",
            input_source="investigation",
            description="From the echo report or known surgical history.",
            options=[
                Option(value="mechanical", label="Mechanical"),
                Option(value="bioprosthetic", label="Bioprosthetic"),
                Option(value="none", label="None"),
            ],
            skip_when={
                "or": [
                    {"!=": [{"var": "shared.echo_status"}, "lesions_present"]},
                    {"in": [{"var": "shared.mitral_stenosis_severity"}, ["moderate_or_severe", "not_graded"]]},
                ]
            },
        ),
    ]
}

RISK_FACTOR_FIELDS: list[FieldDef] = [SHARED_FIELDS[fid] for fid in RISK_FACTOR_FIELD_IDS]
"""The shared-patient-core risk-factor screen (asked once, upfront, as its
own core-intake step) -- the FieldDef objects backing RISK_FACTOR_FIELD_IDS,
in display order."""
