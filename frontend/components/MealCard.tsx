import { PlanItem } from "@/lib/api";

interface MealCardProps {
  item: PlanItem;
  onLog: (item: PlanItem) => void;
}

export function MealCard({ item, onLog }: MealCardProps) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 flex flex-col gap-2">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider">{item.slot}</p>
          <p className="text-white font-semibold">{item.recipe_name}</p>
        </div>
        <button
          onClick={() => onLog(item)}
          className="bg-green-600 hover:bg-green-500 text-white text-xs px-3 py-1 rounded-full transition-colors"
        >
          Log
        </button>
      </div>
      <p className="text-xs text-gray-400 italic">{item.reason}</p>
      <div className="flex gap-3 text-xs text-gray-300">
        <span>{item.calories} kcal</span>
        <span>{item.protein_g}g protein</span>
        <span>{item.carbs_g}g carbs</span>
        <span>{item.fat_g}g fat</span>
      </div>
    </div>
  );
}
