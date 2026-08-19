// Index card intake — name, age, sex, chief complaint. Complaint matched
// against the Protocol Index (deterministic lookup). Visual restyle only.

import { useRouter } from "expo-router";
import { ArrowRight } from "lucide-react-native";
import { useState } from "react";
import { KeyboardAvoidingView, Platform } from "react-native";

import { PageContainer } from "@/components/layout";
import {
    Card,
    ErrorCard,
    FormField,
    PrimaryButton,
    SegmentedControl,
    T,
    TextField,
} from "@/components/ui";
import { useBreakpoint } from "@/hooks/useBreakpoint";
import { lookupProtocol } from "@/lib/protocol-index";
import { useSanhita } from "@/lib/store";
import { ScrollView, View } from "@/tw";
import type { Sex } from "@/types/protocol";

const SEXES: Sex[] = ["Male", "Female", "Other"];

export default function IntakeScreen() {
  const router = useRouter();
  const { isDesktop } = useBreakpoint();
  const addIndexCard = useSanhita((s) => s.addIndexCard);
  const startProtocol = useSanhita((s) => s.startProtocol);

  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<Sex | undefined>(undefined);
  const [complaint, setComplaint] = useState("");
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
    const card = addIndexCard({
      name: name.trim(),
      age: age.trim() || undefined,
      sex,
      complaint: complaint.trim(),
    });
    startProtocol(card, protocol);
    router.replace("/field");
  }

  const form = (
    <Card className="gap-6">
      <View className="gap-1">
        <T variant="section">New encounter</T>
        <T variant="secondary" tone="muted">
          Synthetic record — do not enter real patient data.
        </T>
      </View>

      <FormField label="Full name">
        <TextField
          value={name}
          onChangeText={setName}
          placeholder="e.g. Rohan K."
          autoFocus={!isDesktop}
        />
      </FormField>

      <View className={isDesktop ? "flex-row gap-4" : "gap-4"}>
        <View className={isDesktop ? "flex-1" : ""}>
          <FormField label="Age">
            <TextField
              value={age}
              onChangeText={setAge}
              placeholder="24"
              keyboardType="number-pad"
              maxLength={3}
            />
          </FormField>
        </View>
        <View className={isDesktop ? "flex-2" : ""}>
          <FormField label="Sex">
            <SegmentedControl
              options={SEXES.map((s) => ({
                label: s === "Male" ? "M" : s === "Female" ? "F" : "Other",
                value: s,
              }))}
              value={sex}
              onChange={setSex}
            />
          </FormField>
        </View>
      </View>

      <FormField
        label="Chief complaint"
        hint="Matched against a fixed list — never interpreted freely."
      >
        <TextField
          value={complaint}
          onChangeText={(t) => {
            setComplaint(t);
            setNotFound(false);
          }}
          placeholder="e.g. fever"
        />
      </FormField>

      {notFound && (
        <ErrorCard
          message={`No protocol for "${complaint.trim()}" yet — only "fever" is authored so far.`}
        />
      )}

      <View className="flex-row gap-3 justify-end">
        {isDesktop && (
          <PrimaryButton
            label="Open protocol"
            onPress={save}
            disabled={!canSave}
            icon={ArrowRight}
            fullWidth={false}
          />
        )}
      </View>
    </Card>
  );

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      className="bg-bg"
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerClassName="pb-6"
        keyboardShouldPersistTaps="handled"
      >
        <PageContainer className="pt-2">{form}</PageContainer>
      </ScrollView>

      {!isDesktop && (
        <View className="p-4 bg-card border-t border-border">
          <PrimaryButton
            label="Open protocol"
            onPress={save}
            disabled={!canSave}
            icon={ArrowRight}
          />
        </View>
      )}
    </KeyboardAvoidingView>
  );
}
