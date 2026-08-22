import { useEffect, useState } from "react";
import type { FieldDef } from "../../api/types";

// A mini-form (ECG, vitals) recorded as one unit, so this one keeps an
// explicit submit -- a half-entered tracing should not reach the engine. It
// reopens with whatever was recorded last, so a correction means changing one
// box rather than re-entering the whole panel.
export function StructuredField({
  field,
  value,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  value: unknown;
  onAnswer: (value: Record<string, unknown> | null) => void;
  busy: boolean;
}) {
  const committed = (value ?? null) as Record<string, unknown> | null;
  const [draft, setDraft] = useState<Record<string, unknown>>(committed ?? {});

  useEffect(() => {
    if (committed) setDraft(committed);
  }, [value]);

  const set = (id: string, v: unknown) => setDraft((prev) => ({ ...prev, [id]: v }));

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
                <button type="button" className={draft[sf.id] === true ? "on" : ""} onClick={() => set(sf.id, true)}>
                  Yes
                </button>
                <button type="button" className={draft[sf.id] === false ? "on" : ""} onClick={() => set(sf.id, false)}>
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
                value={(draft[sf.id] as number | undefined) ?? ""}
                onChange={(e) => set(sf.id, e.target.value === "" ? undefined : Number(e.target.value))}
              />
            )}
            {sf.field_type === "text" && (
              <input
                type="text"
                value={(draft[sf.id] as string) ?? ""}
                onChange={(e) => set(sf.id, e.target.value)}
              />
            )}
          </div>
        ))}
      </div>
      <div className="nav">
        <button className="btn" disabled={busy} onClick={() => onAnswer(draft)}>
          Record {field.label.toLowerCase()}
        </button>
        {!field.required && (
          <button className="btn skip" disabled={busy} onClick={() => onAnswer(null)}>
            Not available
          </button>
        )}
      </div>
    </div>
  );
}
