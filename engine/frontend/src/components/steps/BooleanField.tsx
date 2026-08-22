export function BooleanField({
  value,
  onAnswer,
  busy,
}: {
  value: unknown;
  onAnswer: (value: boolean) => void;
  busy: boolean;
}) {
  return (
    <div className="yn">
      <button type="button" className={value === true ? "on" : ""} disabled={busy} onClick={() => onAnswer(true)}>
        Yes
      </button>
      <button type="button" className={value === false ? "on" : ""} disabled={busy} onClick={() => onAnswer(false)}>
        No
      </button>
    </div>
  );
}
