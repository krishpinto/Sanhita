import type { EncounterSummary, NextStepResponse } from "../api/types";

// Doctors move through a long, branching encounter and can lose track of
// where they are (which is exactly what prompted this component). Everything
// it shows is derived from data the engine already returns -- no separate
// progress-tracking state to keep in sync.
const CORE_PHASE_LABELS: Record<string, string> = {
  facility_tier_step: "Setting",
  patient_details: "Patient details",
  risk_factors_step: "Risk factors",
  symptoms_step: "Presenting symptoms",
  differential_review: "Differential review",
  ecg_step: "ECG",
  vitals_step: "Vitals",
};

function currentPhase(step: NextStepResponse): string {
  if (step.core_terminal) return "Hard exit";
  if (step.core_frontier.length > 0) {
    const blockId = step.core_frontier[0].block_id;
    return CORE_PHASE_LABELS[blockId] ?? "Core intake";
  }
  const unresolved = step.active_protocols.filter((p) => p.status !== "resolved");
  if (unresolved.length > 0) {
    return `Assessing ${unresolved.map((p) => p.protocol_name).join(", ")}`;
  }
  if (step.ready_for_result) return "Ready for result";
  return "Core intake";
}

export function ProgressHeader({ summary, step }: { summary: EncounterSummary | null; step: NextStepResponse }) {
  const patientLabel = summary?.patient_name
    ? [summary.patient_name, [summary.patient_age, summary.patient_sex].filter(Boolean).join(" ")]
        .filter(Boolean)
        .join(" · ")
    : "Patient details pending";

  const chips = [
    ...step.active_protocols.map((p) => ({
      key: p.protocol_id,
      label: p.protocol_name,
      state: p.status === "resolved" ? "resolved" : "active",
    })),
    ...step.offered_protocols
      .filter((o) => !step.active_protocols.some((p) => p.protocol_id === o.protocol_id))
      .map((o) => ({ key: o.protocol_id, label: o.name, state: "offered" })),
  ];

  return (
    <div className="progress-header">
      <div className="progress-header-row">
        <span className="progress-patient">{patientLabel}</span>
        <span className="progress-phase">{currentPhase(step)}</span>
      </div>
      {chips.length > 0 && (
        <div className="progress-chips">
          {chips.map((c) => (
            <span key={c.key} className={`progress-chip ${c.state}`}>
              {c.label} · {c.state}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
