// The shared component kit — the ONLY Card / PrimaryButton / Chip / SectionHeader
// in the app. Screens compose these; a screen inventing its own variant is a bug.
//
// Styled with Tailwind (NativeWind v5 / react-native-css) via the CSS-enabled
// primitives in @/tw. Static, token-driven styling lives in className; only
// genuinely dynamic runtime values (an arbitrary severity hex passed as a
// prop, the entrance-animation interpolation) stay as inline `style` —
// Tailwind's JIT scanner can't generate a rule for a color it can't see as a
// literal.

import type { LucideIcon } from 'lucide-react-native';
import { useEffect, useRef } from 'react';
import { ActivityIndicator, Animated, Easing, type StyleProp, type ViewStyle } from 'react-native';

import { cn } from '@/lib/cn';
import { Pressable, ScrollView, Text, View } from '@/tw';

// ---------------------------------------------------------------------------
// Text
// ---------------------------------------------------------------------------

type Variant = 'title' | 'body' | 'secondary' | 'caption' | 'overline';
type Tone = 'primary' | 'secondary' | 'faint' | 'accent' | 'onAccent' | 'danger';

const variantClass: Record<Variant, string> = {
  title: 'text-title font-semibold',
  body: 'text-body',
  secondary: 'text-secondary',
  caption: 'text-caption',
  overline: 'text-overline font-semibold tracking-wide',
};

const toneClass: Record<Tone, string> = {
  primary: 'text-ink',
  secondary: 'text-ink-secondary',
  faint: 'text-ink-faint',
  accent: 'text-accent',
  onAccent: 'text-on-accent',
  danger: 'text-red-flag-text',
};

export function T({
  variant = 'body',
  tone = 'primary',
  className = '',
  children,
  ...rest
}: {
  variant?: Variant;
  tone?: Tone;
  className?: string;
  children?: React.ReactNode;
} & React.ComponentProps<typeof Text>) {
  return (
    <Text {...rest} className={cn(variantClass[variant], toneClass[tone], className)}>
      {children}
    </Text>
  );
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

export function Card({
  children,
  style,
  className = '',
  onPress,
  accent,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  className?: string;
  onPress?: () => void;
  /** Optional thin left-border accent (severity colors) — dynamic, so it stays inline. */
  accent?: string;
}) {
  const accentStyle: StyleProp<ViewStyle> = accent ? { borderLeftWidth: 3, borderLeftColor: accent } : null;
  const base = cn('bg-card rounded-card p-4 shadow-card', className);
  if (!onPress) {
    return (
      <View className={base} style={[accentStyle, style]}>
        {children}
      </View>
    );
  }
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      className={base}
      style={({ pressed }) => [accentStyle, style, pressed && { transform: [{ scale: 0.98 }] }]}>
      {children}
    </Pressable>
  );
}

// ---------------------------------------------------------------------------
// PrimaryButton
// ---------------------------------------------------------------------------

const buttonVariantClass: Record<'solid' | 'quiet' | 'danger' | 'inverse', string> = {
  solid: 'bg-accent',
  danger: 'bg-severity-urgent',
  inverse: 'bg-card',
  quiet: 'bg-accent-soft',
};

const buttonTextClass: Record<'solid' | 'quiet' | 'danger' | 'inverse', string> = {
  solid: 'text-on-accent',
  danger: 'text-on-accent',
  inverse: 'text-accent',
  quiet: 'text-accent',
};

export function PrimaryButton({
  label,
  onPress,
  disabled,
  loading,
  icon: Icon,
  variant = 'solid',
  style,
  className = '',
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  icon?: LucideIcon;
  variant?: 'solid' | 'quiet' | 'danger' | 'inverse';
  style?: StyleProp<ViewStyle>;
  className?: string;
}) {
  const iconColor = disabled ? '#9AA0AA' : variant === 'quiet' || variant === 'inverse' ? '#0F6E6B' : '#FFFFFF';
  const base = cn(
    'rounded-button py-4 px-6 items-center justify-center min-h-[52px]',
    disabled ? 'bg-disabled-bg' : buttonVariantClass[variant],
    className
  );
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      className={base}
      style={({ pressed }) => [style, pressed && { transform: [{ scale: 0.98 }] }]}>
      {loading ? (
        <ActivityIndicator color={iconColor} />
      ) : (
        <View className="flex-row items-center gap-2">
          {Icon && <Icon size={18} color={iconColor} strokeWidth={2.2} />}
          <Text className={cn('text-secondary font-semibold', disabled ? 'text-ink-faint' : buttonTextClass[variant])}>
            {label}
          </Text>
        </View>
      )}
    </Pressable>
  );
}

