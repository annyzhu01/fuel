import logging
from utils import get_supabase_client, parse_float, parse_list, clean_description

logger = logging.getLogger(__name__)


# --- mappers: raw dataset row -> DB dict ---

def map_recipe_foodcom(recipe):
    return {
        "title": recipe['Name'],
        "description": clean_description(recipe['Description']),
        "category": recipe['RecipeCategory'],
        "keywords": parse_list(recipe['Keywords']),
        "steps": parse_list(recipe['RecipeInstructions']),
        "prep_time": recipe['PrepTime'],
        "cook_time": recipe['CookTime'],
        "total_time": recipe['TotalTime'],
        "servings": parse_float(recipe['RecipeServings']),
        "recipe_yield": recipe['RecipeYield'],
        "calories": parse_float(recipe['Calories']),
        "fat_g": parse_float(recipe['FatContent']),
        "saturated_fat_g": parse_float(recipe['SaturatedFatContent']),
        "cholesterol_mg": parse_float(recipe['CholesterolContent']),
        "sodium_mg": parse_float(recipe['SodiumContent']),
        "carbohydrate_g": parse_float(recipe['CarbohydrateContent']),
        "fiber_g": parse_float(recipe['FiberContent']),
        "sugar_g": parse_float(recipe['SugarContent']),
        "protein_g": parse_float(recipe['ProteinContent']),
    }


def map_recipe_shengtao(recipe):
    return {
        "title": recipe['title'],
        "description": clean_description(recipe.get('description')),
        "category": recipe.get('category'),
        "keywords": [],
        "steps": parse_list(recipe.get('instructions_list') or []),
        "prep_time": recipe.get('prep_time'),
        "cook_time": recipe.get('cook_time'),
        "total_time": recipe.get('total_time'),
        "servings": parse_float(recipe.get('servings')),
        "recipe_yield": recipe.get('yields'),
        "calories": parse_float(recipe.get('calories')),
        "fat_g": parse_float(recipe.get('fat_g')),
        "saturated_fat_g": parse_float(recipe.get('saturated_fat_g')),
        "cholesterol_mg": parse_float(recipe.get('cholesterol_mg')),
        "sodium_mg": parse_float(recipe.get('sodium_mg')),
        "carbohydrate_g": parse_float(recipe.get('carbohydrates_g')),
        "fiber_g": parse_float(recipe.get('dietary_fiber_g')),
        "sugar_g": parse_float(recipe.get('sugars_g')),
        "protein_g": parse_float(recipe.get('protein_g')),
    }


# --- ingredient extractors: raw row -> [(name, quantity|None)] ---

def extract_ingredients_foodcom(recipe):
    names = parse_list(recipe['RecipeIngredientParts'])
    quantities = parse_list(recipe['RecipeIngredientQuantities'])
    result = []
    for i, name in enumerate(names):
        name = name.strip()
        if name:
            qty = quantities[i] if i < len(quantities) else None
            result.append((name, str(qty) if qty else None))
    return result


def extract_ingredients_shengtao(recipe):
    raw = recipe.get('ingredients') or ''
    return [(p.strip(), None) for p in raw.split(';') if p.strip()]


# --- DB operations ---

def upsert_recipe(supabase, recipe_dict):
    result = supabase.table("recipes").upsert(recipe_dict, on_conflict="title").execute()
    return result.data[0]['id']


def upsert_ingredients(supabase, recipe_id, ingredients):
    for name, quantity in ingredients:
        row = supabase.table("ingredients").upsert({"name": name}, on_conflict="name").execute()
        ingredient_id = row.data[0]['id']
        supabase.table("recipe_ingredients").upsert({
            "recipe_id": recipe_id,
            "ingredient_id": ingredient_id,
            "quantity": quantity,
        }, on_conflict="recipe_id,ingredient_id").execute()


# --- generic batch loader ---

def insert_recipe_batch(supabase, records, map_fn, extract_ingredients_fn):
    inserted = 0
    errors = 0
    for i, record in enumerate(records):
        mapped = map_fn(record)
        if not mapped.get('title'):
            logger.warning("Skipped record %d: missing title", i)
            continue
        try:
            recipe_id = upsert_recipe(supabase, mapped)
            upsert_ingredients(supabase, recipe_id, extract_ingredients_fn(record))
            inserted += 1
        except Exception as e:
            errors += 1
            logger.error("Failed to insert record %d (%s): %s", i, mapped.get('title'), e)
    logger.info("Batch complete: %d inserted, %d failed out of %d records", inserted, errors, len(records))
    if errors:
        logger.warning("%d records failed during batch insert", errors)
    return inserted, errors


# --- dataset loaders ---

def insert_recipes_foodcom(max_recipes, offset=0):
    from datasets import load_dataset
    records = load_dataset("AkashPS11/recipes_data_food.com")['train'].select(range(offset, offset + max_recipes))
    insert_recipe_batch(get_supabase_client(), records, map_recipe_foodcom, extract_ingredients_foodcom)


def insert_recipes_shengtao(max_recipes, offset=0):
    from datasets import load_dataset
    records = load_dataset("Shengtao/recipe")['train'].select(range(offset, offset + max_recipes))
    insert_recipe_batch(get_supabase_client(), records, map_recipe_shengtao, extract_ingredients_shengtao)
