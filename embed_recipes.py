import logging
from utils import get_supabase_client, is_real_description
from sentence_transformers import SentenceTransformer
from recipe_utils import get_ingredient_names

logger = logging.getLogger(__name__)

def build_embedding_text(recipe: dict, ingredient_names: list[str]) -> str:
    parts = []

    if recipe.get("title"):
        parts.append(recipe["title"])
        parts.append(recipe["title"])

    if is_real_description(recipe.get("description")):
        parts.append(recipe["description"])

    if ingredient_names:
        parts.append("Ingredients: " + ", ".join(ingredient_names))

    if recipe.get("category"):
        parts.append("Category: " + recipe["category"])

    if recipe.get("keywords"):
        parts.append("Keywords: " + ", ".join(recipe["keywords"]))

    return ". ".join(parts)


def embed_recipes(batch_size: int = 50):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    supabase = get_supabase_client()
    total_embedded = 0
    errors = 0
    while True:
        unembedded_data = (
            supabase.table("recipes")
            .select("id, title, description, category, keywords")
            .is_("embedding", "null")
            .range(0, batch_size - 1)
            .execute()
        )
        if not unembedded_data.data:
            break
        for recipe in unembedded_data.data:
            try:
                ingredients = get_ingredient_names(supabase, recipe['id'])
                embedding_text = build_embedding_text(recipe, ingredients)
                vector = model.encode(embedding_text).tolist()
                supabase.table("recipes").update({"embedding": vector}).eq("id", recipe["id"]).execute()
                total_embedded += 1
            except Exception as e:
                errors += 1
                logger.error("Failed to embed recipe %s (%s): %s", recipe['id'], recipe.get('title'), e)
    if errors:
        logger.warning("Embedding complete: %d succeeded, %d failed", total_embedded, errors)
    else:
        logger.info("Embedding complete: %d recipes embedded", total_embedded)
    return total_embedded, errors

if __name__ == "__main__":
    embed_recipes(1000)
