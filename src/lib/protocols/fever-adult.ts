// fever-adult v1 — ported from the walkable demo in ../../../protocol-tree-demo.html.
//
// Three branches (f_danger, f_meningeal, f_vector_long) carry the full,
// four-part outcome as originally authored for that demo. The other six
// outcomes only ever had a one-line action + citation there — they are left
// as explicit TODO stubs below rather than backfilled with invented
// clinical content.
//
// Do not ship this protocol until a clinician has:
//   1. Verified every citation against the live guideline text.
//   2. Authored the missing DO NOW / TELL THE PATIENT / REFER NOW IF /
//      FOLLOW UP detail for the six stub outcomes.
//   3. Reviewed every "Don't know / unable to assess" routing below — each
//      is flagged in a comment. They currently default to the more
//      conservative sibling branch as an engineering placeholder, not a
//      clinical judgment call this file is qualified to make.

import type { ProtocolDefinition } from '@/types/protocol';

export const feverAdult: ProtocolDefinition = {
  id: 'fever-adult',
  version: 1,
  title: 'Fever (Adult)',
  entryStepId: 'f1',
  steps: {
    f1: {
      id: 'f1',
      answerType: 'value',
      question: 'Fever for how many days?',
      unit: 'days',
      buckets: [
        { max: 3, next: { type: 'step', id: 'f2' } },
        { min: 3, next: { type: 'step', id: 'f_prolonged' } },
      ],
      // Unknown duration routes to the danger-sign screen (f2) so an urgent
      // case is never missed just because duration wasn't captured.
      // Needs clinician sign-off.
      unknownNext: { type: 'step', id: 'f2' },
    },
    f2: {
      id: 'f2',
      answerType: 'choice',
      question:
        'Any danger signs — difficulty breathing, confusion/drowsiness, fainting, severe weakness, non-blanching rash, or SpO2 below 90%?',
      options: [
        { label: 'Yes, one or more present', next: { type: 'outcome', id: 'f_danger' }, dangerSign: true },
        { label: 'No', next: { type: 'step', id: 'f3' } },
        // Placeholder default: continues as if "No". Needs clinician
        // sign-off — "unable to assess" on a danger-sign screen may warrant
        // a more cautious route.
        { label: "Don't know / unable to assess", next: { type: 'step', id: 'f3' } },
      ],
    },
    f3: {
      id: 'f3',
      answerType: 'choice',
      question: 'Any localising symptom alongside the fever?',
      options: [
        { label: 'Cough or breathlessness', next: { type: 'outcome', id: 'f_resp' } },
        { label: 'Burning / frequent urination', next: { type: 'outcome', id: 'f_uti' } },
        {
          label: 'Neck stiffness or severe headache',
          next: { type: 'outcome', id: 'f_meningeal' },
          dangerSign: true,
        },
        { label: 'Joint pain with a rash', next: { type: 'outcome', id: 'f_vector_short' } },
        { label: 'Abdominal pain', next: { type: 'outcome', id: 'f_abdo' } },
        { label: 'None of these', next: { type: 'outcome', id: 'f_none' } },
        // Placeholder default. Needs clinician sign-off.
        { label: "Don't know / unable to assess", next: { type: 'outcome', id: 'f_none' } },
      ],
    },
    f_prolonged: {
      id: 'f_prolonged',
      answerType: 'choice',
      question: 'Mosquito exposure or travel to an endemic area?',
      options: [
        { label: 'Yes', next: { type: 'outcome', id: 'f_vector_long' } },
        { label: 'No', next: { type: 'outcome', id: 'f_prolonged_no' } },
        // Placeholder default: treats "don't know" as possible exposure —
        // the more cautious of the two branches. Needs clinician sign-off.
        { label: "Don't know", next: { type: 'outcome', id: 'f_vector_long' } },
      ],
    },
  },
  outcomes: {
    f_danger: {
      id: 'f_danger',
      severity: 'urgent',
      likely: 'Possible severe febrile illness / sepsis',
      doNow: [
        'Begin emergency stabilisation now — do not wait for further workup',
        'Arrange urgent referral to a facility that can manage sepsis',
      ],
      tellPatient: 'This needs emergency care right now — we are sending you for immediate treatment.',
      referIf: ['Already met — refer immediately, no further screening needed'],
      followUp: 'N/A — handled at the referral facility',
      citations: { doNow: 'WHO IMAI District Clinician Manual — Adult Febrile Illness, danger-sign screen' },
    },
    f_meningeal: {
      id: 'f_meningeal',
      severity: 'urgent',
      likely: 'Possible meningitis',
      doNow: [
        'Treat as a medical emergency',
        'Begin empirical treatment per local protocol while arranging transfer',
      ],
      tellPatient:
        'This could be a serious infection around the brain or spine — you need to go to a hospital immediately.',
      referIf: ['Already met — this is the referral trigger itself'],
      followUp: 'N/A — handled at the referral facility',
      citations: { doNow: 'WHO IMAI — Adult Febrile Illness, meningeal signs' },
    },
    f_vector_long: {
      id: 'f_vector_long',
      severity: 'watch',
      likely: 'Dengue fever',
      doNow: [
        'Check platelet count / hematocrit if available',
        'Start oral fluids — no NSAIDs/aspirin (bleeding risk)',
      ],
      tellPatient:
        'You likely have dengue. Drink plenty of fluids, take only paracetamol for fever, and watch for the warning signs below over the next 2 days.',
      referIf: ['Bleeding gums/nose', 'Persistent vomiting', 'Severe abdominal pain', 'Drowsiness'],
      followUp: 'Recheck platelet count in 24h if fever continues past day 3',
      citations: {
        doNow: 'NVBDCP Dengue Guidelines §4.2',
        referIf: 'NVBDCP Dengue Guidelines §4.5',
      },
    },

    // --- Stubs below: one-line action + citation only, ported as-is from
    // the demo. Not ready to ship — see file header.
    f_resp: {
      id: 'f_resp',
      severity: 'routine',
      likely: 'Respiratory source (pneumonia / URI)',
      doNow: ['Assess respiratory rate & chest exam, manage per local ARI protocol'],
      tellPatient: 'TODO — not yet authored by a clinician.',
      referIf: ['TODO — not yet authored by a clinician.'],
      followUp: 'TODO — not yet authored by a clinician.',
      citations: { doNow: 'Local ARI / pneumonia guideline' },
    },
    f_uti: {
      id: 'f_uti',
      severity: 'routine',
      likely: 'Urinary tract infection',
      doNow: ['Send urinalysis, treat per local antibiotic guideline'],
      tellPatient: 'TODO — not yet authored by a clinician.',
      referIf: ['TODO — not yet authored by a clinician.'],
      followUp: 'TODO — not yet authored by a clinician.',
      citations: { doNow: 'Local UTI guideline' },
    },
    f_vector_short: {
      id: 'f_vector_short',
      severity: 'watch',
      likely: 'Vector-borne illness (dengue / chikungunya)',
      doNow: ['Check platelet count, screen for warning signs — endemic-area exposure'],
      tellPatient: 'TODO — not yet authored by a clinician.',
      referIf: ['TODO — not yet authored by a clinician.'],
      followUp: 'TODO — not yet authored by a clinician.',
      citations: { doNow: 'National vector-borne disease guideline' },
    },
    f_abdo: {
      id: 'f_abdo',
      severity: 'watch',
      likely: 'Intra-abdominal source',
      doNow: ['Evaluate per the Abdominal Pain protocol, escalate if guarding/rigidity develops'],
      tellPatient: 'TODO — not yet authored by a clinician.',
      referIf: ['TODO — not yet authored by a clinician.'],
      followUp: 'TODO — not yet authored by a clinician.',
      citations: { doNow: 'Local acute-abdomen guideline' },
    },
    f_none: {
      id: 'f_none',
      severity: 'routine',
      likely: 'Non-localising fever, no danger signs',
      doNow: ['Supportive care, safety-net advice, review if fever persists 3+ days'],
      tellPatient: 'TODO — not yet authored by a clinician.',
      referIf: ['TODO — not yet authored by a clinician.'],
      followUp: 'TODO — not yet authored by a clinician.',
      citations: { doNow: 'General febrile-illness supportive-care guidance' },
    },
    f_prolonged_no: {
      id: 'f_prolonged_no',
      severity: 'watch',
      likely: 'Prolonged fever, no vector exposure',
      doNow: ['Consider typhoid / TB / occult infection workup, refer if not resolving'],
      tellPatient: 'TODO — not yet authored by a clinician.',
      referIf: ['TODO — not yet authored by a clinician.'],
      followUp: 'TODO — not yet authored by a clinician.',
      citations: { doNow: 'Local prolonged-pyrexia pathway' },
    },
  },
};
