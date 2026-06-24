# Agentic Planner + User Pantry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user pantry (ingredients at home) and replace the one-shot meal planner with an agentic Claude loop that iteratively searches 3000+ recipes, biasing toward pantry items.

**Architecture:** Pantry is stored in Supabase and injected into the agentic planner's system prompt as a preference signal. The agentic planner gives Claude two tools — `search_recipes` and `submit_plan` — and loops until Claude calls `submit_plan` or the 3-search budget is exhausted. The existing one-shot planner is untouched; the API toggles between them via `?agentic=true`.

**Tech Stack:** Python 3.11, FastAPI, Supabase (pgvector), sentence-transformers (all-MiniLM-L6-v2), Anthropic claude-haiku-4-5, Next.js 14, Tailwind CSS

## Global Constraints

- Embedding model: `all-MiniLM-L6-v2` (vector dim 384) — do not change
- Anthropic model: `claude-haiku-4-5` — do not upgrade without user approval
- Max search calls per agentic plan: 3
- Pantry is preference only — never a hard filter
- `daily_plan.py` must not be modified — agentic logic lives in `daily_plan_agentic.py`
- User ID: `"mvp-user"` (hardcoded, no auth in MVP)
- All Python source files live at repo root `/Users/annyzhu/Projects/JobRAG/`
- All tests live in `/Users/annyzhu/Projects/JobRAG/tests/`
- Frontend lives in `/Users/annyzhu/Projects/JobRAG/frontend/`

---

## File Map

**New backend files:**
- `daily_plan_agentic.py` — agentic loop with tool use
- `pantry.py` — pantry DB helpers

**Modified backend files:**
- `api.py` — add `/pantry` endpoints + `?agentic=true` toggle on `/daily-plan`

**New SQL:**
- `sql/user_pantry.sql` — `user_pantry` table

**New frontend files:**
- `frontend/components/Pantry.tsx` — collapsible pantry UI

**Modified frontend files:**
- `frontend/app/page.tsx` — embed Pantry component
- `frontend/lib/api.ts` — add pantry API functions + agentic flag

**New test files:**
- `tests/test_pantry.py`
- `tests/test_daily_plan_agentic.py`

---

## Task 1: Pantry DB table

**Files:**
- Create: `sql/user_pantry.sql`

**Interfaces:**
- Produces: `user_pantry` table in Supabase with columns `(id, user_id, ingredient_name, created_at)` and unique constraint on `(user_id, ingredient_name)`

- [ ] **Step 1: Write the SQL**

Create `sql/user_pantry.sql`:

```sql
create table if not exists user_pantry (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  ingredient_name text not null,
  created_at timestamptz default now(),
  unique (user_id, ingredient_name)
);

create index if not exists user_pantry_user_id_idx on user_pantry (user_id);
```

- [ ] **Step 2: Run in Supabase**

Go to Supabase dashboard → SQL Editor → paste `sql/user_pantry.sql` → Run.

Verify: table `user_pantry` appears in Table Editor with columns `id`, `user_id`, `ingredient_name`, `created_at`.

- [ ] **Step 3: Seed some pantry items for testing**

Run in Supabase SQL Editor:

```sql
insert into user_pantry (user_id, ingredient_name) values
  ('mvp-user', 'chicken breast'),
  ('mvp-user', 'eggs'),
  ('mvp-user', 'oats'),
  ('mvp-user', 'greek yoghurt')
on conflict do nothing;
```

- [ ] **Step 4: Commit**

```bash
git add sql/user_pantry.sql
git commit -m "feat: user_pantry table"
```

---

## Task 2: Pantry backend helpers + API endpoints

**Files:**
- Create: `pantry.py`
- Modify: `api.py`

**Interfaces:**
- Consumes: `get_supabase_client()` from `utils.py`
- Produces:
  - `get_pantry(user_id: str) -> list[str]`
  - `add_to_pantry(user_id: str, ingredient_name: str) -> list[str]`
  - `remove_from_pantry(user_id: str, ingredient_name: str) -> list[str]`
  - `GET /pantry` → `{"items": ["chicken breast", "eggs"]}`
  - `POST /pantry` body `{"ingredient": "salmon"}` → `{"added": "salmon", "items": [...]}`
  - `DELETE /pantry/{ingredient}` → `{"removed": "salmon", "items": [...]}`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pantry.py`:

```python
from unittest.mock import patch, MagicMock
import pytest


def make_mock_sb(rows):
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = rows
    mock.table.return_value.insert.return_value.execute.return_value.data = []
    mock.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    return mock


