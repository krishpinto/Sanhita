// Field View — one question at a time with progress bar and segmented answers.

import { useRouter } from "expo-router";
import { ArrowRight } from "lucide-react-native";
import { useEffect, useMemo, useState } from "react";

import { PageContainer } from "@/components/layout";
import {
    Card,
    PrimaryButton,
    ProgressBar,
    SecondaryButton,
    SegmentedControl,
    T,
    TertiaryButton,
    TextField,
} from "@/components/ui";
import { currentStep } from "@/lib/protocol-engine";
import { useSanhita } from "@/lib/store";
import { ScrollView, View } from "@/tw";

export default function FieldScreen() {
  const router = useRouter();
  const engine = useSanhita((s) => s.engine);
  const activeIndexCard = useSanhita((s) => s.activeIndexCard);
  const answerChoice = useSanhita((s) => s.answerCurrentChoice);
  const answerValue = useSanhita((s) => s.answerCurrentValue);
  const [valueText, setValueText] = useState("");

  const step = engine ? currentStep(engine) : null;
  const totalSteps = engine ? Object.keys(engine.protocol.steps).length : 0;
  const currentNum = engine ? engine.trail.length + 1 : 0;

  const choiceSegments = useMemo(() => {
    if (!step?.options) return [];
    const last = step.options.length - 1;
    return step.options
      .slice(0, last)
      .map((opt, i) => ({ label: opt.label, value: String(i) }));
  }, [step]);

  useEffect(() => {
    if (engine?.outcomeId) router.replace("/outcome");
  }, [engine?.outcomeId, router]);

  useEffect(() => {
    setValueText("");
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
  const unknownOption = step.options?.[lastOptionIndex];

  return (
    <ScrollView className="flex-1 bg-bg" contentContainerClassName="pb-8">
      <PageContainer className="pt-4 gap-6">
        <Card className="gap-4">
          <View className="gap-1">
            <T variant="caption" tone="muted">
              {activeIndexCard.name} · {engine.protocol.title.toLowerCase()} · v
              {engine.protocol.version}
            </T>
            <ProgressBar current={currentNum} total={totalSteps} />
          </View>

          <T variant="section" className="font-medium">
            {step.question}
          </T>

          {step.answerType === "choice" && step.options && (
            <View className="gap-3">
              {choiceSegments.length > 0 && choiceSegments.length <= 3 ? (
                <SegmentedControl
                  options={choiceSegments}
                  onChange={(v) => answerChoice(Number(v))}
                  className="py-2"
                />
              ) : (
                step.options
                  .slice(0, lastOptionIndex)
                  .map((opt, i) => (
                    <SecondaryButton
                      key={opt.label}
                      label={opt.label}
                      onPress={() => answerChoice(i)}
                      fullWidth
                    />
                  ))
              )}
              {unknownOption && (
                <TertiaryButton
                  label={unknownOption.label}
                  onPress={() => answerChoice(lastOptionIndex)}
                />
              )}
            </View>
          )}

          {step.answerType === "value" && (
            <View className="gap-3">
              <TextField
                value={valueText}
                onChangeText={setValueText}
                placeholder={
                  step.unit ? `Number of ${step.unit}` : "Enter a number"
                }
                keyboardType="number-pad"
              />
              <View className="flex-row gap-3">
                <PrimaryButton
                  label="Continue"
                  icon={ArrowRight}
                  disabled={valueText.trim().length === 0}
                  onPress={() => answerValue(Number(valueText.trim()))}
                  fullWidth={false}
                />
                <TertiaryButton
                  label="Don't know"
                  onPress={() => answerValue(null)}
                />
              </View>
            </View>
          )}
        </Card>
      </PageContainer>
    </ScrollView>
  );
}
