import type { FieldDef } from "../../api/types";
import { formatAnswer } from "../../state/answers";

// What a question looks like once it has been answered: a settled record,
// with one way back into it.
//
// Changing your mind is an ordinary clinical act -- a pulse gets re-checked, a
// box was ticked by mistake -- so the answer has to be reachable again. It is
// deliberately not left as a live control, though: a row of buttons that still
// looks armed invites a stray tap on a finished question. One explicit
// "change" is the difference between correcting an answer and nudging one.
export function AnsweredValue({
  field,
  value,
  onEdit,
}: {
  field: FieldDef;
  value: unknown;
  onEdit?: () => void;
}) {
  return (
    <div className="answer-value">
      <span className="answer-text">{formatAnswer(field, value)}</span>
      <span className="saved-mark">recorded</span>
      {onEdit && (
        <button type="button" className="change-btn" onClick={onEdit}>
          change
        </button>
      )}
    </div>
  );
}
