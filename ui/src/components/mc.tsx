// "MobileCode" dark kit — hand-built from scratch (NOT react-native-reusables).
// Matches the reference: near-black base, a soft blue top glow, a fine
// starfield, large light-weight headlines, and a single rounded composer input
// with a "+" and a circular send button. Scoped to the dark surfaces of the
// app (auth + landing + home); the clinical screens stay on the light kit in
// src/components/ui.tsx. Reuses the night-* tokens from global.css.

import type { LucideIcon } from 'lucide-react-native';
import { ArrowUp, Plus } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { StyleSheet } from 'react-native';
import Svg, { Rect } from 'react-native-svg';

import { cn } from '@/lib/cn';
import { Pressable, ScrollView, Text as RNText, TextInput, View } from '@/tw';

const isWeb = process.env.EXPO_OS === 'web';
const bgImage = isWeb ? 'backgroundImage' : 'experimental_backgroundImage';

// Palette anchors (kept here so the gradient/glow read exactly like the ref;
// the token set in global.css covers surfaces/text/borders used via className).
export const MC = {
  base: '#06060B',
  ink: '#F5F5F8',
  inkDark: '#0B0B14',
  muted: '#9C9BBE',
  faint: '#6E6D8C',
  accent: '#8B85FF',
} as const;

// ---------------------------------------------------------------------------
// Background — near-black base, soft blue top glow, fine starfield
// ---------------------------------------------------------------------------

function seededStars(count: number, seed: number) {
  let s = seed;
  const rand = () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
  return Array.from({ length: count }, () => ({
    cx: rand() * 100,
    cy: rand() * 46, // upper region only, where the glow lives
    size: rand() * 0.9 + 0.5,
    opacity: rand() * 0.5 + 0.15,
  }));
}

// A vertical wash that fades a cool indigo into the base by ~45%, plus a
// radial glow bloom centered at the top — the two layers together are what
// gives the reference its "light source above the fold" feel.
const wash = `linear-gradient(180deg, #141A33 0%, #0B0E1E 22%, ${MC.base} 46%, ${MC.base} 100%)`;
const glow = `radial-gradient(130% 62% at 50% -8%, rgba(96,116,214,0.30) 0%, rgba(96,116,214,0.10) 34%, transparent 62%)`;

export function MCBackground({ children }: { children: React.ReactNode }) {
  const stars = useMemo(() => seededStars(90, 11), []);
  return (
    <View className="flex-1" style={{ backgroundColor: MC.base }}>
      <View className="absolute inset-0" style={{ [bgImage]: wash } as Record<string, string>} />
      <View className="absolute inset-0" style={{ [bgImage]: glow } as Record<string, string>} />
      <Svg width="100%" height="100%" style={StyleSheet.absoluteFill} pointerEvents="none">
        {stars.map((s, i) => (
          <Rect key={i} x={`${s.cx}%`} y={`${s.cy}%`} width={s.size} height={s.size} fill="#FFFFFF" opacity={s.opacity} />
        ))}
      </Svg>
      {children}
    </View>
  );
}

// Standard scroll scaffold for a dark screen.
export function MCScroll({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <ScrollView
      className="flex-1"
      contentContainerClassName={cn('flex-grow px-6 pb-8', className)}
      contentInsetAdjustmentBehavior="automatic"
      keyboardShouldPersistTaps="handled">
      {children}
    </ScrollView>
  );
}

// ---------------------------------------------------------------------------
// Text — one primitive, a handful of intent-named variants
// ---------------------------------------------------------------------------

type TextVariant = 'eyebrow' | 'greeting' | 'headline' | 'title' | 'body' | 'muted' | 'faint' | 'link';

const TEXT: Record<TextVariant, string> = {
  eyebrow: 'text-[12px] leading-4 tracking-[2px] font-semibold uppercase text-night-text-faint',
  greeting: 'text-[15px] leading-5 text-night-text-muted',
  headline: 'text-[30px] leading-[38px] font-light text-night-text',
  title: 'text-[22px] leading-7 font-semibold text-night-text',
  body: 'text-[16px] leading-6 text-night-text',
  muted: 'text-[14px] leading-5 text-night-text-muted',
  faint: 'text-[13px] leading-[18px] text-night-text-faint',
  link: 'text-[14px] leading-5 font-semibold text-night-accent-2',
};

export function MCText({
  variant = 'body',
  className,
  ...props
}: React.ComponentProps<typeof RNText> & { variant?: TextVariant }) {
  return <RNText className={cn(TEXT[variant], className)} {...props} />;
}

// ---------------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------------

type ButtonVariant = 'primary' | 'ghost' | 'subtle';

const BTN: Record<ButtonVariant, string> = {
  primary: 'bg-night-accent',
  ghost: 'bg-night-surface border border-night-border',
  subtle: 'bg-transparent',
};
const BTN_TEXT: Record<ButtonVariant, string> = {
  primary: 'text-night-accent-ink',
  ghost: 'text-night-text',
  subtle: 'text-night-text',
};

export function MCButton({
  label,
  children,
  variant = 'primary',
  className,
  disabled,
  onPressIn,
  onPressOut,
  ...props
}: React.ComponentProps<typeof Pressable> & { label?: string; variant?: ButtonVariant }) {
  const [pressed, setPressed] = useState(false);
  return (
    <Pressable
      role="button"
      disabled={disabled}
      onPressIn={(e) => {
        setPressed(true);
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        setPressed(false);
        onPressOut?.(e);
      }}
      className={cn(
        'h-12 flex-row items-center justify-center gap-2 rounded-full px-6',
        BTN[variant],
        disabled && 'opacity-40',
        className
      )}
      style={{ transform: [{ scale: pressed && !disabled ? 0.97 : 1 }] }}
      {...props}>
      {label ? <RNText className={cn('text-[16px] font-semibold', BTN_TEXT[variant])}>{label}</RNText> : children}
    </Pressable>
  );
}

