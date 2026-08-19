import type { EncounterSummary, NextStepResponse, ProtocolSummary, ResultPayload } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
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
  return request<{ provider: string; status: string; content: string | null; reason: string | null; disclaimer: string }>(
    `/encounters/${encounterId}/ai-opinion`,
    { method: "POST" },
    token
  );
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
