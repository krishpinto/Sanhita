// Shared component kit — Banner, buttons, Card, SegmentedControl, StatusPill,
// OutcomeSection, ProgressBar, Avatar. Screens compose these; no one-offs.

import type { LucideIcon } from "lucide-react-native";
import { TriangleAlert, X } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Easing,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import { useBreakpoint } from "@/hooks/useBreakpoint";
import { cn } from "@/lib/cn";
import { avatarTint, c, severityMeta, shadowPrimary } from "@/theme";
import { Pressable, Text, TextInput, View } from "@/tw";

const isWeb = process.env.EXPO_OS === "web";

// ---------------------------------------------------------------------------
// Text
// ---------------------------------------------------------------------------

type Variant =
  | "pageTitle"
  | "section"
  | "body"
  | "secondary"
  | "caption"
  | "clinical";
type Tone =
  | "primary"
  | "secondary"
  | "muted"
  | "accent"
  | "onAccent"
  | "danger"
  | "success"
  | "warning"
  | "info";

const variantClass: Record<Variant, string> = {
  pageTitle: "text-page-title font-medium",
  section: "text-section font-medium",
  body: "text-body",
  secondary: "text-secondary",
  caption: "text-caption",
  clinical: "text-clinical font-medium tracking-wide",
};

const toneClass: Record<Tone, string> = {
  primary: "text-ink",
  secondary: "text-ink-secondary",
  muted: "text-ink-muted",
  accent: "text-accent",
  onAccent: "text-on-accent",
  danger: "text-danger-text",
  success: "text-success-text",
  warning: "text-warning-text",
  info: "text-info-text",
};

export function T({
  variant = "body",
  tone = "primary",
  className = "",
  children,
  ...rest
}: {
  variant?: Variant;
  tone?: Tone;
  className?: string;
  children?: React.ReactNode;
} & React.ComponentProps<typeof Text>) {
  return (
    <Text
      {...rest}
      className={cn(variantClass[variant], toneClass[tone], className)}
    >
      {children}
    </Text>
  );
}

// ---------------------------------------------------------------------------
// Banner
// ---------------------------------------------------------------------------