@patch("pantry.get_supabase_client")
def test_get_pantry_returns_names(mock_sb):
    mock_sb.return_value = make_mock_sb([
        {"ingredient_name": "chicken breast"},
        {"ingredient_name": "eggs"},
    ])
    from pantry import get_pantry
    result = get_pantry("mvp-user")
    assert result == ["chicken breast", "eggs"]


@patch("pantry.get_supabase_client")
def test_get_pantry_empty(mock_sb):
    mock_sb.return_value = make_mock_sb([])
    from pantry import get_pantry
    result = get_pantry("mvp-user")
    assert result == []
```

- [ ] **Step 2: Run to verify failure**

```bash
source venv/bin/activate && python -m pytest tests/test_pantry.py -v
```

Expected: `ModuleNotFoundError: No module named 'pantry'`

- [ ] **Step 3: Write pantry.py**

Create `pantry.py`:

```python
from utils import get_supabase_client


def _fetch(user_id: str) -> list[str]:
    sb = get_supabase_client()
    rows = (
        sb.table("user_pantry")
        .select("ingredient_name")
        .eq("user_id", user_id)
        .order("ingredient_name")
        .execute()
    )
    return [r["ingredient_name"] for r in rows.data]


def get_pantry(user_id: str) -> list[str]:
    return _fetch(user_id)


def add_to_pantry(user_id: str, ingredient_name: str) -> list[str]:
    name = ingredient_name.strip().lower()
    sb = get_supabase_client()
    sb.table("user_pantry").insert(
        {"user_id": user_id, "ingredient_name": name}
    ).execute()
    return _fetch(user_id)


def remove_from_pantry(user_id: str, ingredient_name: str) -> list[str]:
    name = ingredient_name.strip().lower()
    sb = get_supabase_client()
    sb.table("user_pantry").delete().eq("user_id", user_id).eq("ingredient_name", name).execute()
    return _fetch(user_id)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_pantry.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Add endpoints to api.py**

Add after the existing imports in `api.py`:

```python
from pantry import get_pantry, add_to_pantry, remove_from_pantry
```

Add after the existing `log_meal` endpoint:

```python
class PantryAdd(BaseModel):
    ingredient: str


@app.get("/pantry")
def pantry_get():
    return {"items": get_pantry(USER_ID)}


@app.post("/pantry")
def pantry_add(body: PantryAdd):
    if not body.ingredient.strip():
        raise HTTPException(400, "ingredient must not be empty")
    items = add_to_pantry(USER_ID, body.ingredient)
    return {"added": body.ingredient.strip().lower(), "items": items}


@app.delete("/pantry/{ingredient}")
def pantry_remove(ingredient: str):
    items = remove_from_pantry(USER_ID, ingredient)
    return {"removed": ingredient.lower(), "items": items}
```

- [ ] **Step 6: Smoke-test endpoints**

Start the backend: `uvicorn api:app --reload --port 8000`

```bash
curl http://localhost:8000/pantry
# Expected: {"items": ["chicken breast", "eggs", "greek yoghurt", "oats"]}

curl -X POST http://localhost:8000/pantry \
  -H "Content-Type: application/json" \
  -d '{"ingredient": "salmon"}'
# Expected: {"added": "salmon", "items": [..., "salmon"]}

curl -X DELETE http://localhost:8000/pantry/salmon
# Expected: {"removed": "salmon", "items": [...]}
```

- [ ] **Step 7: Commit**

```bash
git add pantry.py tests/test_pantry.py api.py
git commit -m "feat: pantry helpers and GET/POST/DELETE /pantry endpoints"
```

---

## Task 3: Agentic meal planner

**Files:**
- Create: `daily_plan_agentic.py`
- Modify: `api.py` — add `?agentic=true` to `/daily-plan`

**Interfaces:**
- Consumes:
  - `query_recipes(query, match_count, max_calories, min_protein)` from `query_recipes.py`
  - `get_daily_budget(user_id, date)` from `daily_plan.py`
  - `get_pantry(user_id)` from `pantry.py`
- Produces:
  - `build_daily_plan_agentic(user_id: str, date: str, preferences: list[str]) -> dict`
  - Returns same shape as `build_daily_plan`: `{budget, plan, total_planned, protein_gap, protein_warning, coach_note}`

- [ ] **Step 1: Write failing tests**

Create `tests/test_daily_plan_agentic.py`:

