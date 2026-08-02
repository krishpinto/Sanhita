// Outcome — the four-part recommendation: LIKELY, DO NOW, TELL THE PATIENT,
// REFER NOW IF, FOLLOW UP. Every line cited to a named guideline section.
// See ../../README.md, "The components" → Protocol Definition.

import { useRouter } from 'expo-router';
import { RotateCcw, ShieldAlert } from 'lucide-react-native';

import { Card, PrimaryButton, SectionHeader, T } from '@/components/ui';
import { currentOutcome } from '@/lib/protocol-engine';
import { useSanhita } from '@/lib/store';
import { severityMeta } from '@/theme';
import { ScrollView, View } from '@/tw';

export default function OutcomeScreen() {
  const router = useRouter();
  const engine = useSanhita((s) => s.engine);
  const reset = useSanhita((s) => s.reset);

  const outcome = engine ? currentOutcome(engine) : null;

  if (!engine || !outcome) {
    return (
      <View className="flex-1 bg-bg items-center justify-center p-6">
        <T variant="secondary" tone="secondary">
          No outcome yet — start an encounter from Home.
        </T>
      </View>
    );
  }

  const meta = severityMeta[outcome.severity];

  function startOver() {
    reset();
    router.replace('/home');
  }

  return (
    <ScrollView className="flex-1 bg-bg" contentContainerClassName="p-6 gap-4 pb-10">
      {engine.redFlagFired && (
        <Card className="flex-row items-center gap-3" style={{ backgroundColor: '#FBEDEB' }}>
          <ShieldAlert size={20} color="#8C3A32" />
          <T variant="secondary" tone="danger" className="flex-1">
            A danger sign was flagged during this encounter.
          </T>
        </Card>
      )}

      <Card className="gap-1" accent={meta.color}>
        <T variant="overline" tone="secondary">
          {meta.label} · LIKELY
        </T>
        <T variant="title">{outcome.likely}</T>
      </Card>

      <Card className="gap-2">
        <SectionHeader title="Do now" />
        {outcome.doNow.map((line) => (
          <T key={line} variant="secondary">
            • {line}
          </T>
        ))}
        {outcome.citations.doNow && (
          <T variant="caption" tone="secondary">
            {outcome.citations.doNow}
          </T>
        )}
      </Card>

      <Card className="gap-2">
        <SectionHeader title="Tell the patient" />
        <T variant="secondary">{outcome.tellPatient}</T>
        {outcome.citations.tellPatient && (
          <T variant="caption" tone="secondary">
            {outcome.citations.tellPatient}
          </T>
        )}
      </Card>

      <Card className="gap-2">
        <SectionHeader title="Refer now if" />
        {outcome.referIf.map((line) => (
          <T key={line} variant="secondary">
            • {line}
          </T>
        ))}
        {outcome.citations.referIf && (
          <T variant="caption" tone="secondary">
            {outcome.citations.referIf}
          </T>
        )}
      </Card>

      <Card className="gap-2">
        <SectionHeader title="Follow up" />
        <T variant="secondary">{outcome.followUp}</T>
        {outcome.citations.followUp && (
          <T variant="caption" tone="secondary">
            {outcome.citations.followUp}
          </T>
        )}
      </Card>

      <PrimaryButton label="Start over" icon={RotateCcw} variant="quiet" onPress={startOver} />
    </ScrollView>
  );
}
