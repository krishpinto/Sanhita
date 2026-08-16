import { DefaultTheme, Stack, ThemeProvider } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { Appearance } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import "../global.css";

import { DemoWatermark } from "@/components/DemoWatermark";
import {
  applyColorScheme,
  c,
  loadUserTheme,
  subscribeThemeChanges,
} from "@/theme";
import {
  Montserrat_400Regular,
  Montserrat_500Medium,
  Montserrat_600SemiBold,
  Montserrat_700Bold,
  useFonts,
} from "@expo-google-fonts/montserrat";

export default function RootLayout() {
  const [scheme, setScheme] = useState<"light" | "dark" | null>(
    Appearance.getColorScheme() === "dark" ? "dark" : "light",
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      const pref = await loadUserTheme();
      if (!mounted) return;
      if (pref === "system" || pref === null) {
        const sys = Appearance.getColorScheme();
        setScheme(sys === "dark" ? "dark" : "light");
        applyColorScheme(sys === "dark" ? "dark" : "light");
        const sub = Appearance.addChangeListener(({ colorScheme }) => {
          const s = colorScheme === "dark" ? "dark" : "light";
          setScheme(s);
          applyColorScheme(s);
        });
        return () => sub.remove();
      } else {
        const use = pref === "dark" ? "dark" : "light";
        setScheme(use);
        applyColorScheme(use);
      }
    })();
    // subscribe to theme changes triggered elsewhere (Settings)
    const unsub = subscribeThemeChanges((s) => {
      setScheme(s === "dark" ? "dark" : "light");
      // applyColorScheme already run by caller; ensure palette applied
      applyColorScheme(s === "dark" ? "dark" : "light");
    });
    return () => {
      mounted = false;
      unsub();
    };
  }, []);

  const [fontsLoaded] = useFonts({
    Montserrat_400Regular,
    Montserrat_500Medium,
    Montserrat_600SemiBold,
    Montserrat_700Bold,
  });

  if (!fontsLoaded) return null;

  // Ensure native React Native Text uses the loaded Montserrat as default
  // Intentionally do not set `Text.defaultProps` here to avoid cross-platform
  // typing issues; fonts are loaded and applied where needed.

  const ClinicalTheme = {
    ...DefaultTheme,
    colors: {
      ...DefaultTheme.colors,
      primary: c.accent,
      background: c.bg,
      card: c.card,
      text: c.ink,
      border: c.border,
    },
  };

  return (
    <ThemeProvider value={ClinicalTheme}>
      <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }} edges={["top"]}>
        <DemoWatermark />
        <Stack
          screenOptions={{
            headerShown: true,
            headerStyle: { backgroundColor: c.bg },
            headerTitleStyle: {
              color: c.ink,
              fontWeight: "500",
              fontSize: 17,
            },
            headerTintColor: c.accent,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: c.bg },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="home" options={{ headerShown: false }} />
          <Stack.Screen name="intake" options={{ title: "New encounter" }} />
          <Stack.Screen name="encounters" options={{ headerShown: false }} />
          <Stack.Screen name="field" options={{ title: "Protocol" }} />
          <Stack.Screen name="outcome" options={{ title: "Outcome" }} />
          <Stack.Screen
            name="review"
            options={{ headerShown: false, title: "Library" }}
          />
          <Stack.Screen name="settings" options={{ title: "Settings" }} />
        </Stack>
      </SafeAreaView>
      <StatusBar style={scheme === "dark" ? "light" : "dark"} />
    </ThemeProvider>
  );
}
