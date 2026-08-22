import { useState } from "react";
import type { AnswerLogEntry } from "../api/types";

// Everything the clinician entered, in the order they entered it.
//
// A routing recommendation whose inputs cannot be inspected is not decision
// support -- when a doctor disagrees with the outcome, the first question is
// always "what did it think I said?". This is the answer to that question.
//
// The rendering is the backend's, done at the moment each answer was
// submitted. Re-rendering it here against today's protocol would let the
// record drift as questions get reworded, and a record that shifts under you
// is not a record.
export function AnswerLogPanel({ log }: { log: AnswerLogEntry[] }) {
  const [open, setOpen] = useState(false);
  if (log.length === 0) return null;

  const questions = log.reduce((n, e) => n + e.entries.length, 0);
  const corrections = log.filter((e) => e.is_correction).length;

  // Consecutive entries from the same block read as one section, the way they
  // appeared on screen -- not as a flat list of paths.
  const sections: { label: string; entries: AnswerLogEntry[] }[] = [];
  for (const entry of log) {
    const label = entry.block_label ?? entry.field_label;
    const last = sections[sections.length - 1];
    if (last && last.label === label) last.entries.push(entry);
    else sections.push({ label, entries: [entry] });
  }

  return (
    <div className="panel">
      <button type="button" className="done-head" onClick={() => setOpen((v) => !v)}>
        <span className="done-title">What was entered</span>
        <span className="done-count mono">
          {questions} question{questions === 1 ? "" : "s"}
          {corrections > 0 && ` · ${corrections} changed`}
        </span>
        <span className="done-toggle mono">{open ? "hide" : "show"}</span>
      </button>

      {open && (
        <div className="answer-log">
          {sections.map((section, i) => (
            <div className="log-section" key={i}>
              <div className="eyebrow">{section.label}</div>
              {section.entries.map((entry) => (
                <div key={entry.seq}>
                  {entry.entries.map((row, j) => (
                    <div className="log-row" key={j}>
                      <span className="log-q">{row.question}</span>
                      <span className="log-a mono">{row.answer}</span>
                    </div>
                  ))}
                  {entry.previous_entries && (
                    <div className="log-was">
                      changed — previously{" "}
                      {entry.previous_entries.map((row) => row.answer).join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
