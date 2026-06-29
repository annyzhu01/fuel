import logging
import sys
import json
import re
import os
import anthropic
import pdfplumber

from utils import get_supabase_client, parse_float
from load_data import upsert_ingredients
from embed_recipes import embed_recipes

logger = logging.getLogger(__name__)

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


def _parse_json_response(text: str) -> list[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("Could not parse JSON", text, 0)


class ChunkExtractionError(Exception):
    pass


def extract_recipes_from_chunk(
    client: anthropic.Anthropic, chunk_text: str, chunk_index: int = 0
) -> list[dict]:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=_EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": _EXTRACT_USER_TMPL.format(chunk_text=chunk_text)}],
        )
        return _parse_json_response(response.content[0].text)
    except anthropic.APIError as e:
        logger.error("Claude API error on chunk %d: %s", chunk_index, e)
        raise ChunkExtractionError(f"API error on chunk {chunk_index}") from e
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from chunk %d", chunk_index)
        raise ChunkExtractionError(f"Invalid JSON from chunk {chunk_index}") from e


def extract_recipes_from_chunks(
    client: anthropic.Anthropic, chunks: list[str]
) -> tuple[list[dict], int]:
    all_recipes = []
    total = len(chunks)
    chunk_errors = 0
    for i, chunk in enumerate(chunks):
        try:
            recipes = extract_recipes_from_chunk(client, chunk, chunk_index=i + 1)
            logger.info("Chunk %d/%d: found %d recipes", i + 1, total, len(recipes))
            all_recipes.extend(recipes)
        except ChunkExtractionError:
            chunk_errors += 1
            logger.warning("Skipping chunk %d/%d due to extraction error", i + 1, total)
    return all_recipes, chunk_errors


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


def insert_pdf_recipes(supabase, recipes: list[dict], source_filename: str) -> tuple[int, int, int]:
    inserted = 0
    skipped = 0
    errors = 0
    for raw in recipes:
        mapped = map_recipe_pdf(raw, source_filename)
        if not mapped.get("title"):
            logger.warning("Skipped recipe with no title from %s", source_filename)
            skipped += 1
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
            logger.info("Inserted: %s, recipe ID: %s", mapped['title'], recipe_id)
            inserted += 1
        except Exception as e:
            errors += 1
            logger.error("Failed to insert recipe %r from %s: %s", mapped.get('title'), source_filename, e)
    return inserted, skipped, errors


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    pdf_paths = sys.argv[1:]
    if not pdf_paths:
        print("Usage: python ingest_pdf.py cookbook.pdf [another.pdf ...]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    supabase = get_supabase_client()

    total_inserted = 0
    total_skipped = 0
    total_errors = 0
    total_chunk_errors = 0
    files_failed = []

    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        logger.info("Processing %s", filename)
        try:
            chunks = extract_text_chunks(pdf_path)
            logger.info("%d chunk(s) from %s", len(chunks), filename)
            recipes, chunk_errors = extract_recipes_from_chunks(client, chunks)
            total_chunk_errors += chunk_errors
            if not recipes:
                logger.warning("No recipes extracted from %s", filename)
                continue
            ins, skp, errs = insert_pdf_recipes(supabase, recipes, filename)
            total_inserted += ins
            total_skipped += skp
            total_errors += errs
        except FileNotFoundError:
            logger.error("File not found: %s", pdf_path)
            files_failed.append(pdf_path)
        except Exception as e:
            logger.error("Failed to process %s: %s", pdf_path, e)
            files_failed.append(pdf_path)

    logger.info("Embedding new recipes...")
    embed_recipes()

    logger.info(
        "Done. %d inserted, %d skipped, %d insert errors, %d chunk errors from %d file(s).",
        total_inserted, total_skipped, total_errors, total_chunk_errors, len(pdf_paths),
    )
    if files_failed:
        logger.error("Failed files: %s", ", ".join(files_failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
