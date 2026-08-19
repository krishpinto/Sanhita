import type { OfferedProtocol } from "../api/types";

export function ProtocolOfferBanner({
  offer,
  onActivate,
  busy,
}: {
  offer: OfferedProtocol;
  onActivate: () => void;
  busy: boolean;
}) {
  return (
    <div className="panel offer">
      <div className="eyebrow">Module offered — not yet started</div>
      <div className="field-label">{offer.name}</div>
      {offer.fidelity === "reduced_fidelity_placeholder" && (
        <div className="field-hint">{offer.fidelity_note}</div>
      )}
      <p style={{ fontSize: 13, color: "var(--ink2)", lineHeight: 1.5 }}>
        This patient's symptoms and findings match this module's activation criteria. It is a longer
        questionnaire and requires your consent to start.
      </p>
      <div className="nav">
        <button className="btn" disabled={busy} onClick={onActivate}>
          Start {offer.name}
        </button>
      </div>
    </div>
  );
}
