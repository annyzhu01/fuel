import sys
import os
import pdfplumber

from utils import get_supabase_client, get_anthropic_client, parse_float
from load_data import upsert_ingredients
from embed_recipes import embed_recipes
from recipe_utils import parse_json_response

_EXTRACT_SYSTEM = (
    "You are a recipe data extractor. Given text from a cookbook PDF, extract every complete recipe "
    "you can identify. Return ONLY a valid JSON array — no prose, no markdown fences, no explanation. "
    "If no recipes are found, return []."
)

_EXTRACT_USER_TMPL = """\
Extract all recipes from the following cookbook text. For each recipe return a JSON object with exactly these fields:

- title: string (required)
- description: string or null
- steps: array of strings (each step as one element)
- ingredients: array of objects, each with "name" (string) and "quantity" (string or null)
- category: string or null (e.g. "main-dish", "dessert", "side-dish", "breakfast")
- keywords: array of strings or []
- servings: number or null
- calories: number or null
- protein_g: number or null
- fat_g: number or null
- carbohydrate_g: number or null

For macros: if the recipe does not state nutrition info, estimate realistic values based on the ingredients and typical serving size. Do not leave all four macro fields as null — provide estimates when you have enough ingredient information.

TEXT:
{chunk_text}"""


def extract_text_chunks(
    pdf_path: str,
    max_pages_before_chunk: int = 40,
    pages_per_chunk: int = 10,
    overlap: int = 2,
) -> list[str]:
    """
    Small PDFs (≤ max_pages_before_chunk pages): one chunk = whole PDF.
    Large PDFs: sliding window with overlap to avoid splitting recipes across boundaries.
    """
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    if len(pages) <= max_pages_before_chunk:
        return ["\n\n".join(pages)]

    chunks = []
    step = pages_per_chunk - overlap
    for i in range(0, len(pages), step):
        chunk_pages = pages[i: i + pages_per_chunk]
        if chunk_pages:
            chunks.append("\n\n".join(chunk_pages))
    return chunks


def extract_recipes_from_chunk(
    client, chunk_text: str, chunk_index: int = 0
) -> list[dict]:
    import json
    import anthropic
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=_EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": _EXTRACT_USER_TMPL.format(chunk_text=chunk_text)}],
        )
        return parse_json_response(response.content[0].text)
    except anthropic.APIError as e:
        print(f"WARNING: Claude API error on chunk {chunk_index}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"WARNING: could not parse JSON from chunk {chunk_index}, skipping")
        return []


def extract_recipes_from_chunks(
    client, chunks: list[str]
) -> list[dict]:
    all_recipes = []
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        recipes = extract_recipes_from_chunk(client, chunk, chunk_index=i + 1)
        print(f"Chunk {i + 1}/{total}: found {len(recipes)} recipes")
        all_recipes.extend(recipes)
    return all_recipes


def map_recipe_pdf(raw: dict, source_filename: str) -> dict:
    return {
        "title": raw.get("title"),
        "description": raw.get("description"),
        "steps": raw.get("steps") or [],
        "category": raw.get("category"),
        "keywords": raw.get("keywords") or [],
        "servings": parse_float(raw.get("servings")),
        "calories": parse_float(raw.get("calories")),
        "fat_g": parse_float(raw.get("fat_g")),
        "carbohydrate_g": parse_float(raw.get("carbohydrate_g")),
        "protein_g": parse_float(raw.get("protein_g")),
        "source_url": f"pdf:{source_filename}",
    }


def insert_recipe_pdf(supabase, recipe_dict: dict) -> str | None:
    try:
        result = supabase.table("recipes").insert(recipe_dict).execute()
        return result.data[0]["id"]
    except Exception as e:
        msg = str(e)
        if "23505" in msg or "duplicate" in msg.lower():
            return None
        raise


def insert_pdf_recipes(supabase, recipes: list[dict], source_filename: str) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for raw in recipes:
        mapped = map_recipe_pdf(raw, source_filename)
        if not mapped.get("title"):
            print("Skipped recipe with no title")
            continue
        try:
            recipe_id = insert_recipe_pdf(supabase, mapped)
            if recipe_id is None:
                skipped += 1
                continue
            ingredient_pairs = [
                (ing["name"], ing.get("quantity"))
                for ing in (raw.get("ingredients") or [])
                if ing.get("name")
            ]
            upsert_ingredients(supabase, recipe_id, ingredient_pairs)
            print(f"Inserted: {mapped['title']}, recipe ID: {recipe_id}")
            inserted += 1
        except Exception as e:
            print(f"ERROR inserting {mapped.get('title')!r}: {e}")
    return inserted, skipped


def main():
    pdf_paths = sys.argv[1:]
    if not pdf_paths:
        print("Usage: python ingest_pdf.py cookbook.pdf [another.pdf ...]")
        sys.exit(1)

    client = get_anthropic_client()
    supabase = get_supabase_client()

    total_inserted = 0
    total_skipped = 0

    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        print(f"\n--- Processing {filename} ---")
        try:
            chunks = extract_text_chunks(pdf_path)
            print(f"{len(chunks)} chunk(s) from {filename}")
            recipes = extract_recipes_from_chunks(client, chunks)
            if not recipes:
                print(f"WARNING: no recipes extracted from {filename}")
                continue
            ins, skp = insert_pdf_recipes(supabase, recipes, filename)
            total_inserted += ins
            total_skipped += skp
        except FileNotFoundError:
            print(f"ERROR: file not found: {pdf_path}")
        except Exception as e:
            print(f"ERROR: could not process {pdf_path}: {e}")

    print(f"\nEmbedding new recipes...")
    embed_recipes()
    print(f"\nDone. {total_inserted} inserted, {total_skipped} skipped from {len(pdf_paths)} file(s).")


if __name__ == "__main__":
    main()