// Circular icon button — "send" (light fill, dark glyph) or "ghost".
export function MCIconButton({
  icon: Icon,
  variant = 'ghost',
  size = 44,
  className,
  disabled,
  onPressIn,
  onPressOut,
  ...props
}: React.ComponentProps<typeof Pressable> & { icon: LucideIcon; variant?: 'send' | 'ghost'; size?: number }) {
  const [pressed, setPressed] = useState(false);
  const send = variant === 'send';
  return (
    <Pressable
      role="button"
      disabled={disabled}
      onPressIn={(e) => {
        setPressed(true);
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        setPressed(false);
        onPressOut?.(e);
      }}
      className={cn(
        'items-center justify-center rounded-full',
        send ? 'bg-night-accent' : 'bg-night-surface border border-night-border',
        disabled && 'opacity-40',
        className
      )}
      style={{ width: size, height: size, transform: [{ scale: pressed && !disabled ? 0.94 : 1 }] }}
      {...props}>
      <Icon size={size * 0.42} color={send ? MC.inkDark : MC.ink} strokeWidth={2.2} />
    </Pressable>
  );
}

// ---------------------------------------------------------------------------
// Field — labelled input with a leading icon and an optional trailing slot
// ---------------------------------------------------------------------------

export function MCField({
  label,
  icon: Icon,
  trailing,
  className,
  ...inputProps
}: React.ComponentProps<typeof TextInput> & { label: string; icon: LucideIcon; trailing?: React.ReactNode }) {
  const [focused, setFocused] = useState(false);
  return (
    <View className="gap-2">
      <MCText variant="muted" className="ml-1">
        {label}
      </MCText>
      <View
        className={cn(
          'h-14 flex-row items-center gap-3 rounded-2xl border bg-night-surface px-4',
          focused ? 'border-night-accent-2' : 'border-night-border'
        )}>
        <Icon size={18} color={focused ? MC.accent : MC.muted} strokeWidth={2} />
        <TextInput
          placeholderTextColor={MC.faint}
          onFocus={(e) => {
            setFocused(true);
            inputProps.onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            inputProps.onBlur?.(e);
          }}
          className={cn('flex-1 text-[16px] leading-5 text-night-text', isWeb && 'outline-none', className)}
          {...inputProps}
        />
        {trailing}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Chip — the small context pills ("patient", "template") under the composer
// ---------------------------------------------------------------------------

export function MCChip({
  label,
  icon: Icon,
  onPress,
}: {
  label: string;
  icon?: LucideIcon;
  onPress?: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-row items-center gap-1.5 self-start rounded-full border border-night-border bg-night-surface px-3 py-1.5">
      {Icon && <Icon size={13} color={MC.muted} strokeWidth={2} />}
      <MCText variant="faint" className="text-night-text-muted">
        {label}
      </MCText>
    </Pressable>
  );
}

// ---------------------------------------------------------------------------
// Composer — the signature block from the reference. A rounded surface with a
// (multiline) input, an optional row of context pills, a "+" on the left and a
// circular send on the right.
// ---------------------------------------------------------------------------

export function MCComposer({
  value,
  onChangeText,
  onSubmit,
  onPlus,
  placeholder = 'Type a message',
  pills,
}: {
  value: string;
  onChangeText: (t: string) => void;
  onSubmit: () => void;
  onPlus?: () => void;
  placeholder?: string;
  pills?: { label: string; icon?: LucideIcon; onPress?: () => void }[];
}) {
  return (
    <View className="gap-3 rounded-[26px] border border-night-border bg-night-surface p-3">
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={MC.faint}
        multiline
        onSubmitEditing={onSubmit}
        className={cn('min-h-11 px-2 pt-1 text-[16px] leading-6 text-night-text', isWeb && 'outline-none')}
      />
      <View className="flex-row items-center justify-between">
        <MCIconButton icon={Plus} variant="ghost" size={40} onPress={onPlus} accessibilityLabel="Add" />
        <MCIconButton
          icon={ArrowUp}
          variant="send"
          size={40}
          onPress={onSubmit}
          disabled={value.trim().length === 0}
          accessibilityLabel="Send"
        />
      </View>
      {pills && pills.length > 0 && (
        <View className="flex-row flex-wrap gap-2 pt-0.5">
          {pills.map((p) => (
            <MCChip key={p.label} label={p.label} icon={p.icon} onPress={p.onPress} />
          ))}
        </View>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Brand mark — a soft glowing rounded badge
// ---------------------------------------------------------------------------

export function MCMark({ icon: Icon, size = 84 }: { icon: LucideIcon; size?: number }) {
  return (
    <View
      className="items-center justify-center self-center rounded-[26px] border border-night-border bg-night-surface-strong"
      style={{
        width: size,
        height: size,
        boxShadow: `0 0 ${Math.round(size * 0.7)}px ${Math.round(size * 0.12)}px rgba(139,133,255,0.30)`,
      }}>
      <Icon size={size * 0.46} color={MC.ink} strokeWidth={2.2} />
    </View>
  );
}
