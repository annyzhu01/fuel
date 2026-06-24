# Agentic Planner + User Pantry Design

**Date:** 2026-06-24
**Status:** Approved

## Goal

Replace the one-shot meal planner with an agentic loop that iteratively searches the recipe database, and add a user pantry so Claude biases suggestions toward ingredients already at home.

## Architecture

Two independent features that compose at the planner level:

```
Pantry (Supabase) ──→ injected into system prompt
                              ↓
User request → Agentic loop (Claude + tools) → plan JSON
                    ↑
              search_recipes() → Supabase vector search
```

## Pantry

### Data model

New Supabase table:
```sql
create table user_pantry (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  ingredient_name text not null,
  created_at timestamptz default now(),
  unique (user_id, ingredient_name)
);
```

### API endpoints

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/pantry` | — | `{items: ["chicken breast", "oats", ...]}` |
| POST | `/pantry` | `{ingredient: "eggs"}` | `{added: "eggs", items: [...]}` |
| DELETE | `/pantry/{ingredient}` | — | `{removed: "eggs", items: [...]}` |

### Behaviour

- Pantry is preference, not filter. Claude gets `"User has at home: chicken breast, oats, eggs"` in its system prompt and biases toward those ingredients naturally.
- No quantity tracking in v1.
- Ingredient names are free text, lowercased on insert.

## Agentic Planner

### File

`daily_plan_agentic.py` — new file alongside `daily_plan.py`. Existing one-shot planner stays untouched.

### API toggle

`GET /daily-plan?agentic=true` uses the agentic planner. Default (`agentic=false`) uses existing one-shot. Allows A/B comparison.

### Tools

**`search_recipes`**
```json
{
  "name": "search_recipes",
  "description": "Search the recipe database. Prefer recipes using the user's pantry ingredients where possible.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Natural language search e.g. 'high protein chicken lunch'"},
      "max_calories": {"type": "number"},
      "min_protein": {"type": "number"},
      "slot": {"type": "string", "description": "Which meal slot this is for: breakfast, lunch, dinner, snack"}
    },
    "required": ["query", "slot"]
  }
}
```

**`submit_plan`**
```json
{
  "name": "submit_plan",
  "description": "Submit the final meal plan. Call this when satisfied with all slots or when you've exhausted your search budget.",
  "input_schema": {
    "type": "object",
    "properties": {
      "plan": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "slot": {"type": "string"},
            "recipe_id": {"type": "string"},
            "recipe_name": {"type": "string"},
            "calories": {"type": "number"},
            "protein_g": {"type": "number"},
            "carbs_g": {"type": "number"},
            "fat_g": {"type": "number"},
            "reason": {"type": "string"}
          }
        }
      },
      "total_planned": {"type": "object"},
      "protein_gap": {"type": "number"},
      "protein_warning": {"type": ["string", "null"]},
      "coach_note": {"type": "string"}
    },
    "required": ["plan", "total_planned", "protein_gap", "coach_note"]
  }
}
```

### Loop logic

```
max_search_calls = 3
search_count = 0

loop:
  response = claude.messages.create(tools=[search_recipes, submit_plan], messages=messages)
  
  if stop_reason == "tool_use":
    for tool_call in response:
      if tool_call.name == "search_recipes":
        search_count += 1
        results = query_recipes(**tool_call.input)
        append tool_result to messages
        
        if search_count >= max_search_calls:
          # inject budget warning
          append "Search budget exhausted. Call submit_plan now." to messages
      
      elif tool_call.name == "submit_plan":
        return tool_call.input  # done
  
  elif stop_reason == "end_turn":
    raise ValueError("Claude ended without submitting plan")
```

### System prompt additions for agentic mode

The system prompt includes:
1. All existing nutrition rules (from `daily_plan.py`)
2. Pantry: `"User has at home: {pantry_items}. Prefer recipes using these ingredients."`
3. Strategy: `"Search one slot at a time. If first result is unsatisfying, refine the query. You have {max_search_calls} searches total across all slots."`
4. Snack rule: `"For the snack slot, call submit_plan directly with a no-cook snack from your knowledge (Greek yoghurt, cottage cheese, eggs, protein shake). Do not waste a search call on snacks."`

## Frontend

### Pantry UI

Collapsible section on the Today screen, below meal suggestions:

```
[Pantry ▾]
  chicken breast  ✕
  oats            ✕
  eggs            ✕
  [add ingredient...] [+]
```

- Collapsed by default, expands on tap
- Text input + add button
- ✕ removes item, calls DELETE /pantry/{ingredient}
- On load, GET /pantry populates the list

### New component

`frontend/components/Pantry.tsx` — self-contained, manages its own fetch state.

## What stays unchanged

- `daily_plan.py` — one-shot planner untouched
- `query_recipes.py` — agentic planner calls it directly
- All existing tests
- DB schema for recipes, daily_targets, workout_logs, food_logs
