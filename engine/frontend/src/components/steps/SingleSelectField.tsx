import type { FieldDef } from "../../api/types";

export function SingleSelectField({
  field,
  onAnswer,
  busy,
  suggestedValue,
}: {
  field: FieldDef;
  onAnswer: (value: string) => void;
  busy: boolean;
  suggestedValue?: unknown;
}) {
  return (
    <div className="opts">
      {field.options.map((opt) => (
        <button
          key={opt.value}
          className={"opt" + (suggestedValue === opt.value ? " on" : "")}
          disabled={busy}
          onClick={() => onAnswer(opt.value)}
        >
          <span className="tick" />
          <span>
            {opt.label}
            {suggestedValue === opt.value && (
              <span style={{ display: "block", fontSize: 11, color: "var(--ink3)", marginTop: 2 }}>
                suggested from another module — confirm or change
              </span>
            )}
          </span>
        </button>
      ))}
    </div>
  );
}
