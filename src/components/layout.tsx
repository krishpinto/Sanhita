// Responsive app shell — bottom tabs on mobile, left sidebar on desktop.
// Navigation targets existing routes only; no routing logic changes.

import { usePathname, useRouter } from "expo-router";
import {
  BookOpen,
  Clock,
  Home,
  Settings,
  Stethoscope,
} from "lucide-react-native";

import { useBreakpoint } from "@/hooks/useBreakpoint";
import { cn } from "@/lib/cn";
import { c, subscribeThemeChanges } from "@/theme";
import { Pressable, Text, View } from "@/tw";
import { useEffect, useState } from "react";

const NAV = [
  { href: "/home" as const, label: "Home", icon: Home },
  { href: "/encounters" as const, label: "History", icon: Clock },
  { href: "/review" as const, label: "Library", icon: BookOpen },
  { href: "/settings" as const, label: "Settings", icon: Settings },
];

function NavItem({
  label,
  icon: Icon,
  active,
  onPress,
  vertical,
}: {
  label: string;
  icon: typeof Home;
  active: boolean;
  onPress?: () => void;
  vertical?: boolean;
}) {
  const color = active ? c.accent : c.inkMuted;
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active, disabled: !onPress }}
      className={cn(
        "items-center justify-center gap-1",
        vertical
          ? "flex-row gap-3 px-4 py-3 rounded-button w-full"
          : "flex-1 py-2",
        vertical && active && "bg-info-bg",
        !onPress && "opacity-40",
      )}
    >
      <Icon size={vertical ? 20 : 22} color={color} strokeWidth={2} />
      <Text
        className={cn(
          "text-caption",
          vertical ? "text-left flex-1" : "text-center",
          active ? "text-accent font-medium" : "text-ink-muted",
        )}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export function BottomNav() {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <View className="flex-row border-t border-border bg-card px-2 pb-2 pt-1">
      {NAV.map((item) => {
        const active = item.href
          ? pathname === item.href ||
            (item.href === "/home" && pathname === "/")
          : false;
        return (
          <NavItem
            key={item.label}
            label={item.label}
            icon={item.icon}
            active={active}
            onPress={item.href ? () => router.push(item.href!) : undefined}
          />
        );
      })}
    </View>
  );
}

export function SideNav() {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <View className="w-55 border-r border-border bg-card py-6 px-3 gap-1">
      <View className="flex-row items-center gap-2 px-3 pb-6">
        <View className="h-9 w-9 items-center justify-center rounded-button bg-ink">
          <Stethoscope size={18} color={c.onAccent} strokeWidth={2} />
        </View>
        <Text className="text-secondary font-medium tracking-wide text-ink">
          SANHITA
        </Text>
      </View>
      {NAV.map((item) => {
        const active = item.href
          ? pathname === item.href ||
            (item.href === "/home" && pathname === "/")
          : false;
        return (
          <NavItem
            key={item.label}
            label={item.label}
            icon={item.icon}
            active={active}
            vertical
            onPress={item.href ? () => router.push(item.href!) : undefined}
          />
        );
      })}
    </View>
  );
}

/** Centers content on wide screens with max-width constraint. */
export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { isDesktop } = useBreakpoint();
  return (
    <View
      className={cn(
        "w-full self-center",
        isDesktop ? "max-w-210 px-6" : "px-5",
        className,
      )}
    >
      {children}
    </View>
  );
}

export function AppHeader({ showProfile = true }: { showProfile?: boolean }) {
  return (
    <View className="flex-row items-center justify-between py-3">
      <View className="flex-row items-center gap-3">
        <Stethoscope size={20} color={c.accent} strokeWidth={2} />
        <Text className="text-section font-semibold tracking-tight text-ink">
          SANHITA
        </Text>
      </View>
      {showProfile && (
        <View className="h-8 w-8 items-center justify-center rounded-full border border-border">
          <View className="h-3.5 w-3.5 rounded-full border border-ink-secondary" />
        </View>
      )}
    </View>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isDesktop } = useBreakpoint();
  const [, setThemeVersion] = useState(0);

  useEffect(() => {
    // subscribeThemeChanges may have a boolean-returning delete under the
    // hood; cast the returned cleanup to `() => void` so TypeScript accepts
    // this as a valid React effect cleanup type.
    const unsubscribe = subscribeThemeChanges(() => {
      setThemeVersion((prev) => prev + 1);
    }) as () => void;
    return () => {
      unsubscribe();
    };
  }, []);

  if (isDesktop) {
    return (
      <View className="flex-1 flex-row bg-bg">
        <SideNav />
        <View className="flex-1">{children}</View>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-bg">
      <View className="flex-1">{children}</View>
      <BottomNav />
    </View>
  );
}
