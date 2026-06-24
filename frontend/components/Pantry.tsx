"use client";

import { useEffect, useState } from "react";
import { getPantry, addToPantry, removeFromPantry } from "@/lib/api";

export function Pantry() {
  const [items, setItems] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);
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
    <div className="bg-gray-900 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex justify-between items-center px-4 py-3 text-white font-semibold text-sm"
      >
        <span>Pantry ({items.length})</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 flex flex-col gap-2">
          {items.length === 0 && (
            <p className="text-gray-500 text-xs">No items yet. Add what you have at home.</p>
          )}
          {items.map((item) => (
            <div key={item} className="flex justify-between items-center">
              <span className="text-gray-300 text-sm">{item}</span>
              <button
                onClick={() => handleRemove(item)}
                className="text-gray-500 hover:text-red-400 text-xs transition-colors"
              >
                ✕
              </button>
            </div>
          ))}
          <div className="flex gap-2 mt-1">
            <input
              className="flex-1 bg-gray-700 text-white rounded-lg px-3 py-1.5 text-sm placeholder-gray-400 outline-none focus:ring-1 focus:ring-green-500"
              placeholder="Add ingredient..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <button
              onClick={handleAdd}
              disabled={loading || !input.trim()}
              className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-sm transition-colors"
            >
              +
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
