import { useState } from "react";
import type { FieldDef, InputSource } from "../../api/types";
import { InputSourceBadge } from "../InputSourceBadge";
import { VitalisAdditionBadge } from "../VitalisAdditionBadge";
import { AnsweredValue } from "./AnsweredValue";
import { BooleanField } from "./BooleanField";
import { DifferentialReviewField } from "./DifferentialReviewField";
import { FindingsReviewField } from "./FindingsReviewField";
import { MultiSelectField } from "./MultiSelectField";
import { SingleSelectField } from "./SingleSelectField";
import { StructuredField } from "./StructuredField";
import { TextField } from "./TextField";

// Switches purely on field_type -- no disease- or protocol-specific branch
// anywhere in this file. A new protocol's fields render here automatically.
//
// Three states, not two. Outstanding: the live control. Answered: a settled
// record of what was entered, which stays on screen -- the engine drops a
// field from its frontier the moment it is answered, and rendering that
// frontier literally made questions vanish from under the clinician
// mid-consultation. Answered-and-being-changed: the same live control again,
// seeded with what is currently recorded, reached only by an explicit tap.
export function StepRenderer({
  field,
  value,
  answered,
  suggestedValue,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  value: unknown;
  answered: boolean;
  suggestedValue?: unknown;
  onAnswer: (value: unknown) => void;
  busy: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const live = !answered || editing;

  const commit = (next: unknown) => {
    setEditing(false);
    onAnswer(next);
  };

  const wide =
    live &&
    (field.field_type === "findings_review" ||
      field.field_type === "differential_review" ||
      field.field_type === "structured_ecg" ||
      field.field_type === "structured_vitals");

  return (
    <div className={"q-row" + (answered && !editing ? " answered" : "") + (wide ? " wide" : "")}>
      <span className="q-state" aria-hidden="true" />
      <div className="q-body">
        <div className="field-label">
          {field.label}
          <InputSourceBadge source={field.input_source as InputSource} />
          {field.vitalis_addition && <VitalisAdditionBadge reason={field.vitalis_addition_reason} />}
        </div>
        {live && field.description && <div className="field-hint">{field.description}</div>}

        {editing && (
          <div className="editing-note">
            Changing a recorded answer. The previous one stays in the encounter record.
            <button type="button" className="cancel-btn" onClick={() => setEditing(false)}>
              keep it as it is
            </button>
          </div>
        )}

        {!live ? (
          <AnsweredValue field={field} value={value} onEdit={() => setEditing(true)} />
        ) : (
          <>
            {field.field_type === "boolean" && <BooleanField value={value} onAnswer={commit} busy={busy} />}
            {field.field_type === "single_select" && (
              <SingleSelectField
                field={field}
                value={value}
                onAnswer={commit}
                busy={busy}
                suggestedValue={suggestedValue}
              />
            )}
            {field.field_type === "multi_select" && (
              <MultiSelectField field={field} value={value} onAnswer={commit} busy={busy} />
            )}
            {field.field_type === "text" && (
              <TextField field={field} value={value} onAnswer={commit} busy={busy} />
            )}
            {field.field_type === "number" && (
              <TextField field={field} value={value} onAnswer={commit} busy={busy} numeric />
            )}
            {(field.field_type === "structured_ecg" || field.field_type === "structured_vitals") && (
              <StructuredField field={field} value={value} onAnswer={commit} busy={busy} />
            )}
            {field.field_type === "differential_review" && (
              <DifferentialReviewField field={field} onAnswer={commit} busy={busy} />
            )}
            {field.field_type === "findings_review" && (
              <FindingsReviewField field={field} value={value} onAnswer={commit} busy={busy} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
