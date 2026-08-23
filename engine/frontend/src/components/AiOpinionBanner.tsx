import { useState } from "react";
import { requestAiOpinion } from "../api/client";
import type { AiOpinionOut } from "../api/types";

/**
 * The model is asked for four fixed headings (see backend app/ai/briefing.py).
 * Rendering them as one grey wall of pre-wrap text is how a second opinion
 * gets skipped between patients -- VERDICT and WORTH A SECOND LOOK are the
 * two a doctor actually stops on, so they get to look like headings.
 *
 * If the model ignores the format, the whole answer falls through as one
 * unlabelled section and is still readable. Nothing is ever dropped.
 */
const HEADINGS = ["VERDICT", "READING", "WORTH A SECOND LOOK", "BEFORE YOU ACT"];

type Section = { heading: string | null; lines: string[] };

function parseSections(content: string): Section[] {
  const sections: Section[] = [];
  let current: Section = { heading: null, lines: [] };
  for (const raw of content.split("\n")) {
    const line = raw.trim();
    if (HEADINGS.includes(line.replace(/[:*#]/g, "").trim().toUpperCase())) {
      if (current.heading || current.lines.length) sections.push(current);
      current = { heading: line.replace(/[:*#]/g, "").trim().toUpperCase(), lines: [] };
    } else if (line) {
      current.lines.push(line);
    }
  }
  if (current.heading || current.lines.length) sections.push(current);
  return sections;
}

function OpinionBody({ content }: { content: string }) {
  const sections = parseSections(content);
  return (
    <div className="ai-sections">
      {sections.map((section, i) => {
        const bullets = section.lines.filter((l) => l.startsWith("-") || l.startsWith("•"));
        const prose = section.lines.filter((l) => !l.startsWith("-") && !l.startsWith("•"));
        return (
          <div className="ai-section" key={i}>
            {section.heading && <div className="ai-section-heading">{section.heading}</div>}
            {prose.map((line, j) => (
              <p key={j}>{line}</p>
            ))}
            {bullets.length > 0 && (
              <ul>
                {bullets.map((line, j) => (
                  <li key={j}>{line.replace(/^[-•]\s*/, "")}</li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function AiOpinionBanner({
  encounterId,
  token,
  aiOpinion,
  onUpdated,
}: {
  encounterId: string;
  token: string;
  aiOpinion: AiOpinionOut | null;
  onUpdated: (opinion: AiOpinionOut) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  const request = async () => {
    setBusy(true);
    setFailed(null);
    try {
      const res = await requestAiOpinion(encounterId, token);
      onUpdated({
        provider: res.provider,
        model: res.model,
        status: res.status,
        content: res.content,
        reason: res.reason,
        requested_at: new Date().toISOString(),
        responded_at: new Date().toISOString(),
      });
    } catch (err) {
      // A network failure here must not look like a clinical finding.
      setFailed(err instanceof Error ? err.message : "The request did not go through.");
    } finally {
      setBusy(false);
    }
  };

  const button = (label: string) => (
    <button className="btn secondary" disabled={busy} onClick={request}>
      {busy ? "Reading the encounter…" : label}
    </button>
  );

  if (busy) {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--ink2)" }}>
          Reading the whole encounter — every answer, the differential, and the routing. This usually
          takes ten to thirty seconds.
        </p>
        <button className="btn secondary" disabled>
          Reading the encounter…
        </button>
      </div>
    );
  }

  if (!aiOpinion || failed) {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--ink2)" }}>
          Optional. A second reader looks over everything you entered and says whether it agrees with
          the routing above, and what it would check before acting. It never replaces the routing.
        </p>
        {failed && <p style={{ fontSize: 13, color: "var(--danger)" }}>Could not reach it: {failed}</p>}
        {button(failed ? "Try again" : "Get AI second opinion")}
      </div>
    );
  }

  if (aiOpinion.status === "unavailable") {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--ink3)" }}>
          Not switched on for this deployment (no API key set). Everything else works normally
          without it.
        </p>
      </div>
    );
  }

  if (aiOpinion.status === "error" || !aiOpinion.content) {
    return (
      <div className="panel">
        <div className="eyebrow">AI second opinion</div>
        <p style={{ fontSize: 13.5, color: "var(--danger)" }}>
          {aiOpinion.reason ?? "The request failed."}
        </p>
        <p style={{ fontSize: 12.5, color: "var(--ink3)" }}>
          The routing above is unaffected — it comes from the rule engine, not the AI.
        </p>
        {button("Try again")}
      </div>
    );
  }

  return (
    <div className="ai-banner">
      <div className="eyebrow" style={{ color: "var(--warn)" }}>
        AI second opinion — {aiOpinion.model || aiOpinion.provider}
      </div>
      <OpinionBody content={aiOpinion.content} />
      <div className="disclaimer">
        This is AI-generated, not a diagnosis, and it did not decide the routing above. It is a
        suggestion for you to weigh alongside your own clinical judgement — agree with it or
        disregard it as you see fit.
      </div>
      <button className="btn secondary" style={{ marginTop: 12 }} onClick={request}>
        Ask again
      </button>
    </div>
  );
}
