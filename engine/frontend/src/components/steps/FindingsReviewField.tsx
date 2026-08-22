import { useState } from "react";
import type { DifferentialItemSpec, FieldDef, InputSource } from "../../api/types";
import { INPUT_SOURCE_LABELS } from "../../api/types";

const TIER_LABEL: Record<number, string> = {
  1: "Tier 1 — Must not miss",
  2: "Tier 2 — Consider",
  3: "Tier 3 — Common, and commonly the answer",
};

const ICON: Record<InputSource, string> = {
  history: "🗣",
  examination: "🩺",
  investigation: "🔬",
  clinical_judgement: "🧠",
};

const POLICY_NOTE: Record<string, string> = {
  confirm: "needs a deliberate confirmation before it can drop",
  never: "cannot be cleared at the bedside",
};

// The doctor reports observations; the engine does the ruling out.
//
// The screen has two halves. Above: every possibility the symptom set raised,
// read-only, worst-first -- nothing here is a checkbox, because deciding to
// exclude something is not the same act as observing a finding. Below: the
// handful of shared findings that settle them, each answerable Yes, No, or
// left blank. Blank is a real third state and stays blank: an unanswered
// finding leaves everything hanging off it standing, and is never counted as
// normal.
//
// No verdict is computed here. The client deliberately holds no exclusion
// logic -- it posts the findings and the backend returns what survived.
export function FindingsReviewField({
  field,
  value,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  value?: unknown;
  onAnswer: (answers: Record<string, boolean>) => void;
  busy: boolean;
}) {
  // Seeded from what is already recorded when the clinician has come back to
  // change a finding -- reopening this screen must not silently blank the
  // other eight observations they already made.
  const [answers, setAnswers] = useState<Record<string, boolean>>(
    value && typeof value === "object"
      ? { ...(value as Record<string, boolean>) }
      : Object.fromEntries(field.findings.filter((f) => f.prefilled).map((f) => [f.id, true]))
  );

  const setAnswer = (id: string, value: boolean) => setAnswers((prev) => ({ ...prev, [id]: value }));
  const clearAnswer = (id: string) =>
    setAnswers((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });

  const byTier = new Map<number, DifferentialItemSpec[]>();
  for (const item of field.differential_items) {
    if (!byTier.has(item.tier)) byTier.set(item.tier, []);
    byTier.get(item.tier)!.push(item);
  }

  const answered = field.findings.filter((f) => answers[f.id] !== undefined).length;

  return (
    <div>
      {[1, 2, 3].map((tier) =>
        byTier.has(tier) ? (
          <div key={tier} style={{ marginBottom: 14 }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>
              {TIER_LABEL[tier]}
            </div>
            {byTier.get(tier)!.map((item) => (
              <div key={item.id} className="axis-row" style={{ alignItems: "flex-start", padding: "6px 0" }}>
                <span className={"dot " + (item.module ? "unknown" : "skipped")} />
                <span style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, fontSize: 13.5 }}>
                    {item.label}
                    {item.module && (
                      <span className="badge" style={{ marginLeft: 8 }}>
                        opens module
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--ink3)", marginTop: 2 }}>
                    settled by: {item.discriminator_question}
                    {POLICY_NOTE[item.exclusion_policy] && (
                      <span style={{ color: "var(--warn)" }}> — {POLICY_NOTE[item.exclusion_policy]}</span>
                    )}
                  </div>
                </span>
              </div>
            ))}
          </div>
        ) : null
      )}

      <div className="eyebrow" style={{ marginTop: 20, marginBottom: 8 }}>
        What you observed — {answered} of {field.findings.length} recorded
      </div>

      {field.findings.map((f) => {
        const answer = answers[f.id];
        return (
          <div key={f.id} className="axis-row" style={{ alignItems: "flex-start", padding: "10px 0" }}>
            <span className={"dot " + (answer === undefined ? "unknown" : answer ? "positive" : "skipped")} />
            <span style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, fontSize: 14 }}>
                {f.question}
                {f.promotes_only && (
                  <span className="badge" style={{ marginLeft: 8 }}>
                    optional
                  </span>
                )}
                {f.prefilled && (
                  <span className="badge" style={{ marginLeft: 8 }}>
                    carried from symptoms
                  </span>
                )}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--ink3)", marginTop: 3 }}>
                {ICON[f.input_source]} {INPUT_SOURCE_LABELS[f.input_source]} · settles: {f.resolves.join(", ")}
              </div>
              {f.help && <div style={{ fontSize: 11.5, color: "var(--ink2)", marginTop: 3 }}>{f.help}</div>}
            </span>
            <span className="yn" style={{ flex: "none" }}>
              <button type="button" className={answer === true ? "on" : ""} disabled={busy} onClick={() => setAnswer(f.id, true)}>
                Yes
              </button>
              <button type="button" className={answer === false ? "on" : ""} disabled={busy} onClick={() => setAnswer(f.id, false)}>
                No
              </button>
              <button
                type="button"
                className={answer === undefined ? "on" : ""}
                disabled={busy}
                onClick={() => clearAnswer(f.id)}
                title="Not yet assessed — leaves everything this settles standing"
              >
                ?
              </button>
            </span>
          </div>
        );
      })}

      <div className="nav" style={{ marginTop: 14 }}>
        <button className="btn" disabled={busy} onClick={() => onAnswer(answers)}>
          Record findings
        </button>
      </div>
    </div>
  );
}
