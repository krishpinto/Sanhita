// Field View — one question at a time. The health worker sees only the
// current step; no tree, no history. Delivery is thin and deliberately
// dumb: it renders whatever the Protocol Engine hands it. See
// ../../README.md, "Field view vs review view".

import { useRouter } from 'expo-router';
import { ArrowRight } from 'lucide-react-native';
import { useEffect, useState } from 'react';

import { Card, PrimaryButton, T } from '@/components/ui';
import { currentStep } from '@/lib/protocol-engine';
import { useSanhita } from '@/lib/store';
import { ScrollView, TextInput, View } from '@/tw';

export default function FieldScreen() {
  const router = useRouter();
  const engine = useSanhita((s) => s.engine);
  const activeIndexCard = useSanhita((s) => s.activeIndexCard);
  const answerChoice = useSanhita((s) => s.answerCurrentChoice);
  const answerValue = useSanhita((s) => s.answerCurrentValue);
  const [valueText, setValueText] = useState('');

  const step = engine ? currentStep(engine) : null;

  useEffect(() => {
    if (engine?.outcomeId) router.replace('/outcome');
  }, [engine?.outcomeId, router]);

  useEffect(() => {
    setValueText('');
  }, [step?.id]);

  if (!engine || !activeIndexCard || !step) {
    return (
      <View className="flex-1 bg-bg items-center justify-center p-6">
        <T variant="secondary" tone="secondary">
          No protocol in progress. Start one from Home.
        </T>
      </View>
    );
  }

  const lastOptionIndex = (step.options?.length ?? 0) - 1;

  return (
    <ScrollView className="flex-1 bg-bg" contentContainerClassName="p-6 gap-4">
      <T variant="caption" tone="secondary" className="font-semibold tracking-wide">
        {activeIndexCard.name} · {engine.protocol.title} v{engine.protocol.version}
      </T>

      <Card className="gap-4">
        <T variant="title">{step.question}</T>

        {step.answerType === 'choice' &&
          step.options?.map((opt, i) => (
            <PrimaryButton
              key={opt.label}
              label={opt.label}
              variant={i === lastOptionIndex ? 'quiet' : 'inverse'}
              onPress={() => answerChoice(i)}
            />
          ))}

        {step.answerType === 'value' && (
          <View className="gap-3">
            <TextInput
              className="bg-bg border border-border rounded-button px-4 py-3 text-body text-ink"
              value={valueText}
              onChangeText={setValueText}
              placeholder={step.unit ? `Number of ${step.unit}` : 'Enter a number'}
              placeholderTextColor="#9AA0AA"
              keyboardType="number-pad"
            />
            <PrimaryButton
              label="Continue"
              icon={ArrowRight}
              disabled={valueText.trim().length === 0}
              onPress={() => answerValue(Number(valueText.trim()))}
            />
            <PrimaryButton label="Don't know / not available" variant="quiet" onPress={() => answerValue(null)} />
          </View>
        )}
      </Card>
    </ScrollView>
  );
}