export function Banner({
  message = "Demo — synthetic patients only · not for clinical use",
  onDismiss,
}: {
  message?: string;
  onDismiss?: () => void;
}) {
  return (
    <View className="flex-row items-center justify-center gap-2 bg-banner-bg border-b border-border px-3 py-2">
      <TriangleAlert size={14} color={c.bannerText} strokeWidth={2} />
      <T variant="caption" tone="secondary" className="flex-1 text-center">
        {message}
      </T>
      {onDismiss && (
        <Pressable onPress={onDismiss} accessibilityRole="button" hitSlop={8}>
          <X size={14} color={c.inkMuted} strokeWidth={2} />
        </Pressable>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

export function Card({
  children,
  style,
  className = "",
  onPress,
  tint,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  className?: string;
  onPress?: () => void;
  /** Optional left accent stripe color. */
  tint?: string;
}) {
  const accentStyle: StyleProp<ViewStyle> = tint
    ? { borderLeftWidth: 3, borderLeftColor: tint }
    : null;
  const base = cn("bg-card rounded-card border border-border p-4", className);
  if (!onPress) {
    return (
      <View className={base} style={[accentStyle, style, shadowPrimary]}>
        {children}
      </View>
    );
  }
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      className={base}
      style={({ pressed }) => [
        accentStyle,
        style,
        shadowPrimary,
        pressed && { opacity: 0.92 },
      ]}
    >
      {children}
    </Pressable>
  );
}

// ---------------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------------

export function PrimaryButton({
  label,
  onPress,
  disabled,
  loading,
  icon: Icon,
  style,
  className = "",
  fullWidth,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  icon?: LucideIcon;
  style?: StyleProp<ViewStyle>;
  className?: string;
  fullWidth?: boolean;
}) {
  const { isDesktop } = useBreakpoint();
  const iconColor = disabled ? c.inkMuted : c.onAccent;
  const widthClass =
    fullWidth === false ? "" : isDesktop && fullWidth !== true ? "" : "w-full";
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      className={cn(
        "rounded-pill items-center justify-center flex-row gap-3 px-5",
        isDesktop ? "min-h-11 self-start" : "min-h-12",
        widthClass,
        className,
      )}
      style={({ pressed }) => [
        { backgroundColor: disabled ? c.disabledBg : c.accent },
        style,
        !disabled && {
          shadowColor: shadowPrimary.shadowColor || "#000",
          shadowOpacity: 0.12,
          shadowRadius: 6,
          shadowOffset: { width: 0, height: 2 },
          elevation: 2,
        },
        pressed && !disabled && { opacity: 0.92 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={iconColor} />
      ) : (
        <>
          {Icon && (
            <Icon
              size={18}
              color={disabled ? c.inkMuted : c.accent}
              strokeWidth={2}
            />
          )}
          <Text
            className={cn("text-secondary font-medium")}
            style={{ color: disabled ? c.inkMuted : c.onAccent }}
          >
            {label}
          </Text>
        </>
      )}
    </Pressable>
  );
}

export function SecondaryButton({
  label,
  onPress,
  disabled,
  icon: Icon,
  className = "",
  fullWidth,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  icon?: LucideIcon;
  className?: string;
  fullWidth?: boolean;
}) {
  const { isDesktop } = useBreakpoint();
  const widthClass =
    fullWidth === false ? "" : isDesktop && fullWidth !== true ? "" : "w-full";
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      className={cn(
        "rounded-button border bg-transparent items-center justify-center flex-row gap-2 px-5",
        isDesktop ? "min-h-11 self-start" : "min-h-12",
        widthClass,
        disabled && "opacity-50",
        className,
      )}
      style={({ pressed }) => [
        { borderColor: c.borderStrong, borderWidth: 1 },
        pressed && { backgroundColor: c.bg },
      ]}
    >
      {Icon && <Icon size={18} color={c.ink} strokeWidth={2} />}
      <Text className="text-secondary font-medium text-ink">{label}</Text>
    </Pressable>
  );
}

export function TertiaryButton({
  label,
  onPress,
  className = "",
}: {
  label: string;
  onPress: () => void;
  className?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      className={cn(
        "rounded-button border bg-transparent items-center justify-center px-4 py-2",
        className,
      )}
      style={({ pressed }) => [
        { borderColor: c.borderStrong, borderWidth: 1 },
        pressed && { backgroundColor: c.bg },
      ]}
    >
      <T
        variant="secondary"
        tone="muted"
        className="text-center"
        style={{ color: c.ink }}
      >
        {label}
      </T>
    </Pressable>
  );
}

/** @deprecated Use PrimaryButton / SecondaryButton / TertiaryButton instead. */
export function Chip({
  label,
  tint = c.accent,
  soft = c.infoBg,
  icon: Icon,
  style,
  className = "",
}: {
  label: string;
  tint?: string;
  soft?: string;
  icon?: LucideIcon;
  style?: StyleProp<ViewStyle>;
  className?: string;
}) {
  return (
    <StatusPill
      label={label}
      role="accent"
      className={className}
      style={style}
    />
  );
}

// ---------------------------------------------------------------------------
// SegmentedControl
// ---------------------------------------------------------------------------

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className = "",
}: {
  options: { label: string; value: T }[];
  value?: T;
  onChange: (value: T) => void;
  className?: string;
}) {
  function hexToRgba(hex: string, alpha = 1) {
    try {
      const h = hex.replace("#", "");
      const bigint = parseInt(
        h.length === 3
          ? h
              .split("")
              .map((c) => c + c)
              .join("")
          : h,
        16,
      );
      const r = (bigint >> 16) & 255;
      const g = (bigint >> 8) & 255;
      const b = bigint & 255;
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    } catch (e) {
      return hex;
    }
  }

  return (
    <View
      className={cn(
        "flex-row bg-bg border border-border rounded-button p-1 gap-1",
        className,
      )}
    >
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <Pressable
            key={opt.value}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            onPress={() => onChange(opt.value)}
            className={cn(
              "flex-1 rounded-button items-center justify-center min-h-10",
            )}
            style={({ pressed }) => {
              const activeBg = active ? hexToRgba(c.accent, 0.12) : undefined;
              const pressedBg = pressed && !active ? c.bg : undefined;
              return [
                { backgroundColor: activeBg },
                pressedBg ? { backgroundColor: pressedBg } : null,
              ];
            }}
          >
            <Text
              className={cn(
                "text-secondary font-medium",
                active ? "text-on-accent" : "text-ink-secondary",
              )}
            >
              {opt.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// ---------------------------------------------------------------------------
// StatusPill
// ---------------------------------------------------------------------------

type PillRole = "success" | "warning" | "danger" | "accent";

const pillClass: Record<PillRole, string> = {
  success: "bg-success-bg",
  warning: "bg-warning-bg",
  danger: "bg-danger-bg",
  accent: "bg-info-bg",
};

const pillText: Record<PillRole, Tone> = {
  success: "success",
  warning: "warning",
  danger: "danger",
  accent: "info",
};

export function StatusPill({
  label,
  role = "accent",
  className = "",
  style,
}: {
  label: string;
  role?: PillRole;
  className?: string;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <View
      className={cn(
        "rounded-full px-2.5 py-1 self-start",
        pillClass[role],
        className,
      )}
      style={style}
    >
      <T variant="caption" tone={pillText[role]} className="font-medium">
        {label}
      </T>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Avatar
// ---------------------------------------------------------------------------

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const tint = avatarTint(name);
  return (
    <View
      className="rounded-full items-center justify-center"
      style={{ width: size, height: size, backgroundColor: tint.bg }}
    >
      <Text
        className="text-secondary font-medium"
        style={{ color: tint.text, fontSize: size * 0.35 }}
      >
        {initials}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// ProgressBar
// ---------------------------------------------------------------------------

export function ProgressBar({
  current,
  total,
}: {
  current: number;
  total: number;
}) {
  const pct =
    total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  return (
    <View className="gap-1.5">
      <View className="h-1 rounded-full bg-border overflow-hidden">
        <View
          className="h-full rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </View>
      <T variant="caption" tone="muted">
        Question {current} of {total}
      </T>
    </View>
  );
}

// ---------------------------------------------------------------------------
// OutcomeSection
// ---------------------------------------------------------------------------

type OutcomeTone = "neutral" | "warning" | "danger";

const outcomeToneClass: Record<OutcomeTone, string> = {
  neutral: "bg-card border-border",
  warning: "bg-warning-bg border-warning-bg",
  danger: "bg-danger-bg border-danger-border",
};

export function OutcomeSection({
  title,
  tone = "neutral",
  citation,
  children,
}: {
  title: string;
  tone?: OutcomeTone;
  citation?: string;
  children: React.ReactNode;
}) {
  return (
    <View
      className={cn("rounded-card border p-4 gap-2", outcomeToneClass[tone])}
    >
      <T
        variant="clinical"
        tone={
          tone === "danger"
            ? "danger"
            : tone === "warning"
              ? "warning"
              : "secondary"
        }
      >
        {title.toUpperCase()}
      </T>
      {children}
      {citation && (
        <T variant="caption" tone="info" className="pt-1">
          {citation}
        </T>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// FormField + TextField
// ---------------------------------------------------------------------------

export function FormField({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <View className="gap-2">
      <T variant="caption" tone="secondary" className="ml-0.5">
        {label}
      </T>
      {children}
      {hint && (
        <T variant="caption" tone="muted">
          {hint}
        </T>
      )}
    </View>
  );
}

export function TextField({
  className = "",
  ...props
}: React.ComponentProps<typeof TextInput> & { className?: string }) {
  const [focused, setFocused] = useState(false);
  const hasNoBorder = className.includes("border-0");
  const borderStyle = hasNoBorder
    ? {}
    : focused
      ? { borderWidth: 1.5 }
      : { borderWidth: 1 };
  return (
    <TextInput
      textAlignVertical="center"
      // ensure consistent vertical centering across platforms
      // paddingVertical keeps single-line inputs centered when container height changes
      style={[borderStyle, { paddingVertical: 8 }]}
      placeholderTextColor={c.inkMuted}
      onFocus={(e) => {
        setFocused(true);
        props.onFocus?.(e);
      }}
      onBlur={(e) => {
        setFocused(false);
        props.onBlur?.(e);
      }}
      className={cn(
        "bg-bg border rounded-button px-4 text-body text-ink min-h-11",
        focused ? "border-accent" : "border-border",
        isWeb && "outline-none",
        className,
      )}
      {...props}
    />
  );
}

// ---------------------------------------------------------------------------
// SectionHeader
// ---------------------------------------------------------------------------

export function SectionHeader({
  title,
  trailing,
  clinical = false,
  className = "",
}: {
  title: string;
  trailing?: React.ReactNode;
  /** When true, renders uppercase clinical label (DO NOW, etc.). */
  clinical?: boolean;
  className?: string;
}) {
  return (
    <View className={cn("flex-row items-center justify-between", className)}>
      <T
        variant={clinical ? "clinical" : "caption"}
        tone="secondary"
        className={clinical ? "" : "font-medium"}
      >
        {clinical ? title.toUpperCase() : title}
      </T>
      {trailing}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Skeleton / Empty / Error / Rise
// ---------------------------------------------------------------------------

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <View className="bg-card rounded-card border border-border p-4 gap-3">
      <View className="h-3 rounded-button bg-border w-[45%]" />
      {Array.from({ length: lines }).map((_, i) => (
        <View
          key={i}
          className={`h-3 rounded-button bg-border ${i % 2 ? "w-[90%]" : "w-[70%]"}`}
        />
      ))}
    </View>
  );
}

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
      <View className="w-14 h-14 rounded-full bg-info-bg items-center justify-center">
        <Icon size={26} color={c.infoText} strokeWidth={1.8} />
      </View>
      <T variant="secondary" tone="secondary" className="text-center">
        {text}
      </T>
      {actionLabel && onAction && (
        <SecondaryButton label={actionLabel} onPress={onAction} />
      )}
    </View>
  );
}

export function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <View className="bg-danger-bg border border-danger-border rounded-card p-4 flex-row items-center gap-4">
      <T variant="secondary" tone="danger" className="flex-1" numberOfLines={4}>
        {message}
      </T>
      {onRetry && (
        <Pressable onPress={onRetry} accessibilityRole="button" hitSlop={8}>
          <T variant="secondary" tone="danger" className="font-medium">
            Retry
          </T>
        </Pressable>
      )}
    </View>
  );
}

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
          transform: [
            {
              translateY: anim.interpolate({
                inputRange: [0, 1],
                outputRange: [4, 0],
              }),
            },
          ],
        },
        style,
      ]}
    >
      {children}
    </Animated.View>
  );
}

export { severityMeta };
