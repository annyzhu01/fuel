import pytest
from unittest.mock import patch, MagicMock, call
from load_data import (
    map_recipe_foodcom,
    map_recipe_shengtao,
    extract_ingredients_foodcom,
    extract_ingredients_shengtao,
    upsert_recipe,
    upsert_ingredients,
    insert_recipe_batch,
)


# --- map_recipe_foodcom ---

class TestMapRecipeFoodcom:
    def test_maps_all_fields(self):
        row = {
            "Name": "Chicken Soup",
            "Description": "A warm soup.",
            "RecipeCategory": "main-dish",
            "Keywords": "['warm', 'soup']",
            "RecipeInstructions": "['Boil water', 'Add chicken']",
            "PrepTime": "PT10M",
            "CookTime": "PT30M",
            "TotalTime": "PT40M",
            "RecipeServings": "4",
            "RecipeYield": "4 servings",
            "Calories": "250",
            "FatContent": "8.5",
            "SaturatedFatContent": "2.0",
            "CholesterolContent": "55",
            "SodiumContent": "600",
            "CarbohydrateContent": "20",
            "FiberContent": "3",
            "SugarContent": "5",
            "ProteinContent": "25",
        }
        result = map_recipe_foodcom(row)
        assert result["title"] == "Chicken Soup"
        assert result["description"] == "A warm soup."
        assert result["category"] == "main-dish"
        assert result["keywords"] == ["warm", "soup"]
        assert result["steps"] == ["Boil water", "Add chicken"]
        assert result["calories"] == 250.0
        assert result["protein_g"] == 25.0
        assert result["fat_g"] == 8.5
        assert result["servings"] == 4.0

    def test_boilerplate_description_cleaned(self):
        row = {
            "Name": "Pasta",
            "Description": "Make and share this Pasta recipe from Food.com.",
            "RecipeCategory": None,
            "Keywords": "[]",
            "RecipeInstructions": "[]",
            "PrepTime": None,
            "CookTime": None,
            "TotalTime": None,
            "RecipeServings": None,
            "RecipeYield": None,
            "Calories": None,
            "FatContent": None,
            "SaturatedFatContent": None,
            "CholesterolContent": None,
            "SodiumContent": None,
            "CarbohydrateContent": None,
            "FiberContent": None,
            "SugarContent": None,
            "ProteinContent": None,
        }
        result = map_recipe_foodcom(row)
        assert result["description"] is None
        assert result["calories"] is None


# --- map_recipe_shengtao ---

class TestMapRecipeShengtao:
    def test_maps_all_fields(self):
        row = {
            "title": "Veggie Stir Fry",
            "description": "Quick veggie dish",
            "category": "main-dish",
            "instructions_list": "['Chop veggies', 'Stir fry']",
            "prep_time": "PT5M",
            "cook_time": "PT10M",
            "total_time": "PT15M",
            "servings": "2",
            "yields": "2 servings",
            "calories": "180",
            "fat_g": "6",
            "saturated_fat_g": "1",
            "cholesterol_mg": "0",
            "sodium_mg": "300",
            "carbohydrates_g": "22",
            "dietary_fiber_g": "4",
            "sugars_g": "8",
            "protein_g": "10",
        }
        result = map_recipe_shengtao(row)
        assert result["title"] == "Veggie Stir Fry"
        assert result["description"] == "Quick veggie dish"
        assert result["calories"] == 180.0
        assert result["protein_g"] == 10.0
        assert result["keywords"] == []

    def test_missing_optional_fields(self):
        row = {"title": "Salad"}
        result = map_recipe_shengtao(row)
        assert result["title"] == "Salad"
        assert result["description"] is None
        assert result["calories"] is None
        assert result["steps"] == []


# --- extract_ingredients_foodcom ---

class TestExtractIngredientsFoodcom:
    def test_basic_extraction(self):
        row = {
            "RecipeIngredientParts": "['chicken', 'salt', 'pepper']",
            "RecipeIngredientQuantities": "['500g', '1 tsp', '0.5 tsp']",
        }
        result = extract_ingredients_foodcom(row)
        assert len(result) == 3
        assert result[0] == ("chicken", "500g")
        assert result[1] == ("salt", "1 tsp")

    def test_more_names_than_quantities(self):
        row = {
            "RecipeIngredientParts": "['chicken', 'salt', 'pepper']",
            "RecipeIngredientQuantities": "['500g']",
        }
        result = extract_ingredients_foodcom(row)
        assert len(result) == 3
        assert result[0] == ("chicken", "500g")
        assert result[1] == ("salt", None)
        assert result[2] == ("pepper", None)

    def test_empty_name_skipped(self):
        row = {
            "RecipeIngredientParts": "['chicken', '', 'pepper']",
            "RecipeIngredientQuantities": "['500g', '1 tsp', '0.5 tsp']",
        }
        result = extract_ingredients_foodcom(row)
        assert len(result) == 2


# --- extract_ingredients_shengtao ---

class TestExtractIngredientsShengtao:
    def test_semicolon_separated(self):
        row = {"ingredients": "chicken breast; garlic; soy sauce"}
        result = extract_ingredients_shengtao(row)
        assert len(result) == 3
        assert result[0] == ("chicken breast", None)
        assert result[1] == ("garlic", None)

    def test_empty_ingredients(self):
        row = {"ingredients": ""}
        result = extract_ingredients_shengtao(row)
        assert result == []

    def test_none_ingredients(self):
        row = {"ingredients": None}
        result = extract_ingredients_shengtao(row)
        assert result == []

    def test_missing_key(self):
        row = {}
        result = extract_ingredients_shengtao(row)
        assert result == []


# --- upsert_recipe ---

class TestUpsertRecipe:
    def test_returns_recipe_id(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "abc-123"}]
        result = upsert_recipe(mock_sb, {"title": "Test"})
        assert result == "abc-123"
        mock_sb.table.assert_called_with("recipes")


# --- upsert_ingredients ---

class TestUpsertIngredients:
    def test_inserts_ingredient_and_links(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "ing-1"}]
        upsert_ingredients(mock_sb, "recipe-1", [("chicken", "500g")])
        assert mock_sb.table.call_count >= 2


# --- insert_recipe_batch ---

class TestInsertRecipeBatch:
    def test_skips_missing_title(self):
        mock_sb = MagicMock()
        records = [{"Name": ""}]

        def map_fn(r):
            return {"title": r["Name"]}

        def extract_fn(r):
            return []

        insert_recipe_batch(mock_sb, records, map_fn, extract_fn)
        mock_sb.table.return_value.upsert.assert_not_called()

    def test_inserts_valid_records(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "r1"}]
        records = [{"Name": "Soup"}]

        def map_fn(r):
            return {"title": r["Name"]}

        def extract_fn(r):
            return [("salt", "1 tsp")]

        insert_recipe_batch(mock_sb, records, map_fn, extract_fn)
        mock_sb.table.assert_called()

    def test_handles_exception_gracefully(self, capsys):
        mock_sb = MagicMock()
        mock_sb.table.return_value.upsert.return_value.execute.side_effect = Exception("DB error")
        records = [{"Name": "Soup"}]

        def map_fn(r):
            return {"title": r["Name"]}

        def extract_fn(r):
            return []

        insert_recipe_batch(mock_sb, records, map_fn, extract_fn)
        captured = capsys.readouterr()
        assert "Skipped" in captured.out
