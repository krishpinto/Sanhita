import type { FrontierFieldOut } from "../api/types";
import { StepRenderer } from "./steps/StepRenderer";

// One panel per (protocol, block, track) group of currently-askable fields.
// Rendering every active group at once -- not one field at a time -- is what
// lets parallel tracks (e.g. two evidence tracks for one disease) appear at
// equal visual weight, neither a fallback of the other.
export function FieldGroupPanel({
  title,
  description,
  kind,
  fields,
  onAnswer,
  busy,
}: {
  title: string;
  description?: string | null;
  kind: "gate" | "track-a" | "track-b" | "track" | "core" | "shared";
  fields: FrontierFieldOut[];
  onAnswer: (path: string, value: unknown) => void;
  busy: boolean;
}) {
  return (
    <div className={"panel " + kind}>
      <div className="eyebrow">{title}</div>
      {description && (
        <p style={{ fontSize: 13, color: "var(--ink2)", margin: "-2px 0 14px", lineHeight: 1.5 }}>{description}</p>
      )}
      {fields.map((f) => (
        <StepRenderer key={f.answer_path} frontierField={f} onAnswer={onAnswer} busy={busy} />
      ))}
    </div>
  );
}
