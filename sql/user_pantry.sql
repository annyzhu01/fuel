create table if not exists user_pantry (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  ingredient_name text not null,
  created_at timestamptz default now(),
  unique (user_id, ingredient_name)
);
create index if not exists user_pantry_user_id_idx on user_pantry (user_id);
