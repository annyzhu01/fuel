"use client";

interface MacroRingProps {
  caloriesConsumed: number;
  caloriesTotal: number;
  protein: { consumed: number; total: number };
  carbs: { consumed: number; total: number };
  fat: { consumed: number; total: number };
}

function MacroBar({ label, consumed, total, color }: { label: string; consumed: number; total: number; color: string }) {
  const pct = Math.min(100, total > 0 ? (consumed / total) * 100 : 0);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm text-gray-500">{Math.round(consumed)} / {Math.round(total)}g</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

export function MacroRing({ caloriesConsumed, caloriesTotal, protein, carbs, fat }: MacroRingProps) {
  const pct = Math.min(1, caloriesTotal > 0 ? caloriesConsumed / caloriesTotal : 0);
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = circ * pct;

  return (
    <div className="flex items-center gap-5">
      <div className="relative flex-shrink-0">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r={r} fill="none" stroke="#e5e7eb" strokeWidth="12" />
          <circle
            cx="70" cy="70" r={r}
            fill="none"
            stroke="#2d6b2d"
            strokeWidth="12"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 70 70)"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-900">{Math.round(caloriesConsumed)}</span>
          <span className="text-xs text-gray-500">of {Math.round(caloriesTotal)} kcal</span>
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-3">
        <MacroBar label="Protein" consumed={protein.consumed} total={protein.total} color="#2d6b2d" />
        <MacroBar label="Carbs" consumed={carbs.consumed} total={carbs.total} color="#f59e0b" />
        <MacroBar label="Fat" consumed={fat.consumed} total={fat.total} color="#ef4444" />
      </div>
    </div>
  );
}
