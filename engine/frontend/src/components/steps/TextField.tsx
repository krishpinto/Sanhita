import { useEffect, useState } from "react";
import type { FieldDef } from "../../api/types";

// Commits on blur or Enter -- no Save button.
//
// Every other control on the screen records an answer the moment the
// clinician acts on it. Making two fields out of thirteen require a separate
// confirming click made the form feel like two different forms.
export function TextField({
  field,
  value,
  onAnswer,
  busy,
  numeric,
}: {
  field: FieldDef;
  value: unknown;
  onAnswer: (value: string | number) => void;
  busy: boolean;
  numeric?: boolean;
}) {
  const committed = value === undefined || value === null ? "" : String(value);
  const [draft, setDraft] = useState(committed);

  // Follow the engine if the value changes underneath us (a re-answer landing,
  // or a prefill arriving from another module).
  useEffect(() => setDraft(committed), [committed]);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed === "" || trimmed === committed) return;
    if (numeric && Number.isNaN(Number(trimmed))) return;
    onAnswer(numeric ? Number(trimmed) : trimmed);
  };

  return (
    <div className="text-row">
      <input
        type={numeric ? "number" : "text"}
        value={draft}
        disabled={busy}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            (e.target as HTMLInputElement).blur();
          }
        }}
        placeholder={field.label}
      />
      {committed !== "" && draft === committed && <span className="saved-mark">saved</span>}
    </div>
  );
}
