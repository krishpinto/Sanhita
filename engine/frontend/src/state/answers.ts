import type { AnsweredFieldOut, FieldDef, FrontierFieldOut, NextStepResponse } from "../api/types";
import { groupKeyOf, groupKindOf, groupTitleOf, type GroupKind } from "./grouping";

// Everything needed to post an answer and put it back on the right panel.
//
// A question can be answered from two places -- the live frontier, or an
// already-answered row the clinician has gone back to change -- and both need
// the same handful of facts. Keeping them in one shape means the correction
// path is not a second, subtly different code path.
export interface AnswerTarget {
  path: string;
  field: FieldDef;
  groupKey: string;
  groupTitle: string;
  groupKind: GroupKind;
}

// A question the clinician has already answered.
//
// The engine returns a *frontier* -- the questions still outstanding -- and
// drops a field from it the moment it is answered. That is correct for the
// engine and wrong for the screen: rendering the frontier literally makes an
// answered question disappear from under the cursor. So the client keeps its
// own record of what it has answered and renders it alongside what is left.
//
// This ledger is a display aid only. The engine remains the sole authority on
// what has been recorded; nothing here is ever sent back as truth.
export interface AnsweredQuestion extends AnswerTarget {
  value: unknown;
}

export type Ledger = Map<string, AnsweredQuestion>;

export function targetOf(f: FrontierFieldOut): AnswerTarget {
  return {
    path: f.answer_path,
    field: f.field,
    groupKey: groupKeyOf(f),
    groupTitle: groupTitleOf(f),
    groupKind: groupKindOf(f),
  };
}

export function recordAnswer(ledger: Ledger, target: AnswerTarget, value: unknown): Ledger {
  const next = new Map(ledger);
  next.set(target.path, { ...target, value });
  return next;
}

// Rebuilds the ledger from what the engine says is answered.
//
// The engine is the authority, so this replaces rather than merges: an answer
// the engine no longer holds -- because correcting an earlier question
// invalidated it -- has to leave the screen too, or the clinician is looking
// at a finding that is no longer part of the encounter. It also means a
// reloaded page comes back with every recorded block intact, which is what
// makes "change an answer" work at all after a refresh.
export function hydrate(step: NextStepResponse): Ledger {
  const ledger: Ledger = new Map();
  const add = (a: AnsweredFieldOut) => {
    const target = targetOf(a);
    ledger.set(target.path, { ...target, value: a.value });
  };
  step.core_answered.forEach(add);
  for (const protocol of step.active_protocols) protocol.answered.forEach(add);
  return ledger;
}

// Renders an answer the way a clinician would read it back, for the collapsed
// summary of a finished block. Never shows a raw enum value.
export function formatAnswer(field: FieldDef, value: unknown): string {
  if (value === null || value === undefined) return "not provided";

  if (field.field_type === "boolean") return value === true ? "Yes" : "No";

  if (field.field_type === "single_select") {
    return field.options.find((o) => o.value === value)?.label ?? String(value);
  }

  if (field.field_type === "multi_select") {
    const chosen = Array.isArray(value) ? (value as string[]) : [];
    if (chosen.length === 0) return "none selected";
    return chosen.map((v) => field.options.find((o) => o.value === v)?.label ?? v).join(", ");
  }

  if (field.field_type === "findings_review") {
    const answers = (value ?? {}) as Record<string, boolean>;
    const recorded = Object.keys(answers).length;
    const total = field.findings.length;
    const blank = total - recorded;
    return blank === 0
      ? `${recorded} of ${total} recorded`
      : `${recorded} of ${total} recorded, ${blank} left unassessed`;
  }

  if (field.field_type === "structured_ecg" || field.field_type === "structured_vitals") {
    const entries = Object.entries((value ?? {}) as Record<string, unknown>).filter(
      ([, v]) => v !== undefined && v !== null && v !== ""
    );
    if (entries.length === 0) return "not provided";
    return entries
      .map(([k, v]) => {
        const sub = field.sub_fields.find((s) => s.id === k);
        const label = sub?.label ?? k.replace(/_/g, " ");
        if (sub?.field_type === "boolean") return `${label}: ${v === true ? "Yes" : "No"}`;
        if (sub?.field_type === "single_select") {
          return `${label}: ${sub.options.find((o) => o.value === v)?.label ?? String(v)}`;
        }
        return `${label}: ${String(v)}`;
      })
      .join(" · ");
  }

  return String(value);
}
