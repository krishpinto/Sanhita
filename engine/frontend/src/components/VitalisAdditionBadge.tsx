export function VitalisAdditionBadge({ reason }: { reason?: string | null }) {
  return <span className="badge vitalis" title={reason ?? undefined}>Vitalis addition</span>;
}
