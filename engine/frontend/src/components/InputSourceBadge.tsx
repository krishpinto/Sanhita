import { INPUT_SOURCE_LABELS, type InputSource } from "../api/types";

const ICON: Record<InputSource, string> = {
  history: "🗣",
  examination: "🩺",
  investigation: "🔬",
  clinical_judgement: "🧠",
};

// Removes any ambiguity about where an answer should come from -- ask the
// patient, examine them, read it off a report, or use clinical judgement.
export function InputSourceBadge({ source }: { source: InputSource | null }) {
  if (!source) return null;
  return (
    <span className="badge" style={{ marginLeft: 8 }}>
      {ICON[source]} {INPUT_SOURCE_LABELS[source]}
    </span>
  );
}
