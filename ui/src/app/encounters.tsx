// Encounters — searchable list with Avatar + StatusPill.

import { useRouter } from "expo-router";
import { Plus, Search, Users, X } from "lucide-react-native";
import { useState } from "react";

import { AppShell, PageContainer } from "@/components/layout";
import {
    Avatar,
    Card,
    EmptyState,
    PrimaryButton,
    Rise,
    SectionHeader,
    StatusPill,
    T,
    TextField,
} from "@/components/ui";
import { useBreakpoint } from "@/hooks/useBreakpoint";
import { getOutcome } from "@/lib/protocol-index";
import { useSanhita } from "@/lib/store";
import { c, severityMeta } from "@/theme";
import { Pressable, ScrollView, View } from "@/tw";

export default function EncountersScreen() {
  const router = useRouter();
  const { isDesktop } = useBreakpoint();
  const encounters = useSanhita((s) => s.encounters);

  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const filtered = q
    ? encounters.filter(
        (e) =>
          e.indexCard.name.toLowerCase().includes(q) ||
          e.indexCard.complaint.toLowerCase().includes(q),
      )
    : encounters;

  return (
    <AppShell>
      <View className="flex-1 bg-bg">
        <ScrollView
          contentContainerClassName="pb-8"
          keyboardShouldPersistTaps="handled"
        >
          <PageContainer className="pt-2 gap-4">
            <Card className="gap-4">
              <View className="flex-row items-center gap-2 bg-card rounded-button px-3 py-2 border border-border">
                <Search size={16} color={c.inkMuted} strokeWidth={2} />
                <TextField
                  className="flex-1 border-0 bg-transparent px-0 min-h-0"
                  value={query}
                  onChangeText={setQuery}
                  placeholder="Search encounters or complaints"
                  returnKeyType="search"
                />
                {query.length > 0 && (
                  <Pressable
                    onPress={() => setQuery("")}
                    accessibilityRole="button"
                    hitSlop={8}
                  >
                    <X size={14} color={c.inkMuted} strokeWidth={3} />
                  </Pressable>
                )}
              </View>
              <SectionHeader title={q ? "Results" : "Recent"} />
            </Card>

            {filtered.length === 0 ? (
              <EmptyState
                icon={Users}
                text={
                  q
                    ? `No encounters match "${query.trim()}".`
                    : "No encounters yet — start one from Home."
                }
                actionLabel={q ? undefined : "New encounter"}
                onAction={q ? undefined : () => router.push("/intake")}
              />
            ) : (
              filtered.map((e, i) => {
                const outcome = e.outcomeId
                  ? getOutcome(e.protocolId, e.outcomeId)
                  : null;
                const meta = outcome ? severityMeta[outcome.severity] : null;
                return (
                  <Rise key={e.id} index={i}>
                    <Card className="flex-row items-center gap-3">
                      <Avatar name={e.indexCard.name} />
                      <View className="flex-1 gap-0.5">
                        <T variant="body" className="font-medium">
                          {e.indexCard.name}
                        </T>
                        <T variant="caption" tone="muted">
                          {[
                            e.indexCard.age && `${e.indexCard.age} years`,
                            e.indexCard.sex,
                            e.indexCard.complaint,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </T>
                      </View>
                      <View className="items-end gap-1">
                        {e.redFlagFired && (
                          <StatusPill label="Red flag" role="danger" />
                        )}
                        {meta && (
                          <StatusPill
                            label={meta.label}
                            role={
                              meta.role === "danger"
                                ? "danger"
                                : meta.role === "warning"
                                  ? "warning"
                                  : "success"
                            }
                          />
                        )}
                      </View>
                    </Card>
                  </Rise>
                );
              })
            )}

            {isDesktop && !(encounters.length === 0 && q === "") && (
              <PrimaryButton
                label="New encounter"
                icon={Plus}
                onPress={() => router.push("/intake")}
                fullWidth={false}
              />
            )}
          </PageContainer>
        </ScrollView>

        {!isDesktop && !(encounters.length === 0 && q === "") && (
          <Pressable
            onPress={() => router.push("/intake")}
            accessibilityRole="button"
            accessibilityLabel="New encounter"
            className="absolute right-5 bottom-6 h-10 rounded-button border px-3 items-center justify-center"
            style={({ pressed }) => [
              {
                borderColor: c.borderStrong,
                borderWidth: 1,
                backgroundColor: "transparent",
              },
              pressed && { opacity: 0.9 },
            ]}
          >
            <Plus size={18} color={c.accent} strokeWidth={2.2} />
          </Pressable>
        )}
      </View>
    </AppShell>
  );
}
