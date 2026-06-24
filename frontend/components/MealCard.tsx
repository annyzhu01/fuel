"use client";

import { useState } from "react";
import { PlanItem, swapMeal } from "@/lib/api";
import { RecipeModal } from "@/components/RecipeModal";

interface MealCardProps {
  item: PlanItem;
  onLog: (item: PlanItem) => void;
  onSwap: (slot: string, newItem: PlanItem) => void;
}

export function MealCard({ item, onLog, onSwap }: MealCardProps) {
  const [swapping, setSwapping] = useState(false);
  const [showRecipe, setShowRecipe] = useState(false);
  const [seenIds, setSeenIds] = useState<string[]>(item.recipe_id ? [item.recipe_id] : []);

  async function handleSwap(e: React.MouseEvent) {
    e.stopPropagation();
    setSwapping(true);
    try {
      const newItem = await swapMeal(item.slot, seenIds);
      if (newItem.recipe_id) setSeenIds((prev) => [...prev, newItem.recipe_id]);
      onSwap(item.slot, newItem);
    } catch (e) {
      console.error("Swap failed", e);
    } finally {
      setSwapping(false);
    }
  }

  return (
    <>
      <div
        className="bg-gray-800 rounded-xl p-4 flex flex-col gap-2 cursor-pointer hover:bg-gray-750 active:bg-gray-700 transition-colors"
        onClick={() => item.recipe_id && setShowRecipe(true)}
      >
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wider">{item.slot}</p>
            <p className="text-white font-semibold">{item.recipe_name}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSwap}
              disabled={swapping}
              className="text-gray-400 hover:text-white disabled:opacity-40 text-xs px-2 py-1 rounded-full border border-gray-600 hover:border-gray-400 transition-colors"
            >
              {swapping ? "..." : "↻"}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onLog(item); }}
              className="bg-green-600 hover:bg-green-500 text-white text-xs px-3 py-1 rounded-full transition-colors"
            >
              Log
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-400 italic">{item.reason}</p>
        <div className="flex gap-3 text-xs text-gray-300">
          <span>{item.calories} kcal</span>
          <span>{item.protein_g}g protein</span>
          <span>{item.carbs_g}g carbs</span>
          <span>{item.fat_g}g fat</span>
        </div>
        {item.recipe_id && (
          <p className="text-xs text-gray-500">Tap to view recipe</p>
        )}
      </div>

      {showRecipe && item.recipe_id && (
        <RecipeModal recipeId={item.recipe_id} onClose={() => setShowRecipe(false)} />
      )}
    </>
  );
}