```python
from unittest.mock import patch, MagicMock
import json


def _make_submit_response(plan_items):
    """Simulate Claude calling submit_plan."""
    tool_use = MagicMock()
    tool_use.type = "tool_use"
    tool_use.name = "submit_plan"
    tool_use.id = "tool_123"
    tool_use.input = {
        "plan": plan_items,
        "total_planned": {"calories": 500, "protein_g": 42, "carbs_g": 50, "fat_g": 15},
        "protein_gap": 0,
        "protein_warning": None,
        "coach_note": "Good plan."
    }
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [tool_use]
    return response


@patch("daily_plan_agentic.get_pantry", return_value=["chicken breast", "eggs"])
@patch("daily_plan_agentic.get_daily_budget")
@patch("daily_plan_agentic._get_claude")
def test_agentic_plan_returns_on_submit(mock_claude, mock_budget, mock_pantry):
    mock_budget.return_value = {
        "target": {"base_calories": 1800, "goal_protein_g": 160, "goal_carbs_g": 200, "goal_fat_g": 60},
        "workout_burn": 0,
        "remaining": {
            "remaining_calories": 500,
            "remaining_protein_g": 42,
            "remaining_carbs_g": 50,
            "remaining_fat_g": 15,
            "slots_needed": ["dinner"],
        },
    }
    plan_item = {"slot": "dinner", "recipe_id": "abc", "recipe_name": "Chicken Rice",
                 "calories": 500, "protein_g": 42, "carbs_g": 50, "fat_g": 15, "reason": "high protein"}
    mock_claude.return_value.messages.create.return_value = _make_submit_response([plan_item])

    from daily_plan_agentic import build_daily_plan_agentic
    result = build_daily_plan_agentic("mvp-user", "2026-06-24", [])

    assert "plan" in result
    assert len(result["plan"]) == 1
    assert result["plan"][0]["recipe_name"] == "Chicken Rice"
    assert result["protein_gap"] == 0


@patch("daily_plan_agentic.get_pantry", return_value=[])
@patch("daily_plan_agentic.get_daily_budget")
def test_agentic_all_slots_logged(mock_budget, mock_pantry):
    mock_budget.return_value = {
        "target": {"base_calories": 1800, "goal_protein_g": 160, "goal_carbs_g": 200, "goal_fat_g": 60},
        "workout_burn": 0,
        "remaining": {
            "remaining_calories": 0,
            "remaining_protein_g": 0,
            "remaining_carbs_g": 0,
            "remaining_fat_g": 0,
            "slots_needed": [],
        },
    }
    from daily_plan_agentic import build_daily_plan_agentic
    result = build_daily_plan_agentic("mvp-user", "2026-06-24", [])
    assert result["plan"] == []
    assert "message" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_daily_plan_agentic.py -v
```

Expected: `ModuleNotFoundError: No module named 'daily_plan_agentic'`

- [ ] **Step 3: Write daily_plan_agentic.py**

Create `daily_plan_agentic.py`:

