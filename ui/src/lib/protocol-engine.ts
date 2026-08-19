// The Protocol Engine — generic interpreter with zero medical knowledge.
// Loads a Protocol Definition, holds the current step + answer trail,
// resolves what's next. The same engine runs every protocol. See README.md.

import type { AnsweredStep, NextRef, Outcome, ProtocolDefinition, Step } from '@/types/protocol';

export interface EngineState {
  protocol: ProtocolDefinition;
  currentStepId: string | null;
  trail: AnsweredStep[];
  outcomeId: string | null;
  redFlagFired: boolean;
}

export function startEngine(protocol: ProtocolDefinition): EngineState {
  return {
    protocol,
    currentStepId: protocol.entryStepId,
    trail: [],
    outcomeId: null,
    redFlagFired: false,
  };
}

export function currentStep(state: EngineState): Step | null {
  if (!state.currentStepId) return null;
  return state.protocol.steps[state.currentStepId] ?? null;
}

export function currentOutcome(state: EngineState): Outcome | null {
  if (!state.outcomeId) return null;
  return state.protocol.outcomes[state.outcomeId] ?? null;
}

function resolve(state: EngineState, next: NextRef): EngineState {
  if (next.type === 'outcome') {
    return { ...state, currentStepId: null, outcomeId: next.id };
  }
  return { ...state, currentStepId: next.id };
}

/**
 * Record a choice-type answer and advance. A `dangerSign` option is expected
 * to route straight to an outcome — the "interrupt" is that resolution
 * happens on this answer, not after more questions are asked.
 */
export function answerChoice(state: EngineState, step: Step, optionIndex: number): EngineState {
  const option = step.options?.[optionIndex];
  if (!option) return state;

  const answered: AnsweredStep = {
    stepId: step.id,
    question: step.question,
    answerLabel: option.label,
    dangerSign: !!option.dangerSign,
    answeredAt: Date.now(),
  };
  const withTrail: EngineState = {
    ...state,
    trail: [...state.trail, answered],
    redFlagFired: state.redFlagFired || !!option.dangerSign,
  };
  return resolve(withTrail, option.next);
}

/** Record a value-type answer (bucketed into a range) and advance. `null` = "don't know". */
export function answerValue(state: EngineState, step: Step, rawValue: number | null): EngineState {
  let next: NextRef | undefined;
  let label: string;

  if (rawValue === null) {
    next = step.unknownNext;
    label = "Don't know / not available";
  } else {
    const bucket = step.buckets?.find(
      (b) => (b.min === undefined || rawValue >= b.min) && (b.max === undefined || rawValue < b.max)
    );
    next = bucket?.next;
    label = step.unit ? `${rawValue} ${step.unit}` : String(rawValue);
  }
  if (!next) return state;

  const answered: AnsweredStep = {
    stepId: step.id,
    question: step.question,
    answerLabel: label,
    dangerSign: false,
    answeredAt: Date.now(),
  };
  return resolve({ ...state, trail: [...state.trail, answered] }, next);
}
