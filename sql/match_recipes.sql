drop function if exists match_recipes(vector,integer,double precision,double precision,double precision,double precision,double precision,double precision,double precision,double precision);
drop function if exists match_recipes(vector,integer,double precision,double precision,double precision,double precision,double precision,double precision,double precision,double precision,text);

create or replace function match_recipes(
    query_embedding vector(384),
    match_count int default 5,
    min_calories float default null,
    max_calories float default null,
    min_protein float default null,
    max_protein float default null,
    min_carbs float default null,
    max_carbs float default null,
    min_fat float default null,
    max_fat float default null,
    filter_category text default null
)
returns table (
    id uuid,
    title text,
    similarity float,
    description text,
    category text,
    calories numeric,
    protein_g numeric,
    fat_g numeric,
    carbohydrate_g numeric,
    fiber_g numeric
)
language sql stable as $$
select
    recipes.id,
    recipes.title,
    1 - (recipes.embedding <=> query_embedding) as similarity,
    recipes.description,
    recipes.category,
    recipes.calories,
    recipes.protein_g,
    recipes.fat_g,
    recipes.carbohydrate_g,
    recipes.fiber_g
from recipes
where recipes.embedding is not null
    and (min_calories is null or recipes.calories >= min_calories)
    and (max_calories is null or recipes.calories <= max_calories)
    and (min_protein  is null or recipes.protein_g >= min_protein)
    and (max_protein  is null or recipes.protein_g <= max_protein)
    and (min_carbs    is null or recipes.carbohydrate_g >= min_carbs)
    and (max_carbs    is null or recipes.carbohydrate_g <= max_carbs)
    and (min_fat      is null or recipes.fat_g >= min_fat)
    and (max_fat      is null or recipes.fat_g <= max_fat)
    and (filter_category is null or recipes.category = filter_category)
order by recipes.embedding <=> query_embedding
limit match_count;
$$;