```python
import os
import anthropic
from daily_plan import get_daily_budget
from pantry import get_pantry
from query_recipes import query_recipes

MAX_SEARCH_CALLS = 3

_claude = None


def _get_claude():
    global _claude
    if _claude is None:
        _claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _claude


_TOOLS = [
    {
        "name": "search_recipes",
        "description": (
            "Search the recipe database by natural language query with optional macro filters. "
            "Prefer recipes that use the user's pantry ingredients. "
            "For the snack slot: do NOT call this tool — call submit_plan directly with a no-cook snack."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language e.g. 'high protein chicken lunch'"},
                "slot": {"type": "string", "description": "Which meal slot: breakfast, lunch, dinner"},
                "max_calories": {"type": "number"},
                "min_protein": {"type": "number"},
            },
            "required": ["query", "slot"],
        },
    },
    {
        "name": "submit_plan",
        "description": "Submit the final meal plan. Call when all slots are filled or search budget is exhausted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "slot": {"type": "string"},
                            "recipe_id": {"type": ["string", "null"]},
                            "recipe_name": {"type": "string"},
                            "calories": {"type": "number"},
                            "protein_g": {"type": "number"},
                            "carbs_g": {"type": "number"},
                            "fat_g": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["slot", "recipe_name", "calories", "protein_g", "carbs_g", "fat_g", "reason"],
                    },
                },
                "total_planned": {
                    "type": "object",
                    "properties": {
                        "calories": {"type": "number"},
                        "protein_g": {"type": "number"},
                        "carbs_g": {"type": "number"},
                        "fat_g": {"type": "number"},
                    },
                },
                "protein_gap": {"type": "number", "description": "How many grams of protein short of target. 0 if on target."},
                "protein_warning": {"type": ["string", "null"], "description": "Actionable fix if protein_gap > 10g, else null."},
                "coach_note": {"type": "string"},
            },
            "required": ["plan", "total_planned", "protein_gap", "coach_note"],
        },
    },
]


def _build_system_prompt(remaining: dict, pantry: list[str], preferences: list[str]) -> str:
    pantry_str = ", ".join(pantry) if pantry else "nothing specified"
    pref_str = ", ".join(preferences) if preferences else "none"
    slots = ", ".join(remaining["slots_needed"])

    return f"""You are a sports nutritionist building a meal plan for someone doing body recomposition (cut + strength, 65kg).

NUTRITION RULES:
- Protein is priority #1. Target: 150-200g/day. Never sacrifice protein for calories.
- Do NOT eat back calories from weight training. Cardio: eat back 50% only if burn > 300 kcal.
- Distribute protein: ~26g minimum per meal.
- Training days: favour higher carbs. Rest days: lower carbs, higher fat.
- Snack slot: use your own knowledge — quick no-cook options only (Greek yoghurt, cottage cheese, boiled eggs, protein shake, rice cakes + nut butter). Set recipe_id to null.

USER CONTEXT:
- Pantry (ingredients at home): {pantry_str}. PREFER recipes using these ingredients.
- Preferences: {pref_str}

REMAINING MACRO TARGETS FOR TODAY:
- Calories: {remaining['remaining_calories']:.0f} kcal
- Protein: {remaining['remaining_protein_g']:.0f}g
- Carbs: {remaining['remaining_carbs_g']:.0f}g
- Fat: {remaining['remaining_fat_g']:.0f}g

SLOTS NEEDED: {slots}
SEARCH BUDGET: {MAX_SEARCH_CALLS} search_recipes calls total across all slots. Use them wisely.

STRATEGY:
1. Search for each non-snack slot. Prefer pantry ingredients in your query.
2. If results are unsatisfying (protein too low, calories over budget), refine and search again — but remember your search budget.
3. For snack: call submit_plan directly with a no-cook suggestion from your knowledge.
4. Call submit_plan when all slots are filled or budget is exhausted.
5. protein_gap = target_protein - total_planned_protein (0 if on target or over).
6. protein_warning = null if gap <= 10g, otherwise a short actionable tip."""


def build_daily_plan_agentic(user_id: str, date: str, preferences: list[str] = None) -> dict:
    budget = get_daily_budget(user_id, date)
    remaining = budget["remaining"]

    if not remaining["slots_needed"]:
        return {"message": "All meals logged for today.", "plan": [], "budget": budget}

    pantry = get_pantry(user_id)
    system_prompt = _build_system_prompt(remaining, pantry, preferences or [])

    messages = [{"role": "user", "content": "Build the meal plan now."}]
    search_count = 0
    claude = _get_claude()

    while True:
        response = claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            system=system_prompt,
            tools=_TOOLS,
            messages=messages,
        )

        # Append assistant response to message history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Claude stopped without calling submit_plan — force it
            messages.append({
                "role": "user",
                "content": "You must call submit_plan now with whatever plan you have.",
            })
            continue

        # Process tool calls
        tool_results = []
        should_submit = False

        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "search_recipes":
                search_count += 1
                kwargs = {k: v for k, v in block.input.items() if k != "slot"}
                results = query_recipes(match_count=5, **kwargs)

                result_text = f"Results for '{block.input['query']}' ({block.input['slot']}):\n"
                if not results:
                    result_text += "No results found."
                else:
                    for r in results:
                        result_text += (
                            f"- [{r['id']}] {r['title']}: "
                            f"{r.get('calories') or '?'} kcal, "
                            f"{r.get('protein_g') or '?'}g protein, "
                            f"{r.get('carbohydrate_g') or '?'}g carbs, "
                            f"{r.get('fat_g') or '?'}g fat\n"
                        )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

                if search_count >= MAX_SEARCH_CALLS:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id + "_budget",
                        "content": f"Search budget exhausted ({MAX_SEARCH_CALLS}/{MAX_SEARCH_CALLS}). Call submit_plan now.",
                    })
                    should_submit = True

            elif block.name == "submit_plan":
                return {"budget": budget, **block.input}

        messages.append({"role": "user", "content": tool_results})

        if should_submit:
            messages.append({
                "role": "user",
                "content": "Search budget exhausted. You MUST call submit_plan now.",
            })
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_daily_plan_agentic.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Add ?agentic=true to /daily-plan in api.py**

In `api.py`, add import at top:

```python
from daily_plan_agentic import build_daily_plan_agentic
```

Replace the existing `/daily-plan` endpoint:

```python
@app.get("/daily-plan")
def daily_plan(preferences: str = "", agentic: bool = False):
    prefs = [p.strip() for p in preferences.split(",") if p.strip()]
    if agentic:
        return build_daily_plan_agentic(USER_ID, str(date.today()), prefs)
    return build_daily_plan(USER_ID, str(date.today()), prefs)
