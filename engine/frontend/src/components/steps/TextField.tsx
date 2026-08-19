import { useState } from "react";
import type { FieldDef } from "../../api/types";

export function TextField({
  field,
  onAnswer,
  busy,
  numeric,
}: {
  field: FieldDef;
  onAnswer: (value: string | number) => void;
  busy: boolean;
  numeric?: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (value === "") return;
    onAnswer(numeric ? Number(value) : value);
  };

  return (
    <div className="nav" style={{ marginTop: 0 }}>
      <input
        type={numeric ? "number" : "text"}
        value={value}
        disabled={busy}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
        placeholder={field.label}
      />
      <button className="btn" disabled={busy || value === ""} onClick={submit}>
        Save
      </button>
    </div>
  );
}
