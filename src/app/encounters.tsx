// Encounters — searchable list of completed Encounter Records (avatar
// initials, complaint + red-flag chips) with a FAB for starting a new one.

import { useRouter } from 'expo-router';
import { Plus, Search, Users } from 'lucide-react-native';
import { useState } from 'react';

import { Card, Chip, EmptyState, Rise, SectionHeader, T } from '@/components/ui';
import { useSanhita } from '@/lib/store';
import { Pressable, ScrollView, TextInput, View } from '@/tw';

function initials(name: string) {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export default function EncountersScreen() {
  const router = useRouter();
  const encounters = useSanhita((s) => s.encounters);

  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const filtered = q
    ? encounters.filter(
        (e) => e.indexCard.name.toLowerCase().includes(q) || e.indexCard.complaint.toLowerCase().includes(q)
      )
    : encounters;

  return (
    <View className="flex-1 bg-bg">
      <ScrollView contentContainerClassName="p-6 gap-3 pb-28" keyboardShouldPersistTaps="handled">
        {/* Search */}
        <View className="flex-row items-center gap-2 bg-card border border-border rounded-button px-4">
          <Search size={16} color="#9AA0AA" strokeWidth={2} />
          <TextInput
            className="flex-1 py-3 text-secondary text-ink"
            value={query}
            onChangeText={setQuery}
            placeholder="Search encounters or complaints"
            placeholderTextColor="#9AA0AA"
            returnKeyType="search"
          />
        </View>

        <SectionHeader title={q ? 'Results' : 'Recent'} />

        {filtered.length === 0 ? (
          <EmptyState
            icon={Users}
            text={
              q
                ? `No encounters match "${query.trim()}".`
                : 'No encounters yet — start one from Home.'
            }
            actionLabel={q ? undefined : 'New encounter'}
            onAction={q ? undefined : () => router.push('/intake')}
          />
        ) : (
          filtered.map((e, i) => (
            <Rise key={e.id} index={i}>
              <Card className="gap-3">
                <View className="flex-row items-center gap-3">
                  <View className="w-11 h-11 rounded-full bg-accent-soft items-center justify-center">
                    <T variant="secondary" className="text-accent font-semibold">
                      {initials(e.indexCard.name)}
                    </T>
                  </View>
                  <View className="flex-1">
                    <T variant="body" className="font-semibold">
                      {e.indexCard.name}
                    </T>
                    <T variant="caption" tone="secondary">
                      {[e.indexCard.age && `${e.indexCard.age} years`, e.indexCard.sex].filter(Boolean).join(' · ') ||
                        'No details recorded'}
                    </T>
                  </View>
                </View>

                <View className="flex-row flex-wrap gap-2">
                  <Chip label={e.indexCard.complaint} />
                  {e.redFlagFired && <Chip label="Red flag" tint="#8C3A32" soft="#FBEDEB" />}
                  {!e.completedAt && <Chip label="In progress" tint="#8A6D1D" soft="#F7F1E1" />}
                </View>
              </Card>
            </Rise>
          ))
        )}
      </ScrollView>

      {/* FAB — new encounter */}
      <Pressable
        onPress={() => router.push('/intake')}
        accessibilityRole="button"
        accessibilityLabel="New encounter"
        className="absolute right-6 bottom-8 w-14 h-14 rounded-full bg-accent items-center justify-center shadow-card"
        style={({ pressed }) => pressed && { transform: [{ scale: 0.98 }] }}>
        <Plus size={26} color="#FFFFFF" strokeWidth={2.2} />
      </Pressable>
    </View>
  );
}
