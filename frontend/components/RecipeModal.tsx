"use client";

import { useEffect, useState } from "react";
import { getRecipe, RecipeDetail } from "@/lib/api";

interface RecipeModalProps {
  recipeId: string;
  onClose: () => void;
}

export function RecipeModal({ recipeId, onClose }: RecipeModalProps) {
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecipe(recipeId)
      .then(setRecipe)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [recipeId]);

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-end justify-center"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-t-3xl w-full max-w-md max-h-[88vh] overflow-y-auto flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle bar */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-gray-200" />
        </div>

        <div className="px-5 pb-8 flex flex-col gap-4">
          <div className="flex justify-between items-start pt-2">
            <h2 className="text-gray-900 font-bold text-lg pr-4 leading-snug">
              {loading ? "Loading..." : recipe?.title}
            </h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none w-7 h-7 flex items-center justify-center">✕</button>
          </div>

          {!loading && recipe && (
            <>
              {recipe.description && (
                <p className="text-gray-500 text-sm">{recipe.description}</p>
              )}

              {/* Macros */}
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: "kcal", value: recipe.calories?.toFixed(0) },
                  { label: "protein", value: `${recipe.protein_g?.toFixed(0)}g` },
                  { label: "carbs", value: `${recipe.carbohydrate_g?.toFixed(0)}g` },
                  { label: "fat", value: `${recipe.fat_g?.toFixed(0)}g` },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-gray-50 rounded-xl p-2.5 text-center">
                    <p className="text-sm font-semibold text-gray-900">{value}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>

              {(recipe.prep_time || recipe.cook_time) && (
                <div className="flex gap-4 text-xs text-gray-400">
                  {recipe.prep_time && <span>Prep: {recipe.prep_time.replace("PT", "").toLowerCase()}</span>}
                  {recipe.cook_time && <span>Cook: {recipe.cook_time.replace("PT", "").toLowerCase()}</span>}
                </div>
              )}

              {/* Ingredients */}
              {recipe.ingredients?.length > 0 && (
                <div className="flex flex-col gap-2">
                  <h3 className="text-gray-900 font-semibold text-sm">Ingredients</h3>
                  <div className="bg-gray-50 rounded-xl p-3 flex flex-col gap-1.5">
                    {recipe.ingredients.map((ing, i) => (
                      <div key={i} className="flex gap-2 text-sm text-gray-700">
                        <span className="text-[#2d6b2d] font-bold">·</span>
                        <span>{ing}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Healthy tips */}
              {recipe.healthy_tip && (
                <div className="flex flex-col gap-2">
                  {recipe.healthy_tip.split("\n\n").filter(Boolean).map((tip, i) => (
                    <div key={i} className="bg-[#e8f0e8] rounded-xl px-4 py-3 flex gap-2 items-start">
                      <span className="text-[#2d6b2d] text-base leading-none mt-0.5">💡</span>
                      <p className="text-[#2d6b2d] text-sm">{tip.trim()}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Steps */}
              {recipe.steps?.length > 0 && (
                <div className="flex flex-col gap-3">
                  <h3 className="text-gray-900 font-semibold text-sm">Steps</h3>
                  {recipe.steps.map((step, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="text-[#2d6b2d] font-bold text-sm min-w-[1.25rem]">{i + 1}.</span>
                      <p className="text-gray-600 text-sm leading-relaxed">{step}</p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
