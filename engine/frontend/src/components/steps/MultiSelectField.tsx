import { useEffect, useState } from "react";
import type { FieldDef } from "../../api/types";

// Needs an explicit confirm, and legitimately so: "nothing applies" is a real
// answer, and there is no way to tell it apart from "not finished ticking yet".
// The button therefore states what it will record rather than saying "Save".
export function MultiSelectField({
  field,
  value,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  value: unknown;
  onAnswer: (value: string[]) => void;
  busy: boolean;
}) {
  const committed = Array.isArray(value) ? (value as string[]) : null;
  const [selected, setSelected] = useState<string[]>(committed ?? []);

  useEffect(() => {
    if (committed) setSelected(committed);
  }, [value]);

  const toggle = (v: string) =>
    setSelected((prev) => (prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]));

  const dirty = committed === null || committed.join("|") !== selected.join("|");

  return (
    <div>
      <div className="opts">
        {field.options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={"opt" + (selected.includes(opt.value) ? " on" : "")}
            disabled={busy}
            onClick={() => toggle(opt.value)}
          >
            <span className="tick" />
            <span>{opt.label}</span>
          </button>
        ))}
      </div>
      <div className="nav">
        <button className="btn" disabled={busy || !dirty} onClick={() => onAnswer(selected)}>
          {selected.length === 0 ? "Record: none apply" : `Record ${selected.length} selected`}
        </button>
        {!dirty && <span className="saved-mark">saved</span>}
      </div>
    </div>
  );
}
