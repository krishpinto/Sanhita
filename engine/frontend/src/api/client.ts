import type { EncounterSummary, NextStepResponse, ProtocolSummary, ResultPayload } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** FastAPI puts the human-readable message in `detail`. Showing the raw
 *  body instead puts `{"detail":"..."}` on screen in front of a doctor. */
async function readError(res: Response): Promise<string> {
  const body = await res.text();
  if (!body) return res.statusText;
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed?.detail === "string") return parsed.detail;
    if (Array.isArray(parsed?.detail)) {
      // Pydantic validation errors arrive as a list of objects.
      const first = parsed.detail[0];
      if (typeof first?.msg === "string") return first.msg;
    }
  } catch {
    // Not JSON. Fall through and show whatever the server actually sent.
  }
  return body;
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    throw new ApiError(res.status, await readError(res));
  }
  return res.json() as Promise<T>;
}

export { ApiError };

export function createEncounter() {
  return request<{ encounter_id: string; access_token: string }>("/encounters", { method: "POST" });
}

export function getNextStep(encounterId: string, token: string) {
  return request<NextStepResponse>(`/encounters/${encounterId}/next-step`, {}, token);
}

export function postAnswer(encounterId: string, token: string, fieldPath: string, value: unknown) {
  return request<NextStepResponse>(
    `/encounters/${encounterId}/answer`,
    { method: "POST", body: JSON.stringify({ field_path: fieldPath, value }) },
    token
  );
}

export function activateProtocol(encounterId: string, token: string, protocolId: string) {
  return request<NextStepResponse>(
    `/encounters/${encounterId}/activate-protocol/${protocolId}`,
    { method: "POST" },
    token
  );
}

export function getEncounterSummary(encounterId: string, token: string) {
  return request<EncounterSummary>(`/encounters/${encounterId}`, {}, token);
}

export function getResult(encounterId: string, token: string) {
  return request<ResultPayload>(`/encounters/${encounterId}/result`, {}, token);
}

export function listProtocols() {
  return request<ProtocolSummary[]>("/protocols");
}

export function requestAiOpinion(encounterId: string, token: string) {
  return request<{
    provider: string;
    model: string | null;
    status: string;
    content: string | null;
    reason: string | null;
    disclaimer: string;
  }>(`/encounters/${encounterId}/ai-opinion`, { method: "POST" }, token);
}

export function postDoctorOpinion(
  encounterId: string,
  token: string,
  body: { doctor_note: string | null; structured_alternate_diagnosis: string | null }
) {
  return request<{ ok: boolean }>(
    `/encounters/${encounterId}/doctor-opinion`,
    { method: "POST", body: JSON.stringify(body) },
    token
  );
}

export interface ConsultationRow {
  id: string;
  access_token: string;
  created_at: string;
  updated_at: string;
  status: string;
  patient_name: string | null;
  patient_age: number | null;
  patient_sex: string | null;
  facility_tier: string | null;
  symptoms: string[];
  questions_answered: number;
  safety_exit: string | null;
  outcomes: { protocol_id: string; status: string; headline: string | null }[];
}

export interface ConsultationsPage {
  total: number;
  limit: number;
  offset: number;
  consultations: ConsultationRow[];
}

/** The one call that crosses encounters -- gated by the shared review key,
 *  not by an encounter token. See backend app/routers/history.py. */
export function listConsultations(reviewKey: string, offset = 0, limit = 100) {
  return request<ConsultationsPage>(
    `/consultations?limit=${limit}&offset=${offset}`,
    {},
    reviewKey
  );
}
