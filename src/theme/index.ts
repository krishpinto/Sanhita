// Design tokens — "clinical calm", LIGHT theme only. This is the single
// source of truth for color, spacing, radius, type and shadow. No inline hex
// anywhere else in the app; screens and components import from here.

import type { TextStyle, ViewStyle } from 'react-native';

import type { Severity } from '@/types/protocol';

export const color = {
  // Surfaces
  bg: '#FAF9F6',
  card: '#FFFFFF',
  // Translucent card surface — ONLY for the three sanctioned glass accents.
  glassCard: 'rgba(255,255,255,0.85)',
  glassHeader: 'rgba(250,249,246,0.72)',

  // Ink
  ink: '#1A1D1F',
  inkSecondary: '#5E6470',
  inkFaint: '#9AA0AA',

  // Accent (the only one)
  accent: '#0F6E6B',
  accentSoft: '#EAF4F3',

  // Outcome severity colors — thin left borders + label chips only, never full fills
  severityUrgent: '#8C3A32',
  severityWatch: '#8A6D1D',
  severityRoutine: '#0F6E6B',
  severityUrgentSoft: '#FBEDEB',
  severityWatchSoft: '#F7F1E1',
  severityRoutineSoft: '#EAF4F3',

  // Semantic
  redFlagBg: '#FBEDEB',
  redFlagText: '#8C3A32',

  // Modal backdrop scrim
  scrim: 'rgba(26,29,31,0.35)',

  // DEMO ribbon
  ribbonBg: '#FDF6E9',
  ribbonText: '#B7791F',

  // Hairlines / borders
  border: '#ECEAE3',
  borderStrong: '#DDDAD1',

  // On-accent text
  onAccent: '#FFFFFF',
  // Hero (landing) — supporting tints over the deep-teal accent surface
  onAccentSoft: 'rgba(255,255,255,0.78)',
  heroChip: 'rgba(255,255,255,0.12)',
  heroLine: 'rgba(255,255,255,0.10)',

  // Disabled
  disabledBg: '#E4E2DC',
} as const;

export const radius = {
  card: 16,
  button: 12,
  chip: 999,
} as const;

/** Spacing scale 4/8/12/16/24/32 — no arbitrary values. */
export const space = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 24,
  xxl: 32,
} as const;

export const font = {
  title: { fontSize: 28, lineHeight: 39, fontWeight: '600' } as TextStyle,
  body: { fontSize: 17, lineHeight: 24 } as TextStyle,
  secondary: { fontSize: 15, lineHeight: 21 } as TextStyle,
  caption: { fontSize: 13, lineHeight: 18 } as TextStyle,
  /** Small uppercase section label. */
  overline: { fontSize: 13, lineHeight: 18, fontWeight: '600', letterSpacing: 0.6 } as TextStyle,
} as const;

/** The one sanctioned elevation. No stacked heavy shadows. */
export const shadow: ViewStyle = {
  shadowColor: '#1A1D1F',
  shadowOpacity: 0.06,
  shadowRadius: 8,
  shadowOffset: { width: 0, height: 2 },
  elevation: 2,
};

export const severityMeta: Record<Severity, { label: string; color: string; soft: string }> = {
  urgent: { label: 'Urgent', color: color.severityUrgent, soft: color.severityUrgentSoft },
  watch: { label: 'Watch closely', color: color.severityWatch, soft: color.severityWatchSoft },
  routine: { label: 'Routine', color: color.severityRoutine, soft: color.severityRoutineSoft },
};
