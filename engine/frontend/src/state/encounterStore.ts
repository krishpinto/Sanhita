const KEY = "vitalis.encounter";

export interface StoredEncounter {
  encounterId: string;
  accessToken: string;
}

export function saveEncounter(e: StoredEncounter) {
  localStorage.setItem(KEY, JSON.stringify(e));
}

export function loadEncounter(): StoredEncounter | null {
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredEncounter;
  } catch {
    return null;
  }
}

export function clearEncounter() {
  localStorage.removeItem(KEY);
}
