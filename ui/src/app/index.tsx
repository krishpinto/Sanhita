// Landing — hero headline, feature cards, single CTA. Light clinical kit.

import { useRouter } from "expo-router";
import { BookOpenCheck, ClipboardList, ShieldAlert } from "lucide-react-native";

import { AppHeader, PageContainer } from "@/components/layout";
import { Card, PrimaryButton, T } from "@/components/ui";
import { c } from "@/theme";
import { ScrollView, View } from "@/tw";

const FEATURES = [
  {
    icon: ClipboardList,
    title: "Walks the protocol",
    text: "One question at a time — nothing to interpret, nothing to guess.",
  },
  {
    icon: ShieldAlert,
    title: "Danger signs interrupt",
    text: "A red flag short-circuits straight to an urgent recommendation.",
  },
  {
    icon: BookOpenCheck,
    title: "Guideline citations",
    text: "DO NOW / TELL THE PATIENT / REFER NOW IF — each traced to a guideline section.",
  },
];

export default function LandingScreen() {
  const router = useRouter();

  return (
    <ScrollView className="flex-1 bg-bg" contentContainerClassName="pb-12">
      <PageContainer className="pt-4 gap-8">
        <AppHeader showProfile={false} />

        <View className="gap-4 pt-4">
          <T variant="pageTitle">No guessing. No LLM.</T>
          <T variant="secondary" tone="secondary">
            Every recommendation traces to a named guideline section — never a
            diagnosis on its own.
          </T>
          <PrimaryButton
            label="Get started"
            onPress={() => router.push("/home")}
            fullWidth={false}
          />
        </View>

        <View className="gap-3">
          {FEATURES.map((f, i) => (
            <Card key={f.title} className="flex-row items-center gap-4">
              <View className="h-10 w-10 items-center justify-center rounded-full bg-info-bg">
                <f.icon size={18} color={c.infoText} strokeWidth={2} />
              </View>
              <View className="flex-1">
                <T variant="section" className="text-left">
                  {f.title}
                </T>
                {/** no inner caption per design — main message above */}
              </View>
            </Card>
          ))}
        </View>

        {/* Footer removed for a cleaner, modern landing */}
      </PageContainer>
    </ScrollView>
  );
}
