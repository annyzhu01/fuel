-- Enable pgvector extension (safe to run even if already enabled)
create extension if not exists vector;

-- Recipes table (this is what gets embedded + retrieved)
create table if not exists recipes (
  id uuid primary key default gen_random_uuid(),

  title text not null,
  steps text[] not null,                -- list of step strings

  num_ingredients int,
  num_steps int,
  char_count int,

  source_url text,
  tags text,                            -- e.g. NER-extracted food items, comma-separated

  embedding vector(384),                -- adjust dimension to match your embedding model

  created_at timestamptz default now()
);

-- Ingredients table (one row per unique ingredient, e.g. "garlic", "olive oil")
create table if not exists ingredients (
  id uuid primary key default gen_random_uuid(),
  name text not null unique
);

-- Join table: links recipes to ingredients, many-to-many
-- also stores the raw ingredient line from the source recipe (e.g. "2 cloves garlic, minced")
-- since that's different from the canonical ingredient name
create table if not exists recipe_ingredients (
  id uuid primary key default gen_random_uuid(),
  recipe_id uuid not null references recipes(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete cascade,
  raw_text text,                        -- original line, e.g. "1/2 c. evaporated milk"

  unique (recipe_id, ingredient_id)
);

-- Indexes
create index if not exists recipes_embedding_idx
  on recipes
  using hnsw (embedding vector_cosine_ops);

create index if not exists recipe_ingredients_recipe_id_idx
  on recipe_ingredients (recipe_id);

create index if not exists recipe_ingredients_ingredient_id_idx
  on recipe_ingredients (ingredient_id);