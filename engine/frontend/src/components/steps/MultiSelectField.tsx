import { useState } from "react";
import type { FieldDef } from "../../api/types";

export function MultiSelectField({
  field,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  onAnswer: (value: string[]) => void;
  busy: boolean;
}) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (value: string) => {
    setSelected((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  };

  return (
    <div>
      <div className="opts">
        {field.options.map((opt) => (
          <button
            key={opt.value}
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
        <button className="btn" disabled={busy} onClick={() => onAnswer(selected)}>
          Save
        </button>
      </div>
    </div>
  );
}
