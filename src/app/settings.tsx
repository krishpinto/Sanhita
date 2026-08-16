import { PageContainer } from "@/components/layout";
import { Card, SegmentedControl, T } from "@/components/ui";
import { loadUserTheme, setUserTheme } from "@/theme";
import { ScrollView, View } from "@/tw";
import { useEffect, useState } from "react";

export default function SettingsScreen() {
  const [pref, setPref] = useState<"system" | "light" | "dark">("system");

  useEffect(() => {
    let mounted = true;
    (async () => {
      const v = await loadUserTheme();
      if (!mounted) return;
      setPref(v === null ? "system" : v);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  function onChange(v: "system" | "light" | "dark") {
    setPref(v);
    setUserTheme(v === "system" ? "system" : v);
  }

  return (
    <ScrollView className="flex-1 bg-bg" contentContainerClassName="pb-8">
      <PageContainer className="pt-2">
        <Card>
          <View className="gap-3">
            <T variant="section">Theme</T>
            <T variant="caption" tone="muted">
              Choose app theme (System uses OS setting)
            </T>
            <SegmentedControl
              options={[
                { label: "System", value: "system" },
                { label: "Light", value: "light" },
                { label: "Dark", value: "dark" },
              ]}
              value={pref}
              onChange={(v) => onChange(v as "system" | "light" | "dark")}
            />
          </View>
        </Card>
      </PageContainer>
    </ScrollView>
  );
}
