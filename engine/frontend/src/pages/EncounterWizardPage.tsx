import { useEffect, useState } from "react";
import { activateProtocol, getEncounterSummary, getNextStep, postAnswer } from "../api/client";
import type { EncounterSummary, FrontierFieldOut, NextStepResponse } from "../api/types";
import { FieldGroupPanel } from "../components/FieldGroupPanel";
import { ProgressHeader } from "../components/ProgressHeader";
import { ProtocolOfferBanner } from "../components/ProtocolOfferBanner";

type Kind = "gate" | "track-a" | "track-b" | "track" | "core" | "shared";
type Group = { key: string; title: string; description: string | null; kind: Kind; fields: FrontierFieldOut[] };

function groupFrontier(fields: FrontierFieldOut[]): Group[] {
  const groups = new Map<string, Group>();
  for (const f of fields) {
    const key = `${f.protocol_id}:${f.block_id}:${f.track_id ?? ""}`;
    if (!groups.has(key)) {
      let kind: Kind = "track";
      if (f.protocol_id === "core") kind = "core";
      else if (f.answer_path.startsWith("shared.")) kind = "shared";
      else if (f.track_id) {
        kind = /track_a|^t1/.test(f.track_id) ? "track-a" : /track_b|^t2/.test(f.track_id) ? "track-b" : "track";
      } else if (f.block_label.toLowerCase().includes("gate")) {
        kind = "gate";
      }
      const title = f.track_label ?? f.block_label;
      const description = f.track_description ?? f.block_description;
      groups.set(key, { key, title, description, kind, fields: [] });
    }
    groups.get(key)!.fields.push(f);
  }
  return Array.from(groups.values());
}

export function EncounterWizardPage({
  encounterId,
  token,
  onReadyForResult,
  onReset,
}: {
  encounterId: string;
  token: string;
  onReadyForResult: () => void;
  onReset: () => void;
}) {
  const [step, setStep] = useState<NextStepResponse | null>(null);
  const [summary, setSummary] = useState<EncounterSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSummary = () => {
    getEncounterSummary(encounterId, token)
      .then(setSummary)
      .catch(() => {});
  };

  const refresh = async () => {
    const result = await getNextStep(encounterId, token);
    setStep(result);
    refreshSummary();
  };

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, [encounterId]);

  const handleAnswer = async (path: string, value: unknown) => {
    setBusy(true);
    setError(null);
    try {
      const result = await postAnswer(encounterId, token, path, value);
      setStep(result);
      refreshSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleActivate = async (protocolId: string) => {
    setBusy(true);
    try {
      const result = await activateProtocol(encounterId, token, protocolId);
      setStep(result);
      refreshSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!step) return <div className="wrap">Loading…</div>;

  if (step.core_terminal) {
    return (
      <div className="wrap">
        <div className="result-head emergency">
          <div className="k mono">Hard exit</div>
          <h2>{step.core_terminal.headline}</h2>
        </div>
        <div className="nav">
          <button className="btn secondary" onClick={onReset}>
            New patient
          </button>
        </div>
      </div>
    );
  }

  const activeFrontierGroups = groupFrontier(step.active_protocols.flatMap((p) => p.frontier));
  const coreGroups = groupFrontier(step.core_frontier);

  return (
    <div className="wrap">
      <ProgressHeader summary={summary} step={step} />

      {error && (
        <div className="panel gate">
          <div className="field-label" style={{ color: "var(--danger)" }}>
            {error}
          </div>
        </div>
      )}

      {coreGroups.map((g) => (
        <FieldGroupPanel key={g.key} title={g.title} description={g.description} kind={g.kind} fields={g.fields} onAnswer={handleAnswer} busy={busy} />
      ))}

      {step.offered_protocols.map((offer) => (
        <ProtocolOfferBanner
          key={offer.protocol_id}
          offer={offer}
          busy={busy}
          onActivate={() => handleActivate(offer.protocol_id)}
        />
      ))}

      {step.active_protocols
        .filter((p) => p.status === "resolved")
        .map((p) => (
          <div className="panel" key={p.protocol_id}>
            <div className="eyebrow">{p.protocol_name} — resolved</div>
            <div className="field-label">{p.terminal?.headline}</div>
          </div>
        ))}

      {activeFrontierGroups.map((g) => (
        <FieldGroupPanel key={g.key} title={g.title} description={g.description} kind={g.kind} fields={g.fields} onAnswer={handleAnswer} busy={busy} />
      ))}

      {step.ready_for_result && (
        <div className="panel">
          <div className="nav" style={{ marginTop: 0 }}>
            <button className="btn" onClick={onReadyForResult}>
              View result
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
