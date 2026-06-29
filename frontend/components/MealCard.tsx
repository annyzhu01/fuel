"use client";

import { useState } from "react";
import { PlanItem, swapMeal } from "@/lib/api";
import { RecipeModal } from "@/components/RecipeModal";

const MAX_SWAPS = 5;

interface MealCardProps {
  item: PlanItem;
  onLog: (item: PlanItem) => void;
  onSwap: (slot: string, newItem: PlanItem) => void;
  otherSlotIds?: string[];
}

export function MealCard({ item, onLog, onSwap, otherSlotIds = [] }: MealCardProps) {
  const [swapping, setSwapping] = useState(false);
  const [showRecipe, setShowRecipe] = useState(false);
  const [showVibeInput, setShowVibeInput] = useState(false);
  const [vibeInput, setVibeInput] = useState("");
  const [seenIds, setSeenIds] = useState<string[]>(item.recipe_id ? [item.recipe_id] : []);
  const swapsUsed = seenIds.length - 1;
  const swapsLeft = MAX_SWAPS - swapsUsed;

  async function handleSwap(vibe?: string) {
    setSwapping(true);
    setShowVibeInput(false);
    try {
      const allExcluded = Array.from(new Set([...seenIds, ...otherSlotIds]));
      const newItem = await swapMeal(item.slot, allExcluded, vibe);
      if (newItem.recipe_id) setSeenIds((prev) => [...prev, newItem.recipe_id]);
      onSwap(item.slot, newItem);
      setVibeInput("");
    } catch (e) {
      console.error("Swap failed", e);
    } finally {
      setSwapping(false);
    }
  }

  function handleSwapClick(e: React.MouseEvent) {
    e.stopPropagation();
    setShowVibeInput((v) => !v);
  }

  return (
    <>
      <div className="flex flex-col">
        <div
          className="bg-white rounded-2xl p-4 shadow-sm border border-gray-50 cursor-pointer active:scale-[0.99] transition-transform"
          onClick={() => item.recipe_id && setShowRecipe(true)}
        >
          <div className="flex justify-between items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-[#2d6b2d] uppercase tracking-wider mb-0.5">{item.slot}</p>
              <p className="text-gray-900 font-semibold text-sm leading-snug">{item.recipe_name}</p>
              <p className="text-xs text-gray-400 mt-0.5 italic truncate">{item.reason}</p>
            </div>
            <div className="flex gap-2 items-center flex-shrink-0">
              {swapsLeft > 0 ? (
                <button
                  onClick={handleSwapClick}
                  disabled={swapping}
                  title={`${swapsLeft} swap${swapsLeft !== 1 ? "s" : ""} left`}
                  className={`disabled:opacity-40 text-xs w-7 h-7 rounded-full border flex items-center justify-center transition-colors ${showVibeInput ? "border-[#2d6b2d] text-[#2d6b2d]" : "border-gray-200 text-gray-400 hover:text-gray-700 hover:border-gray-400"}`}
                >
                  {swapping ? "·" : "↻"}
                </button>
              ) : (
                <span className="text-gray-300 text-xs w-7 text-center">↻</span>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); onLog(item); }}
                className="bg-[#2d6b2d] hover:bg-[#245824] text-white text-xs px-3 py-1.5 rounded-full transition-colors font-medium"
              >
                Log
              </button>
            </div>
          </div>

          <div className="flex gap-3 mt-3 text-xs text-gray-500">
            <span className="font-medium text-gray-700">{item.calories} kcal</span>
            <span>{item.protein_g}g protein</span>
            <span>{item.carbs_g}g carbs</span>
            <span>{item.fat_g}g fat</span>
          </div>

          {item.recipe_id && (
            <p className="text-xs text-gray-300 mt-2">Tap to view recipe →</p>
          )}
        </div>

        {/* Per-meal vibe input */}
        {showVibeInput && (
          <div
            className="bg-gray-50 border border-gray-100 rounded-b-2xl -mt-2 pt-4 pb-3 px-4 flex gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              autoFocus
              className="flex-1 bg-white text-gray-900 rounded-xl px-3 py-2 text-sm placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#2d6b2d]/30 border border-gray-100"
              placeholder={`Something specific for ${item.slot}? (optional)`}
              value={vibeInput}
              onChange={(e) => setVibeInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSwap(vibeInput.trim() || undefined)}
            />
            <button
              onClick={() => handleSwap(vibeInput.trim() || undefined)}
              className="bg-[#2d6b2d] hover:bg-[#245824] text-white px-3 py-2 rounded-xl text-sm font-semibold transition-colors"
            >
              ↻
            </button>
          </div>
        )}
      </div>

      {showRecipe && item.recipe_id && (
        <RecipeModal recipeId={item.recipe_id} onClose={() => setShowRecipe(false)} />
      )}
    </>
  );
}
