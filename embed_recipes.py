from utils import get_supabase_client, is_real_description
from sentence_transformers import SentenceTransformer

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


def get_ingredient_names_for_recipe(supabase, recipe_id: str) -> list[str]:
    result = (
        supabase.table("recipe_ingredients")
        .select("ingredients(name)")
        .eq("recipe_id", recipe_id)
        .execute()
    )
    return [row["ingredients"]["name"] for row in result.data if row.get("ingredients")]

def embed_recipes(batch_size: int = 50):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    supabase = get_supabase_client()
    total_embedded = 0
    while True:
        unembedded_data = (
            supabase.table("recipes")
            .select("id, title, description, category, keywords")
            .is_("embedding", "null")
            .range(0, batch_size - 1)
            .execute()
        )
        if not unembedded_data.data:
            print(f"No unembedded recipes")
            break
        for recipe in unembedded_data.data:
            ingredients = get_ingredient_names_for_recipe(supabase, recipe['id'])
            embedding_text = build_embedding_text(recipe, ingredients)
            vector = model.encode(embedding_text).tolist()
            supabase.table("recipes").update({"embedding": vector}).eq("id", recipe["id"]).execute()
            total_embedded += 1
            print(f"Embedded {total_embedded}: {recipe['title']}")

if __name__ == "__main__":
    embed_recipes(1000)
    
    
        
        