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

// Symptoms in, differential out. Every item the symptom set raised is shown
// with one factual yes/no discriminator question -- the doctor answers what
// they observe, the engine decides what survives. No free-form "exclude
// this" judgement call: an item is only ruled out when its discriminator is
// answered No, and anything left unanswered stays open, never silently
// dropped.
export function DifferentialReviewField({
  field,
  onAnswer,
  busy,
}: {
  field: FieldDef;
  onAnswer: (answers: Record<string, boolean>) => void;
  busy: boolean;
}) {
  const [answers, setAnswers] = useState<Record<string, boolean>>({});

  const setAnswer = (id: string, value: boolean) => {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  };

  const clearAnswer = (id: string) => {
    setAnswers((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const byTier = new Map<number, DifferentialItemSpec[]>();
  for (const item of field.differential_items) {
    if (!byTier.has(item.tier)) byTier.set(item.tier, []);
    byTier.get(item.tier)!.push(item);
  }

  const survivingModules = new Set(
    field.differential_items.filter((i) => i.module && answers[i.id] !== false).map((i) => i.module as string)
  );

  return (
    <div>
      {[1, 2, 3].map((tier) =>
        byTier.has(tier) ? (
          <div key={tier} style={{ marginBottom: 18 }}>
            <div className="eyebrow" style={{ marginBottom: 8 }}>
              {TIER_LABEL[tier]}
              {tier === 1 && (
                <span style={{ color: "var(--danger)", marginLeft: 8, textTransform: "none", letterSpacing: 0 }}>
                  — no confirmatory pathway in this build; stays listed, never goes silent
                </span>
              )}
            </div>
            {byTier.get(tier)!.map((item) => {
              const answer = answers[item.id];
              const isExcluded = answer === false;
              return (
                <div key={item.id} className="axis-row" style={{ alignItems: "flex-start", padding: "10px 0" }}>
                  <span className={"dot " + (isExcluded ? "skipped" : answer === true ? "positive" : item.module ? "unknown" : "unknown")} />
                  <span style={{ flex: 1 }}>
                    <div
                      style={{
                        fontWeight: 500,
                        fontSize: 14,
                        textDecoration: isExcluded ? "line-through" : "none",
                        color: isExcluded ? "var(--ink3)" : "var(--ink)",
                      }}
                    >
                      {item.label}
                      {item.module && !isExcluded && <span className="badge" style={{ marginLeft: 8 }}>opens module</span>}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--ink2)", marginTop: 3 }}>
                      {item.discriminator_question}
                      <span style={{ marginLeft: 6, fontSize: 10, color: "var(--ink3)" }}>
                        {ICON[item.discriminator_input_source]} {INPUT_SOURCE_LABELS[item.discriminator_input_source]}
                      </span>
                    </div>
                  </span>
                  <span className="yn" style={{ flex: "none" }}>
                    <button type="button" className={answer === true ? "on" : ""} disabled={busy} onClick={() => setAnswer(item.id, true)}>
                      Yes
                    </button>
                    <button type="button" className={answer === false ? "on" : ""} disabled={busy} onClick={() => setAnswer(item.id, false)}>
                      No
                    </button>
                    {answer !== undefined && (
                      <button type="button" disabled={busy} onClick={() => clearAnswer(item.id)} title="Not yet assessed">
                        ?
                      </button>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
        ) : null
      )}

      <div className="unassessed-list" style={{ marginBottom: 14 }}>
        Currently surviving: {survivingModules.size === 0 ? "no confirmatory module" : Array.from(survivingModules).join(", ")}
      </div>

      <div className="nav" style={{ marginTop: 0 }}>
        <button className="btn" disabled={busy} onClick={() => onAnswer(answers)}>
          Confirm differential
        </button>
      </div>
    </div>
  );
}
