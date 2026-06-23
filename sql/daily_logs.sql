-- Per-user daily calorie/macro targets (one row per user per day)
create table if not exists daily_targets (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  date date not null default current_date,
  base_calories numeric not null,
  goal_protein_g numeric not null,
  goal_carbs_g numeric not null,
  goal_fat_g numeric not null,
  unique (user_id, date)
);

-- Workout entries logged today
create table if not exists workout_logs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  date date not null default current_date,
  exercise_type text not null,
  duration_minutes numeric,
  calories_burned numeric not null,
  created_at timestamptz default now()
);

-- Meals logged today
create table if not exists food_logs (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  date date not null default current_date,
  meal_slot text not null,
  description text not null,
  calories numeric not null,
  protein_g numeric not null,
  carbs_g numeric not null,
  fat_g numeric not null,
  created_at timestamptz default now()
);
