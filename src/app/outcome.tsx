// Outcome — severity pill + four-part recommendation with citations.

import { useRouter } from "expo-router";
import { ShieldAlert } from "lucide-react-native";

import { PageContainer } from "@/components/layout";
import { Card, OutcomeSection, PrimaryButton, StatusPill, T } from "@/components/ui";
import { currentOutcome } from "@/lib/protocol-engine";
import { useSanhita } from "@/lib/store";
import { c, severityMeta } from "@/theme";
import { ScrollView, View } from "@/tw";

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
    router.replace("/home");
  }

  return (
    <ScrollView className="flex-1 bg-bg" contentContainerClassName="pb-10">
      <PageContainer className="pt-2 gap-4">
        <Card className="gap-4">
          {engine.redFlagFired && (
            <View className="flex-row items-center gap-3 bg-danger-bg border border-danger-border rounded-card p-4">
              <ShieldAlert size={20} color={c.dangerText} />
              <T variant="secondary" tone="danger" className="flex-1">
                A danger sign was flagged during this encounter.
              </T>
            </View>
          )}

          <View className="gap-2">
            <StatusPill
              label={meta.clinicalLabel}
              role={
                meta.role === "danger"
                  ? "danger"
                  : meta.role === "warning"
                    ? "warning"
                    : "success"
              }
            />
            <T variant="pageTitle">{outcome.likely}</T>
          </View>

          <View className="gap-3">
            <OutcomeSection
              title="Do now"
              tone="neutral"
              citation={outcome.citations.doNow}
            >
              {outcome.doNow.map((line) => (
                <T key={line} variant="secondary">
                  • {line}
                </T>
              ))}
            </OutcomeSection>

            <OutcomeSection
              title="Tell the patient"
              tone="neutral"
              citation={outcome.citations.tellPatient}
            >
              <T variant="secondary">{outcome.tellPatient}</T>
            </OutcomeSection>

            <OutcomeSection
              title="Refer now if"
              tone="danger"
              citation={outcome.citations.referIf}
            >
              {outcome.referIf.map((line) => (
                <T key={line} variant="secondary">
                  • {line}
                </T>
              ))}
            </OutcomeSection>

            <OutcomeSection
              title="Follow up"
              tone="neutral"
              citation={outcome.citations.followUp}
            >
              <T variant="secondary">{outcome.followUp}</T>
            </OutcomeSection>
          </View>

          <PrimaryButton label="Start over" onPress={startOver} fullWidth={false} />
        </Card>
      </PageContainer>
    </ScrollView>
  );
}
