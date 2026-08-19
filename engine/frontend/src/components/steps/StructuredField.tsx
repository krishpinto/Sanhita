import { useState } from "react";
import type { FieldDef } from "../../api/types";

export function StructuredField({
  field,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  onAnswer: (value: Record<string, unknown> | null) => void;
  busy: boolean;
}) {
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const set = (id: string, value: unknown) => setDraft((prev) => ({ ...prev, [id]: value }));

  return (
    <div>
      <div className="sub-grid">
        {field.sub_fields.map((sf) => (
          <div key={sf.id} className="field-block" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: 12.5, fontWeight: 500, display: "block", marginBottom: 6 }}>
              {sf.label}
              {!sf.required && <span style={{ color: "var(--ink3)", fontWeight: 400 }}> (optional)</span>}
            </label>
            {sf.field_type === "boolean" && (
              <div className="yn">
                <button
                  type="button"
                  className={draft[sf.id] === true ? "on" : ""}
                  onClick={() => set(sf.id, true)}
                >
                  Yes
                </button>
                <button
                  type="button"
                  className={draft[sf.id] === false ? "on" : ""}
                  onClick={() => set(sf.id, false)}
                >
                  No
                </button>
              </div>
            )}
            {sf.field_type === "single_select" && (
              <select
                className="text-input"
                value={(draft[sf.id] as string) ?? ""}
                onChange={(e) => set(sf.id, e.target.value || undefined)}
              >
                <option value="">—</option>
                {sf.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
            {sf.field_type === "number" && (
              <input
                type="number"
                onChange={(e) => set(sf.id, e.target.value === "" ? undefined : Number(e.target.value))}
              />
            )}
            {sf.field_type === "text" && <input type="text" onChange={(e) => set(sf.id, e.target.value)} />}
          </div>
        ))}
      </div>
      <div className="nav">
        <button className="btn" disabled={busy} onClick={() => onAnswer(draft)}>
          Save {field.label}
        </button>
        {!field.required && (
          <button className="btn skip" disabled={busy} onClick={() => onAnswer(null)}>
            Skip — not provided
          </button>
        )}
      </div>
    </div>
  );
}
