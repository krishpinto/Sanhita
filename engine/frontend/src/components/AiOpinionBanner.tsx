import { useState } from "react";
import { requestAiOpinion } from "../api/client";
import type { ResultPayload } from "../api/types";

export function AiOpinionBanner({
  encounterId,
  token,
  aiOpinion,
  onUpdated,
}: {
  encounterId: string;
  token: string;
  aiOpinion: ResultPayload["ai_opinion"];
  onUpdated: (opinion: ResultPayload["ai_opinion"]) => void;
}) {
  const [busy, setBusy] = useState(false);

  const request = async () => {
    setBusy(true);
    try {
      const res = await requestAiOpinion(encounterId, token);
      onUpdated({
        provider: res.provider,
        status: res.status,
        content: res.content,
        reason: res.reason,
        requested_at: new Date().toISOString(),
        responded_at: new Date().toISOString(),
      });
    } finally {
      setBusy(false);
    }
  };

  if (!aiOpinion) {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--ink2)" }}>
          Optional. Generates a short second opinion from an AI model, shown alongside — never in place
          of — the rule engine's routing above.
        </p>
        <button className="btn secondary" disabled={busy} onClick={request}>
          {busy ? "Requesting…" : "Get AI second opinion"}
        </button>
      </div>
    );
  }

  if (aiOpinion.status === "unavailable") {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--ink3)" }}>
          Not configured on this deployment (no API key set). The rest of the tool works normally
          without it.
        </p>
      </div>
    );
  }

  if (aiOpinion.status === "error") {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--danger)" }}>Request failed: {aiOpinion.reason}</p>
        <button className="btn secondary" disabled={busy} onClick={request}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="ai-banner">
      <div className="eyebrow" style={{ color: "var(--warn)" }}>
        AI second opinion — {aiOpinion.provider}
      </div>
      <div style={{ whiteSpace: "pre-wrap" }}>{aiOpinion.content}</div>
      <div className="disclaimer">
        This is AI-generated, not a diagnosis. It is a suggestion for you to weigh alongside your own
        clinical judgement — agree with it or disregard it as you see fit.
      </div>
    </div>
  );
}
