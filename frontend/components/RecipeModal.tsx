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
      className="fixed inset-0 bg-black/70 z-50 flex items-end justify-center"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-t-2xl w-full max-w-md max-h-[85vh] overflow-y-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start">
          <h2 className="text-white font-bold text-lg pr-4">
            {loading ? "Loading..." : recipe?.title}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">✕</button>
        </div>

        {!loading && recipe && (
          <>
            {recipe.description && (
              <p className="text-gray-400 text-sm">{recipe.description}</p>
            )}

            <div className="flex gap-4 text-xs text-gray-300 bg-gray-800 rounded-xl p-3">
              <span>{recipe.calories?.toFixed(0)} kcal</span>
              <span>{recipe.protein_g?.toFixed(0)}g protein</span>
              <span>{recipe.carbohydrate_g?.toFixed(0)}g carbs</span>
              <span>{recipe.fat_g?.toFixed(0)}g fat</span>
            </div>

            {(recipe.prep_time || recipe.cook_time) && (
              <div className="flex gap-4 text-xs text-gray-400">
                {recipe.prep_time && <span>Prep: {recipe.prep_time.replace("PT", "").toLowerCase()}</span>}
                {recipe.cook_time && <span>Cook: {recipe.cook_time.replace("PT", "").toLowerCase()}</span>}
              </div>
            )}

            {recipe.steps?.length > 0 && (
              <div className="flex flex-col gap-2">
                <h3 className="text-white font-semibold text-sm">Steps</h3>
                {recipe.steps.map((step, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-green-400 font-bold text-sm min-w-[1.25rem]">{i + 1}.</span>
                    <p className="text-gray-300 text-sm">{step}</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
