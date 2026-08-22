import type { FieldDef } from "../../api/types";

export function SingleSelectField({
  field,
  value,
  onAnswer,
  busy,
  suggestedValue,
}: {
  field: FieldDef;
  value: unknown;
  onAnswer: (value: string) => void;
  busy: boolean;
  suggestedValue?: unknown;
}) {
  // An answered option stays lit. A suggestion carried from another module is
  // shown as a hint, never as a selection -- the clinician still has to choose.
  const answered = value !== undefined;
  return (
    <div className="opts">
      {field.options.map((opt) => {
        const chosen = value === opt.value;
        const suggested = !answered && suggestedValue === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            className={"opt" + (chosen ? " on" : "") + (suggested ? " suggested" : "")}
            disabled={busy}
            onClick={() => onAnswer(opt.value)}
          >
            <span className="tick" />
            <span>
              {opt.label}
              {suggested && <span className="opt-note">suggested from another module — confirm or change</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}
