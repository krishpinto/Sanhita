// Mirrors app/models_protocol.py + app/engine_service.py serialization on the
// backend. Deliberately generic -- nothing here names a specific disease.

export type FieldType =
  | "boolean"
  | "single_select"
  | "multi_select"
  | "text"
  | "number"
  | "structured_ecg"
  | "structured_vitals"
  | "differential_review"
  | "findings_review";

export interface Option {
  value: string;
  label: string;
}

export interface DifferentialItemSpec {
  id: string;
  label: string;
  tier: 1 | 2 | 3;
  discriminator: string;
  discriminator_question: string;
  discriminator_input_source: InputSource;
  module: string | null;
  exclusion_policy: "auto" | "confirm" | "never";
}

// One observation on the findings screen. Shared: a single question can
// settle several differential items at once, which is why the doctor
// answers ~7 of these rather than one per possibility.
export interface FindingSpec {
  id: string;
  question: string;
  short_label: string;
  input_source: InputSource;
  help: string | null;
  carried_from_symptom: string | null;
  prefilled: boolean;
  promotes_only: boolean;
  resolves: string[];
}

export type InputSource = "history" | "examination" | "investigation" | "clinical_judgement";

export const INPUT_SOURCE_LABELS: Record<InputSource, string> = {
  history: "Ask the patient",
  examination: "Examination finding",
  investigation: "From investigation (ECG, echo, labs)",
  clinical_judgement: "Clinical judgement",
};

export interface FieldDef {
  id: string;
  label: string;
  field_type: FieldType;
  description: string | null;
  input_source: InputSource | null;
  options: Option[];
  sub_fields: FieldDef[];
  value_scoring: Record<string, string>;
  skip_when: unknown;
  source: "protocol" | "core" | "shared";
  shared_path: string | null;
  core_path: string | null;
  prefill: { source_path: string; value_map: Record<string, string>; default: string | null } | null;
  required: boolean;
  vitalis_addition: boolean;
  vitalis_addition_reason: string | null;
  differential_items: DifferentialItemSpec[];
  findings: FindingSpec[];
}

export interface FrontierFieldOut {
  protocol_id: string;
  block_id: string;
  block_label: string;
  block_description: string | null;
  track_id: string | null;
  track_label: string | null;
  track_description: string | null;
  answer_path: string;
  field: FieldDef;
  suggested_value?: unknown;
}

// A question this encounter already holds an answer for. Same shape as a
// frontier field plus the recorded value, because the client renders and
// re-posts both through one code path.
export interface AnsweredFieldOut extends FrontierFieldOut {
  value: unknown;
}

export interface TrackEvidenceOut {
  track_id: string;
  label: string;
  mode: string;
  resolution: string | null;
  positive_count: number;
  negative_count: number;
  unknown_count: number;
  skipped_count: number;
  total_scored_fields: number;
  per_field: Record<string, { status: string; value: unknown }>;
}

export interface ContextBlockOut {
  id: string;
  label: string;
  render_hint: "plain" | "flag_positive";
  fields: Record<string, unknown>;
}

export interface DerivedTagOut {
  id: string;
  label: string;
  value: boolean | null;
}

export interface DrugReason {
  reason: string;
  vitalis_addition: boolean;
}

export interface DrugEntryOut {
  id: string;
  name: string;
  dose: string;
  group_label: string;
  state: "clear" | "caution" | "block" | "quarantined";
  block_reasons: DrugReason[];
  caution_reasons: DrugReason[];
  note: string | null;
}

export interface DrugBlockOut {
  id: string;
  label: string;
  status: "ready" | "pending" | "not_applicable";
  entries: DrugEntryOut[];
  hidden_count: number;
}

export interface ProtocolResultOut {
  protocol_id: string;
  status: "active" | "resolved";
  frontier: FrontierFieldOut[];
  answered: AnsweredFieldOut[];
  terminal: { code: string; headline: string } | null;
  fidelity: "full" | "reduced_fidelity_placeholder";
  fidelity_note: string | null;
  protocol_name: string;
  source_citation: string;
  tracks: TrackEvidenceOut[];
  unassessed: { field_id: string; label: string; reason: string }[];
  derived_tags: DerivedTagOut[];
  context_blocks: ContextBlockOut[];
  drug_blocks: DrugBlockOut[];
}

export interface OfferedProtocol {
  protocol_id: string;
  name: string;
  fidelity: string;
  fidelity_note: string;
}

export interface NextStepResponse {
  core_frontier: FrontierFieldOut[];
  core_answered: AnsweredFieldOut[];
  core_terminal: { code: string; headline: string } | null;
  offered_protocols: OfferedProtocol[];
  active_protocols: ProtocolResultOut[];
  ready_for_result: boolean;
}

export interface DifferentialItemAudit extends DifferentialItemSpec {
  status: "raised" | "promoted" | "pending_confirmation" | "excluded";
  reason: string;
  finding: string;
}

export interface FindingAudit {
  id: string;
  question: string;
  short_label: string;
  answer: boolean | null;
  carried_from_symptom: string | null;
}

export interface DifferentialAudit {
  symptoms: string[];
  findings: FindingAudit[];
  items: DifferentialItemAudit[];
  surviving_modules: string[];
}

// One submitted answer, rendered by the backend at the moment it was
// submitted. `entries` is a list because one answer path can be many
// questions -- the findings screen is nine observations behind a single post.
export interface AnswerLogEntry {
  seq: number;
  field_path: string;
  protocol_id: string;
  block_label: string | null;
  field_label: string;
  entries: { question: string; answer: string }[];
  is_correction: boolean;
  previous_entries: { question: string; answer: string }[] | null;
  answered_at: string;
}

export interface ResultPayload {
  core_terminal: { code: string; headline: string } | null;
  core: { name: string | null; age: number | null; sex: string | null; symptoms: string[] };
  differential: DifferentialAudit | null;
  protocols: ProtocolResultOut[];
  unrun_protocols: { protocol_id: string; name: string; reason: string }[];
  answer_log: AnswerLogEntry[];
  ai_opinion: {
    provider: string;
    status: string;
    content: string | null;
    reason: string | null;
    requested_at: string;
    responded_at: string | null;
  } | null;
  doctor_opinion: { doctor_note: string | null; structured_alternate_diagnosis: string | null; updated_at: string } | null;
}

export interface EncounterSummary {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  patient_name: string | null;
  patient_age: number | null;
  patient_sex: string | null;
  symptoms: string[];
  facility_tier: string | null;
  core_terminal_code: string | null;
  core_terminal_headline: string | null;
}

export interface ProtocolSummary {
  protocol_id: string;
  name: string;
  version: string;
  fidelity: string;
  fidelity_note: string | null;
  source_citation: string;
  has_auto_trigger: boolean;
  has_offer_trigger: boolean;
}
