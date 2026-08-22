import type { DifferentialAudit } from "../api/types";

const TIER_LABEL: Record<number, string> = { 1: "Tier 1 — must not miss", 2: "Tier 2 — consider", 3: "Tier 3 — common" };

// Four states, not two. "Ruled out" is the only one that means the item is
// gone; "unlikely" and "still open" both keep it on the list, and the
// difference between them is why it is still there.
const STATUS_LABEL: Record<string, string> = {
  excluded: "ruled out",
  promoted: "promoted",
  pending_confirmation: "unlikely",
  raised: "still open",
};

const STATUS_COLOUR: Record<string, string> = {
  excluded: "var(--ink3)",
  promoted: "var(--danger)",
  pending_confirmation: "var(--warn)",
  raised: "var(--warn)",
};

// "Not considered" can never look like "considered and cleared" -- every
// raised item is shown here regardless of whether it survived or was
// excluded by the clinician.
export function DifferentialAuditPanel({ audit }: { audit: DifferentialAudit }) {
  const byTier = new Map<number, typeof audit.items>();
  for (const item of audit.items) {
    if (!byTier.has(item.tier)) byTier.set(item.tier, []);
    byTier.get(item.tier)!.push(item);
  }

  return (
    <div className="panel">
      <div className="eyebrow">Differential audit — what was considered</div>
      <div style={{ fontSize: 13, color: "var(--ink2)", marginBottom: 10 }}>
        Symptoms: {audit.symptoms.map((s) => s.replace(/_/g, " ")).join(" · ")}
      </div>
      <div style={{ fontSize: 12, color: "var(--ink2)", marginBottom: 12 }}>
        <div style={{ fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)", marginBottom: 4 }}>
          Findings recorded
        </div>
        {audit.findings.map((f) => (
          <div key={f.id} style={{ display: "flex", gap: 8 }}>
            <span className="mono" style={{ width: 96, flex: "none", color: f.answer === null ? "var(--warn)" : "var(--ink3)" }}>
              {f.answer === null ? "not checked" : f.answer ? "yes" : "no"}
            </span>
            <span>
              {f.short_label}
              {f.carried_from_symptom && f.answer === true && (
                <span style={{ color: "var(--ink3)" }}> — carried from the symptom screen</span>
              )}
            </span>
          </div>
        ))}
      </div>
      {[1, 2, 3].map((tier) =>
        byTier.has(tier) ? (
          <div key={tier} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink3)", marginBottom: 6 }}>
              {TIER_LABEL[tier]}
            </div>
            {byTier.get(tier)!.map((item) => (
              <div className="li" key={item.id} style={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                  <span className="m mono" style={{ color: STATUS_COLOUR[item.status] ?? "var(--ink2)" }}>
                    {STATUS_LABEL[item.status] ?? item.status}
                  </span>
                  <span style={{ textDecoration: item.status === "excluded" ? "line-through" : "none", color: item.status === "excluded" ? "var(--ink3)" : "var(--ink)" }}>
                    {item.label}
                  </span>
                </div>
                <span style={{ fontSize: 11.5, color: "var(--ink3)" }}>{item.reason}</span>
              </div>
            ))}
          </div>
        ) : null
      )}
    </div>
  );
}
