-- 1. Add nutrition and metadata fields to recipes
alter table recipes
  add column if not exists description text,
  add column if not exists category text,
  add column if not exists keywords text[],

  add column if not exists prep_time text,
  add column if not exists cook_time text,
  add column if not exists total_time text,

  add column if not exists servings numeric,
  add column if not exists recipe_yield text,

  add column if not exists calories numeric,
  add column if not exists fat_g numeric,
  add column if not exists saturated_fat_g numeric,
  add column if not exists cholesterol_mg numeric,
  add column if not exists sodium_mg numeric,
  add column if not exists carbohydrate_g numeric,
  add column if not exists fiber_g numeric,
  add column if not exists sugar_g numeric,
  add column if not exists protein_g numeric;

-- 2. Rename raw_text to quantity on the join table
-- (now that ingredient quantity and name are separate fields in the source dataset)
alter table recipe_ingredients
  rename column raw_text to quantity;

-- 3. Remove count columns
ALTER TABLE recipes
DROP COLUMN IF EXISTS num_ingredients,
DROP COLUMN IF EXISTS num_steps,
DROP COLUMN IF EXISTS char_count;

-- Unique constraint on title - prevent duplicate insert
ALTER TABLE recipes ADD CONSTRAINT recipes_title_key UNIQUE (title);