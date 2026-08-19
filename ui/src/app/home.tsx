// Home — greeting, new encounter CTA, recent encounters with status pills.

import { useRouter } from "expo-router";
import { Plus } from "lucide-react-native";

import { AppHeader, AppShell, PageContainer } from "@/components/layout";
import {
    Avatar,
    Card,
    SecondaryButton,
    SectionHeader,
    StatusPill,
    T,
} from "@/components/ui";
import { getOutcome } from "@/lib/protocol-index";
import { useSanhita } from "@/lib/store";
import { ScrollView, View } from "@/tw";
import type { EncounterRecord } from "@/types/protocol";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function encounterPill(e: EncounterRecord) {
  if (!e.outcomeId) return { label: "In progress", role: "accent" as const };
  const outcome = getOutcome(e.protocolId, e.outcomeId);
  if (!outcome || outcome.severity === "routine")
    return { label: "Done", role: "success" as const };
  if (outcome.severity === "watch")
    return { label: "Watch", role: "warning" as const };
  return { label: "Refer now", role: "danger" as const };
}

function encounterSubtitle(e: EncounterRecord) {
  if (!e.outcomeId)
    return (
      e.indexCard.complaint.charAt(0).toUpperCase() +
      e.indexCard.complaint.slice(1)
    );
  const outcome = getOutcome(e.protocolId, e.outcomeId);
  const parts = [
    e.indexCard.complaint.charAt(0).toUpperCase() +
      e.indexCard.complaint.slice(1),
    outcome?.likely,
  ].filter(Boolean);
  return parts.join(" · ");
}

function patientLine(e: EncounterRecord) {
  const bits = [e.indexCard.name];
  if (e.indexCard.age) bits.push(String(e.indexCard.age));
  const sexShort =
    e.indexCard.sex === "Male"
      ? "M"
      : e.indexCard.sex === "Female"
        ? "F"
        : e.indexCard.sex?.[0];
  if (sexShort) bits.push(sexShort);
  return bits.join(", ");
}

export default function HomeScreen() {
  const router = useRouter();
  const encounters = useSanhita((s) => s.encounters);
  const recent = encounters.slice(0, 5);

  return (
    <AppShell>
      <ScrollView
        className="flex-1"
        contentContainerClassName="pb-6"
        keyboardShouldPersistTaps="handled"
      >
        <PageContainer className="pt-2 gap-6">
          <AppHeader showProfile={false} />

          <Card className="gap-5">
            <View className="gap-1">
              <T variant="secondary" tone="secondary">
                {greeting()}, doctor
              </T>
              <T variant="pageTitle">Who are we seeing today?</T>
            </View>
            <SecondaryButton
              label="New encounter"
              icon={Plus}
              onPress={() => router.push("/intake")}
              fullWidth={false}
              className="px-4 py-2"
            />
          </Card>

          {recent.length > 0 && (
            <View className="gap-3">
              <SectionHeader title="Recent encounters" />
              {recent.map((e) => {
                const pill = encounterPill(e);
                return (
                  <Card
                    key={e.id}
                    onPress={() => router.push("/encounters")}
                    className="flex-row items-center gap-3"
                  >
                    <Avatar name={e.indexCard.name} size={44} />
                    <View className="flex-1 gap-0.5">
                      <T variant="body" className="font-medium">
                        {patientLine(e)}
                      </T>
                      <T variant="caption" tone="muted" numberOfLines={1}>
                        {encounterSubtitle(e)}
                      </T>
                    </View>
                    <StatusPill label={pill.label} role={pill.role} />
                  </Card>
                );
              })}
            </View>
          )}
        </PageContainer>
      </ScrollView>
    </AppShell>
  );
}
