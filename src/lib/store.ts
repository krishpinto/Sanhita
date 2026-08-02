// Global app state — index card intake → protocol engine run → outcome. A
// small zustand store keeps screens decoupled from navigation.

import { create } from 'zustand';

import { answerChoice, answerValue, currentStep, startEngine, type EngineState } from '@/lib/protocol-engine';
import type { EncounterRecord, IndexCard, ProtocolDefinition, Sex } from '@/types/protocol';

interface AppState {
  indexCards: IndexCard[];
  encounters: EncounterRecord[];

  engine: EngineState | null;
  activeIndexCard: IndexCard | null;

  addIndexCard: (input: { name: string; age?: string; sex?: Sex; complaint: string }) => IndexCard;
  startProtocol: (card: IndexCard, protocol: ProtocolDefinition) => void;
  answerCurrentChoice: (optionIndex: number) => void;
  answerCurrentValue: (value: number | null) => void;
  reset: () => void;
}

function finishIfDone(engine: EngineState, card: IndexCard, encounters: EncounterRecord[]): EncounterRecord[] {
  if (!engine.outcomeId) return encounters;
  const record: EncounterRecord = {
    id: `enc_${Date.now()}`,
    indexCard: card,
    protocolId: engine.protocol.id,
    protocolVersion: engine.protocol.version,
    trail: engine.trail,
    outcomeId: engine.outcomeId,
    redFlagFired: engine.redFlagFired,
    startedAt: card.createdAt,
    completedAt: Date.now(),
  };
  return [record, ...encounters];
}

export const useSanhita = create<AppState>((set, get) => ({
  indexCards: [],
  encounters: [],
  engine: null,
  activeIndexCard: null,

  addIndexCard: (input) => {
    const card: IndexCard = { ...input, id: `card_${Date.now()}`, createdAt: Date.now() };
    set((s) => ({ indexCards: [card, ...s.indexCards] }));
    return card;
  },

  startProtocol: (card, protocol) => {
    set({ activeIndexCard: card, engine: startEngine(protocol) });
  },

  answerCurrentChoice: (optionIndex) => {
    const { engine, activeIndexCard, encounters } = get();
    if (!engine || !activeIndexCard) return;
    const step = currentStep(engine);
    if (!step) return;
    const next = answerChoice(engine, step, optionIndex);
    set({ engine: next, encounters: finishIfDone(next, activeIndexCard, encounters) });
  },

  answerCurrentValue: (value) => {
    const { engine, activeIndexCard, encounters } = get();
    if (!engine || !activeIndexCard) return;
    const step = currentStep(engine);
    if (!step) return;
    const next = answerValue(engine, step, value);
    set({ engine: next, encounters: finishIfDone(next, activeIndexCard, encounters) });
  },

  reset: () => set({ engine: null, activeIndexCard: null }),
}));
