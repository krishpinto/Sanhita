// Landing — dark "MobileCode" hero: near-black starfield sky, an eyebrow
// brand row, a large light-weight headline, and the primary CTA. Built on
// src/components/mc.tsx.

import { useRouter } from 'expo-router';
import { BookOpenCheck, ClipboardList, ShieldAlert, Stethoscope } from 'lucide-react-native';

import { MC, MCBackground, MCButton, MCScroll, MCText } from '@/components/mc';
import { View } from '@/tw';

const FEATURES = [
  { icon: ClipboardList, title: 'Walks the protocol', text: 'One question at a time — nothing to interpret, nothing to guess.' },
  { icon: ShieldAlert, title: 'Danger signs interrupt', text: 'A red flag short-circuits straight to an urgent recommendation.' },
  { icon: BookOpenCheck, title: 'Every line cited', text: 'DO NOW / TELL THE PATIENT / REFER NOW IF — each traced to a guideline section.' },
];

export default function LandingScreen() {
  const router = useRouter();

  return (
    <MCBackground>
      <MCScroll className="gap-10">
        {/* Brand row */}
        <View className="flex-row items-center gap-3 pt-6">
          <View className="h-9 w-9 items-center justify-center rounded-xl border border-night-border bg-night-surface">
            <Stethoscope size={18} color={MC.ink} strokeWidth={2} />
          </View>
          <MCText variant="eyebrow">Sanhita</MCText>
        </View>

        {/* Hero headline */}
        <View className="gap-6 pt-6">
          <View>
            <MCText variant="headline" className="text-night-text-muted">
              The protocol,{'\n'}made walkable.
            </MCText>
            <MCText variant="headline" className="font-normal">
              No guessing. No LLM.
            </MCText>
          </View>
          <View className="gap-4">
            <MCButton label="Get started" className="self-start px-8" onPress={() => router.push('/home')} />
          </View>
        </View>

        {/* Feature rows */}
        <View className="gap-3 pt-2">
          {FEATURES.map((f) => (
            <View
              key={f.title}
              className="flex-row items-center gap-4 rounded-3xl border border-night-border bg-night-surface p-4">
              <View className="h-10 w-10 items-center justify-center rounded-full bg-night-surface-strong">
                <f.icon size={18} color={MC.accent} strokeWidth={2} />
              </View>
              <View className="flex-1">
                <MCText variant="body" className="font-semibold">
                  {f.title}
                </MCText>
                <MCText variant="muted">{f.text}</MCText>
              </View>
            </View>
          ))}
        </View>

        <View className="flex-1" />
        <MCText variant="faint" className="pb-2 text-center">
          Every recommendation traces to a named guideline section — never a diagnosis on its own.
        </MCText>
      </MCScroll>
    </MCBackground>
  );
}
