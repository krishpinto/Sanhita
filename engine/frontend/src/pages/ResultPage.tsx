import { useEffect, useState } from "react";
import { getResult, postDoctorOpinion } from "../api/client";
import type { ProtocolResultOut, ResultPayload, TrackEvidenceOut } from "../api/types";
import { AiOpinionBanner } from "../components/AiOpinionBanner";
import { ContextBlockPanel } from "../components/ContextBlockPanel";
import { DerivedTagsList } from "../components/DerivedTagsList";
import { DifferentialAuditPanel } from "../components/DifferentialAuditPanel";
import { DrugBlockPanel } from "../components/DrugBlockPanel";

function statusDotClass(status: string): string {
  if (status === "true") return "true";
  if (status === "false") return "false";
  return status; // positive | negative | partial_negative | unknown | skipped
}

function TrackCard({ track }: { track: TrackEvidenceOut }) {
  return (
    <div className="track-block">
      <div className="bt">{track.label}</div>
      <div className={"bv" + (track.resolution === null ? " off" : "")}>
        {track.resolution ?? "not yet resolved"}
      </div>
      {Object.entries(track.per_field).map(([fieldId, entry]) => (
        <div className="axis-row" key={fieldId}>
          <span className={"dot " + statusDotClass(entry.status)} />
          <span className="lbl">{fieldId.replace(/_/g, " ")}</span>
          <span className={"st" + (entry.status === "unknown" ? " unknown" : "")}>{entry.status}</span>
        </div>
      ))}
    </div>
  );
}

function ProtocolResultCard({ result }: { result: ProtocolResultOut }) {
  const isEmergency = /emergency|ACS|STEMI|bleed/i.test(result.terminal?.code ?? "");
  return (
    <div>
      <div className={"result-head" + (isEmergency ? " emergency" : "")}>
        <div className="k mono">
          {result.protocol_name}
          {result.fidelity === "reduced_fidelity_placeholder" && <span className="badge placeholder">placeholder</span>}
        </div>
        <h2>{result.terminal?.headline}</h2>
        {result.fidelity_note && (
          <p style={{ color: "var(--warn)" }}>{result.fidelity_note}</p>
        )}
        <p>Decision support only. This is a routing recommendation, not a diagnosis.</p>
      </div>

      {result.tracks.length > 0 && (
        <div className="two-col" style={{ marginTop: 16 }}>
          {result.tracks.map((t) => (
            <TrackCard key={t.track_id} track={t} />
          ))}
        </div>
      )}

      {result.unassessed.length > 0 && (
        <div className="unassessed-list">
          Not assessed: {result.unassessed.map((u) => u.label).join(" · ")}
        </div>
      )}

      <div className="cite mono">{result.source_citation}</div>

      <DerivedTagsList tags={result.derived_tags} title="Flags" />

      {result.context_blocks.map((cb) => (
        <ContextBlockPanel key={cb.id} block={cb} />
      ))}

      {result.drug_blocks.map((db) => (
        <DrugBlockPanel key={db.id} block={db} />
      ))}
    </div>
  );
}

function DoctorOpinionForm({
  encounterId,
  token,
  existing,
}: {
  encounterId: string;
  token: string;
  existing: ResultPayload["doctor_opinion"];
}) {
  const [note, setNote] = useState(existing?.doctor_note ?? "");
  const [altDx, setAltDx] = useState(existing?.structured_alternate_diagnosis ?? "");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await postDoctorOpinion(encounterId, token, {
        doctor_note: note || null,
        structured_alternate_diagnosis: altDx || null,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div className="eyebrow">Your second opinion</div>
      <p style={{ fontSize: 13.5, color: "var(--ink2)" }}>
        If you agree with the routing above, no need to fill this in. If you don't — record what you
        think it is instead. This is never fed back into the engine.
      </p>
      <div className="field-block">
        <label style={{ fontSize: 12.5, fontWeight: 500, display: "block", marginBottom: 6 }}>
          Alternate diagnosis / impression
        </label>
        <input type="text" value={altDx} onChange={(e) => setAltDx(e.target.value)} />
      </div>
      <div className="field-block">
        <label style={{ fontSize: 12.5, fontWeight: 500, display: "block", marginBottom: 6 }}>Notes</label>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <div className="nav">
        <button className="btn secondary" disabled={busy} onClick={save}>
          {saved ? "Saved" : "Save"}
        </button>
      </div>
    </div>
  );
}

export function ResultPage({
  encounterId,
  token,
  onReset,
}: {
  encounterId: string;
  token: string;
  onReset: () => void;
}) {
  const [result, setResult] = useState<ResultPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getResult(encounterId, token)
      .then(setResult)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [encounterId]);

  if (error) {
    return (
      <div className="wrap">
        <p style={{ color: "var(--danger)" }}>{error}</p>
        <button className="btn secondary" onClick={onReset}>
          New patient
        </button>
      </div>
    );
  }
  if (!result) return <div className="wrap">Loading…</div>;

  if (result.core_terminal) {
    return (
      <div className="wrap">
        <div className="result-head emergency">
          <div className="k mono">Hard exit</div>
          <h2>{result.core_terminal.headline}</h2>
        </div>
        <div className="nav">
          <button className="btn secondary" onClick={onReset}>
            New patient
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="panel">
        <div className="eyebrow">Patient</div>
        <div style={{ fontSize: 14 }}>
          {result.core.name} · {result.core.age}{result.core.sex} · symptoms:{" "}
          {result.core.symptoms.map((s) => s.replace(/_/g, " ")).join(", ") || "none recorded"}
        </div>
      </div>

      {result.differential && <DifferentialAuditPanel audit={result.differential} />}

      {result.protocols.map((p) => (
        <ProtocolResultCard key={p.protocol_id} result={p} />
      ))}

      {result.unrun_protocols.length > 0 && (
        <div className="panel">
          <div className="eyebrow">Modules not run</div>
          {result.unrun_protocols.map((u) => (
            <div key={u.protocol_id} style={{ fontSize: 13.5, color: "var(--ink2)" }}>
              {u.name} — {u.reason === "offered_not_accepted" ? "offered, not started" : "activation criteria not met"}
            </div>
          ))}
        </div>
      )}

      <AiOpinionBanner
        encounterId={encounterId}
        token={token}
        aiOpinion={result.ai_opinion}
        onUpdated={(opinion) => setResult((prev) => (prev ? { ...prev, ai_opinion: opinion } : prev))}
      />

      <DoctorOpinionForm encounterId={encounterId} token={token} existing={result.doctor_opinion} />

      <div className="nav">
        <button className="btn secondary" onClick={onReset}>
          New patient
        </button>
      </div>
    </div>
  );
}
