import type { DrugBlockOut, DrugEntryOut } from "../api/types";

function DrugRow({ entry }: { entry: DrugEntryOut }) {
  const struck = entry.state === "block" || entry.state === "quarantined";
  const reasons = [...entry.block_reasons, ...entry.caution_reasons];
  return (
    <div
      style={{
        padding: "10px 0",
        borderTop: "1px solid var(--line2)",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <span style={{ fontSize: 14, fontWeight: 500, textDecoration: struck ? "line-through" : "none", color: struck ? "var(--ink3)" : "var(--ink)" }}>
          {entry.name} <span className="mono" style={{ fontWeight: 400, color: "var(--ink2)" }}>{entry.dose}</span>
        </span>
        {entry.state === "block" && <span className="badge" style={{ borderColor: "var(--danger)", color: "var(--danger)" }}>blocked</span>}
        {entry.state === "caution" && <span className="badge" style={{ borderColor: "var(--warn)", color: "var(--warn)" }}>caution</span>}
        {entry.state === "quarantined" && <span className="badge">quarantined</span>}
      </div>
      {entry.note && <div style={{ fontSize: 12, color: "var(--ink3)" }}>{entry.note}</div>}
      {reasons.map((r, i) => (
        <div key={i} style={{ fontSize: 12, color: entry.state === "block" ? "var(--danger)" : "var(--warn)" }}>
          {r.reason}
          {r.vitalis_addition && <span className="badge vitalis" style={{ marginLeft: 6 }}>Vitalis addition</span>}
        </div>
      ))}
    </div>
  );
}

export function DrugBlockPanel({ block }: { block: DrugBlockOut }) {
  if (block.status === "not_applicable") return null;
  if (block.status === "pending") return null;

  const groups = new Map<string, DrugEntryOut[]>();
  for (const e of block.entries) {
    if (!groups.has(e.group_label)) groups.set(e.group_label, []);
    groups.get(e.group_label)!.push(e);
  }

  return (
    <div className="panel">
      <div className="eyebrow">{block.label}</div>
      {block.entries.length === 0 ? (
        <div style={{ fontSize: 13.5, color: "var(--ink2)" }}>No medication indicated for this routing.</div>
      ) : (
        Array.from(groups.entries()).map(([groupLabel, entries]) => (
          <div key={groupLabel} style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11.5, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--ink3)", marginBottom: 4 }}>
              {groupLabel}
            </div>
            {entries.map((e) => (
              <DrugRow key={e.id} entry={e} />
            ))}
          </div>
        ))
      )}
      {block.hidden_count > 0 && (
        <div className="unassessed-list">
          {block.hidden_count} item{block.hidden_count > 1 ? "s" : ""} not shown at the current facility tier.
        </div>
      )}
    </div>
  );
}
