import { useState } from "react";
import { clearEncounter, loadEncounter, saveEncounter } from "./state/encounterStore";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import { EncounterWizardPage } from "./pages/EncounterWizardPage";
import { PastConsultationsPage } from "./pages/PastConsultationsPage";
import { ResultPage } from "./pages/ResultPage";

type View = "new" | "wizard" | "result" | "history";

function initialView(): View {
  return loadEncounter() ? "wizard" : "new";
}

export default function App() {
  const [view, setView] = useState<View>(initialView());
  const [encounter, setEncounter] = useState(loadEncounter());

  const handleCreated = (encounterId: string, accessToken: string) => {
    const e = { encounterId, accessToken };
    saveEncounter(e);
    setEncounter(e);
    setView("wizard");
  };

  const handleReset = () => {
    clearEncounter();
    setEncounter(null);
    setView("new");
  };

  /**
   * Opening a past consultation makes it the current one, so the wizard and
   * result pages work on it exactly as they did the day it was recorded --
   * including the change-an-answer flow. A second, read-only copy of those
   * pages would be two renderers to keep in step, and they would drift.
   */
  const handleOpenPast = (encounterId: string, accessToken: string) => {
    const e = { encounterId, accessToken };
    saveEncounter(e);
    setEncounter(e);
    setView("result");
  };

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <h1>Vitalis</h1>
          <span className="mono">Protocol engine · demo</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {view !== "history" && (
            <button className="btn secondary" onClick={() => setView("history")}>
              Past consultations
            </button>
          )}
          {encounter && (
            <button className="btn secondary" onClick={handleReset}>
              New patient
            </button>
          )}
        </div>
      </header>

      {view === "new" && <NewEncounterPage onCreated={handleCreated} />}

      {view === "history" && (
        <PastConsultationsPage
          onOpen={handleOpenPast}
          onBack={() => setView(encounter ? "wizard" : "new")}
        />
      )}

      {view === "wizard" && encounter && (
        <EncounterWizardPage
          encounterId={encounter.encounterId}
          token={encounter.accessToken}
          onReadyForResult={() => setView("result")}
          onReset={handleReset}
        />
      )}

      {view === "result" && encounter && (
        <ResultPage
          encounterId={encounter.encounterId}
          token={encounter.accessToken}
          onReset={handleReset}
          onBack={() => setView("wizard")}
        />
      )}

      <footer className="app-footer">
        Prototype · not for clinical use. Backend engine is protocol-driven; adding a new disease means
        authoring a new protocol JSON file, not changing this code.
      </footer>
    </div>
  );
}
