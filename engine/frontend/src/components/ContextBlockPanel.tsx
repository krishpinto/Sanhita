import type { ContextBlockOut } from "../api/types";

function fmt(value: unknown): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  if (value === null || value === undefined) return "—";
  return String(value);
}

// render_hint="flag_positive" (e.g. potentiating factors): true answers are
// pulled out as an "address first" list. render_hint="plain": an ordinary
// key/value list. Neither ever scores or gates a track resolution.
export function ContextBlockPanel({ block }: { block: ContextBlockOut }) {
  const entries = Object.entries(block.fields);
  if (block.render_hint === "flag_positive") {
    const positive = entries.filter(([, v]) => v === true);
    return (
      <div className="panel">
        <div className="eyebrow">{block.label}</div>
        {positive.length === 0 ? (
          <div style={{ fontSize: 13.5, color: "var(--ink3)" }}>None present.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {positive.map(([id]) => (
              <li key={id} style={{ fontSize: 14, marginBottom: 4 }}>
                {id.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="eyebrow">{block.label}</div>
      {entries.map(([id, value]) => (
        <div className="axis-row" key={id}>
          <span className="lbl">{id.replace(/_/g, " ")}</span>
          <span className="st">{fmt(value)}</span>
        </div>
      ))}
    </div>
  );
}
