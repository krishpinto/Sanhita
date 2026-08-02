// Home — the health worker's daily entry point, dark "MobileCode" aesthetic
// (greeting + large light headline + a composer pinned at the bottom).
// The composer starts a new encounter (routes into intake); recent
// encounters come from the Encounter Record list. Built on src/components/mc.tsx.

import { useRouter } from 'expo-router';
import { ChevronRight, History, Stethoscope, UserRoundPlus } from 'lucide-react-native';
import { useState } from 'react';

import { MC, MCBackground, MCComposer, MCText } from '@/components/mc';
import { useSanhita } from '@/lib/store';
import { Pressable, ScrollView, View } from '@/tw';

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function initials(name: string) {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export default function HomeScreen() {
  const router = useRouter();
  const encounters = useSanhita((s) => s.encounters);
  const [query, setQuery] = useState('');

  const recent = encounters.slice(0, 3);

  return (
    <MCBackground>
      <View className="flex-1">
        {/* Top bar */}
        <View className="flex-row items-center justify-between px-6 pt-4">
          <View className="h-9 w-9 items-center justify-center rounded-xl border border-night-border bg-night-surface">
            <Stethoscope size={18} color={MC.ink} strokeWidth={2} />
          </View>
          <MCText variant="eyebrow">Sanhita</MCText>
          <View className="h-9 w-9" />
        </View>

        {/* Greeting + headline + recent encounters (scrolls) */}
        <ScrollView className="flex-1" contentContainerClassName="px-6 pt-10 pb-4" keyboardShouldPersistTaps="handled">
          <View className="items-center gap-2">
            <MCText variant="greeting">{greeting()}, Doctor 👋</MCText>
            <MCText variant="headline" className="text-center">
              Who are we seeing today?
            </MCText>
          </View>

          {recent.length > 0 && (
            <View className="gap-3 pt-12">
              <MCText variant="eyebrow" className="ml-1">
                Recent encounters
              </MCText>
              {recent.map((e) => (
                <Pressable
                  key={e.id}
                  onPress={() => router.push('/encounters')}
                  className="flex-row items-center gap-3 rounded-3xl border border-night-border bg-night-surface p-4">
                  <View className="h-10 w-10 items-center justify-center rounded-full bg-night-surface-strong">
                    <MCText variant="muted" className="font-semibold text-night-text">
                      {initials(e.indexCard.name)}
                    </MCText>
                  </View>
                  <View className="flex-1">
                    <MCText variant="body" className="font-semibold">
                      {e.indexCard.name}
                    </MCText>
                    <MCText variant="muted" numberOfLines={1}>
                      {e.indexCard.complaint}
                    </MCText>
                  </View>
                  <ChevronRight size={16} color={MC.faint} strokeWidth={2} />
                </Pressable>
              ))}
            </View>
          )}
        </ScrollView>

        {/* Composer — pinned at the bottom */}
        <View className="px-6 pb-6 pt-1">
          <MCComposer
            value={query}
            onChangeText={setQuery}
            onSubmit={() => router.push('/intake')}
            onPlus={() => router.push('/intake')}
            placeholder="Start a new encounter…"
            pills={[
              { label: 'Encounters', icon: History, onPress: () => router.push('/encounters') },
              { label: 'New encounter', icon: UserRoundPlus, onPress: () => router.push('/intake') },
            ]}
          />
        </View>
      </View>
    </MCBackground>
  );
}
