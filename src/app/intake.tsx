// Index card intake — the one-time input before any protocol opens: name,
// age, sex, chief complaint. The complaint is matched against the Protocol
// Index (a deterministic lookup, never interpreted) to pick which protocol
// to open. See ../../README.md, "Two moments of input".

import { useRouter } from 'expo-router';
import { ArrowRight } from 'lucide-react-native';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform } from 'react-native';

import { ErrorCard, PrimaryButton, T } from '@/components/ui';
import { lookupProtocol } from '@/lib/protocol-index';
import { useSanhita } from '@/lib/store';
import { Pressable, ScrollView, TextInput, View } from '@/tw';
import type { Sex } from '@/types/protocol';

const SEXES: Sex[] = ['Male', 'Female', 'Other'];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View className="gap-2">
      <T variant="caption" tone="secondary" className="font-semibold tracking-wide ml-1">
        {label.toUpperCase()}
      </T>
      {children}
    </View>
  );
}

export default function IntakeScreen() {
  const router = useRouter();
  const addIndexCard = useSanhita((s) => s.addIndexCard);
  const startProtocol = useSanhita((s) => s.startProtocol);

  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [sex, setSex] = useState<Sex | undefined>(undefined);
  const [complaint, setComplaint] = useState('');
  const [notFound, setNotFound] = useState(false);

  const canSave = name.trim().length > 0 && complaint.trim().length > 0;

  function save() {
    if (!canSave) return;
    const ageNum = age.trim() ? Number(age.trim()) : undefined;
    const protocol = lookupProtocol(complaint, ageNum);
    if (!protocol) {
      setNotFound(true);
      return;
    }
    setNotFound(false);
    const card = addIndexCard({ name: name.trim(), age: age.trim() || undefined, sex, complaint: complaint.trim() });
    startProtocol(card, protocol);
    router.replace('/field');
  }

  const inputClass = 'bg-card border border-border rounded-button px-4 py-3 text-body text-ink';

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: '#FAF9F6' }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerClassName="p-6 gap-4 pb-6" keyboardShouldPersistTaps="handled">
        <T variant="title">New encounter</T>
        <T variant="secondary" tone="secondary">
          Synthetic record — do not enter real patient data.
        </T>

        <Field label="Full name">
          <TextInput
            className={inputClass}
            value={name}
            onChangeText={setName}
            placeholder="e.g. Rohan K."
            placeholderTextColor="#9AA0AA"
            autoFocus
          />
        </Field>

        <View className="flex-row gap-3">
          <View className="flex-1">
            <Field label="Age">
              <TextInput
                className={inputClass}
                value={age}
                onChangeText={setAge}
                placeholder="24"
                placeholderTextColor="#9AA0AA"
                keyboardType="number-pad"
                maxLength={3}
              />
            </Field>
          </View>
          <View className="flex-[2]">
            <Field label="Sex">
              <View className="flex-row bg-card border border-border rounded-button p-1">
                {SEXES.map((s) => {
                  const active = sex === s;
                  return (
                    <Pressable
                      key={s}
                      accessibilityRole="button"
                      className={`flex-1 py-2 rounded-[8px] items-center ${active ? 'bg-accent' : ''}`}
                      style={({ pressed }) => pressed && { transform: [{ scale: 0.98 }] }}
                      onPress={() => setSex(s)}>
                      <T
                        variant="secondary"
                        tone={active ? 'onAccent' : 'secondary'}
                        className={active ? 'font-semibold' : ''}>
                        {s}
                      </T>
                    </Pressable>
                  );
                })}
              </View>
            </Field>
          </View>
        </View>

        <Field label="Chief complaint">
          <TextInput
            className={inputClass}
            value={complaint}
            onChangeText={(t) => {
              setComplaint(t);
              setNotFound(false);
            }}
            placeholder="e.g. fever"
            placeholderTextColor="#9AA0AA"
          />
        </Field>
        <T variant="caption" tone="secondary">
          Matched against a fixed list of known complaints — never interpreted freely.
        </T>

        {notFound && (
          <ErrorCard message={`No protocol for "${complaint.trim()}" yet — only "fever" is authored so far.`} />
        )}
      </ScrollView>

      <View className="p-4 bg-card border-t border-border">
        <PrimaryButton label="Open protocol" onPress={save} disabled={!canSave} icon={ArrowRight} />
      </View>
    </KeyboardAvoidingView>
  );
}
