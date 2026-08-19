// Types for the Protocol Definition / Protocol Engine / Encounter Record.
// See ../../README.md for the full explanation of each shape.

export type AnswerType = 'choice' | 'value';

export interface NextRef {
  type: 'step' | 'outcome';
  id: string;
}

export interface ChoiceOption {
  label: string;
  next: NextRef;
  /** Marks this specific answer as a danger sign — checked the instant it's given. */
  dangerSign?: boolean;
}

export interface ValueBucket {
  /** Inclusive lower bound; omit for "anything below the next bucket's min". */
  min?: number;
  /** Exclusive upper bound; omit for "anything at or above min". */
  max?: number;
  next: NextRef;
}

export interface Step {
  id: string;
  answerType: AnswerType;
  question: string;
  /** answerType: 'choice' — always include an explicit Unknown/n.a. option. */
  options?: ChoiceOption[];
  /** answerType: 'value' — numeric buckets, in order. */
  buckets?: ValueBucket[];
  /** answerType: 'value' — where "don't know / can't measure" routes. Always present. */
  unknownNext?: NextRef;
  unit?: string;
}

export type Severity = 'urgent' | 'watch' | 'routine';

export interface Outcome {
  id: string;
  severity: Severity;
  likely: string;
  doNow: string[];
  tellPatient: string;
  referIf: string[];
  followUp: string;
  citations: Partial<Record<'doNow' | 'tellPatient' | 'referIf' | 'followUp', string>>;
}

export interface ProtocolDefinition {
  id: string;
  version: number;
  title: string;
  /** The Step every run starts at. */
  entryStepId: string;
  steps: Record<string, Step>;
  outcomes: Record<string, Outcome>;
}

// ---------------------------------------------------------------------------
// Protocol Index — deterministic lookup, not a classifier.
// ---------------------------------------------------------------------------

export interface ProtocolIndexEntry {
  complaint: string;
  synonyms: string[];
  protocolId: string;
  /** Optional age gate — e.g. an adult protocol vs a pediatric one for the same complaint. */
  minAge?: number;
  maxAge?: number;
}

// ---------------------------------------------------------------------------
// Index card — the one-time intake before any protocol opens.
// ---------------------------------------------------------------------------

export type Sex = 'Male' | 'Female' | 'Other';

export interface IndexCard {
  id: string;
  name: string;
  age?: string;
  sex?: Sex;
  /** Chief complaint, typed or picked — matched against the Protocol Index, never interpreted. */
  complaint: string;
  createdAt: number;
}

// ---------------------------------------------------------------------------
// Encounter Record — the audit trail. Immutable once the outcome is reached.
// ---------------------------------------------------------------------------

export interface AnsweredStep {
  stepId: string;
  /** Snapshot of the question text at the time it was asked — protocols change later, this must not. */
  question: string;
  answerLabel: string;
  dangerSign: boolean;
  answeredAt: number;
}

export interface EncounterRecord {
  id: string;
  indexCard: IndexCard;
  protocolId: string;
  protocolVersion: number;
  trail: AnsweredStep[];
  outcomeId: string | null;
  redFlagFired: boolean;
  startedAt: number;
  completedAt: number | null;
}
