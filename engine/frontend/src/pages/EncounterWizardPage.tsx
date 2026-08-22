import { useEffect, useRef, useState } from "react";
import { activateProtocol, getEncounterSummary, getNextStep, postAnswer } from "../api/client";
import type { EncounterSummary, FrontierFieldOut, NextStepResponse } from "../api/types";
import { CompletedGroupPanel } from "../components/CompletedGroupPanel";
import { FieldGroupPanel, type QuestionRow } from "../components/FieldGroupPanel";
import { ProgressHeader } from "../components/ProgressHeader";
import { ProtocolOfferBanner } from "../components/ProtocolOfferBanner";
import {
  hydrate,
  recordAnswer,
  targetOf,
  type AnsweredQuestion,
  type AnswerTarget,
  type Ledger,
} from "../state/answers";
import { groupDescriptionOf, type GroupKind } from "../state/grouping";

interface LiveGroup {
  key: string;
  title: string;
  description: string | null;
  kind: GroupKind;
  rows: QuestionRow[];
}

export function EncounterWizardPage({
  encounterId,
  token,
  onReadyForResult,
  onReset,
}: {
  encounterId: string;
  token: string;
  onReadyForResult: () => void;
  onReset: () => void;
}) {
  const [step, setStep] = useState<NextStepResponse | null>(null);
  const [summary, setSummary] = useState<EncounterSummary | null>(null);
  const [ledger, setLedger] = useState<Ledger>(new Map());
  // Only the control being posted is disabled, never the whole screen. A global
  // freeze on every answer is what made rapid tick-through feel unresponsive.
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Questions render in the order the engine first offered them, so answering
  // one never reshuffles the rest of the block under the clinician's hand.
  const seen = useRef<Map<string, number>>(new Map());
  const seenCount = useRef(0);
  const orderOf = (path: string) => {
    if (!seen.current.has(path)) seen.current.set(path, seenCount.current++);
    return seen.current.get(path)!;
  };

  const refreshSummary = () => {
    getEncounterSummary(encounterId, token)
      .then(setSummary)
      .catch(() => {});
  };

  // Every engine reply carries both halves of the encounter -- what is still
  // outstanding and what is already recorded -- and the ledger is rebuilt from
  // the recorded half each time. That is what makes a reloaded page come back
  // with its answered blocks intact, and what makes an answer invalidated by
  // a correction actually leave the screen.
  const applyStep = (result: NextStepResponse) => {
    const next = hydrate(result);
    for (const path of next.keys()) orderOf(path);
    for (const f of result.core_frontier) orderOf(f.answer_path);
    setStep(result);
    setLedger(next);
  };

  useEffect(() => {
    getNextStep(encounterId, token)
      .then((r) => {
        applyStep(r);
        refreshSummary();
      })
      .catch((e) => setError(String(e)));
  }, [encounterId]);

  // Answering and correcting are the same act here. The engine accepts a
  // replacement on a path it already holds, so the client does not need a
  // separate correction path -- only the previous value, to put back if the
  // post fails.
  const handleAnswer = async (target: AnswerTarget, value: unknown) => {
    setPending((p) => new Set(p).add(target.path));
    setError(null);
    // Show it as recorded straight away; the engine's reply is authoritative
    // and arrives a moment later.
    const lastKnown = step;
    setLedger((l) => recordAnswer(l, target, value));
    try {
      const result = await postAnswer(encounterId, token, target.path, value);
      applyStep(result);
      refreshSummary();
    } catch (e) {
      // The optimistic row is rolled back to the last state the engine
      // confirmed, so a rejected answer never lingers on screen as recorded.
      setError(e instanceof Error ? e.message : String(e));
      if (lastKnown) setLedger(hydrate(lastKnown));
    } finally {
      setPending((p) => {
        const next = new Set(p);
        next.delete(target.path);
        return next;
      });
    }
  };

  const handleActivate = async (protocolId: string) => {
    setPending((p) => new Set(p).add(protocolId));
    try {
      const result = await activateProtocol(encounterId, token, protocolId);
      applyStep(result);
      refreshSummary();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending((p) => {
        const next = new Set(p);
        next.delete(protocolId);
        return next;
      });
    }
  };

  if (!step) return <div className="wrap">Loading...</div>;

  // A live group is any block with an outstanding question. Its rows are the
  // outstanding fields plus everything already answered in the same block.
  const buildGroups = (frontier: FrontierFieldOut[]): LiveGroup[] => {
    const groups = new Map<string, LiveGroup>();
    for (const f of frontier) {
      const target = targetOf(f);
      orderOf(target.path);
      if (!groups.has(target.groupKey)) {
        groups.set(target.groupKey, {
          key: target.groupKey,
          title: target.groupTitle,
          description: groupDescriptionOf(f),
          kind: target.groupKind,
          rows: [],
        });
      }
      groups
        .get(target.groupKey)!
        .rows.push({ path: target.path, outstanding: f, answered: ledger.get(target.path) ?? null });
    }
    for (const a of ledger.values()) {
      const g = groups.get(a.groupKey);
      if (g && !g.rows.some((r) => r.path === a.path)) {
        g.rows.push({ path: a.path, outstanding: null, answered: a });
      }
    }
    for (const g of groups.values()) g.rows.sort((x, y) => orderOf(x.path) - orderOf(y.path));
    return Array.from(groups.values());
  };

  const coreGroups = buildGroups(step.core_frontier);
  const activeGroups = buildGroups(step.active_protocols.flatMap((p) => p.frontier));
  const liveKeys = new Set([...coreGroups, ...activeGroups].map((g) => g.key));

  // Blocks with nothing outstanding left. They collapse rather than vanish.
  const completed = new Map<string, { title: string; answers: AnsweredQuestion[] }>();
  for (const a of ledger.values()) {
    if (liveKeys.has(a.groupKey)) continue;
    if (!completed.has(a.groupKey)) completed.set(a.groupKey, { title: a.groupTitle, answers: [] });
    completed.get(a.groupKey)!.answers.push(a);
  }
  for (const c of completed.values()) c.answers.sort((x, y) => orderOf(x.path) - orderOf(y.path));
  const completedGroups = Array.from(completed.entries()).sort(
    (a, b) => orderOf(a[1].answers[0].path) - orderOf(b[1].answers[0].path)
  );

  const completedPanels = completedGroups.map(([key, c]) => (
    <CompletedGroupPanel
      key={key}
      title={c.title}
      answers={c.answers}
      pending={pending}
      onAnswer={handleAnswer}
    />
  ));

  const errorPanel = error && (
    <div className="panel gate">
      <div className="field-label" style={{ color: "var(--danger)" }}>
        {error}
      </div>
    </div>
  );

  // A hard exit stops the consultation, but it is still a conclusion drawn
  // from an answer -- and the answer it was drawn from may have been a
  // mis-tap. The recorded blocks stay reachable underneath so the ECG can be
  // corrected and the exit lifted, rather than the clinician having to start
  // the patient again.
  if (step.core_terminal) {
    return (
      <div className="wrap">
        <div className="result-head emergency">
          <div className="k mono">Hard exit</div>
          <h2>{step.core_terminal.headline}</h2>
        </div>
        {errorPanel}
        {completedPanels.length > 0 && (
          <p className="panel-desc" style={{ marginTop: 18 }}>
            Entered something by mistake? Open a block below to change it.
          </p>
        )}
        {completedPanels}
        <div className="nav">
          <button className="btn secondary" onClick={onReset}>
            New patient
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <ProgressHeader summary={summary} step={step} />

      {errorPanel}

      {completedPanels}

      {coreGroups.map((g) => (
        <FieldGroupPanel
          key={g.key}
          title={g.title}
          description={g.description}
          kind={g.kind}
          rows={g.rows}
          pending={pending}
          onAnswer={handleAnswer}
        />
      ))}

      {step.offered_protocols.map((offer) => (
        <ProtocolOfferBanner
          key={offer.protocol_id}
          offer={offer}
          busy={pending.has(offer.protocol_id)}
          onActivate={() => handleActivate(offer.protocol_id)}
        />
      ))}

      {step.active_protocols
        .filter((p) => p.status === "resolved")
        .map((p) => (
          <div className="panel" key={p.protocol_id}>
            <div className="eyebrow">{p.protocol_name} resolved</div>
            <div className="field-label">{p.terminal?.headline}</div>
          </div>
        ))}

      {activeGroups.map((g) => (
        <FieldGroupPanel
          key={g.key}
          title={g.title}
          description={g.description}
          kind={g.kind}
          rows={g.rows}
          pending={pending}
          onAnswer={handleAnswer}
        />
      ))}

      {step.ready_for_result && (
        <div className="panel">
          <div className="nav" style={{ marginTop: 0 }}>
            <button className="btn" onClick={onReadyForResult}>
              View result
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
