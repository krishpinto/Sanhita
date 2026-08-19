export function BooleanField({
  onAnswer,
  busy,
}: {
  onAnswer: (value: boolean) => void;
  busy: boolean;
}) {
  return (
    <div className="yn">
      <button disabled={busy} onClick={() => onAnswer(true)}>
        Yes
      </button>
      <button disabled={busy} onClick={() => onAnswer(false)}>
        No
      </button>
    </div>
  );
}
