// The Protocol Index — deterministic lookup, not a classifier. See README.md.

import { feverAdult } from '@/lib/protocols/fever-adult';
import type { ProtocolDefinition, ProtocolIndexEntry } from '@/types/protocol';

const REGISTRY: Record<string, ProtocolDefinition> = {
  'fever-adult': feverAdult,
};

const INDEX: ProtocolIndexEntry[] = [
  { complaint: 'fever', synonyms: ['temperature', 'pyrexia', 'high temperature'], protocolId: 'fever-adult', minAge: 12 },
];

/** Deterministic string match against the controlled vocabulary above — never a guess. */
export function lookupProtocol(complaintText: string, age?: number): ProtocolDefinition | null {
  const q = complaintText.trim().toLowerCase();
  if (!q) return null;
  const entry = INDEX.find((e) => {
    const matches = e.complaint === q || e.synonyms.includes(q);
    if (!matches) return false;
    if (e.minAge !== undefined && age !== undefined && age < e.minAge) return false;
    if (e.maxAge !== undefined && age !== undefined && age > e.maxAge) return false;
    return true;
  });
  return entry ? (REGISTRY[entry.protocolId] ?? null) : null;
}

/** Read-only lookup for displaying encounter outcome severity — not routing logic. */
export function getOutcome(protocolId: string, outcomeId: string) {
  return REGISTRY[protocolId]?.outcomes[outcomeId] ?? null;
}
