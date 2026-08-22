import { useState } from "react";
import { formatAnswer, type AnsweredQuestion, type AnswerTarget } from "../state/answers";
import { StepRenderer } from "./steps/StepRenderer";

// A block the clinician has finished. It collapses rather than disappearing.
//
// The engine moves on the moment a block's last question is answered, and for
// a while this screen moved with it -- the block simply went. Mid-consultation
// that reads as data loss, and it leaves no way to check what was entered.
// Collapsed it costs one line; expanded it reads back every answer, and every
// answer can still be changed from there.
export function CompletedGroupPanel({
  title,
  answers,
  pending,
  onAnswer,
}: {
  title: string;
  answers: AnsweredQuestion[];
  pending: Set<string>;
  onAnswer: (target: AnswerTarget, value: unknown) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="panel done-panel">
      <button type="button" className="done-head" onClick={() => setOpen((v) => !v)}>
        <span className="done-check" aria-hidden="true" />
        <span className="done-title">{title}</span>
        <span className="done-count mono">{answers.length} recorded</span>
        <span className="done-toggle mono">{open ? "hide" : "review or change"}</span>
      </button>

      {!open && (
        <div className="done-peek">
          {answers.map((a) => formatAnswer(a.field, a.value)).join(" · ")}
        </div>
      )}

      {open && (
        <div className="done-summary">
          {answers.map((a) => (
            <StepRenderer
              key={a.path}
              field={a.field}
              value={a.value}
              answered
              busy={pending.has(a.path)}
              onAnswer={(value) => onAnswer(a, value)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