// ---------------------------------------------------------------------------
// Chip
// ---------------------------------------------------------------------------

export function Chip({
  label,
  tint = '#0F6E6B',
  soft = '#EAF4F3',
  icon: Icon,
  style,
  className = '',
}: {
  label: string;
  /** Text/icon color — dynamic (severity colors), so it stays inline. */
  tint?: string;
  /** Background — dynamic, so it stays inline. */
  soft?: string;
  icon?: LucideIcon;
  style?: StyleProp<ViewStyle>;
  className?: string;
}) {
  return (
    <View
      className={cn('flex-row items-center gap-1 rounded-full px-3 py-1 self-start', className)}
      style={[{ backgroundColor: soft }, style]}>
      {Icon && <Icon size={13} color={tint} strokeWidth={2.2} />}
      <Text className="text-caption font-semibold" style={{ color: tint }}>
        {label}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// SectionHeader
// ---------------------------------------------------------------------------

export function SectionHeader({
  title,
  trailing,
  style,
  className = '',
}: {
  title: string;
  trailing?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  className?: string;
}) {
  return (
    <View className={cn('flex-row items-center justify-between mt-2', className)} style={style}>
      <T variant="overline" tone="secondary">
        {title.toUpperCase()}
      </T>
      {trailing}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton — static blocks (nothing loops except the entrance rise).
// ---------------------------------------------------------------------------

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <View className="bg-card rounded-card p-4 shadow-card gap-3">
      <View className="h-3.5 rounded-button bg-border w-[45%]" />
      {Array.from({ length: lines }).map((_, i) => (
        <View key={i} className={`h-3.5 rounded-button bg-border ${i % 2 ? 'w-[90%]' : 'w-[70%]'}`} />
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Empty state — icon + one line + optional action, never blank.
// ---------------------------------------------------------------------------

export function EmptyState({
  icon: Icon,
  text,
  actionLabel,
  onAction,
}: {
  icon: LucideIcon;
  text: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View className="items-center justify-center gap-3 px-8 py-8">
      <View className="w-14 h-14 rounded-full bg-accent-soft items-center justify-center">
        <Icon size={26} color="#0F6E6B" strokeWidth={1.8} />
      </View>
      <T variant="secondary" tone="secondary" className="text-center">
        {text}
      </T>
      {actionLabel && onAction && (
        <PrimaryButton label={actionLabel} onPress={onAction} variant="quiet" className="self-center" />
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Inline error card with retry — never Alert.alert.
// ---------------------------------------------------------------------------

export function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View className="bg-red-flag-bg rounded-card p-4 flex-row items-center gap-4">
      <T variant="secondary" tone="danger" className="flex-1" numberOfLines={3}>
        {message}
      </T>
      {onRetry && (
        <Pressable onPress={onRetry} accessibilityRole="button" hitSlop={8}>
          <T variant="secondary" tone="danger" className="font-semibold">
            Retry
          </T>
        </Pressable>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Entrance — fade + 4px rise, 150ms, staggered 40ms per index. Runs once.
// Kept on RN's built-in Animated (runtime-interpolated values) rather than
// Tailwind — there's no static class for an animated value.
// ---------------------------------------------------------------------------

export function Rise({
  index = 0,
  children,
  style,
}: {
  index?: number;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(anim, {
      toValue: 1,
      duration: 150,
      delay: index * 40,
      easing: Easing.out(Easing.ease),
      useNativeDriver: true,
    }).start();
  }, [anim, index]);
  return (
    <Animated.View
      style={[
        {
          opacity: anim,
          transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [4, 0] }) }],
        },
        style,
      ]}>
      {children}
    </Animated.View>
  );
}
