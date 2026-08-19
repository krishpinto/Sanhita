// Design tokens — flat, clinical, trusted. Light + dark role mapping.
// Import from here when a raw JS value is needed (StyleSheet, icon colors).

import * as SecureStore from "expo-secure-store";
import type { TextStyle, ViewStyle } from "react-native";
import { Appearance } from "react-native";

import type { Severity } from "@/types/protocol";

export const color = {
  light: {
    bg: "#F5F5F5",
    card: "#FFFFFF",
    border: "rgba(0,0,0,0.08)",
    borderStrong: "rgba(0,0,0,0.22)",
    ink: "#1A1A18",
    inkSecondary: "#5F5E5A",
    inkMuted: "#888780",
    accent: "#141414",
    accentPressed: "#000000",
    onAccent: "#FFFFFF",
    successBg: "#EAF3DE",
    successText: "#3B6D11",
    warningBg: "#FAEEDA",
    warningText: "#854F0B",
    dangerBg: "#FCEBEB",
    dangerText: "#791F1F",
    dangerBorder: "#E24B4A",
    infoBg: "#F2F2F2",
    infoText: "#1A1A18",
    bannerBg: "#F0EDE4",
    bannerText: "#5F5E5A",
    disabledBg: "#E8E6DF",
    scrim: "rgba(26,26,24,0.35)",
  },
  dark: {
    bg: "#121210",
    card: "#1E1E1C",
    border: "rgba(255,255,255,0.10)",
    borderStrong: "rgba(255,255,255,0.24)",
    ink: "#F5F4F0",
    inkSecondary: "#B8B7B0",
    inkMuted: "#888780",
    accent: "#FFFFFF",
    accentPressed: "#DDDDDD",
    onAccent: "#141414",
    successBg: "#1E2E14",
    successText: "#A8D46A",
    warningBg: "#2E2410",
    warningText: "#E8B84A",
    dangerBg: "#2E1414",
    dangerText: "#F08080",
    dangerBorder: "#E24B4A",
    infoBg: "#1E1E1E",
    infoText: "#FFFFFF",
    bannerBg: "#1E1E1C",
    bannerText: "#B8B7B0",
    disabledBg: "#2A2A28",
    scrim: "rgba(0,0,0,0.55)",
  },
} as const;

/** Active palette — CSS variables drive runtime theming on web; this is the light default for inline styles. */
// Export a mutable palette object so callers can read properties directly.
export let c = {
  ...(Appearance.getColorScheme() === "dark" ? color.dark : color.light),
};

/** Apply a color scheme to the exported `c` object (mutates in place). */
export function applyColorScheme(scheme: "light" | "dark" | null) {
  const pal = scheme === "dark" ? color.dark : color.light;
  Object.keys(pal).forEach((k) => {
    // @ts-ignore
    c[k] = pal[k as keyof typeof pal];
  });
  // For web, toggle the `.dark` CSS class on the document root so Tailwind
  // and the CSS variables in `global.css` switch accordingly.
  try {
    if (typeof document !== "undefined" && document.documentElement) {
      if (scheme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    }
  } catch (e) {
    // ignore on native platforms
  }
  // notify subscribers (UI root listens to this to trigger re-render)
  try {
    themeSubscribers.forEach((cb) => cb(scheme === "dark" ? "dark" : "light"));
  } catch (e) {}
}

const themeSubscribers = new Set<(s: "light" | "dark") => void>();

export function subscribeThemeChanges(
  cb: (s: "light" | "dark") => void,
): () => void {
  themeSubscribers.add(cb);
  // Return a cleanup function that does not return the boolean from Set.delete
  // to keep the return type `() => void` and satisfy React effect typing.
  return () => {
    themeSubscribers.delete(cb);
  };
}

const THEME_KEY = "sanhita:theme";

export type UserThemePref = "system" | "light" | "dark" | null;

export async function setUserTheme(pref: UserThemePref) {
  if (pref === "system" || pref === null) {
    const scheme = Appearance.getColorScheme();
    applyColorScheme(scheme === "dark" ? "dark" : "light");
  } else if (pref === "dark" || pref === "light") {
    applyColorScheme(pref === "dark" ? "dark" : "light");
  }
  try {
    if (pref === null) await SecureStore.deleteItemAsync(THEME_KEY);
    else await SecureStore.setItemAsync(THEME_KEY, pref);
  } catch (e) {
    // ignore persistence errors
  }
}

export async function loadUserTheme(): Promise<UserThemePref> {
  try {
    const v = await SecureStore.getItemAsync(THEME_KEY);
    if (!v) return "system";
    if (v === "light" || v === "dark" || v === "system")
      return v === "system" ? "system" : (v as UserThemePref);
    return "system";
  } catch (e) {
    return "system";
  }
}

export const radius = {
  card: 13,
  button: 8,
  pill: 999,
} as const;

export const space = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 24,
  xxl: 32,
} as const;

export const font = {
  pageTitle: { fontSize: 21, lineHeight: 28, fontWeight: "500" } as TextStyle,
  section: { fontSize: 17, lineHeight: 24, fontWeight: "500" } as TextStyle,
  body: { fontSize: 15, lineHeight: 24 } as TextStyle,
  secondary: { fontSize: 14, lineHeight: 22 } as TextStyle,
  caption: { fontSize: 12, lineHeight: 18 } as TextStyle,
  /** Clinical section labels — DO NOW, REFER NOW IF, etc. */
  clinical: {
    fontSize: 11,
    lineHeight: 16,
    fontWeight: "500",
    letterSpacing: 0.4,
  } as TextStyle,
} as const;

/** Subtle shadow — primary CTA only. */
export const shadowPrimary: ViewStyle = {
  shadowColor: "#000000",
  shadowOpacity: 0.12,
  shadowRadius: 6,
  shadowOffset: { width: 0, height: 2 },
  elevation: 2,
};

export const severityMeta: Record<
  Severity,
  {
    label: string;
    role: "danger" | "warning" | "success";
    clinicalLabel: string;
  }
> = {
  urgent: { label: "Refer now", role: "danger", clinicalLabel: "Urgent" },
  watch: {
    label: "Watch closely",
    role: "warning",
    clinicalLabel: "Watch closely · likely",
  },
  routine: { label: "Routine", role: "success", clinicalLabel: "Routine" },
};

/** Deterministic avatar tint from a name string. */
export function avatarTint(name: string): { bg: string; text: string } {
  const tints = [
    { bg: "#F5F5F5", text: "#1A1A18" },
    { bg: "#E9E9E9", text: "#1A1A18" },
    { bg: "#D9D9D9", text: "#1A1A18" },
    { bg: "#C9C9C9", text: "#1A1A18" },
    { bg: "#BFBFBF", text: "#1A1A18" },
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++)
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return tints[Math.abs(hash) % tints.length];
}
