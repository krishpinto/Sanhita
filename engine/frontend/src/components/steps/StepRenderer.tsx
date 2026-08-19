import type { FrontierFieldOut } from "../../api/types";
import { InputSourceBadge } from "../InputSourceBadge";
import { VitalisAdditionBadge } from "../VitalisAdditionBadge";
import { BooleanField } from "./BooleanField";
import { DifferentialReviewField } from "./DifferentialReviewField";
import { MultiSelectField } from "./MultiSelectField";
import { SingleSelectField } from "./SingleSelectField";
import { StructuredField } from "./StructuredField";
import { TextField } from "./TextField";

// Switches purely on field_type -- no disease- or protocol-specific branch
// anywhere in this file. A new protocol's fields render here automatically.
export function StepRenderer({
  frontierField,
  onAnswer,
  busy,
}: {
  frontierField: FrontierFieldOut;
  onAnswer: (path: string, value: unknown) => void;
  busy: boolean;
}) {
  const { field, answer_path, suggested_value } = frontierField;
  const answer = (value: unknown) => onAnswer(answer_path, value);

  return (
    <div className="field-block">
      <div className="field-label">
        {field.label}
        <InputSourceBadge source={field.input_source} />
        {field.vitalis_addition && <VitalisAdditionBadge reason={field.vitalis_addition_reason} />}
      </div>
      {field.description && <div className="field-hint">{field.description}</div>}
      {field.field_type === "boolean" && <BooleanField onAnswer={answer} busy={busy} />}
      {field.field_type === "single_select" && (
        <SingleSelectField field={field} onAnswer={answer} busy={busy} suggestedValue={suggested_value} />
      )}
      {field.field_type === "multi_select" && <MultiSelectField field={field} onAnswer={answer} busy={busy} />}
      {field.field_type === "text" && <TextField field={field} onAnswer={answer} busy={busy} />}
      {field.field_type === "number" && <TextField field={field} onAnswer={answer} busy={busy} numeric />}
      {(field.field_type === "structured_ecg" || field.field_type === "structured_vitals") && (
        <StructuredField field={field} onAnswer={answer} busy={busy} />
      )}
      {field.field_type === "differential_review" && (
        <DifferentialReviewField field={field} onAnswer={answer} busy={busy} />
      )}
    </div>
  );
}
