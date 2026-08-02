import { DefaultTheme, Stack, ThemeProvider, usePathname } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView } from 'react-native-safe-area-context';

import '../global.css';

import { DemoWatermark } from '@/components/DemoWatermark';
import { color, font } from '@/theme';

// Locked light theme — "clinical calm". No dark mode for the protocol flow.
const ClinicalTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: color.accent,
    background: color.bg,
    card: color.card,
    text: color.ink,
    border: color.border,
  },
};

// The entry + home screens use the dark "MobileCode" theme (see global.css
// night-* tokens + src/components/mc.tsx) — the protocol-walking flow
// (intake → field → outcome → review) stays on the light clinical kit. This
// outer shell paints the safe-area background per-route so the notch/
// status-bar strip matches whichever screen is showing.
const DARK_ROUTES = ['/', '/home'];
const MC_BG = '#06060B';

export default function RootLayout() {
  const pathname = usePathname();
  const isDark = DARK_ROUTES.includes(pathname);
  const bg = isDark ? MC_BG : color.bg;

  return (
    <ThemeProvider value={ClinicalTheme}>
      <SafeAreaView style={{ flex: 1, backgroundColor: bg }} edges={['top']}>
        <DemoWatermark />
        <Stack
          screenOptions={{
            headerShown: true,
            headerStyle: { backgroundColor: color.bg },
            headerTitleStyle: { color: color.ink, fontWeight: '600', fontSize: font.body.fontSize },
            headerTintColor: color.accent,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: color.bg },
          }}>
          <Stack.Screen name="index" options={{ headerShown: false, contentStyle: { backgroundColor: MC_BG } }} />
          <Stack.Screen name="home" options={{ headerShown: false, contentStyle: { backgroundColor: MC_BG } }} />
          <Stack.Screen name="intake" options={{ title: 'New encounter' }} />
          <Stack.Screen name="encounters" options={{ title: 'Encounters' }} />
          <Stack.Screen name="field" options={{ title: 'Protocol' }} />
          <Stack.Screen name="outcome" options={{ title: 'Outcome' }} />
          <Stack.Screen name="review" options={{ title: 'Review view' }} />
        </Stack>
      </SafeAreaView>
      <StatusBar style={isDark ? 'light' : 'dark'} />
    </ThemeProvider>
  );
}
