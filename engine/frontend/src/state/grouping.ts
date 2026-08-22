import type { FrontierFieldOut } from "../api/types";

// How a block is presented. Kept here rather than in a component because both
// the live panels and the collapsed "already answered" strips need to agree on
// which block a field belongs to -- if they disagree, an answered question
// appears in one place and vanishes from the other.
export type GroupKind = "gate" | "track-a" | "track-b" | "track" | "core" | "shared";

export function groupKeyOf(f: FrontierFieldOut): string {
  return `${f.protocol_id}:${f.block_id}:${f.track_id ?? ""}`;
}

export function groupTitleOf(f: FrontierFieldOut): string {
  return f.track_label ?? f.block_label;
}

export function groupDescriptionOf(f: FrontierFieldOut): string | null {
  return f.track_description ?? f.block_description;
}

export function groupKindOf(f: FrontierFieldOut): GroupKind {
  if (f.protocol_id === "core") return "core";
  if (f.answer_path.startsWith("shared.")) return "shared";
  if (f.track_id) {
    if (/track_a|^t1/.test(f.track_id)) return "track-a";
    if (/track_b|^t2/.test(f.track_id)) return "track-b";
    return "track";
  }
  if (f.block_label.toLowerCase().includes("gate")) return "gate";
  return "track";
}
