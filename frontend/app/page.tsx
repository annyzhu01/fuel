"use client";

import { useEffect, useState } from "react";
import {
  getBudget,
  getDailyPlan,
  logWorkout,
  logMeal,
  Budget,
  DailyPlan,
  PlanItem,
} from "@/lib/api";
import { MacroRing } from "@/components/MacroRing";
import { MealCard } from "@/components/MealCard";
import { Pantry } from "@/components/Pantry";

type Tab = "today" | "pantry";

export default function TodayPage() {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("today");

  const [showWorkout, setShowWorkout] = useState(false);
  const [exercise, setExercise] = useState("");
  const [duration, setDuration] = useState("");
  const [logging, setLogging] = useState(false);


  async function refresh() {
    const b = await getBudget();
    setBudget(b);
  }

  async function refreshPlan() {
    setPlanLoading(true);
    try {
      const p = await getDailyPlan();
      setPlan(p);
    } catch (e) {
      console.error("Plan fetch failed", e);
    } finally {
      setPlanLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        await refresh();
        await refreshPlan();
      } catch {
        setError("Cannot reach API. Is the backend running on port 8000?");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  async function handleLogWorkout() {
    if (!exercise || !duration) return;
    setLogging(true);
    try {
      await logWorkout(exercise, parseFloat(duration));
      setShowWorkout(false);
      setExercise("");
      setDuration("");
      await refresh();
      await refreshPlan();
    } finally {
      setLogging(false);
    }
  }

  function handleSwap(slot: string, newItem: PlanItem) {
    setPlan((prev) => {
      if (!prev) return prev;
      return { ...prev, plan: prev.plan.map((p) => (p.slot === slot ? newItem : p)) };
    });
  }

  async function handleLogMeal(item: PlanItem) {
    await logMeal({
      meal_slot: item.slot,
      description: item.recipe_name,
      calories: item.calories,
      protein_g: item.protein_g,
      carbs_g: item.carbs_g,
      fat_g: item.fat_g,
    });
    await refresh();
    await refreshPlan();
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400 bg-[#f5f5f0]">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-500 text-sm px-8 text-center bg-[#f5f5f0]">
        {error}
      </div>
    );
  }

  const r = budget?.remaining;
  const t = budget?.target;
  const totalCal = (t?.base_calories ?? 0) + (budget?.workout_burn ?? 0);
  const consumedCal = totalCal - (r?.remaining_calories ?? totalCal);
  const consumedProtein = (t?.goal_protein_g ?? 0) - (r?.remaining_protein_g ?? 0);
  const consumedCarbs = (t?.goal_carbs_g ?? 0) - (r?.remaining_carbs_g ?? 0);
  const consumedFat = (t?.goal_fat_g ?? 0) - (r?.remaining_fat_g ?? 0);

  return (
    <div className="min-h-screen bg-[#f5f5f0] flex flex-col">
      <main className="flex-1 max-w-md mx-auto w-full px-4 pb-28 flex flex-col gap-5">

        {/* Header */}
        <div className="pt-12 pb-1">
          <p className="text-gray-500 text-sm">Good morning 👋</p>
          <h1 className="text-2xl font-bold text-gray-900">Fuel</h1>
        </div>

        {tab === "today" && (
          <>
            {/* Macro card */}
            {r && t && (
              <div className="bg-white rounded-2xl p-5 shadow-sm">
                <MacroRing
                  caloriesConsumed={consumedCal}
                  caloriesTotal={totalCal}
                  protein={{ consumed: consumedProtein, total: t.goal_protein_g }}
                  carbs={{ consumed: consumedCarbs, total: t.goal_carbs_g }}
                  fat={{ consumed: consumedFat, total: t.goal_fat_g }}
                />
                {(budget?.workout_burn ?? 0) > 0 && (
                  <p className="text-xs text-[#2d6b2d] font-medium mt-3">
                    +{budget!.workout_burn} kcal from workout added to budget
                  </p>
                )}
              </div>
            )}

            {/* Log Workout */}
            <button
              onClick={() => setShowWorkout(!showWorkout)}
              className="w-full bg-white hover:bg-gray-50 text-gray-800 rounded-2xl py-3 font-semibold shadow-sm border border-gray-100 transition-colors text-sm"
            >
              {showWorkout ? "Cancel" : "+ Log Workout"}
            </button>

            {showWorkout && (
              <div className="bg-white rounded-2xl p-4 shadow-sm flex flex-col gap-3">
                <input
                  className="bg-gray-50 text-gray-900 rounded-xl px-3 py-2.5 text-sm placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#2d6b2d]/30 border border-gray-100"
                  placeholder="Exercise type (e.g. run, weights, legs)"
                  value={exercise}
                  onChange={(e) => setExercise(e.target.value)}
                />
                <input
                  className="bg-gray-50 text-gray-900 rounded-xl px-3 py-2.5 text-sm placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#2d6b2d]/30 border border-gray-100"
                  placeholder="Duration (minutes)"
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                />
                <button
                  onClick={handleLogWorkout}
                  disabled={logging || !exercise || !duration}
                  className="bg-[#2d6b2d] hover:bg-[#245824] disabled:opacity-40 text-white rounded-xl py-2.5 font-semibold text-sm transition-colors"
                >
                  {logging ? "Saving..." : "Log Workout"}
                </button>
              </div>
            )}

            {/* Warnings / Coach */}
            {plan?.protein_warning && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 flex gap-2 items-start">
                <span className="text-amber-500 text-lg leading-none">⚠</span>
                <p className="text-amber-700 text-sm">{plan.protein_warning}</p>
              </div>
            )}

            {plan?.coach_note && (
              <div className="bg-[#e8f0e8] rounded-2xl px-4 py-3 flex gap-2 items-start">
                <span className="text-[#2d6b2d] text-lg leading-none">💬</span>
                <p className="text-[#2d6b2d] text-sm font-medium">{plan.coach_note}</p>
              </div>
            )}

            {/* Meal Plan */}
            <div className="flex flex-col gap-3">
              <h2 className="text-base font-bold text-gray-900">Today's Plan</h2>

              {planLoading ? (
                <p className="text-gray-400 text-sm">Updating suggestions...</p>
              ) : plan?.plan?.length ? (
                plan.plan.map((item, i) => (
                  <MealCard
                    key={i}
                    item={item}
                    onLog={handleLogMeal}
                    onSwap={handleSwap}
                    otherSlotIds={plan.plan
                      .filter((p) => p.slot !== item.slot && p.recipe_id)
                      .map((p) => p.recipe_id)}
                  />
                ))
              ) : (
                <p className="text-gray-400 text-sm">All meals logged for today.</p>
              )}
            </div>
          </>
        )}

        {tab === "pantry" && (
          <div className="pt-2">
            <h2 className="text-base font-bold text-gray-900 mb-4">Pantry</h2>
            <Pantry />
          </div>
        )}
      </main>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 shadow-lg z-40">
        <div className="max-w-md mx-auto flex items-center justify-around px-8 py-3">
          <button
            onClick={() => setTab("today")}
            className={`flex flex-col items-center gap-1 transition-colors ${tab === "today" ? "text-[#2d6b2d]" : "text-gray-400"}`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span className="text-xs font-medium">Today</span>
          </button>

          <button
            onClick={() => setTab("pantry")}
            className={`flex flex-col items-center gap-1 transition-colors ${tab === "pantry" ? "text-[#2d6b2d]" : "text-gray-400"}`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <span className="text-xs font-medium">Pantry</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