```

- [ ] **Step 6: Smoke-test agentic planner**

Start backend: `uvicorn api:app --reload --port 8000`

```bash
curl "http://localhost:8000/daily-plan?agentic=true"
```

Expected: JSON with `plan` array, `coach_note`, `protein_gap`. Watch terminal — you'll see multiple Claude tool calls logged.

- [ ] **Step 7: Commit**

```bash
git add daily_plan_agentic.py tests/test_daily_plan_agentic.py api.py
git commit -m "feat: agentic meal planner with tool use loop and 3-search budget"
```

---

## Task 4: Pantry frontend component

**Files:**
- Create: `frontend/components/Pantry.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `GET /pantry`, `POST /pantry`, `DELETE /pantry/{ingredient}` from FastAPI
- Produces: `<Pantry />` component — self-contained, manages own fetch state

- [ ] **Step 1: Add pantry API functions to lib/api.ts**

Append to `frontend/lib/api.ts`:

```typescript
export async function getPantry(): Promise<string[]> {
  const res = await fetch(`${BASE}/pantry`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch pantry");
  const data = await res.json();
  return data.items;
}

export async function addToPantry(ingredient: string): Promise<string[]> {
  const res = await fetch(`${BASE}/pantry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredient }),
  });
  if (!res.ok) throw new Error("Failed to add to pantry");
  const data = await res.json();
  return data.items;
}

export async function removeFromPantry(ingredient: string): Promise<string[]> {
  const res = await fetch(`${BASE}/pantry/${encodeURIComponent(ingredient)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to remove from pantry");
  const data = await res.json();
  return data.items;
}
```

- [ ] **Step 2: Write Pantry.tsx**

Create `frontend/components/Pantry.tsx`:

```tsx
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
```

- [ ] **Step 3: Add Pantry to page.tsx**

In `frontend/app/page.tsx`, add import at top:

```tsx
import { Pantry } from "@/components/Pantry";
```

Add `<Pantry />` after the meal suggestions section (before closing `</main>`):

```tsx
      <Pantry />
    </main>
```

- [ ] **Step 4: Test in browser**

Start both servers:

```bash
# Terminal 1
source venv/bin/activate && uvicorn api:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open `http://localhost:3000`. Verify:
- "Pantry (4)" collapsed section appears at bottom
- Expand it → see chicken breast, eggs, greek yoghurt, oats
- Type "salmon" + Enter → appears in list
- Click ✕ next to salmon → removed
- Refresh page → pantry items persist (fetched from DB)

- [ ] **Step 5: Commit**

```bash
git add frontend/components/Pantry.tsx frontend/lib/api.ts frontend/app/page.tsx
git commit -m "feat: pantry UI component with add/remove and collapsible panel"
```

---

## Self-Review

**Spec coverage:**
- ✅ `user_pantry` table with unique constraint — Task 1
- ✅ `GET /pantry`, `POST /pantry`, `DELETE /pantry/{ingredient}` — Task 2
- ✅ Pantry as preference (injected into system prompt, not hard filter) — Task 3
- ✅ Agentic loop with `search_recipes` + `submit_plan` tools — Task 3
- ✅ Max 3 search calls enforced — Task 3
- ✅ `?agentic=true` toggle — Task 3
- ✅ Snack slot bypasses search (Claude knowledge) — Task 3 system prompt
- ✅ Pantry UI component, collapsible — Task 4
- ✅ Existing `daily_plan.py` untouched — confirmed, not in file map

**Placeholder scan:** None found.

**Type consistency:**
- `get_pantry(user_id: str) -> list[str]` — defined Task 2, consumed Task 3 ✅
- `build_daily_plan_agentic(user_id, date, preferences)` — defined Task 3, wired in Task 3 step 5 ✅
- `getPantry()`, `addToPantry()`, `removeFromPantry()` — defined Task 4 step 1, used in `Pantry.tsx` Task 4 step 2 ✅
- Response shape `{budget, plan, total_planned, protein_gap, protein_warning, coach_note}` — matches existing `DailyPlan` interface in `lib/api.ts` ✅
