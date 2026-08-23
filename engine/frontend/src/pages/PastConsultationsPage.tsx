import { useCallback, useEffect, useState } from "react";
import { listConsultations, type ConsultationRow } from "../api/client";

const KEY_STORAGE = "vitalis.reviewKey";

function when(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * What this consultation actually ended in.
 *
 * A safety exit outranks everything: an encounter that stopped at ST
 * elevation reached the most important outcome the tool has, and must never
 * render as "did not finish".
 */
function outcomeOf(row: ConsultationRow): { text: string; tone: "exit" | "routed" | "open" } {
  if (row.safety_exit) return { text: row.safety_exit, tone: "exit" };
  const resolved = row.outcomes.filter((o) => o.headline);
  if (resolved.length) return { text: resolved.map((o) => o.headline).join(" · "), tone: "routed" };
  return { text: "Not finished", tone: "open" };
}

export function PastConsultationsPage({
  onOpen,
  onBack,
}: {
  onOpen: (encounterId: string, token: string) => void;
  onBack: () => void;
}) {
  const [reviewKey, setReviewKey] = useState(() => localStorage.getItem(KEY_STORAGE) ?? "");
  const [typed, setTyped] = useState("");
  const [rows, setRows] = useState<ConsultationRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (key: string) => {
    setBusy(true);
    setError(null);
    try {
      const page = await listConsultations(key, 0, 200);
      setRows(page.consultations);
      setTotal(page.total);
      localStorage.setItem(KEY_STORAGE, key);
      setReviewKey(key);
    } catch (e) {
      // A wrong key must not leave a stale list on screen from a previous
      // successful load.
      setRows(null);
      setError(e instanceof Error ? e.message : String(e));
      localStorage.removeItem(KEY_STORAGE);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (reviewKey) void load(reviewKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!rows) {
    return (
      <div className="panel" style={{ maxWidth: 460, margin: "40px auto" }}>
        <div className="eyebrow">Past consultations</div>
        <p style={{ fontSize: 13.5, color: "var(--ink2)" }}>
          This page shows every patient recorded on this deployment, so it needs the review key.
        </p>
        <input
          type="password"
          value={typed}
          autoFocus
          placeholder="Review key"
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && typed) void load(typed);
          }}
        />
        {error && (
          <p style={{ fontSize: 13, color: "var(--danger)", marginTop: 10 }}>{error}</p>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" disabled={!typed || busy} onClick={() => void load(typed)}>
            {busy ? "Checking…" : "Open"}
          </button>
          <button className="btn secondary" onClick={onBack}>
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Past consultations</div>
            <div style={{ fontSize: 13, color: "var(--ink2)" }}>
              {total} recorded{rows.length < total ? ` · showing the most recent ${rows.length}` : ""}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn secondary" disabled={busy} onClick={() => void load(reviewKey)}>
              {busy ? "Refreshing…" : "Refresh"}
            </button>
            <button className="btn secondary" onClick={onBack}>
              Back
            </button>
          </div>
        </div>

        {rows.length === 0 ? (
          <p style={{ fontSize: 13.5, color: "var(--ink3)" }}>
            Nothing recorded yet. Consultations appear here as soon as someone starts one.
          </p>
        ) : (
          <div className="history-scroll">
            <table className="history">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Patient</th>
                  <th>Presenting</th>
                  <th>Outcome</th>
                  <th className="num">Answers</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const outcome = outcomeOf(row);
                  return (
                    <tr key={row.id}>
                      <td className="mono nowrap">{when(row.created_at)}</td>
                      <td>
                        <div className="history-name">{row.patient_name || "No name entered"}</div>
                        <div className="history-sub">
                          {[
                            row.patient_age != null ? `${row.patient_age}` : null,
                            row.patient_sex,
                            row.facility_tier,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </div>
                      </td>
                      <td className="history-sub">{row.symptoms.join(", ") || "—"}</td>
                      <td>
                        <span className={`history-outcome ${outcome.tone}`}>{outcome.text}</span>
                      </td>
                      <td className="num mono">{row.questions_answered}</td>
                      <td>
                        <button
                          className="btn secondary small"
                          onClick={() => onOpen(row.id, row.access_token)}
                        >
                          Open
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <p style={{ fontSize: 11.5, color: "var(--ink3)", marginTop: 14 }}>
          The review key is shared, not personal — it does not record who looked. Anyone holding it
          can read every record here.
        </p>
      </div>
    </div>
  );
}
