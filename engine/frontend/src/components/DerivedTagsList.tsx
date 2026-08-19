import type { DerivedTagOut } from "../api/types";

// Derived flags (e.g. Angina's negative features N1-N6, RHD's strep-evidence
// and referral flags) are display-only -- they never gate a track resolution.
// Only tags that resolved true are worth surfacing; false/unknown ones are
// noise for a doctor scanning the result.
export function DerivedTagsList({ tags, title }: { tags: DerivedTagOut[]; title: string }) {
  const positive = tags.filter((t) => t.value === true);
  if (positive.length === 0) return null;
  return (
    <div className="panel">
      <div className="eyebrow">{title}</div>
      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {positive.map((t) => (
          <li key={t.id} style={{ fontSize: 14, marginBottom: 4 }}>
            {t.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
