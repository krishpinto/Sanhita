import { useState } from "react";
import { clearEncounter, loadEncounter, saveEncounter } from "./state/encounterStore";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import { EncounterWizardPage } from "./pages/EncounterWizardPage";
import { ResultPage } from "./pages/ResultPage";

type View = "new" | "wizard" | "result";

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

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <h1>Vitalis</h1>
          <span className="mono">Protocol engine · demo</span>
        </div>
        {encounter && (
          <button className="btn secondary" onClick={handleReset}>
            New patient
          </button>
        )}
      </header>

      {view === "new" && <NewEncounterPage onCreated={handleCreated} />}

      {view === "wizard" && encounter && (
        <EncounterWizardPage
          encounterId={encounter.encounterId}
          token={encounter.accessToken}
          onReadyForResult={() => setView("result")}
          onReset={handleReset}
        />
      )}

      {view === "result" && encounter && (
        <ResultPage encounterId={encounter.encounterId} token={encounter.accessToken} onReset={handleReset} />
      )}

      <footer className="app-footer">
        Prototype · not for clinical use. Backend engine is protocol-driven; adding a new disease means
        authoring a new protocol JSON file, not changing this code.
      </footer>
    </div>
  );
}
