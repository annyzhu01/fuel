"use client";

import { useEffect, useState } from "react";
import { getPantry, addToPantry, removeFromPantry } from "@/lib/api";

export function Pantry() {
  const [items, setItems] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getPantry().then(setItems).catch(console.error);
  }, []);

  async function handleAdd() {
    const val = input.trim();
    if (!val) return;
    setLoading(true);
    try {
      const updated = await addToPantry(val);
      setItems(updated);
      setInput("");
    } finally {
      setLoading(false);
    }
  }

  async function handleRemove(ingredient: string) {
    const updated = await removeFromPantry(ingredient);
    setItems(updated);
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Add input */}
      <div className="flex gap-2">
        <input
          className="flex-1 bg-white text-gray-900 rounded-xl px-4 py-2.5 text-sm placeholder-gray-400 outline-none focus:ring-2 focus:ring-[#2d6b2d]/30 border border-gray-100 shadow-sm"
          placeholder="Add ingredient..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
        />
        <button
          onClick={handleAdd}
          disabled={loading || !input.trim()}
          className="bg-[#2d6b2d] hover:bg-[#245824] disabled:opacity-40 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors shadow-sm"
        >
          + Add
        </button>
      </div>

      {/* Items */}
      {items.length === 0 ? (
        <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
          <p className="text-gray-400 text-sm">No items yet.</p>
          <p className="text-gray-300 text-xs mt-1">Add what you have at home to get better meal suggestions.</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          {items.map((item, i) => (
            <div
              key={item}
              className={`flex justify-between items-center px-4 py-3 ${i < items.length - 1 ? "border-b border-gray-50" : ""}`}
            >
              <span className="text-gray-800 text-sm">{item}</span>
              <button
                onClick={() => handleRemove(item)}
                className="text-gray-300 hover:text-red-400 text-sm transition-colors w-6 h-6 flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
