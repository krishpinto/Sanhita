import type { FrontierFieldOut } from "../api/types";
import { targetOf, type AnsweredQuestion, type AnswerTarget } from "../state/answers";
import type { GroupKind } from "../state/grouping";
import { StepRenderer } from "./steps/StepRenderer";

export interface QuestionRow {
  path: string;
  outstanding: FrontierFieldOut | null;
  answered: AnsweredQuestion | null;
}

// One panel per (protocol, block, track) group. Rendering every active group at
// once -- not one field at a time -- is what lets parallel tracks appear at
// equal visual weight, neither a fallback of the other.
//
// Rows include questions already answered in this block, not just outstanding
// ones. A clinician mid-consultation needs to see what they have just
// recorded, and to be able to fix it; a question that vanishes the instant it
// is answered gives them no way to check their own work.
export function FieldGroupPanel({
  title,
  description,
  kind,
  rows,
  pending,
  onAnswer,
}: {
  title: string;
  description?: string | null;
  kind: GroupKind;
  rows: QuestionRow[];
  pending: Set<string>;
  onAnswer: (target: AnswerTarget, value: unknown) => void;
}) {
  const done = rows.filter((r) => r.answered).length;

  return (
    <div className={"panel " + kind}>
      <div className="panel-head">
        <div className="eyebrow" style={{ marginBottom: 0 }}>
          {title}
        </div>
        {rows.length > 1 && (
          <span className="group-progress mono">
            {done} of {rows.length}
          </span>
        )}
      </div>
      {description && <p className="panel-desc">{description}</p>}
      {rows.map((row) => {
        const spec = row.outstanding;
        const target: AnswerTarget = spec ? targetOf(spec) : row.answered!;
        return (
          <StepRenderer
            key={row.path}
            field={target.field}
            value={row.answered ? row.answered.value : undefined}
            answered={row.answered !== null}
            suggestedValue={spec?.suggested_value}
            busy={pending.has(row.path)}
            onAnswer={(value) => onAnswer(target, value)}
          />
        );
      })}
    </div>
  );
}
