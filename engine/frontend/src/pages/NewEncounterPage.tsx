import { useState } from "react";
import { createEncounter } from "../api/client";

export function NewEncounterPage({ onCreated }: { onCreated: (encounterId: string, token: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const { encounter_id, access_token } = await createEncounter();
      onCreated(encounter_id, access_token);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="landing">
      <div>
        <div className="eyebrow" style={{ textAlign: "center" }}>
          Physician-facing decision support · demo
        </div>
        <h1 style={{ margin: "6px 0 0", fontSize: 26 }}>Vitalis</h1>
      </div>
      <p>
        Enter a patient's basic details, risk factors, symptoms, ECG and vitals. Symptoms in,
        differential out — the system raises a tiered list of possibilities with discriminators, you
        exclude what's ruled out, and the survivors decide which modules open. Ends with a routing
        recommendation you can confirm, override, or check against an AI-generated second opinion.
      </p>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <button className="btn" disabled={busy} onClick={start}>
        Start new patient encounter
      </button>
    </div>
  );
}
